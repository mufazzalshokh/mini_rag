from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List
from pathlib import Path
import shutil
import hashlib

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.document_loaders import PyPDFLoader
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
import tiktoken

app = FastAPI()

DOCS_PATH = Path("docs")
INDEX_PATH = "faiss_index"
HASHES_PATH = DOCS_PATH / ".hashes"

DOCS_PATH.mkdir(exist_ok=True)
HASHES_PATH.touch(exist_ok=True)

# Load previously hashed filenames
def load_hashed_files():
    with HASHES_PATH.open("r", encoding="utf-8") as f:
        return set(line.strip() for line in f.readlines())

# Save new file hash
def save_hashed_file(filename: str):
    with HASHES_PATH.open("a", encoding="utf-8") as f:
        f.write(filename + "\n")

def file_hash(file: UploadFile) -> str:
    content = file.file.read()
    file.file.seek(0)
    return hashlib.sha256(content).hexdigest()

def save_uploaded_files(files: List[UploadFile]):
    saved_files = []
    existing_hashes = load_hashed_files()

    for file in files:
        hash_val = file_hash(file)
        if hash_val in existing_hashes:
            print(f"Skipping previously ingested file: {file.filename}")
            continue
        dest = DOCS_PATH / file.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        save_hashed_file(hash_val)
        saved_files.append(dest)
    return saved_files

def load_all_documents():
    texts = []

    for file in DOCS_PATH.glob("*.txt"):
        with file.open("r", encoding="utf-8") as f:
            texts.append(Document(page_content=f.read(), metadata={"source": file.name}))

    for file in DOCS_PATH.glob("*.pdf"):
        loader = PyPDFLoader(str(file))
        texts.extend(loader.load())

    return texts

def estimate_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

@app.get("/health")
def health_check():
    return {"status": "OK"}

@app.post("/ingest")
async def ingest(files: List[UploadFile] = File(None)):
    # Save uploaded files if any
    if files:
        save_uploaded_files(files)

    docs = load_all_documents()
    if not docs:
        return JSONResponse(status_code=400, content={"error": "No documents found to ingest."})

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    all_chunks = text_splitter.split_documents(docs)

    # Remove duplicate chunks
    seen = set()
    unique_chunks = []
    for chunk in all_chunks:
        if chunk.page_content not in seen:
            seen.add(chunk.page_content)
            unique_chunks.append(chunk)

    est_tokens = sum(estimate_tokens(chunk.page_content) for chunk in unique_chunks)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(unique_chunks, embeddings)
    vectorstore.save_local(INDEX_PATH)

    return JSONResponse({
        "docs": len(docs),
        "chunks": len(unique_chunks),
        "est_tokens": est_tokens
    })
