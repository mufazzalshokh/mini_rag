from fastapi import FastAPI, UploadFile, File
from typing import List

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "OK"}

@app.post("/ingest")
async def ingest(files: List[UploadFile] = File(None)):
    return {"files": len(files) if files else 0}

