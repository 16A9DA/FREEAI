import json

import httpx

BASE = "http://localhost:11434"


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


def chat(model, messages, stream=True):
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
