import ast
import hashlib
import json
import re

_ORIGINALS = {}

_CAPS = {"high": 1500, "moderate": 6000, "low": 1_000_000}


def compress_output(text, aggressiveness="moderate"):
    text = "" if text is None else str(text)
    cap = _CAPS.get(aggressiveness, _CAPS["moderate"])
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
