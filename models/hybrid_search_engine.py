"""
HYBRID SEARCH ENGINE MODULE
Hybrid = Dense Search (Qdrant) + BM25 Keyword Search + BGE-Reranker
Includes:
- Local caching (embeddings, dense results, bm25 results, hybrid results)
- Product ID mapping (string → numeric Qdrant ID)
- Qdrant dense retrieval
- BM25 keyword scoring
- BGE Reranker for final ranking (optional but recommended)
"""

import os
import pickle
import numpy as np
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

load_dotenv()

class HybridSearchEngine:
    def __init__(self):
        print("Initializing Hybrid Search Engine")

        # QDRANT CONNECTION
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.collection_name = "amazon-products"

        # EMBEDDING MODEL
        print("Loading embedder (BGE-small)")
        self.embedder = TextEmbedding("BAAI/bge-small-en-v1.5")

        # BM25 INDEX
        print("Loading BM25 index")
        with open("cache/bm25_index.pkl", "rb") as f:
            data = pickle.load(f)
            self.bm25 = data["bm25"]
            self.bm25_product_ids = data["product_ids"]

        # PRODUCT ID -> NUMERIC ID MAPPING
        print("Loading product_id mapping")
        with open("cache/product_id_mapping.pkl", "rb") as f:
            self.product_id_to_idx = pickle.load(f)

        # RERANKER MODEL
        print("Loading BGE CrossEncoder Reranker")
        self.reranker = CrossEncoder("BAAI/bge-reranker-base", max_length=512)

        # CACHES
        self._embedding_cache = {}
        self._dense_cache = {}
        self._bm25_cache = {}
        self._hybrid_cache = {}

        self.max_cache_size = 1000  # LRU-like capacity

        print("Ready with Hybrid Search + Reranker!\n")

    # CACHED EMBEDDING
    def get_embedding(self, query: str):
        if query not in self._embedding_cache:
            emb = list(self.embedder.embed([query]))[0]
            self._embedding_cache[query] = emb

            # Limit cache size
            if len(self._embedding_cache) > self.max_cache_size:
                oldest = next(iter(self._embedding_cache))
                del self._embedding_cache[oldest]

        return self._embedding_cache[query]

    # DENSE SEARCH (QDRANT)
    def dense_search(self, query: str, top_k: int = 50):
        cache_key = f"dense::{query}::{top_k}"

        if cache_key not in self._dense_cache:
            vector = self.get_embedding(query)

            results = self.qdrant.query_points(
                collection_name=self.collection_name,
                query=vector.tolist(),
                limit=top_k
            )

            scores = {}
            for r in results.points:
                scores[r.payload["product_id"]] = r.score

            # Cache
            self._dense_cache[cache_key] = scores

            if len(self._dense_cache) > self.max_cache_size:
                oldest = next(iter(self._dense_cache))
                del self._dense_cache[oldest]

        return self._dense_cache[cache_key]

    # BM25 SEARCH
    def bm25_search(self, query: str, top_k: int = 50):
        cache_key = f"bm25::{query}::{top_k}"

        if cache_key not in self._bm25_cache:
            tokens = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokens)

            top_idx = np.argsort(bm25_scores)[-top_k:][::-1]
            max_score = bm25_scores[top_idx[0]] if len(top_idx) else 1.0

            scores = {}
            for idx in top_idx:
                pid = self.bm25_product_ids[idx]
                scores[pid] = float(bm25_scores[idx] / max_score)

            # Cache
            self._bm25_cache[cache_key] = scores

            if len(self._bm25_cache) > self.max_cache_size:
                oldest = next(iter(self._bm25_cache))
                del self._bm25_cache[oldest]

        return self._bm25_cache[cache_key]

    # HYBRID SEARCH (BM25 + DENSE)
    def hybrid_search(self, query: str, top_k: int = 20, alpha: float = 0.65):
        """
        alpha = weight for dense search
        (1 - alpha) = weight for BM25
        """
        cache_key = f"hybrid::{query}::{top_k}::{alpha}"

        if cache_key not in self._hybrid_cache:
            dense = self.dense_search(query, 50)
            bm25 = self.bm25_search(query, 50)

            all_ids = set(dense.keys()) | set(bm25.keys())

            hybrid_scores = {}
            for pid in all_ids:
                hybrid_scores[pid] = alpha * dense.get(pid, 0) + (1 - alpha) * bm25.get(pid, 0)

            ranked = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

            # Convert product IDs → numeric Qdrant IDs
            numeric_ids = [
                self.product_id_to_idx[pid]
                for pid, _ in ranked
                if pid in self.product_id_to_idx
            ]

            points = self.qdrant.retrieve(self.collection_name, ids=numeric_ids)

            results = []
            for point in points:
                p = point.payload
                results.append({
                    "product_id": p["product_id"],
                    "hybrid_score": hybrid_scores[p["product_id"]],
                    "title": p["title"],
                    "brand": p["brand"],
                    "price": p["price"],
                    "avg_rating": p["avg_rating"],
                    "review_count": p["review_count"],
                    "sentiment_score": p["sentiment_score"],
                    "abstracted_summary": p["abstracted_summary"],
                    "aspects": p["aspects"],
                })

            results.sort(key=lambda x: x["hybrid_score"], reverse=True)
            self._hybrid_cache[cache_key] = results

            if len(self._hybrid_cache) > self.max_cache_size:
                oldest = next(iter(self._hybrid_cache))
                del self._hybrid_cache[oldest]

        return self._hybrid_cache[cache_key]

    # RERANKING (CrossEncoder)
    def rerank(self, query: str, results: list, top_k: int = 3):
        """ Apply the CrossEncoder BGE-Reranker """
        if not results:
            return []

        pairs = []
        for r in results:
            doc = f"{r['title']} {r['abstracted_summary']}"
            pairs.append([query, doc])

        print(f"  Reranking {len(pairs)} candidates with BGE-Reranker...")
        rerank_scores = self.reranker.predict(pairs)

        combined = []
        for i, r in enumerate(results):
            combined_score = (
                0.70 * rerank_scores[i] +
                0.20 * r["sentiment_score"] +
                0.10 * min(r["review_count"] / 500, 1.0)
            )
            combined.append((combined_score, r))

        combined.sort(key=lambda x: x[0], reverse=True)

        final = []
        for i, (score, r) in enumerate(combined[:top_k], 1):
            r["rerank_score"] = score
            r["rank"] = i
            final.append(r)

        return final

    # FINAL SEARCH PIPELINE
    def search(self, query: str, top_k: int = 3, use_reranker: bool = True):
        """
        Unified search interface:
        1. Hybrid Retrieval (20 candidates)
        2. Optional Reranking (CrossEncoder)
        """
        candidates = self.hybrid_search(query, top_k=20, alpha=0.65)

        if use_reranker:
            return self.rerank(query, candidates, top_k=top_k)

        return candidates[:top_k]

    # CACHE STATISTICS
    def get_cache_stats(self):
        return {
            "embedding_cache": len(self._embedding_cache),
            "dense_cache": len(self._dense_cache),
            "bm25_cache": len(self._bm25_cache),
            "hybrid_cache": len(self._hybrid_cache),
        }
