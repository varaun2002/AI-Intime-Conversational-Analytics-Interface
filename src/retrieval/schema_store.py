"""
Schema search using TF-IDF + cosine similarity.
Same interface as Milvus version — drop-in replacement.
Swap to Milvus when Python 3.13 support lands.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class SchemaStore:
    def __init__(self, **kwargs):
        """kwargs accepted for Milvus compatibility — ignored here."""
        self.vectorizer = TfidfVectorizer()
        self.table_names = []
        self.descriptions = []
        self.vectors = None
        self._ready = False

    def ingest(self, schema: dict):
        """Embed all table descriptions using TF-IDF."""
        self.table_names = list(schema.keys())
        self.descriptions = [schema[t]["description"] for t in self.table_names]
        self.vectors = self.vectorizer.fit_transform(self.descriptions)
        self._ready = True
        print(f"[SchemaStore] Ingested {len(self.table_names)} tables (TF-IDF)")

    def search(self, query: str, top_k: int = 3) -> list:
        """Find the most relevant tables for a user query."""
        if not self._ready:
            raise RuntimeError("SchemaStore not initialized. Call ingest() first.")

        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self.vectors).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        matched = []
        for i in top_indices:
            matched.append({
                "table_name": self.table_names[i],
                "score": round(float(scores[i]), 4),
            })
        return matched

    def get_matched_table_names(self, query: str, top_k: int = 3) -> list:
        """Convenience method — returns just table name strings."""
        results = self.search(query, top_k)
        return [r["table_name"] for r in results]