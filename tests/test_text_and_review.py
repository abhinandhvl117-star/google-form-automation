import json

from automation.review import confirm_submission, render_summary
from models.question_bank import QuestionBank
from models.respondent import Respondent
from models.validator import RespondentValidator
from utils.text import clean_label, normalize_label

QUESTIONS = {
    "scales": {"yn": ["Yes", "No"]},
    "pages": {"page_1": {"title": "P1", "questions": {
        "p1_q1": {"label": "Age", "type": "text", "required": True,
                  "validation": {"numeric": True, "min": 18, "max": 70}},
        "p1_q2": {"label": "Employed?", "type": "radio", "scale": "yn"},
    }}},
}


def build(tmp_path):
    path = tmp_path / "q.json"
    path.write_text(json.dumps(QUESTIONS), encoding="utf-8")
    bank = QuestionBank(path)
    bank.load()
    return bank


def respondent(age, employed="Yes"):
    return Respondent("T1", "Synthetic", {"page_1": {"p1_q1": age, "p1_q2": employed}})


def test_valid_text_answer(tmp_path):
    assert RespondentValidator(build(tmp_path)).validate(respondent("25")) == []


def test_text_out_of_range_and_not_numeric(tmp_path):
    v = RespondentValidator(build(tmp_path))
    assert [i.kind for i in v.validate(respondent("12"))] == ["invalid_value"]
    assert [i.kind for i in v.validate(respondent("abc"))] == ["invalid_value"]


def test_label_normalisation():
    assert clean_label("  My   manager\n *") == "My manager"
    assert normalize_label("Gender *") == normalize_label("gender")


def test_confirmation_requires_exact_phrase(tmp_path):
    bank, r = build(tmp_path), respondent("25")
    assert confirm_submission(r, bank, input_fn=lambda _: "SUBMIT T1") is True
    assert confirm_submission(r, bank, input_fn=lambda _: "yes") is False


def test_summary_lists_answers(tmp_path):
    text = render_summary(respondent("25"), build(tmp_path))
    assert "Age" in text and "25" in text