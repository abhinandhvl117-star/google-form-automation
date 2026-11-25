import json
import pytest
from models.respondent import Respondent
from models.respondent_manager import RespondentDataError, RespondentManager

def write_json(tmp_path, payload):
    path = tmp_path / "respondents.json"
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path

def valid_entry(rid="TEST_001"):
    return {"id": rid, "name": "Synthentic", "answers": {"page_2": {"p2_q1": "Frequently"}}}

def test_get_answer_returns_value_or_none():
    r = Respondent("T1", "x", {"page_2": {"p2_q1": "Frequently"}})
    assert r.get_answer("page_2", "p2_q1") == "Frequently"
    assert r.get_answer("page_2", "p2_q9") is None
    assert r.get_answer("page_9", "p9_q1") is None
    
def test_load_and_get_by_id(tmp_path):
    path = write_json(tmp_path, {"respondents": [valid_entry("A"), valid_entry("B")]})
    manager = RespondentManager(path)
    manager.load()
    assert manager.list_ids() == ["A", "B"]
    assert manager.get_by_id("B").id == "B"
    assert manager.get_by_id("nope") is None


def test_duplicate_ids_rejected(tmp_path):
    path = write_json(tmp_path, {"respondents": [valid_entry("A"), valid_entry("A")]})
    with pytest.raises(RespondentDataError, match="Duplicate"):
        RespondentManager(path).load()


def test_missing_field_rejected(tmp_path):
    path = write_json(tmp_path, {"respondents": [{"id": "A", "name": "x"}]})
    with pytest.raises(RespondentDataError, match="answers"):
        RespondentManager(path).load()


def test_missing_file_rejected(tmp_path):
    with pytest.raises(RespondentDataError, match="not found"):
        RespondentManager(tmp_path / "nope.json").load()


def test_invalid_json_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(RespondentDataError, match="Invalid JSON"):
        RespondentManager(path).load()
    