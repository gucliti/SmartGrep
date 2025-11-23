import ollama
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

class CodeQA:
    def __init__(self, model: str = "llama3"):
        self.model = model
        self.console = Console()

    def answer(self, query: str, snippets: list[dict]):
        self.console.print(f"[bold cyan]Generating answer with {self.model}...[/bold cyan]")

        prompt = self._build_prompt(query, snippets)

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True
            )

            full_response = ""
            with self.console.status("[bold green]Thinking...") as status:
                for chunk in response:
                    content = chunk['message']['content']
                    full_response += content
                    status.update(f"[bold green]Thinking...[/bold green]\n{full_response}")

            self.console.print(Panel(Markdown(full_response), title="[bold green]Answer[/bold green]", border_style="green"))

        except ollama.ResponseError as e:
            self.console.print(f"[red]Error communicating with Ollama: {e.error}[/red]")
            if "model not found" in e.error:
                self.console.print(f"[yellow]Model '{self.model}' not found. Try pulling it with 'ollama pull {self.model}'[/yellow]")
        except Exception as e:
            self.console.print(f"[red]An unexpected error occurred: {e}[/red]")
            self.console.print("[yellow]Is Ollama running?[/yellow]")

    def _build_prompt(self, query: str, snippets: list[dict]) -> str:
        context = "\n\n".join([f"File: {s['file_path']}\n```\n{s['text']}\n```" for s in snippets])

        return (
            f"You are a senior software engineer. Your task is to answer a question about a codebase using the provided context."
            f"The user's question is: '{query}'\n\n"
            f"Here are the most relevant code snippets from the codebase:\n\n"
            f"{context}\n\n"
            f"Based on these snippets, please provide a clear and concise answer to the user's question."
            f"If the provided context is not sufficient to answer the question, state that and explain what information is missing."
        )
