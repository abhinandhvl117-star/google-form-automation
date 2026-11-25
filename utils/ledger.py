import json
import os
from datetime import datetime

import config

LEDGER_FILE = config.DATA_DIR / "submitted_ledger.json"


class LedgerError(Exception):
    """The ledger file exists but can't be read."""


def _load() -> dict[str, str]:
    if not LEDGER_FILE.exists():
        return {}
    try:
        return json.loads(LEDGER_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError(
            f"{LEDGER_FILE.name} is corrupt. Fix it by hand, or delete it "
            "(deleting makes the tool forget every past submission)."
        ) from exc


def _key(respondent_id: str, target: str) -> str:
    return f"{target}:{respondent_id}"


def was_submitted(respondent_id: str, target: str) -> bool:
    return _key(respondent_id, target) in _load()


def record_submission(respondent_id: str, target: str) -> None:
    data = _load()
    data[_key(respondent_id, target)] = datetime.now().isoformat(timespec="seconds")
    tmp = LEDGER_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, LEDGER_FILE)       # atomic: never leaves a half-written ledger