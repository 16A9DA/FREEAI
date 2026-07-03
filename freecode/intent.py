import math
from freecode.ollama_client import get_embedding
from .ollama_client import embed

QUESTION_EXAMPLES = [
    "what model are you using right now",
    "what skill is currently active",
    "why did the last step fail",
    "how does the assistance level work",
    "are you using ultra mode",
    "what did you just change",
]

TASK_EXAMPLES = [
    "create a file called app.py",
    "fix the bug in the login form",
    "add input validation to this function",
    "build a website explaining LLMs",
    "why did the build fail, and can you fix it",
    "refactor this class to use composition",
]


_question_vectors = None
_task_vectors = None


def _ensure_anchors_loaded():
    """Lazily embed the reference examples exactly once."""
    global _question_vectors, _task_vectors
    if _question_vectors is None:
        _question_vectors = [get_embedding(t) for t in QUESTION_EXAMPLES]
        _task_vectors = [get_embedding(t) for t in TASK_EXAMPLES]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = math.sqrt(sum(x * x for x in a))
    magnitude_b = math.sqrt(sum(y * y for y in b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def _best_match_score(vector: list[float], anchor_vectors: list[list[float]]) -> float:
    return max(_cosine_similarity(vector, anchor) for anchor in anchor_vectors)


def classify_by_embedding(text: str) -> tuple[str, float]:

    _ensure_anchors_loaded()

    text_vector = get_embedding(text)

    question_score = _best_match_score(text_vector, _question_vectors)
    task_score = _best_match_score(text_vector, _task_vectors)

    if question_score > task_score:
        return "question", question_score - task_score
    else:
        return "task", task_score - question_score



_QUESTION_STARTERS = ("what", "why", "how", "is", "are", "do you", "can you")
_TASK_VERBS = ("create", "write", "add", "fix", "build", "delete", "run", "install")


def classify_by_keywords(text: str) -> str | None:
    low = text.strip().lower()

    starts_like_question = low.startswith(_QUESTION_STARTERS) or low.endswith("?")
    contains_task_verb = any(verb in low for verb in _TASK_VERBS)
    if starts_like_question and not contains_task_verb:
        return "question"
    if contains_task_verb and not starts_like_question:
        return "task"
    return None   



def classify_intent(text: str) -> str:
    result = classify_by_keywords(text)
    if result is not None:
        return result
    classification, confidence = classify_by_embedding(text)
    if confidence > 0.15:   
        return classification
    from freecode.planner import classify_with_model
    return classify_with_model(text)