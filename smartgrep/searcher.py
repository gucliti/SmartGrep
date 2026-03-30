import lancedb
from sentence_transformers import SentenceTransformer, CrossEncoder
import warnings
import numpy as np
from typing import Dict, List, Any, Optional
import hashlib
import json

# Suppress warnings
warnings.filterwarnings("ignore", message=".*optimum is not installed.*")

class EmbeddingCache:
    """Simple in-memory cache for query embeddings."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, np.ndarray] = {}
        self.max_size = max_size
    
    def get(self, query: str) -> Optional[np.ndarray]:
        return self.cache.get(query)
    
    def set(self, query: str, embedding: np.ndarray):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry (simple FIFO)
            self.cache.pop(next(iter(self.cache)))
        self.cache[query] = embedding


class CodeSearcher:
    def __init__(self, db_path: str = ".smartgrep/lancedb", model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        self.db_path = db_path
        
        try:
            self.db = lancedb.connect(db_path)
            self.table = self.db.open_table("code_chunks")
        except Exception as e:
            # Handle gracefully if db doesn't exist
            self.table = None
            
        # Initialize Bi-Encoder (for retrieval)
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        
        # Initialize Cross-Encoder (for reranking)
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        # Initialize embedding cache
        self.embedding_cache = EmbeddingCache(max_size=1000)

    def _convert_types(self, results: list[dict]):
        for r in results:
            if '_rerank_score' in r and isinstance(r['_rerank_score'], np.float32):
                r['_rerank_score'] = float(r['_rerank_score'])
            if '_distance' in r and isinstance(r['_distance'], np.float32):
                r['_distance'] = float(r['_distance'])
        return results

    def search(self, query: str, limit: int = 5, threshold: float = 1.3, hybrid: bool = True, max_rerank: int = 50):
        """
        Search the codebase with optional caching and optimized reranking.
        
        Args:
            query: Natural language search query
            limit: Maximum number of results to return
            threshold: Distance threshold for filtering (lower is stricter)
            hybrid: Enable hybrid search (Vector + Keyword + Rerank)
            max_rerank: Maximum number of candidates to rerank (improves latency on large result sets)
        """
        if not self.table:
            return []

        # 1. Vector Search with cached query embedding
        cached_vector = self.embedding_cache.get(query)
        if cached_vector is not None:
            query_vector = cached_vector
        else:
            query_vector = self.model.encode(query, normalize_embeddings=True)
            self.embedding_cache.set(query, query_vector)
        
        # Retrieve more candidates initially for better filtering
        vector_results = self.table.search(query_vector).limit(max(limit * 3, max_rerank)).to_list()
        
        # Filter by distance threshold EARLY to reduce candidate set
        vector_results = [r for r in vector_results if r.get('_distance', 0) <= threshold]
        
        candidates = {r['text']: r for r in vector_results}
        
        # 2. FTS Search (Keyword)
        if hybrid:
            try:
                fts_results = self.table.search(query, query_type="fts").limit(max(limit * 3, max_rerank)).to_list()
                for r in fts_results:
                    if r['text'] not in candidates:
                        candidates[r['text']] = r
            except Exception:
                pass

        unique_candidates = list(candidates.values())
        
        if not unique_candidates:
            return []

        # 3. Reranking with early termination
        if not hybrid:
             sorted_results = sorted(unique_candidates, key=lambda x: x.get('_distance', 999))
             return self._convert_types(sorted_results[:limit])

        # Limit reranking to top candidates for better performance
        if len(unique_candidates) > max_rerank:
            # Pre-sort by distance to get most promising candidates
            unique_candidates.sort(key=lambda x: x.get('_distance', 999))
            candidates_to_rerank = unique_candidates[:max_rerank]
        else:
            candidates_to_rerank = unique_candidates
        
        # Rerank only the selected candidates
        pairs = [[query, r['text']] for r in candidates_to_rerank]
        scores = self.reranker.predict(pairs)
        
        for i, r in enumerate(candidates_to_rerank):
            r['_rerank_score'] = scores[i]
            
        ranked_results = sorted(candidates_to_rerank, key=lambda x: x['_rerank_score'], reverse=True)
        
        # Apply score threshold filter
        filtered_results = [r for r in ranked_results if r['_rerank_score'] > 0]
        
        final_results = filtered_results[:limit]
        return self._convert_types(final_results)
