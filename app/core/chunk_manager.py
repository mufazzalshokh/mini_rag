import faiss
import numpy as np
from typing import List, Dict


class ChunkManager:
    def __init__(self, embed_dim: int = 384):  # all-MiniLM-L6-v2 dimension
        self.index = faiss.IndexFlatL2(embed_dim)
        self.chunks = []

    def add_chunks(self, chunks: List[Dict], embeddings: np.ndarray):
        """Add chunks with their embeddings to index"""
        if not self.index.is_trained:
            self.index.add(embeddings)
        self.chunks.extend(chunks)

    def get_similar_chunks(self, query_embedding: np.ndarray, k: int = 3) -> List[Dict]:
        """Retrieve top-k most similar chunks"""
        distances, indices = self.index.search(query_embedding, k)
        return [self.chunks[i] for i in indices[0]]
