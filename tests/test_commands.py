"""Day 35 guard: the slash popup is prompt_toolkit completion data, never printed
output, so it cannot stack/duplicate on resize (resolved by architecture)."""
from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

from freecode.commands import CommandCompleter


def _complete(text):
    return list(CommandCompleter().get_completions(Document(text), None))


def test_popup_yields_completion_objects_not_prints():
    out = _complete("/mod")
    assert out, "expected completions for /mod"
    assert all(isinstance(c, Completion) for c in out)


def test_popup_filters_on_prefix():
    texts = {c.text for c in _complete("/hist")}
    assert "history" in texts and "model" not in texts


if __name__ == "__main__":
    test_popup_yields_completion_objects_not_prints()
    test_popup_filters_on_prefix()
    print("ok")
