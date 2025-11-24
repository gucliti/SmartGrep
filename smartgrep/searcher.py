import lancedb
from sentence_transformers import SentenceTransformer, CrossEncoder
import warnings
import numpy as np

# Suppress warnings
warnings.filterwarnings("ignore", message=".*optimum is not installed.*")

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

    def _convert_types(self, results: list[dict]):
        for r in results:
            if '_rerank_score' in r and isinstance(r['_rerank_score'], np.float32):
                r['_rerank_score'] = float(r['_rerank_score'])
            if '_distance' in r and isinstance(r['_distance'], np.float32):
                r['_distance'] = float(r['_distance'])
        return results

    def search(self, query: str, limit: int = 5, threshold: float = 1.3, hybrid: bool = True):
        if not self.table:
            return []

        # 1. Vector Search
        query_vector = self.model.encode(query, normalize_embeddings=True)
        vector_results = self.table.search(query_vector).limit(limit * 2).to_list()
        
        # Filter by distance threshold
        vector_results = [r for r in vector_results if r.get('_distance', 0) <= threshold]
        
        candidates = {r['text']: r for r in vector_results}
        
        # 2. FTS Search (Keyword)
        if hybrid:
            try:
                fts_results = self.table.search(query, query_type="fts").limit(limit * 2).to_list()
                for r in fts_results:
                    if r['text'] not in candidates:
                        candidates[r['text']] = r
            except Exception:
                pass

        unique_candidates = list(candidates.values())
        
        if not unique_candidates:
            return []

        # 3. Reranking
        if not hybrid:
             sorted_results = sorted(unique_candidates, key=lambda x: x.get('_distance', 999))
             return self._convert_types(sorted_results[:limit])

        # Rerank logic
        pairs = [[query, r['text']] for r in unique_candidates]
        scores = self.reranker.predict(pairs)
        
        for i, r in enumerate(unique_candidates):
            r['_rerank_score'] = scores[i]
            
        ranked_results = sorted(unique_candidates, key=lambda x: x['_rerank_score'], reverse=True)
        
        filtered_results = [r for r in ranked_results if r['_rerank_score'] > 0]
        
        final_results = filtered_results[:limit]
        return self._convert_types(final_results)
