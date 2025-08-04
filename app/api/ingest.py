from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from pathlib import Path
import shutil, hashlib

import tiktoken
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings

router = APIRouter()

DOCS_PATH   = Path("docs")
INDEX_PATH  = "faiss_index"
HASHES_PATH = DOCS_PATH / ".hashes"

DOCS_PATH.mkdir(exist_ok=True)
if not HASHES_PATH.exists():
    HASHES_PATH.touch()

def load_hashed_files() -> set[str]:
    return {line.strip() for line in HASHES_PATH.read_text().splitlines()}

def save_hashed_file(hash_val: str):
    with HASHES_PATH.open("a", encoding="utf-8") as f:
        f.write(f"{hash_val}\n")

def file_hash(file: UploadFile) -> str:
    data = file.file.read()
    file.file.seek(0)
    return hashlib.sha256(data).hexdigest()

def save_uploaded_files(files: List[UploadFile]) -> List[Path]:
    existing = load_hashed_files()
    saved = []
    for file in files:
        h = file_hash(file)
        if h in existing:
            continue
        dest = DOCS_PATH / file.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
        save_hashed_file(h)
        saved.append(dest)
    return saved

def load_all_documents() -> List[Document]:
    docs: List[Document] = []
    # TXT
    for f in DOCS_PATH.glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": f.name}))
    # PDF
    for f in DOCS_PATH.glob("*.pdf"):
        loader = PyPDFLoader(str(f))
        docs.extend(loader.load())
    # MD
    for f in DOCS_PATH.glob("*.md"):
        text = f.read_text(encoding="utf-8")
        docs.append(Document(page_content=text, metadata={"source": f.name}))
    return docs

def estimate_tokens(text: str) -> int:
    enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

@router.post("/ingest")
async def ingest(files: List[UploadFile] = File(None)):
    if files:
        save_uploaded_files(files)

    docs = load_all_documents()
    if not docs:
        raise HTTPException(status_code=400, detail="No docs to ingest")

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks  = splitter.split_documents(docs)

    seen = set(); unique = []
    for idx, c in enumerate(chunks):
        if c.page_content not in seen:
            seen.add(c.page_content)
            c.metadata["chunk"] = idx
            unique.append(c)

    est = sum(estimate_tokens(c.page_content) for c in unique)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(unique, embeddings)
    db.save_local(INDEX_PATH)

    return JSONResponse({
        "docs": len(docs),
        "chunks": len(unique),
        "est_tokens": est
    })
