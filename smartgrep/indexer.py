import os
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Generator, Set
import lancedb
from sentence_transformers import SentenceTransformer
import tree_sitter_python
import tree_sitter_javascript
import tree_sitter_go
import tree_sitter_rust
import tree_sitter_cpp
import tree_sitter_java
from tree_sitter import Language, Parser, QueryCursor, Query
import rich
from rich.console import Console
from rich.progress import track
import pathspec

console = Console()

# Supported languages and their extensions
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "javascript", # reusing js parser for ts for now (often works well enough for simple things)
    ".go": "go",
    ".rs": "rust",
    ".c": "cpp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".java": "java",
}

class CodeIndexer:
    def __init__(self, db_path: str = ".smartgrep/lancedb", model_name: str = "jinaai/jina-embeddings-v2-base-code"):
        self.db_path = db_path
        self.model_name = model_name
        self.console = Console()
        
        # Initialize DB
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db = lancedb.connect(db_path)
        
        # Initialize Model
        self.console.print(f"[bold blue]Loading model {model_name}...[/bold blue]")
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        
        # Initialize Parsers
        self.parsers = {}
        self.languages = {}
        
        try:
            self.languages["python"] = Language(tree_sitter_python.language())
            self.parsers["python"] = Parser(self.languages["python"])
            
            self.languages["javascript"] = Language(tree_sitter_javascript.language())
            self.parsers["javascript"] = Parser(self.languages["javascript"])
            
            self.languages["go"] = Language(tree_sitter_go.language())
            self.parsers["go"] = Parser(self.languages["go"])
            
            self.languages["rust"] = Language(tree_sitter_rust.language())
            self.parsers["rust"] = Parser(self.languages["rust"])
            
            self.languages["cpp"] = Language(tree_sitter_cpp.language())
            self.parsers["cpp"] = Parser(self.languages["cpp"])
            
            self.languages["java"] = Language(tree_sitter_java.language())
            self.parsers["java"] = Parser(self.languages["java"])
        except Exception as e:
            self.console.print(f"[red]Error initializing parsers: {e}[/red]")

    def _get_files(self, root_dir: str) -> Generator[Path, None, None]:
        """Recursively yield supported files, respecting .gitignore (basic implementation)."""
        # Load .gitignore patterns
        gitignore_path = Path(root_dir) / ".gitignore"
        spec = None
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                patterns = f.read().splitlines()
                spec = pathspec.PathSpec.from_lines("gitwildmatch", patterns)
        
        for root, dirs, files in os.walk(root_dir):
            # Convert to relative path for matching
            rel_root = Path(root).relative_to(root_dir)
            
            # Filter directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if spec:
                dirs[:] = [d for d in dirs if not spec.match_file(str(rel_root / d))]
            
            for file in files:
                if file.startswith('.'):
                    continue
                path = Path(root) / file
                rel_path = path.relative_to(root_dir)
                
                # Check gitignore
                if spec and spec.match_file(str(rel_path)):
                    continue
                    
                if path.suffix in LANGUAGE_MAP:
                    yield path

    def _chunk_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """Parse file with tree-sitter and return chunks."""
        lang_id = LANGUAGE_MAP.get(file_path.suffix)
        if not lang_id or lang_id not in self.parsers:
            return []

        parser = self.parsers[lang_id]
        language = self.languages[lang_id]

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
        except UnicodeDecodeError:
            return []

        tree = parser.parse(bytes(code, "utf8"))
        chunks = []
        
        # Query to find function and class definitions
        query_scm = ""
        if lang_id == "python":
            query_scm = """
            (function_definition) @func
            (class_definition) @class
            """
        elif lang_id == "javascript":
            query_scm = """
            (function_declaration) @func
            (class_declaration) @class
            (method_definition) @func
            (arrow_function) @func
            """
        elif lang_id == "go":
            query_scm = """
            (function_declaration) @func
            (method_declaration) @func
            """
        elif lang_id == "rust":
            query_scm = """
            (function_item) @func
            (impl_item) @impl
            (trait_item) @trait
            (struct_item) @struct
            """
        elif lang_id == "cpp":
            query_scm = """
            (function_definition) @func
            (class_specifier) @class
            (struct_specifier) @struct
            (namespace_definition) @namespace
            """
        elif lang_id == "java":
            query_scm = """
            (method_declaration) @func
            (class_declaration) @class
            (interface_declaration) @interface
            (enum_declaration) @enum
            """
            
        try:
            from tree_sitter import Query
            query = Query(language, query_scm)
            cursor = QueryCursor(query)
            captures = cursor.captures(tree.root_node)
            
            # Captures is a dict {name: [nodes]}
            # We need to flatten it or iterate
            all_nodes = []
            for name, nodes in captures.items():
                for node in nodes:
                    all_nodes.append((node, name))
            
            # Sort by start byte to maintain order
            all_nodes.sort(key=lambda x: x[0].start_byte)
            
            for node, _ in all_nodes:
                start_byte = node.start_byte
                end_byte = node.end_byte
                
                chunk_text = bytes(code, "utf8")[start_byte:end_byte].decode("utf8")
                
                chunks.append({
                    "file_path": str(file_path),
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1,
                    "text": chunk_text,
                    "type": "code_block",
                    "language": lang_id
                })
        except Exception as e:
            pass
            
        if not chunks:
            chunks.append({
                "file_path": str(file_path),
                "start_line": 1,
                "end_line": len(code.splitlines()),
                "text": code,
                "type": "file",
                "language": lang_id
            })
            
        return chunks
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file content."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()

    def index(self, root_dir: str):
        """Main indexing logic with incremental updates."""
        files = list(self._get_files(root_dir))
        self.console.print(f"Found {len(files)} files.")
        
        # Calculate current file hashes
        current_hashes = {str(f): self._calculate_file_hash(f) for f in files}
        
        # Load stored hashes from existing table
        stored_hashes = {}
        table_exists = False
        try:
            tbl = self.db.open_table("code_chunks")
            table_exists = True
            # Get unique file_path and file_hash pairs using native LanceDB API
            all_rows = tbl.to_arrow().to_pylist()
            stored_hashes = {}
            for row in all_rows:
                file_path = row['file_path']
                file_hash = row.get('file_hash', '')
                if file_path and file_hash:
                    stored_hashes[file_path] = file_hash
            self.console.print(f"[dim]Loaded {len(stored_hashes)} existing file hashes.[/dim]")
        except Exception as e:
            self.console.print(f"[dim]No existing index found. Creating new index. ({e})[/dim]")
        
        # Detect changes
        new_files = [p for p in current_hashes if p not in stored_hashes]
        modified_files = [p for p in current_hashes 
                          if p in stored_hashes and current_hashes[p] != stored_hashes[p]]
        deleted_files = [p for p in stored_hashes if p not in current_hashes]
        unchanged_files = [p for p in current_hashes 
                           if p in stored_hashes and current_hashes[p] == stored_hashes[p]]
        
        self.console.print(f"[cyan]Changes detected:[/cyan]")
        self.console.print(f"  New: {len(new_files)}, Modified: {len(modified_files)}, Deleted: {len(deleted_files)}, Unchanged: {len(unchanged_files)}")
        
        files_to_process = new_files + modified_files
        
        if not files_to_process and not deleted_files:
            self.console.print("[green]No changes detected. Index is up to date.[/green]")
            return
        
        # Delete old chunks for modified and deleted files
        if table_exists and (modified_files or deleted_files):
            for file_path in modified_files + deleted_files:
                # Escape single quotes in file path for SQL
                escaped_path = file_path.replace("'", "''")
                tbl.delete(f"file_path = '{escaped_path}'")
            self.console.print(f"[yellow]Deleted chunks for {len(modified_files + deleted_files)} files.[/yellow]")
        
        if not files_to_process:
            self.console.print("[green]Cleanup complete.[/green]")
            return
        
        # Process changed files
        all_chunks = []
        for file_path_str in track(files_to_process, description="Chunking files..."):
            file_path = Path(file_path_str)
            file_chunks = self._chunk_file(file_path)
            # Add file hash to each chunk
            for chunk in file_chunks:
                chunk['file_hash'] = current_hashes[file_path_str]
            all_chunks.extend(file_chunks)
            
        if not all_chunks:
            self.console.print("[yellow]No code chunks found.[/yellow]")
            return

        self.console.print(f"Generated {len(all_chunks)} chunks. Generating embeddings...")
        # Batch embedding
        texts = [c["text"] for c in all_chunks]
        embeddings = self.model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
        
        data = []
        for i, chunk in enumerate(all_chunks):
            record = chunk.copy()
            record["vector"] = embeddings[i]
            data.append(record)
        
        # Create or append to table
        if table_exists:
            tbl.add(data)
            self.console.print(f"[green]Added {len(data)} new chunks.[/green]")
        else:
            tbl = self.db.create_table("code_chunks", data=data, mode="overwrite")
            self.console.print(f"[green]Created index with {len(data)} chunks.[/green]")
        
        # Create/update FTS index
        self.console.print("[blue]Updating FTS index...[/blue]")
        try:
            tbl.create_fts_index("text", replace=True)
        except Exception:
            # If replace not supported, just create
            tbl.create_fts_index("text")
        
        self.console.print(f"[green]Successfully updated index![/green]")

if __name__ == "__main__":
    indexer = CodeIndexer()
    indexer.index(".")
