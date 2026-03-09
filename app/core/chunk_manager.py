import os
import faiss
import numpy as np
import pickle
from app.core.config import settings
from sentence_transformers import SentenceTransformer
import numpy as np

_model = None  # Global model instance for reuse

def load_docs(file_paths):
    docs = []
    sources = []
    for fp in file_paths:
        with open(fp, "r", encoding="utf-8") as f:
            txt = f.read()
        docs.append(txt)
        sources.append(os.path.basename(fp))
    return docs, sources

def simple_chunk(text, size=512, overlap=64):
    tokens = text.split()
    chunks = []
    i = 0
    while i < len(tokens):
        chunk = tokens[i:i+size]
        chunks.append(" ".join(chunk))
        i += size - overlap
    return chunks

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")  # 384-dim, fast, free
    return _model

def embed(texts: list[str]) -> np.ndarray:
    model = get_embedding_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return vectors.astype("float32")

def build_index(file_paths):
    docs, sources = load_docs(file_paths)
    all_chunks, chunk_sources = [], []
    for doc, src in zip(docs, sources):
        chunks = simple_chunk(doc, size=settings.CHUNK_SIZE, overlap=settings.CHUNK_OVERLAP)
        all_chunks.extend(chunks)
        chunk_sources.extend([src]*len(chunks))

    X = embed(all_chunks)
    faiss.normalize_L2(X)
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)

    # Save index and metadata
    os.makedirs(os.path.dirname(settings.INDEX_PATH), exist_ok=True)
    faiss.write_index(index, settings.INDEX_PATH)
    with open(settings.META_PATH, "wb") as f:
        pickle.dump({"chunks": all_chunks, "sources": chunk_sources}, f)

    return len(all_chunks), sum(len(chunk.split()) for chunk in all_chunks)
