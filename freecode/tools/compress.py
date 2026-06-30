"""Tool-output compression for the agent loop.

compress_output shrinks large tool results before they are fed back to the model,
keeping the head and stashing the full text so it can be pulled back on demand.
Aggressiveness comes from the active assistance level (Day 18).
"""
import json

# ponytail: in-memory store, lost on process exit; persist to disk only if a session needs replay.
_ORIGINALS = {}

# Character budget per aggressiveness. Output longer than the cap is truncated.
_CAPS = {"high": 1500, "moderate": 6000, "low": 1_000_000}


def compress_output(text, aggressiveness="moderate"):
    text = "" if text is None else str(text)
    cap = _CAPS.get(aggressiveness, _CAPS["moderate"])
    # At high aggressiveness, collapse pretty-printed JSON to its compact form first.
    if aggressiveness == "high":
        text = _collapse_json(text)
    if len(text) <= cap:
        return text
    key = f"c{len(_ORIGINALS) + 1}"
    _ORIGINALS[key] = text
    dropped = len(text) - cap
    return f"{text[:cap]}\n... [truncated {dropped} chars; call retrieve_original('{key}') for full output]"


def retrieve_original(key):
    return _ORIGINALS.get(key, "")


def _collapse_json(text):
    stripped = text.strip()
    if not (stripped.startswith("{") or stripped.startswith("[")):
        return text
    try:
        return json.dumps(json.loads(stripped), separators=(",", ":"))
    except ValueError:
        return text


def demo():
    _ORIGINALS.clear()
    big = "x" * 5000
    out = compress_output(big, "high")
    assert "truncated" in out and len(out) < len(big)
    assert retrieve_original("c1") == big
    assert compress_output("short", "high") == "short"
    assert compress_output(big, "low") == big  # low passes through under the 1M cap
    assert compress_output('{\n  "a":  1\n}', "high") == '{"a":1}'
    print("ok")


if __name__ == "__main__":
    demo()
