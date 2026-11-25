import json
from pathlib import Path
from models.respondent import Respondent
from utils.logger import get_logger

logger = get_logger(__name__)

class RespondentDataError(Exception):
    """Raised when respondents.json is missing, malformed, or inconsistent"""
    
class RespondentManager:
    def __init__(self, file_path: Path):
        self.file_path = Path(file_path)
        self._respondents: dict[str, Respondent] = {}
        
    def load(self) -> list[Respondent]:
        try:
            with self.file_path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError as exc:
            raise RespondentDataError(f"Respondent file not found: {self.file_path}") from exc
        except json.JSONDecodeError as exc:
            raise RespondentDataError(
                f"Invalid JSON in {self.file_path} (line {exc.lineno}: {exc.msg})"
            ) from exc
        
        entries = raw.get("respondents") if isinstance(raw, dict) else None
        if not isinstance(entries, list):
            raise RespondentDataError("Top level must be on object with a 'respondents' list")
        
        loaded: dict[str, Respondent] = {}
        for index, entry in enumerate(entries):
            try:
                respondent = Respondent(
                    id=entry["id"],
                    name=entry["name"],
                    answers=entry["answers"],
                    source=entry.get("source", "synthetic"),
                )
            except KeyError as exc:
                raise RespondentDataError(
                    f"Respondent #{index} is missing required field {exc}"
                ) from exc
                
            if respondent.id in loaded:
                raise RespondentDataError(f"Duplicate respondent id: {respondent.id}")
            loaded[respondent.id] = respondent
            
        self._respondents = loaded
        logger.info("Loaded %d respondents from %s", len(loaded), self.file_path.name)
        return list(loaded.values())
    
    def get_by_id(self, respondent_id: str) -> Respondent | None:
        return self._respondents.get(respondent_id)
    
    def list_ids(self) -> list[str]:
        return list(self._respondents)