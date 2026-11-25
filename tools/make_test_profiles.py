import json
import shutil

import config
from models.question_bank import QuestionBank

PROFILES = [
    ("TEST_001", "Synthetic Test Respondent 1", "middle"),
    ("TEST_002", "Synthetic Test Respondent 2", "alternating"),
]


def pick_choice(strategy: str, options: tuple[str, ...], position: int) -> str:
    if not options:
        return ""
    if strategy == "middle":
        return options[len(options) // 2]
    return options[0] if position % 2 == 0 else options[-1]


def pick_text(strategy: str, rules: dict) -> str:
    if rules.get("numeric") and "min" in rules and "max" in rules:
        lo, hi = rules["min"], rules["max"]
        value = (lo + hi) // 2 if strategy == "middle" else lo + (hi - lo) // 4
        return str(int(value))
    return ""   # unknown free text: fill in by hand


def main() -> None:
    bank = QuestionBank(config.QUESTIONS_FILE)
    bank.load()

    path = config.RESPONDENTS_FILE
    existing: dict[str, dict] = {}
    if path.exists():
        shutil.copy(path, path.with_name(path.name + ".bak"))
        for r in json.loads(path.read_text(encoding="utf-8")).get("respondents", []):
            existing[r["id"]] = r.get("answers", {})

    respondents, blanks = [], []
    for rid, name, strategy in PROFILES:
        answers: dict[str, dict] = {}
        for page_id in bank.page_ids():
            page: dict = {}
            for position, (qid, q) in enumerate(bank.get_page(page_id).items()):
                value = (pick_text(strategy, q.validation) if q.type == "text"
                         else pick_choice(strategy, q.options, position))
                old = existing.get(rid, {}).get(page_id, {}).get(qid)
                page[qid] = old if old not in (None, "", []) else value
                if page[qid] == "":
                    blanks.append(f"{rid} {page_id}/{qid}: {q.label}")
            answers[page_id] = page
        respondents.append({"id": rid, "name": name, "source": "synthetic", "answers": answers})

    path.write_text(json.dumps({"respondents": respondents}, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    print(f"Wrote {path} with {len(respondents)} respondents")
    if blanks:
        print("\nFill these in by hand (free-text with no rules):")
        print("\n".join(f"  {b}" for b in blanks))


if __name__ == "__main__":
    main()