from dataclasses import dataclass

from models.question_bank import QuestionBank
from models.respondent import Respondent


@dataclass
class ValidationIssue:
    respondent_id: str
    page_id: str
    question_id: str
    kind: str   
    message: str    

    def __str__(self) -> str:
        return f"[{self.respondent_id}] {self.page_id}/{self.question_id}: {self.message}"


class RespondentValidator:
    def __init__(self, bank: QuestionBank):
        self.bank = bank

    def validate(self, respondent: Respondent, page_ids: list[str] | None = None) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for page_id in page_ids or self.bank.page_ids():
            issues.extend(self._validate_page(respondent, page_id))
        return issues

    def _validate_page(self, respondent: Respondent, page_id: str) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        questions = self.bank.get_page(page_id)
        given = respondent.get_page_answers(page_id)

        # 1. Every expected question: missing or invalid?
        for qid, question in questions.items():
            answer = given.get(qid)
            if answer is None or answer == "" or answer == []:
                if question.required:
                    issues.append(ValidationIssue(
                        respondent.id, page_id, qid, "missing",
                        f"no answer for required question: {question.label!r}"))
                continue
            issues.extend(self._validate_answer(respondent.id, question, answer))

        # 2. Answers for questions that don't exist (usually a typo in the ID)
        for qid in given:
            if qid not in questions:
                issues.append(ValidationIssue(
                    respondent.id, page_id, qid, "unknown_question",
                    "answer provided for a question not defined in questions.json"))
        return issues

    @staticmethod
    def _validate_answer(rid, question, answer) -> list[ValidationIssue]:
        selected = [answer] if isinstance(answer, str) else answer
        if not isinstance(selected, list) or not all(isinstance(s, str) for s in selected):
            return [ValidationIssue(rid, question.page_id, question.id, "bad_type",
                                    f"answer must be a string or list of strings, got {answer!r}")]

        issues = []
        if question.type in {"checkbox", "radio", "dropdown"}:
            if len(selected) > question.max_selections:
                issues.append(ValidationIssue(
                    rid, question.page_id, question.id, "too_many",
                    f"{len(selected)} selections given, max is {question.max_selections}"))
            for value in selected:
                if value not in question.options:
                    issues.append(ValidationIssue(
                        rid, question.page_id, question.id, "invalid_option",
                        f"{value!r} is not one of {list(question.options)}"))

        elif question.type == "text":
            if len(selected) != 1:
                return [ValidationIssue(rid, question.page_id, question.id, "too_many",
                                        "text question needs exactly one value")]
            rules = question.validation
            if rules.get("numeric"):
                try:
                    number = float(selected[0].strip())
                except ValueError:
                    return [ValidationIssue(rid, question.page_id, question.id, "invalid_value",
                                            f"{selected[0]!r} is not a number")]
                if "min" in rules and number < rules["min"]:
                    issues.append(ValidationIssue(rid, question.page_id, question.id, "invalid_value",
                                                  f"{number:g} is below the minimum {rules['min']}"))
                if "max" in rules and number > rules["max"]:
                    issues.append(ValidationIssue(rid, question.page_id, question.id, "invalid_value",
                                                  f"{number:g} is above the maximum {rules['max']}"))
        return issues