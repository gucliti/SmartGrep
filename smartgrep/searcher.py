import lancedb
from sentence_transformers import SentenceTransformer, CrossEncoder
from rich.console import Console
from rich.syntax import Syntax
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", message=".*optimum is not installed.*")

class CodeSearcher:
    def __init__(self, db_path: str = ".smartgrep/lancedb", model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        self.db_path = db_path
        self.console = Console()
        
        try:
            self.db = lancedb.connect(db_path)
            self.table = self.db.open_table("code_chunks")
        except Exception as e:
            self.console.print(f"[red]Error opening database: {e}[/red]")
            self.console.print("[yellow]Did you run 'sgrep index' first?[/yellow]")
            self.table = None
            
        # Initialize Bi-Encoder (for retrieval)
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        
        # Initialize Cross-Encoder (for reranking) - Lazy load could be better but loading here for simplicity
        # Using a lightweight model for speed
        self.reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def search(self, query: str, limit: int = 5, threshold: float = 1.3, hybrid: bool = True):
        if not self.table:
            return

        # 1. Vector Search (Primary)
        query_vector = self.model.encode(query, normalize_embeddings=True)
        vector_results = self.table.search(query_vector).limit(40).to_list()
        
        # Filter by distance threshold
        vector_results = [r for r in vector_results if r.get('_distance', 0) <= threshold]
        
        # Start with a prioritized list of candidates
        # Vector results are higher quality, so they go first
        unique_candidates = []
        seen_texts = set()

        for r in vector_results:
            if r['text'] not in seen_texts:
                unique_candidates.append(r)
                seen_texts.add(r['text'])
        
        # 2. FTS Search (Keyword) - to fill in gaps
        if hybrid:
            try:
                fts_results = self.table.search(query, query_type="fts").limit(40).to_list()
                for r in fts_results:
                    if r['text'] not in seen_texts:
                        unique_candidates.append(r)
                        seen_texts.add(r['text'])
            except Exception as e:
                # FTS might fail if index doesn't exist
                pass

        # Now, we have a combined list of up to 80 candidates, with vector results first.
        # We'll take the top 20 to rerank.
        rerank_candidates = unique_candidates[:20]
        
        if not unique_candidates:
            self.console.print("[yellow]No results found.[/yellow]")
            return

        # 3. Reranking
        if not hybrid:
             # If not hybrid, just return the vector results (candidates) sorted by distance (if available) or just as is
             # Vector results from LanceDB are already sorted by distance (ascending)
             # But we collected them into a dict, so order is lost.
             # We should recover the order or just use the list.
             
             # Actually, if not hybrid, we only did vector search.
             # So 'unique_candidates' contains vector results.
             # We should sort them by _distance (ascending)
             
             sorted_results = sorted(unique_candidates, key=lambda x: x['_distance'])
             final_results = sorted_results[:limit]
             
             for res in final_results:
                dist = res['_distance']
                self.console.print(f"[bold blue]{res['file_path']}:{res['start_line']}-{res['end_line']}[/bold blue] [dim](Dist: {dist:.4f})[/dim]")
                
                lang = res.get('language', 'python')
                syntax = Syntax(res['text'], lang, theme="monokai", line_numbers=True, start_line=res['start_line'])
                self.console.print(syntax)
                self.console.print("-" * 80)
             return

        self.console.print(f"[dim]Reranking {len(rerank_candidates)} candidates...[/dim]")
        
        pairs = [[query, r['text']] for r in rerank_candidates]
        scores = self.reranker.predict(pairs)
        
        # Attach scores
        for i, r in enumerate(rerank_candidates):
            r['_rerank_score'] = scores[i]
            
        # Sort by rerank score (descending)
        ranked_results = sorted(rerank_candidates, key=lambda x: x['_rerank_score'], reverse=True)
        
        # Filter by score (CrossEncoder logits usually > 0 for relevant)
        # We use a conservative threshold of 0.0
        filtered_results = [r for r in ranked_results if r['_rerank_score'] > 0]
        
        if not filtered_results:
             self.console.print("[yellow]No relevant results found after reranking.[/yellow]")
             return

        # Top-K
        final_results = filtered_results[:limit]

        for res in final_results:
            score = res['_rerank_score']
            # Sigmoid-ish score, usually between -10 and 10 for logits, or 0-1 if normalized. 
            # CrossEncoder output is usually logits.
            
            self.console.print(f"[bold blue]{res['file_path']}:{res['start_line']}-{res['end_line']}[/bold blue] [green](Score: {score:.4f})[/green]")
            
            # Show code snippet
            lang = res.get('language', 'python')
            syntax = Syntax(res['text'], lang, theme="monokai", line_numbers=True, start_line=res['start_line'])
            self.console.print(syntax)
            self.console.print("-" * 80)
