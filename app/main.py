from fastapi import FastAPI
from dotenv import load_dotenv

from app.api.ingest import router as ingest_router
from app.api.ask    import router as ask_router

load_dotenv()

app = FastAPI()

@app.get("/health")
async def health_check():
    return {"status": "OK"}

app.include_router(ingest_router)
app.include_router(ask_router)
