import json

import pytest

from models.question_bank import QuestionBank, QuestionDataError
from models.respondent import Respondent
from models.validator import RespondentValidator

QUESTIONS = {
    "scales": {"gtl": ["Rarely or never", "Seldom", "Occasionally", "Frequently", "Very frequently or always"]},
    "pages": {"page_2": {"title": "GTL", "questions": {
        "p2_q1": {"label": "Q1", "type": "checkbox", "max_selections": 1, "required": True, "scale": "gtl"},
        "p2_q2": {"label": "Q2", "type": "checkbox", "max_selections": 1, "required": True, "scale": "gtl"},
    }}},
}


@pytest.fixture
def validator(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    bank = QuestionBank(path)
    bank.load()
    return RespondentValidator(bank)


def make(answers):
    return Respondent("T1", "Synthetic", {"page_2": answers})


def test_valid_respondent_has_no_issues(validator):
    assert validator.validate(make({"p2_q1": "Seldom", "p2_q2": "Frequently"})) == []


def test_missing_answer_detected(validator):
    issues = validator.validate(make({"p2_q1": "Seldom"}))
    assert [i.kind for i in issues] == ["missing"]
    assert issues[0].question_id == "p2_q2"


def test_wrong_case_option_detected(validator):
    issues = validator.validate(make({"p2_q1": "seldom", "p2_q2": "Frequently"}))
    assert [i.kind for i in issues] == ["invalid_option"]


def test_too_many_selections_detected(validator):
    issues = validator.validate(make({"p2_q1": ["Seldom", "Frequently"], "p2_q2": "Seldom"}))
    assert "too_many" in [i.kind for i in issues]


def test_unknown_question_detected(validator):
    issues = validator.validate(make({"p2_q1": "Seldom", "p2_q2": "Seldom", "p2_q9": "Seldom"}))
    assert [i.kind for i in issues] == ["unknown_question"]


def test_unknown_scale_fails_at_load(tmp_path):
    bad = {"scales": {}, "pages": {"page_2": {"questions": {
        "p2_q1": {"label": "Q", "type": "checkbox", "scale": "nope"}}}}}
    path = tmp_path / "q.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(QuestionDataError, match="unknown scale"):
        QuestionBank(path).load()