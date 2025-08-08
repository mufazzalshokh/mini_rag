from fastapi import APIRouter, Request, HTTPException, status, Header
from sse_starlette.sse import EventSourceResponse
from app.core.config import settings
import time

router = APIRouter()

# Dummy answer streaming for demo. Replace with real RAG logic!
def dummy_stream_answer(question, max_tokens, budget_usd):
    tokens = [
        "This", "is", "a", "streamed", "answer.", "Citations:", "[1]", "Source1: snippet", "[2]", "Source2: snippet"
    ]
    usage = {"prompt_tokens": 10, "completion_tokens": len(tokens), "cost_usd": 0.001}
    start = time.time()
    for t in tokens:
        yield {"event": "token", "data": t}
        time.sleep(0.25)  # simulate latency

    latency = int((time.time() - start) * 1000)
    done_event = {
        "event": "done",
        "data": {
            "answer": " ".join(tokens),
            "citations": [
                {"source_id": "source1.txt#0-512", "snippet": "Source1: snippet"},
                {"source_id": "source2.txt#512-1024", "snippet": "Source2: snippet"}
            ],
            "usage": {**usage, "latency_ms": latency}
        }
    }
    yield done_event

@router.post("/ask")
async def ask_endpoint(
    request: Request,
    x_api_key: str = Header(...),
):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    body = await request.json()
    question = body.get("question")
    max_tokens = body.get("max_tokens", 400)
    budget_usd = body.get("budget_usd", 0.01)
    if not question:
        raise HTTPException(status_code=400, detail="Missing question")

    async def event_generator():
        for event in dummy_stream_answer(question, max_tokens, budget_usd):
            if await request.is_disconnected():
                break
            if event["event"] == "token":
                yield {"event": "token", "data": event["data"]}
            elif event["event"] == "done":
                yield {
                    "event": "done",
                    "data": event["data"]
                }
                break

    return EventSourceResponse(event_generator())
