import hashlib
import json
import re
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from freecode import ollama_client
from freecode.tools import compress

app = typer.Typer(help="Build or refresh the project search index.")
console = Console()

EMBED_MODEL = "nomic-embed-text"
EMB_DIR = Path.home() / ".freecode" / "embeddings"
MAX_CHARS = 6000
_BOUNDARY = re.compile(r"^\s*(def |class |async def |function |func |public |private |export )")


def _project_id(directory):
    return hashlib.sha1(str(Path(directory).resolve()).encode()).hexdigest()[:16]


def _mtime_path(directory):
    return EMB_DIR / f"{_project_id(directory)}.mtimes.json"


def _collection(directory):
    import chromadb  # heavy, optional dependency: imported only when indexing/searching

    EMB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(EMB_DIR))
    return client.get_or_create_collection(_project_id(directory))


def _project_files(directory):
    # git already knows what to ignore; reuse it so .gitignore is honoured for free.
    try:
        out = subprocess.run(
            ["git", "-C", str(directory), "ls-files", "--cached", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0:
            return [Path(directory) / f for f in out.stdout.splitlines() if f]
    except Exception:
        pass
    return [p for p in Path(directory).rglob("*") if p.is_file() and ".git" not in p.parts]


def _read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None  # binary or unreadable: skip


def _chunk_text(text):
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if _BOUNDARY.match(l)]
    bounds = sorted(set([0] + starts))
    chunks = []
    for idx, s in enumerate(bounds):
        e = bounds[idx + 1] if idx + 1 < len(bounds) else len(lines)
        block = lines[s:e]
        # Split oversized blocks into line windows so embeddings stay within model limits.
        step = max(1, MAX_CHARS // 80)
        for off in range(0, len(block), step):
            window = block[off:off + step]
            content = "\n".join(window).strip()
            if content:
                chunks.append((s + off + 1, s + off + len(window), content))
    return chunks


def embed_project(directory="."):
    """Embed changed files of a project into its chroma collection. Returns count of files (re)indexed."""
    directory = Path(directory).resolve()
    coll = _collection(directory)
    mtime_path = _mtime_path(directory)
    mtimes = json.loads(mtime_path.read_text()) if mtime_path.exists() else {}
    indexed = 0
    for path in _project_files(directory):
        try:
            rel = str(path.relative_to(directory))
            mt = path.stat().st_mtime
        except (ValueError, OSError):
            continue
        if mtimes.get(rel) == mt:
            continue  # unchanged since last index
        text = _read_text(path)
        if text is None:
            continue
        coll.delete(where={"file": rel})
        ids, embs, metas, docs = [], [], [], []
        for start, end, content in _chunk_text(text):
            ids.append(f"{rel}:{start}")
            embs.append(ollama_client.embed(EMBED_MODEL, content))
            metas.append({"file": rel, "start": start, "end": end})
            docs.append(content)
        if ids:
            coll.add(ids=ids, embeddings=embs, metadatas=metas, documents=docs)
        mtimes[rel] = mt
        indexed += 1
    EMB_DIR.mkdir(parents=True, exist_ok=True)
    mtime_path.write_text(json.dumps(mtimes))
    return indexed


def search_relevant_chunks(query, project_path, top_k=5):
    coll = _collection(project_path)
    count = coll.count()
    if count == 0:
        return []
    qvec = ollama_client.embed(EMBED_MODEL, query)
    res = coll.query(query_embeddings=[qvec], n_results=min(top_k, count))
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    out = []
    for doc, meta in zip(docs, metas):
        comp = compress.compress_chunk(doc)
        out.append({
            "file": meta["file"], "start": meta["start"], "end": meta["end"],
            "content": comp["content"], "hash": comp["hash"], "ratio": comp["ratio"],
            "type": comp["type"], "raw_len": len(doc),
        })
    # CacheAligner: stable order (path, start) keeps the prompt prefix identical across
    # consecutive tasks so Ollama's KV cache can be reused.
    out.sort(key=lambda c: (c["file"], c["start"]))
    return out


def has_index(project_path):
    return _mtime_path(project_path).exists()


def demo():
    src = "import os\n\ndef a():\n    return 1\n\nclass B:\n    def m(self):\n        pass\n"
    chunks = _chunk_text(src)
    files = [c[2].splitlines()[0] for c in chunks]
    assert "import os" in chunks[0][2]
    assert any(c[2].startswith("def a():") for c in chunks)
    assert any(c[2].startswith("class B:") for c in chunks)
    big = "x = 1\n" * 5000
    assert all(len(c[2]) <= MAX_CHARS + 200 for c in _chunk_text(big)), "oversized block not split"
    assert _project_id("/a") == _project_id("/a") and _project_id("/a") != _project_id("/b")
    print("ok")


@app.callback(invoke_without_command=True)
def main():
    """Index the current directory for relevant-file retrieval."""
    if not ollama_client.check_running():
        console.print("[red]Ollama not running at localhost:11434. Start it with `ollama serve`.[/red]")
        raise typer.Exit(1)
    if not ollama_client.is_model_pulled(EMBED_MODEL, ollama_client.list_models()):
        console.print(f"[yellow]{EMBED_MODEL} not pulled. Run `freeai model pull {EMBED_MODEL}` first.[/yellow]")
        raise typer.Exit(1)
    with console.status("[cyan]Indexing project...[/cyan]"):
        n = embed_project(".")
    console.print(f"[green]Indexed {n} file(s).[/green]")
