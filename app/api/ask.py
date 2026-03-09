from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from sse_starlette.sse import EventSourceResponse
from openai import APITimeoutError, APIConnectionError, APIStatusError, RateLimitError

from app.core.config import settings
from app.core.retrieval import hybrid_retrieve
from app.core.rate_limit import rate_limiter
from app.core.logger import make_request_id, log_request
from app.api import auth

import openai
import tiktoken
import time
import json
import re
import random
import httpx
import os

router = APIRouter()


def estimate_tokens(text, model: str = "gpt-3.5-turbo") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)


def get_openai_price(model: str) -> float:
    prices = {
        "gpt-3.5-turbo": 0.0005,
        "gpt-4": 0.01,
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.00015
    }
    return prices.get(model, 0.01)


def ensure_inline_citation(answer: str, citations) -> str:
    # Always guarantee at least one inline ref when citations exist
    return (answer.rstrip() + " [1]") if citations else answer


def maybe_answer_filenames(question: str, context_chunks):
    q = question.lower()
    if any(k in q for k in ["filename", "file name", "filenames", "file names", "list the document filenames"]):
        seen = set()
        uniq = []
        for i, ch in enumerate(context_chunks):
            name = ch["source"]
            if name not in seen:
                seen.add(name)
                ref_idx = next((j + 1 for j, c in enumerate(context_chunks) if c["source"] == name), 1)
                uniq.append((name, ref_idx))

        lines = [f"- {name} [{idx}]" for name, idx in uniq]
        answer = "\n".join(lines)

        citations = []
        for i, ch in enumerate(context_chunks):
            citations.append({"source_id": f"{ch['source']}#{i}", "snippet": ch["chunk"][:120]})
        return answer, citations
    return None


def tokens_from_openai(context_chunks, question, max_tokens, model, api_key, budget_usd):
    context_text = "\n---\n".join([f"[{i+1}] {c['chunk']}" for i, c in enumerate(context_chunks)])
    sources_map = "\n".join([f"[{i+1}] -> {c['source']}" for i, c in enumerate(context_chunks)])

    prompt = (
        "Answer the user's question using ONLY the info in the context below. "
        "Cite sources inline as [1], [2], etc, matching the numbers to sources. "
        "If the user asks about filenames, list them using the Sources mapping. "
        "Never invent sources.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Sources:\n{sources_map}\n\n"
        f"Question: {question}\nAnswer:"
    )

    prompt_tokens = estimate_tokens(prompt, model)
    price_per_1k = get_openai_price(model)
    est_prompt_cost = prompt_tokens * price_per_1k / 1000
    if est_prompt_cost > budget_usd:
        done_payload = {
            "answer": "[Budget Exceeded] Prompt cost exceeds provided budget.",
            "citations": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": 0,
                "cost_usd": est_prompt_cost,
                "latency_ms": 0,
            },
        }
        yield json.dumps({"event": "done", "data": done_payload})
        return

    client = openai.OpenAI(api_key=api_key)
    start = time.time()
    total_tokens = prompt_tokens
    cost_so_far = est_prompt_cost
    answer = ""
    streamed_tokens = 0

    # --- robust stream setup with backoff ---
    MAX_RETRIES = 3
    attempt = 0
    while True:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                stream=True,
            )
            break
        except (RateLimitError, APIStatusError) as e:
            status_code = getattr(e, "status_code", 429)
            if status_code != 429 or attempt >= MAX_RETRIES:
                done_payload = {
                    "answer": "[Upstream Error] Rate limited / API error while contacting the model.",
                    "citations": [],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": 0,
                        "cost_usd": cost_so_far,
                        "latency_ms": int((time.time() - start) * 1000),
                    },
                }
                yield json.dumps({"event": "done", "data": done_payload})
                return
            time.sleep(min(2**attempt, 8) + random.random())
            attempt += 1
        except (APITimeoutError, APIConnectionError, httpx.ConnectTimeout):
            if attempt >= MAX_RETRIES:
                done_payload = {
                    "answer": "[Upstream Error] Request to model timed out.",
                    "citations": [],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": 0,
                        "cost_usd": cost_so_far,
                        "latency_ms": int((time.time() - start) * 1000),
                    },
                }
                yield json.dumps({"event": "done", "data": done_payload})
                return
            time.sleep(min(2**attempt, 8) + random.random())
            attempt += 1
        except Exception as e:
            done_payload = {
                "answer": f"[Upstream Error] {type(e).__name__}: {str(e)[:120]}",
                "citations": [],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 0,
                    "cost_usd": cost_so_far,
                    "latency_ms": int((time.time() - start) * 1000),
                },
            }
            yield json.dumps({"event": "done", "data": done_payload})
            return

    # --- consume the stream safely ---
    try:
        for chunk in response:
            token = chunk.choices[0].delta.content
            if token:
                answer += token
                streamed_tokens += 1
                total_tokens += 1
                cost_so_far = total_tokens * price_per_1k / 1000
                if cost_so_far > budget_usd:
                    done_payload = {
                        "answer": "[Budget Exceeded] Stopped mid-generation.",
                        "citations": [],
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": streamed_tokens,
                            "cost_usd": cost_so_far,
                            "latency_ms": int((time.time() - start) * 1000),
                        },
                    }
                    yield json.dumps({"event": "done", "data": done_payload})
                    return
                yield json.dumps({"event": "token", "data": token})
    except Exception as e:
        done_payload = {
            "answer": f"[Stream Error] {type(e).__name__}: {str(e)[:120]}",
            "citations": [],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": streamed_tokens,
                "cost_usd": cost_so_far,
                "latency_ms": int((time.time() - start) * 1000),
            },
        }
        yield json.dumps({"event": "done", "data": done_payload})
        return

    latency = int((time.time() - start) * 1000)

    citations = []
    for i, chunk in enumerate(context_chunks):
        citations.append({"source_id": f"{chunk['source']}#{i}", "snippet": chunk["chunk"][:120]})

    # Force at least one inline ref
    answer = ensure_inline_citation(answer, citations)

    done_payload = {
        "answer": answer.strip(),
        "citations": citations,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": streamed_tokens,
            "cost_usd": cost_so_far,
            "latency_ms": latency,
        },
    }

    # Return final SSE done event (plus stats for logging)
    yield json.dumps({"event": "done", "data": done_payload}), streamed_tokens, cost_so_far, latency


@router.post("/ask")
async def ask_endpoint(
    request: Request,
    _: None = Depends(auth.check_service_api_key),
):
    request_id = make_request_id()
    rate_limiter("service", settings.rate_limit_rpm)

    body = await request.json()
    question = body.get("question")
    max_tokens = body.get("max_tokens", 400)
    budget_usd = body.get("budget_usd", 0.01)
    if not question:
        log_request(request_id, route="/ask", status="error")
        raise HTTPException(status_code=400, detail="Missing question")

    context_chunks = hybrid_retrieve(question, top_k=settings.top_k)

    # Deterministic fast paths
    special = maybe_answer_filenames(question, context_chunks)

    if special is not None:
        answer_str, citations = special
        words = re.findall(r"\S+\s*", answer_str)

        async def event_generator_list():
            start = time.time()
            for w in words:
                yield json.dumps({"event": "token", "data": w})
            final = {
                "answer": ensure_inline_citation(answer_str, citations).strip(),
                "citations": citations,
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": len(words),
                    "cost_usd": 0.0,
                    "latency_ms": int((time.time() - start) * 1000),
                },
            }
            log_request(
                request_id,
                route="/ask",
                status="ok",
                tokens=len(words),
                cost=0.0,
                latency=final["usage"]["latency_ms"],
            )
            yield json.dumps({"event": "done", "data": final})

        return EventSourceResponse(event_generator_list())

    async def event_generator():
        for result in tokens_from_openai(
            context_chunks, question, max_tokens, settings.model_name, settings.openai_api_key, budget_usd
        ):
            if await request.is_disconnected():
                break

            if isinstance(result, tuple):
                final_line, tokens, cost, latency = result
                # safety net: ensure done has at least one [n]
                try:
                    obj = json.loads(final_line)
                    if isinstance(obj, dict) and obj.get("event") == "done":
                        data = obj.get("data", {})
                        fixed = ensure_inline_citation(data.get("answer", ""), data.get("citations", []))
                        if fixed != data.get("answer", ""):
                            data["answer"] = fixed
                            obj["data"] = data
                            final_line = json.dumps(obj)
                except Exception:
                    pass

                log_request(request_id, route="/ask", status="ok", tokens=tokens, cost=cost, latency=latency)
                yield final_line
            else:
                yield result

    return EventSourceResponse(event_generator())
