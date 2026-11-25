import re


def clean_label(text: str) -> str:
    """Collapse whitespace and drop the trailing ' *' Google adds to required questions."""
    text = re.sub(r"\s+", " ", text or "").strip()
    return re.sub(r"\s*\*$", "", text).strip()


def normalize_label(text: str) -> str:
    """Key used to match a label from questions.json against the live page."""
    return clean_label(text).casefold()