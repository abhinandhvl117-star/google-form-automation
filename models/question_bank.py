import json
from pathlib import Path
from models.question import Question
from utils.logger import get_logger
from utils.text import clean_label

logger = get_logger(__name__)

VALID_TYPES = {"checkbox", "radio", "dropdown", "text"}

class QuestionDataError(Exception):
    """Raised when questions.json is missing, malformed, or inconsistent."""

class QuestionBank:
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self._pages: dict[str, dict[str, Question]] = {}
        
    def load(self) -> None:
        try:
            with self.file_path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError as exc:
            raise QuestionDataError(f"Questions file not found: {self.file_path}") from exc
        except json.JSONDecodeError as exc:
            raise QuestionDataError(
                f"Invalid JSON in {self.file_path} (line {exc.lineno}): {exc.msg}"
            ) from exc
            
        scales = raw.get("scales", {})
        pages_raw = raw.get("pages")
        if not isinstance(pages_raw, dict):
            raise QuestionDataError("Top level must contain a 'pages' object")

        pages: dict[str, dict[str, Question]] = {}
        seen_ids: set[str] = set()
        
        for page_id, page in pages_raw.items():
            questions: dict[str, Question] = {}
            for qid, q in page.get("questions", {}).items():
                if qid in seen_ids:
                    raise QuestionDataError(f"Duplicate question id: {qid}")
                seen_ids.add(qid)
                questions[qid] = self._build_question(page_id, qid, q, scales)
            pages[page_id] = questions
        
        self._pages = pages
        total = sum(len(p) for p in pages.values())
        logger.info("Loaded %d questions across %d pages", total, len(pages))
        
    @staticmethod
    def _build_question(page_id: str, qid: str, q: dict, scales: dict) -> Question:
        try:
            label = q["label"]
            qtype = q["type"]
        except KeyError as exc:
            raise QuestionDataError(f"{qid}: missing field {exc}") from exc
        
        if qtype not in VALID_TYPES:
            raise QuestionDataError(f"{qid}: unkown type '{qtype}'")
        
        options: tuple[str, ...] = ()
        if "scale" in q:
            if q['scale'] not in scales:
                raise QuestionDataError(f"{qid}: unknown scale '{q['scale']}'")
            options = tuple(scales[q['scale']])
        elif "options" in q:
            options = tuple(q["options"])
            
        if qtype in {"checkbox", "radio", "dropdown"} and not options:
            raise QuestionDataError(f"{qid}: {qtype} question needs a scale or options")
        
        return Question(
            id=qid,
            page_id=page_id,
            label=clean_label(label),
            type=qtype,
            required=q.get("required", True),
            max_selections=q.get("max_selections", 1),
            options=options,
            validation=q.get("validation", {}),
        )

    def page_ids(self) -> list[str]:
        return list(self._pages)

    def get_page(self, page_id: str) -> dict[str, Question]:
        return self._pages.get(page_id, {})

    def get_question(self, page_id: str, question_id: str) -> Question | None:
        return self._pages.get(page_id, {}).get(question_id)
        