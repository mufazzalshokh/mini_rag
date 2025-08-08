import faiss
import numpy as np
import pickle
from app.core.config import settings


def embed_query(text):
    # For demo: use random vectors, replace with real embedding!
    return np.random.rand(1, 384).astype('float32')

def bm25_score(chunk, query):
    # Simple lexical: count shared words (improve later)
    chunk_words = set(chunk.lower().split())
    query_words = set(query.lower().split())
    return len(chunk_words & query_words)

def hybrid_retrieve(query, top_k=5):
    # 1. Load FAISS index and meta
    index = faiss.read_index(settings.INDEX_PATH)
    with open(settings.META_PATH, "rb") as f:
        meta = pickle.load(f)
    chunks = meta["chunks"]
    sources = meta["sources"]

    # 2. Vector similarity
    qv = embed_query(query)
    faiss.normalize_L2(qv)
    D, I = index.search(qv, min(top_k * 2, len(chunks)))
    faiss_hits = [(chunks[i], sources[i], float(D[0][j])) for j, i in enumerate(I[0])]

    # 3. Lexical (BM25/TfIdf): Just using word overlap as a placeholder
    lex_scores = [(chunk, src, bm25_score(chunk, query)) for chunk, src in zip(chunks, sources)]

    # 4. Combine: Take best from each, no dups
    all_hits = { (chunk, src): max(faiss_score, lex_score)
                 for (chunk, src, faiss_score), (_, _, lex_score) in zip(faiss_hits, lex_scores)}
    # Sort by score, get top_k
    sorted_hits = sorted(all_hits.items(), key=lambda x: -x[1])[:top_k]
    result = [{"chunk": chunk, "source": src} for (chunk, src), score in sorted_hits]
    return result
