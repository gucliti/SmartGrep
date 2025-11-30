import warnings
# Suppress "optimum is not installed" warning from jina-embeddings
warnings.filterwarnings("ignore", message=".*optimum is not installed.*")

import typer
import requests
import time
from smartgrep.indexer import CodeIndexer
from smartgrep.daemon import start_daemon, stop_daemon, get_daemon_status, HOST, PORT
from smartgrep.qa import CodeQA
from rich.console import Console
from rich.syntax import Syntax

app = typer.Typer(help="SmartGrep: Semantic Code Search CLI")
console = Console()

def display_results(results: list[dict]):
    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    for res in results:
        if '_rerank_score' in res:
            score = res['_rerank_score']
            console.print(f"[bold blue]{res['file_path']}:{res['start_line']}-{res['end_line']}[/bold blue] [green](Score: {score:.4f})[/green]")
        else:
            dist = res.get('_distance', float('inf'))
            console.print(f"[bold blue]{res['file_path']}:{res['start_line']}-{res['end_line']}[/bold blue] [dim](Dist: {dist:.4f})[/dim]")

        lang = res.get('language', 'python')
        syntax = Syntax(res['text'], lang, theme="monokai", line_numbers=True, start_line=res['start_line'])
        console.print(syntax)
        console.print("-" * 80)

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
    auto_index: bool = typer.Option(False, help="Automatically update index if stale"),
    qa: bool = typer.Option(False, "--qa", help="Enable Code QA with a local LLM (Ollama)"),
    ollama_model: str = typer.Option("llama3", help="Ollama model to use for Code QA")
):
    """
    Search the indexed codebase.
    """
    if get_daemon_status() == "stopped":
        console.print("[yellow]Daemon not running. Starting it now...[/yellow]")
        start_daemon()

    if auto_index:
        console.print("[dim]Checking for code changes...[/dim]")
        indexer = CodeIndexer()
        indexer.index(".")
        console.print()

    # Retry logic to handle daemon startup
    max_retries = 5
    retry_delay = 1  # seconds
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"http://{HOST}:{PORT}/search",
                json={
                    "query": query,
                    "limit": limit,
                    "threshold": threshold,
                    "hybrid": hybrid,
                },
                timeout=10, # Add a timeout
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            display_results(results)

            if qa and results:
                qa_service = CodeQA(model=ollama_model)
                qa_service.answer(query, results)

            return # Success, exit the function

        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                console.print(f"[red]Error connecting to daemon after {max_retries} attempts: {e}[/red]")
                console.print("[yellow]Is the daemon running? Try 'sgrep daemon status'[/yellow]")
        except requests.exceptions.RequestException as e:
            console.print(f"[red]An unexpected error occurred: {e}[/red]")
            return

daemon_app = typer.Typer(help="Manage the SmartGrep background daemon.")
app.add_typer(daemon_app, name="daemon")

@daemon_app.command()
def start():
    """Start the daemon."""
    start_daemon()

@daemon_app.command()
def stop():
    """Stop the daemon."""
    stop_daemon()

@daemon_app.command()
def status():
    """Check the daemon's status."""
    console.print(f"Daemon status: {get_daemon_status()}")

def main():
    app()

if __name__ == "__main__":
    main()
