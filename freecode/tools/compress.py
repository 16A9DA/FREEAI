"""Tool-output compression for the agent loop.

compress_output shrinks large tool results before they are fed back to the model,
keeping the head and stashing the full text so it can be pulled back on demand.
Aggressiveness comes from the active assistance level (Day 18).
"""
import ast
import hashlib
import json
import re

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


# --- Day 17 headroom pipeline: route a chunk to the right compressor, store the original in
# the CCR store under an 8-char hash embedded in the output so the model can retrieve it. ---

def store_original(content):
    """Hash content, keep the original in the CCR store, return the short hash."""
    h = hashlib.sha1(content.encode("utf-8", "replace")).hexdigest()[:8]
    _ORIGINALS[h] = content
    return h


def _ratio(before, after):
    return 0.0 if not before else round(1 - len(after) / len(before), 3)


class ContentRouter:
    """Detect a chunk's type so the caller picks the matching compressor."""

    _CODE = re.compile(r"^\s*(def |class |async def |function |func |import |from )")

    def route(self, chunk):
        stripped = chunk.lstrip()
        if stripped[:1] in "{[":
            try:
                json.loads(stripped)
                return "json"
            except ValueError:
                pass
        if any(self._CODE.match(line) for line in chunk.splitlines()):
            return "code"
        return "prose"


class SmartCrusher:
    """JSON: drop empty values, flatten single-key nesting, truncate long strings, compact."""

    def _clean(self, obj):
        if isinstance(obj, dict):
            cleaned = {}
            for k, v in obj.items():
                v = self._clean(v)
                if v in ("", None, [], {}):
                    continue
                cleaned[k] = v
            if len(cleaned) == 1:  # flatten one level of single-key nesting
                (only,) = cleaned.values()
                if isinstance(only, dict):
                    return only
            return cleaned
        if isinstance(obj, list):
            return [self._clean(v) for v in obj]
        if isinstance(obj, str) and len(obj) > 200:
            return obj[:200] + "..."
        return obj

    def compress(self, text):
        try:
            data = json.loads(text)
        except ValueError:
            return text, 0.0
        out = json.dumps(self._clean(data), separators=(",", ":"))
        return out, _ratio(text, out)


class CodeCompressor:
    """Code: emit a structural summary of defs/classes (name + first docstring line)."""

    def compress(self, text):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            out = "\n".join(text.splitlines()[:30])
            return out, _ratio(text, out)
        lines = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                kind = "class" if isinstance(node, ast.ClassDef) else "def"
                doc = ast.get_docstring(node) or ""
                summary = doc.splitlines()[0] if doc else ""
                lines.append(f"{kind} {node.name}: {summary}".rstrip(": ").rstrip())
        out = "\n".join(lines) or "\n".join(text.splitlines()[:30])
        return out, _ratio(text, out)


class ProseCompressor:
    """Logs/text: strip ANSI, collapse blank runs, drop duplicate adjacent lines, cap 60 lines."""

    _ANSI = re.compile(r"\x1b\[[0-9;]*m")

    def compress(self, text):
        t = self._ANSI.sub("", text)
        t = re.sub(r"\n{3,}", "\n\n", t)
        deduped = []
        for line in t.splitlines():
            if not deduped or deduped[-1] != line:
                deduped.append(line)
        if len(deduped) > 60:
            removed = len(deduped) - 60
            deduped = deduped[:60] + [f"... [{removed} lines removed]"]
        out = "\n".join(deduped)
        return out, _ratio(text, out)


_ROUTER = ContentRouter()
_COMPRESSORS = {"json": SmartCrusher(), "code": CodeCompressor(), "prose": ProseCompressor()}


def compress_chunk(content):
    """Route, compress, and CCR-store one chunk. Returns dict with type/content/hash/ratio."""
    ctype = _ROUTER.route(content)
    compressed, ratio = _COMPRESSORS[ctype].compress(content)
    h = store_original(content)
    return {"type": ctype, "content": f"# ccr:{h}\n{compressed}", "hash": h, "ratio": ratio}


def demo():
    _ORIGINALS.clear()
    big = "x" * 5000
    out = compress_output(big, "high")
    assert "truncated" in out and len(out) < len(big)
    assert retrieve_original("c1") == big
    assert compress_output("short", "high") == "short"
    assert compress_output(big, "low") == big  # low passes through under the 1M cap
    assert compress_output('{\n  "a":  1\n}', "high") == '{"a":1}'

    assert _ROUTER.route('{"a": 1}') == "json"
    assert _ROUTER.route("def f():\n    pass") == "code"
    assert _ROUTER.route("just some log text") == "prose"
    c = compress_chunk("def f(x):\n    \"\"\"Add one.\"\"\"\n    return x + 1\n")
    assert c["type"] == "code" and "def f: Add one." in c["content"]
    assert retrieve_original(c["hash"]).startswith("def f(x)")
    j, r = SmartCrusher().compress('{"a": 1, "b": "", "c": null}')
    assert j == '{"a":1}' and r > 0
    p, _ = ProseCompressor().compress("a\na\n\n\n\nb")
    assert p == "a\n\nb"
    print("ok")


if __name__ == "__main__":
    demo()
