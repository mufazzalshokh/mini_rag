from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from collections import deque
import time, json
import tiktoken

from app.api.vectorstore import similarity_search_with_citations
from app.api.llm         import stream_openai_chat_completion
from app.api.token_utils import estimate_costs

router = APIRouter()

RATE_LIMIT = 60   # max requests
WINDOW     = 60   # per WINDOW seconds
timestamps = deque()

@router.post("/ask")
async def ask(request: Request):
    now = time.time()
    while timestamps and timestamps[0] < now - WINDOW:
        timestamps.popleft()
    if len(timestamps) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    timestamps.append(now)

    body   = await request.json()
    q      = body.get("question")
    max_t  = body.get("max_tokens", 400)
    budget = body.get("budget_usd")
    if not q or budget is None:
        raise HTTPException(status_code=400, detail="`question` and `budget_usd` required")

    # 1) retrieve similar chunks
    docs = similarity_search_with_citations(q, k=5)
    context = "\n\n".join(d.page_content for d in docs)

    # 2) build prompt & count prompt tokens
    prompt = (
        "Answer using the context below. If unknown, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {q}\nAnswer:"
    )
    prompt_tokens = len(
        tiktoken.get_encoding("cl100k_base").encode(prompt)
    )
    start = time.perf_counter()
    tokens = []

    async def gen():
        try:
            async for tok in stream_openai_chat_completion(
                [{"role":"user","content":prompt}],
                max_tokens=max_t
            ):
                tokens.append(tok)
                cost = estimate_costs(prompt_tokens, len("".join(tokens).split()))
                if cost > budget:
                    payload = {
                        "answer": None,
                        "citations": [],
                        "usage": {
                            "prompt_tokens": prompt_tokens,
                            "completion_tokens": len("".join(tokens).split()),
                            "cost_usd": cost,
                            "latency_ms": int((time.perf_counter()-start)*1000)
                        },
                        "error": "budget_exceeded"
                    }
                    yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                    return
                yield f"event: token\ndata: {tok}\n\n"
        except Exception as e:
            # Stream an error event if something breaks
            err = {"error": str(e)}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"
            return

        # send final event
        answer = "".join(tokens)
        cost   = estimate_costs(prompt_tokens, len(answer.split()))
        citations = [
            {
                "source_id": f"{d.metadata['source']}#{d.metadata.get('chunk','')}",
                "snippet": d.page_content[:200],
            }
            for d in docs
        ]
        payload = {
            "answer": answer,
            "citations": citations,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": len(answer.split()),
                "cost_usd": cost,
                "latency_ms": int((time.perf_counter()-start)*1000)
            }
        }
        yield f"event: done\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
