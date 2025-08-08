from fastapi import APIRouter, UploadFile, File, Request, HTTPException, status, Depends
from app.core.config import settings
import os
import shutil
from typing import List
from fastapi import Header


router = APIRouter()

def save_upload_file(upload_file: UploadFile, dest_folder: str):
    os.makedirs(dest_folder, exist_ok=True)
    file_path = os.path.join(dest_folder, upload_file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return file_path

@router.post("/ingest")
async def ingest_endpoint(
    files: List[UploadFile] = File(None),
    x_api_key: str = Header(...)
):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    doc_folder = settings.DOCS_PATH
    docs_ingested = []

    # 1. Save any uploaded files
    if files:
        for upload_file in files:
            file_path = save_upload_file(upload_file, doc_folder)
            docs_ingested.append(file_path)

    # 2. Load all docs in /docs
    doc_files = [os.path.join(doc_folder, f) for f in os.listdir(doc_folder)
                 if os.path.isfile(os.path.join(doc_folder, f))]
    if not doc_files:
        return {"error": "No documents found in docs folder."}

    # 3. Chunk, deduplicate, embed, index
    # -----> Put your actual chunking & indexing code here <-----
    # We'll call a function like: build_index(doc_files)
    # For now, let's mock:
    chunk_count = 0
    est_tokens = 0
    try:
        # Imagine this calls your core RAG logic
        from app.core.chunk_manager import build_index  # you implement this!
        chunk_count, est_tokens = build_index(doc_files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return {
        "docs": len(doc_files),
        "chunks": chunk_count,
        "est_tokens": est_tokens
    }
