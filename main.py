import warnings
# Suppress "optimum is not installed" warning from jina-embeddings
warnings.filterwarnings("ignore", message=".*optimum is not installed.*")

import typer
from smartgrep.indexer import CodeIndexer
from smartgrep.searcher import CodeSearcher
from rich.console import Console

app = typer.Typer(help="SmartGrep: Semantic Code Search CLI")
console = Console()

@app.command()
def index(path: str = typer.Argument(".", help="Path to the directory to index")):
    """ 
    Index the codebase in the specified path.
    """
    console.print(f"[bold green]Indexing {path}...[/bold green]")
    indexer = CodeIndexer()
    indexer.index(path)

@app.command()
def search(
    query: str = typer.Argument(..., help="Natural language query"),
    threshold: float = typer.Option(1.3, help="Distance threshold (lower is stricter)", min=0.0, max=2.0),
    limit: int = typer.Option(5, help="Max results", min=1, max=50),
    hybrid: bool = typer.Option(True, help="Enable hybrid search (Vector + Keyword + Rerank)"),
    auto_index: bool = typer.Option(True, help="Automatically update index if stale")
):
    """
    Search the indexed codebase.
    """
    if auto_index:
        console.print("[dim]Checking for code changes...[/dim]")
        indexer = CodeIndexer()
        indexer.index(".")
        console.print()
    
    console.print(f"[bold green]Searching for: '{query}' (Hybrid: {hybrid})...[/bold green]")
    searcher = CodeSearcher()
    searcher.search(query, limit=limit, threshold=threshold, hybrid=hybrid)

if __name__ == "__main__":
    app()
