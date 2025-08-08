from fastapi import FastAPI
from app.api.ingest import router as ingest_router
from app.api.ask import router as ask_router
from app.core.config import settings

app = FastAPI(title="Mini RAG Q&A")

@app.get("/")
def root():
    return {"msg": "Mini RAG Q&A is running"}

app.include_router(ingest_router)
app.include_router(ask_router)
