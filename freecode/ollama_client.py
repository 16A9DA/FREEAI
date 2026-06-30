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
