# SmartGrep

**SmartGrep** is a local, semantic code search tool that understands *what your code does*, not just what it says. It uses advanced embeddings and AST parsing to find relevant code snippets based on natural language queries.

## Features

- 🧠 **Semantic Understanding**: Uses `jina-embeddings-v2-base-code` (8k context) to understand long functions and complex logic.
- 🌳 **Smart Chunking**: Uses `tree-sitter` to parse code into meaningful blocks (functions, classes) rather than arbitrary text lines.
- 🚀 **Fast & Local**: Built on **LanceDB** (serverless vector DB) and **SentenceTransformers**. Runs entirely on your CPU/GPU. No data leaves your machine.
- 🔍 **Gitignore Support**: Respects `.gitignore` patterns to exclude files from indexing.
- 💻 **CLI Interface**: Simple, developer-friendly command-line interface.

## Installation

This project uses `uv` for dependency management.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/SmartGrep.git
    cd SmartGrep
    ```

2.  **Install SmartGrep as a CLI tool**:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```
    
    Or manually:
    ```bash
    uv pip install -e .
    ```

After installation, you can use `smartgrep` or `sgrep` commands directly!

**Alternative: Run with uv (without installation)**:
```bash
uv sync  # Install dependencies first
uv run python -m smartgrep.cli index .
uv run python -m smartgrep.cli search "your query"
```

## System Requirements

⚠️ **Memory Warning**: Indexing requires ~2-4GB RAM for the embedding model. On WSL2 with limited memory, consider:
- Increasing WSL2 memory limit in `.wslconfig`
- Indexing smaller directories first
- Using the uv run method which may have better memory management

## Usage

### 1. Indexing Your Codebase
Run the indexer to scan your files, parse them, and build the vector index.
```bash
smartgrep index .
# or use the short alias
sgrep index .
```
*Note: The first run will download the embedding model (~0.5GB).*

**Incremental Indexing:**
The indexer automatically detects changes using file hashing and only reprocesses new or modified files. Simply run the same command again to update the index.

### 2. Searching
Search using natural language.
```bash
smartgrep search "how to connect to the database"
# or
sgrep search "how to connect to the database"
```

**Auto-Index (Default):**
By default, the search command automatically checks for code changes and updates the index before searching. This ensures results are always up-to-date.

```bash
# Auto-index enabled (default)
sgrep search "authentication middleware"

# Disable auto-index for faster search
sgrep search "authentication middleware" --no-auto-index
```

### 3. Advanced Search Options

**Adjust Relevance Threshold:**
```bash
# Lower threshold = stricter matching (default: 1.3)
sgrep search "auth middleware" --threshold 1.0
```

**Limit Results:**
```bash
# Show only top 3 results (default: 5)
sgrep search "database query" --limit 3
```

**Disable Hybrid Search:**
```bash
# Use vector search only, skip keyword search and reranking
sgrep search "error handling" --no-hybrid
```

**Combine Options:**
```bash
sgrep search "logging utility" --threshold 1.0 --limit 3 --no-hybrid --no-auto-index
```

### Command Reference

#### `index` Command
```bash
smartgrep index [PATH]
```
- `PATH`: Directory to index (default: current directory `.`)

#### `search` Command
```bash
smartgrep search QUERY [OPTIONS]
```

**Arguments:**
- `QUERY`: Natural language search query (required)

**Options:**
- `--threshold FLOAT`: Distance threshold for relevance (default: 1.3, range: 0.0-2.0, lower = stricter)
- `--limit INT`: Maximum number of results to show (default: 5, range: 1-50)
- `--hybrid / --no-hybrid`: Enable/disable hybrid search with reranking (default: enabled)
- `--auto-index / --no-auto-index`: Auto-update index before search (default: enabled)
- `--qa`: Enable Code QA with a local LLM (Ollama) to get a natural language answer.
- `--ollama-model TEXT`: The Ollama model to use for Code QA (default: `llama3`).

### `daemon` Command
For faster searches, SmartGrep runs a background daemon to keep the AI models loaded in memory. The search command will start it automatically.

- `sgrep daemon start`: Start the daemon manually.
- `sgrep daemon stop`: Stop the daemon.
- `sgrep daemon status`: Check if the daemon is running.

## Supported Languages
- Python (`.py`)
- JavaScript/TypeScript (`.js`, `.ts`)
- Go (`.go`)
- Rust (`.rs`)
- C (`.c`, `.h`)
- C++ (`.cpp`, `.cc`, `.cxx`, `.hpp`)
- Java (`.java`)

## Architecture
- **Embeddings**: `jinaai/jina-embeddings-v2-base-code`
- **Vector Store**: `lancedb`
- **Parsing**: `tree-sitter`
- **CLI**: `typer` + `rich`
