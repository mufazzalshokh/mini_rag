from fastapi import APIRouter, Request, HTTPException, status, Header
from sse_starlette.sse import EventSourceResponse
from app.core.config import settings
from app.core.retrieval import hybrid_retrieve
from app.core.rate_limit import rate_limiter
from app.core.logging import make_request_id, log_request

import openai
import tiktoken
import time

router = APIRouter()

def estimate_tokens(text, model="gpt-3.5-turbo"):
    try:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text) // 4)

def get_openai_price(model):
    prices = {
        "gpt-3.5-turbo": 0.0005,
        "gpt-4": 0.01,
        "gpt-4o": 0.005,
    }
    return prices.get(model, 0.01)

def tokens_from_openai(context_chunks, question, max_tokens, model, api_key, budget_usd):
    context_text = "\n---\n".join([f"[{i+1}] {c['chunk']}" for i, c in enumerate(context_chunks)])
    prompt = (
        f"Answer the user's question using ONLY the info in the context below. "
        f"Cite sources inline as [1], [2], etc, matching the numbers to sources. "
        f"Return only the answer with citations.\n\n"
        f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
    )

    prompt_tokens = estimate_tokens(prompt, model)
    price_per_1k = get_openai_price(model)
    est_prompt_cost = prompt_tokens * price_per_1k / 1000
    if est_prompt_cost > budget_usd:
        yield {
            "event": "done",
            "data": {
                "answer": "[Budget Exceeded] Prompt cost exceeds provided budget.",
                "citations": [],
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": 0,
                    "cost_usd": est_prompt_cost,
                    "latency_ms": 0
                }
            }
        }
        return

    client = openai.OpenAI(api_key=api_key)
    start = time.time()
    total_tokens = prompt_tokens
    cost_so_far = est_prompt_cost
    answer = ""
    streamed_tokens = 0

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        stream=True,
    )

    for chunk in response:
        token = chunk.choices[0].delta.content
        if token:
            answer += token
            streamed_tokens += 1
            total_tokens += 1
            cost_so_far = total_tokens * price_per_1k / 1000
            if cost_so_far > budget_usd:
                yield {
                    "event": "done",
                    "data": {
                        "answer": "[Budget Exceeded] Stopped mid-generation.",
                        "citations": [],
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": streamed_tokens,
                            "cost_usd": cost_so_far,
                            "latency_ms": int((time.time() - start) * 1000)
                        }
                    }
                }
                return
            yield {"event": "token", "data": token}

    latency = int((time.time() - start) * 1000)
    citations = []
    for i, chunk in enumerate(context_chunks):
        citations.append({
            "source_id": f"{chunk['source']}#{i}",
            "snippet": chunk['chunk'][:120]
        })

    yield {
        "event": "done",
        "data": {
            "answer": answer.strip(),
            "citations": citations,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": streamed_tokens,
                "cost_usd": cost_so_far,
                "latency_ms": latency
            }
        }
    }, streamed_tokens, cost_so_far, latency  # <--- Return for logging

@router.post("/ask")
async def ask_endpoint(
    request: Request,
    x_api_key: str = Header(...),
):
    request_id = make_request_id()
    start_time = time.time()

    if x_api_key != settings.API_KEY:
        log_request(request_id, route="/ask", status="error")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    rate_limiter(x_api_key, settings.RATE_LIMIT_RPM)

    body = await request.json()
    question = body.get("question")
    max_tokens = body.get("max_tokens", 400)
    budget_usd = body.get("budget_usd", 0.01)
    if not question:
        log_request(request_id, route="/ask", status="error")
        raise HTTPException(status_code=400, detail="Missing question")

    context_chunks = hybrid_retrieve(question, top_k=settings.TOP_K)

    async def event_generator():
        stats = None
        for result in tokens_from_openai(
            context_chunks, question, max_tokens, settings.MODEL, settings.OPENAI_API_KEY, budget_usd
        ):
            if await request.is_disconnected():
                break
            if isinstance(result, tuple):
                # Final done event with stats
                event, tokens, cost, latency = result
                log_request(
                    request_id,
                    route="/ask",
                    status="ok",
                    tokens=tokens,
                    cost=cost,
                    latency=latency
                )
                yield event
            else:
                yield result

    return EventSourceResponse(event_generator())
