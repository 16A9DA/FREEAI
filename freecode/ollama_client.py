import json

import httpx

BASE = "http://localhost:11434"

EMBEDDING_MODEL_MARKERS = {"embed", "nomic-embed", "bge-", "minilm", "e5-"}


def normalize_model_name(name):
    return name if ":" in name else f"{name}:latest"


def is_model_pulled(name, pulled_models):
    # Compare base name (before ':') so an untagged name like "qwen2.5-coder" matches
    # a tagged pull like "qwen2.5-coder:7b", not just an explicit ":latest".
    base = name.split(":")[0]
    return any(m.split(":")[0] == base for m in pulled_models)


def is_embedding_model(name, extra_markers=()):
    lowered = name.lower()
    return any(marker in lowered for marker in (*EMBEDDING_MODEL_MARKERS, *extra_markers))


def demo():
    assert normalize_model_name("qwen2.5-coder") == "qwen2.5-coder:latest"
    assert normalize_model_name("qwen2.5-coder:7b") == "qwen2.5-coder:7b"
    assert is_model_pulled("qwen2.5-coder", ["qwen2.5-coder:7b"])
    assert not is_model_pulled("llama3", ["qwen2.5-coder:7b"])
    assert is_embedding_model("nomic-embed-text:latest")
    assert not is_embedding_model("qwen2.5-coder:7b")
    assert is_embedding_model("custom-e", ["custom-e"])
    print("ok")


if __name__ == "__main__":
    demo()


def check_running():
    try:
        httpx.get(BASE, timeout=2.0)
        return True
    except httpx.HTTPError:
        return False


def list_models():
    r = httpx.get(f"{BASE}/api/tags", timeout=5.0)
    r.raise_for_status()
    return [m["name"] for m in r.json().get("models", [])]


def list_models_detailed():
    r = httpx.get(f"{BASE}/api/tags", timeout=5.0)
    r.raise_for_status()
    return [{"name": m["name"], "size": m.get("size", 0)} for m in r.json().get("models", [])]


def pull_model(name):
    with httpx.stream("POST", f"{BASE}/api/pull", json={"name": name}, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                yield json.loads(line)


def delete_model(name):
    r = httpx.request("DELETE", f"{BASE}/api/delete", json={"name": name}, timeout=30.0)
    r.raise_for_status()


def embed(model, text):
    r = httpx.post(f"{BASE}/api/embeddings", json={"model": model, "prompt": text}, timeout=120.0)
    r.raise_for_status()
    return r.json()["embedding"]


def chat(model, messages, stream=True, known_embedding_models=()):
    if is_embedding_model(model, known_embedding_models):
        raise ValueError(
            f"'{model}' is an embedding-only model and cannot be used for chat. "
            "Run `freeai model use <name>` to pick a chat model."
        )
    payload = {"model": model, "messages": messages, "stream": stream}
    with httpx.stream("POST", f"{BASE}/api/chat", json=payload, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                yield chunk
            if data.get("done"):
                break


def chat_with_usage(model, messages, known_embedding_models=()):
    """Like chat(stream=False) but also returns token usage from the final chunk."""
    if is_embedding_model(model, known_embedding_models):
        raise ValueError(
            f"'{model}' is an embedding-only model and cannot be used for chat. "
            "Run `freeai model use <name>` to pick a chat model."
        )
    payload = {"model": model, "messages": messages, "stream": True}
    text, usage = [], {"prompt_tokens": 0, "completion_tokens": 0}
    with httpx.stream("POST", f"{BASE}/api/chat", json=payload, timeout=None) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                text.append(chunk)
            if data.get("done"):
                usage["prompt_tokens"] = data.get("prompt_eval_count", 0)
                usage["completion_tokens"] = data.get("eval_count", 0)
                break
    return "".join(text), usage
