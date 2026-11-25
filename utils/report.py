import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import config


def write_report(result) -> Path:
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = config.REPORT_DIR / f"{result.respondent_id}_{stamp}.json"
    path.write_text(json.dumps(asdict(result), indent=2), encoding="utf-8")
    return path