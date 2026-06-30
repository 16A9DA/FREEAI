from pathlib import Path

from freecode import ollama_client

SKILLS_DIR = Path.home() / ".freecode" / "skills"

MATCH_SYSTEM = (
    "You match a coding task to relevant skills. You are given a task and a list "
    "of skills with descriptions. Return ONLY the names of skills relevant to the "
    "task, one per line, exactly as written. If none apply, return only the word "
    "'none'. No explanations, no other text."
)


_EXAMPLE_SKILL = """\
This skill defines general coding conventions and applies to most coding
tasks. This first paragraph is the description the model reads to decide
whether the skill is relevant, so keep it clear and specific.

Rules:
- Prefer small, readable functions over clever one-liners.
- Write a short comment only where intent is not obvious from the code.
- Match the style, naming, and structure of the surrounding code.
- Handle errors explicitly; never swallow exceptions silently.
- Add or update tests when you change behaviour.
"""


_PONYTAIL_SKILL = """\
Forces the laziest solution that actually works: simplest, shortest, most
minimal code. Force-included at the low assistance level to keep generated
code small.

Rules:
- Question whether the code needs to exist at all before writing it.
- Reuse a helper or pattern already in this codebase before adding one.
- Prefer the standard library, then a native platform feature, then an
  already-installed dependency. Never add a dependency for a few lines.
- No speculative abstractions: no interface with one implementation, no
  config for a value that never changes.
- Shortest working diff wins. Deletion over addition.
"""


def bootstrap_skills():
    """Create the skills dir with starter skills on first run. Returns True if created."""
    if SKILLS_DIR.exists():
        return False
    for name, body in (("general-coding", _EXAMPLE_SKILL), ("ponytail", _PONYTAIL_SKILL)):
        folder = SKILLS_DIR / name
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text(body)
    return True


def _first_paragraph(text):
    text = text.strip()
    # Skip a leading YAML frontmatter block (Claude skill format).
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:].strip()
    para = []
    for line in text.splitlines():
        if not line.strip():
            if para:
                break
            continue
        para.append(line.strip())
    return " ".join(para)


def list_skills():
    if not SKILLS_DIR.is_dir():
        return []
    skills = []
    for child in sorted(SKILLS_DIR.iterdir()):
        f = child / "SKILL.md"
        if child.is_dir() and f.is_file():
            skills.append(
                {"name": child.name, "path": str(f), "description": _first_paragraph(f.read_text())}
            )
    return skills


def match_skills(task, available_skills, model):
    if not available_skills:
        return []
    listing = "\n".join(f"- {s['name']}: {s['description']}" for s in available_skills)
    messages = [
        {"role": "system", "content": MATCH_SYSTEM},
        {"role": "user", "content": f"Task: {task}\n\nSkills:\n{listing}"},
    ]
    reply = "".join(ollama_client.chat(model, messages, stream=False))
    names = {s["name"] for s in available_skills}
    picked = []
    for line in reply.splitlines():
        cand = line.strip().lstrip("-").strip()
        if cand in names and cand not in picked:
            picked.append(cand)
    return picked


def load_skill_content(skill_name):
    f = SKILLS_DIR / skill_name / "SKILL.md"
    return f.read_text() if f.is_file() else ""


def skills_for_task(task, model):
    """Return (matched_names, prompt_text) for skills relevant to this task."""
    available = list_skills()
    matched = match_skills(task, available, model)
    if not matched:
        return [], ""
    blocks = [f"## Skill: {n}\n{load_skill_content(n)}" for n in matched]
    text = "Active skills (follow their instructions):\n\n" + "\n\n".join(blocks)
    return matched, text


def demo():
    md = "---\ndesc: x\n---\nFirst para line one.\nLine two.\n\nSecond para."
    assert _first_paragraph(md) == "First para line one. Line two."
    assert _first_paragraph("Just one line.") == "Just one line."
    skills = [{"name": "django-rest", "description": "Django REST APIs"}]

    class _Stub:
        @staticmethod
        def chat(model, messages, stream=True):
            yield "django-rest\nnonexistent"

    g = globals()
    real, g["ollama_client"] = g["ollama_client"], _Stub
    try:
        assert match_skills("build an API", skills, "m") == ["django-rest"]
        assert match_skills("anything", [], "m") == []
    finally:
        g["ollama_client"] = real
    print("ok")


if __name__ == "__main__":
    demo()
