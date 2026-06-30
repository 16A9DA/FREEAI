"""Assistance levels (Day 18): low, full, ultra.

Always-on. One level maps to three knobs:
  code_minimalism           - force-include the ponytail skill so the model writes the least code.
  compression_aggressiveness- passed to compress_output for every tool result in the agent loop.
  response_style            - prepended to the system prompt to set how the model talks.
"""
from freecode import skills

_PROFILES = {
    "low": {
        "code_minimalism": True,
        "compression_aggressiveness": "high",
        "response_style": "ultra",
    },
    "full": {
        "code_minimalism": False,
        "compression_aggressiveness": "moderate",
        "response_style": "normal",
    },
    "ultra": {
        "code_minimalism": False,
        "compression_aggressiveness": "low",
        "response_style": "verbose",
    },
}

_STYLE_PROMPT = {
    "ultra": "Answer as tersely as possible. Drop articles, filler, and hedging. "
             "Keep all technical content, code, and exact error strings intact.",
    "normal": "",
    "verbose": "Favour thorough, high-quality work: explain non-obvious reasoning, write "
               "clear comments, handle errors explicitly, and add defensive checks where they help.",
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
