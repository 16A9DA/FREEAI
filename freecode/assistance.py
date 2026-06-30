from freecode import skills

_PROFILES = {
    "low": {
        "code_minimalism": False,
        "compression_aggressiveness": "low",
        "response_style": "verbose",
    },
    "full": {
        "code_minimalism": True,
        "compression_aggressiveness": "moderate",
        "response_style": "normal",
    },
    "ultra": {
        "code_minimalism": True,
        "compression_aggressiveness": "high",
        "response_style": "ultra",
    },
}

_STYLE_PROMPT = {
    "ultra": (
        "Minimize text. Only essential explanation. "
        "Prefer compact code. No filler. "
        "Assume expert user."
    ),
    "normal": (
        "Balanced explanation and code. Keep clarity."
    ),
    "verbose": (
        "Explain step-by-step. Include reasoning, comments, and safety checks."
    ),
}


def get_assistance_profile(level):
    return dict(_PROFILES.get(level, _PROFILES["full"]))


def system_prefix(level):
    """Build the system-prompt prefix for an assistance level: response style plus, for
    code_minimalism, the force-included ponytail skill."""
    profile = get_assistance_profile(level)
    parts = []
    style = _STYLE_PROMPT.get(profile["response_style"], "")
    if style:
        parts.append(style)
    if profile["code_minimalism"]:
        ponytail = skills.load_skill_content("ponytail").strip()
        if ponytail:
            parts.append("Write the minimum code that works. Follow this skill:\n" + ponytail)
        else:
            parts.append("Write the minimum code that works: reuse existing code, prefer the "
                         "standard library, no speculative abstractions, shortest working diff.")
    return "\n\n".join(parts)


def demo():
    assert get_assistance_profile("low")["compression_aggressiveness"] == "high"
    assert get_assistance_profile("ultra")["response_style"] == "verbose"
    assert get_assistance_profile("bogus") == get_assistance_profile("full")
    assert system_prefix("full") == ""
    assert "minimum code" in system_prefix("low")
    assert "thorough" in system_prefix("ultra")
    print("ok")


if __name__ == "__main__":
    demo()
