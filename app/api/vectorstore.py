import os
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.docstore.document import Document

INDEX_PATH = "faiss_index"

def similarity_search_with_citations(query: str, k: int = 5) -> List[Document]:
    if not os.path.exists(INDEX_PATH):
        raise ValueError("Index not found; run /ingest first.")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.load_local(INDEX_PATH, embeddings)
    docs_and_scores = db.similarity_search_with_relevance_scores(query, k=k)
    return [doc for doc, _ in docs_and_scores]
