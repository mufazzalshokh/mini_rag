from fastapi import APIRouter, Request, HTTPException, status, Header
from sse_starlette.sse import EventSourceResponse
from app.core.config import settings
from app.core.retrieval import hybrid_retrieve
import openai

router = APIRouter()

def tokens_from_openai(context_chunks, question, max_tokens, model, api_key, budget_usd):
    context_text = "\n---\n".join([f"[{i+1}] {c['chunk']}" for i, c in enumerate(context_chunks)])
    prompt = (
        f"Answer the user's question using ONLY the info in the context below. "
        f"Cite sources inline as [1], [2], etc.\n\n"
        f"Context:\n{context_text}\n\nQuestion: {question}\nAnswer:"
    )

    client = openai.OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        stream=True,
    )

    answer = ""
    for chunk in response:
        token = chunk.choices[0].delta.content
        if token:
            answer += token
            yield {"event": "token", "data": token}
    yield {"event": "done", "data": answer}

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

    context_chunks = hybrid_retrieve(question, top_k=settings.TOP_K)

    async def event_generator():
        for event in tokens_from_openai(
            context_chunks, question, max_tokens, settings.MODEL, settings.OPENAI_API_KEY, budget_usd
        ):
            if await request.is_disconnected():
                break
            yield event

    return EventSourceResponse(event_generator())
