"""Guard: a failed step's transcript is dropped so its error text does not
poison later steps (no whole-plan derail)."""
import json

from freecode import agent, ollama_client


def _run_two_steps(step1_replies, step2_reply):
    """Drive agent.run with a scripted model. Returns the history passed to the
    model at the start of step 2, to prove step 1's failure was rolled back."""
    replies = list(step1_replies)
    seen = {}

    def fake(model, history, known=()):  # noqa: ARG001
        # snapshot history the first time step 2 runs (user msg mentions step 2)
        if any("step 2" in m.get("content", "") for m in history) and "step2" not in seen:
            seen["step2"] = [dict(m) for m in history]
        text = replies.pop(0) if replies else step2_reply
        return text, {"prompt_tokens": 0, "completion_tokens": 0}

    orig = ollama_client.chat_with_usage
    ollama_client.chat_with_usage = fake
    try:
        agent.run(["do thing one", "do thing two"], "m")
    finally:
        ollama_client.chat_with_usage = orig
    return seen.get("step2", [])


def test_failed_step_not_carried_into_next():
    # Step 1 emits junk (no valid JSON) every iteration -> fails.
    junk = ["not json at all"] * 8
    hist = _run_two_steps(junk, json.dumps({"done": True}))
    # Step 2's history must contain only its own instruction, no step-1 poison.
    joined = " ".join(m.get("content", "") for m in hist)
    assert "step 2" in joined
    assert "not json" not in joined
    assert "step 1" not in joined


if __name__ == "__main__":
    test_failed_step_not_carried_into_next()
    print("ok")
