from pathlib import Path

from freecode import ollama_client

SKILLS_DIR = Path.home() / ".freecode" / "skills"

MATCH_SYSTEM = (
    "You match a coding task to relevant skills. You are given a task and a list "
    "of skills with descriptions. Return ONLY the names of skills relevant to the "
    "task, one per line, exactly as written. If none apply, return only the word "
    "'none'. No explanations, no other text."
)


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
