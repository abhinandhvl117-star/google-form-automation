from dataclasses import dataclass, field

Answer = str | list[str]

@dataclass
class Respondent:
    id: str
    name: str
    answers: dict[str, dict[str, Answer]] = field(default_factory=dict)
    source: str = "synthetic" 
    
    def get_answer(self, page_id: str, question_id: str) -> Answer | None:
        return self.answers.get(page_id, {}).get(question_id)
    
    def get_page_answers(self, page_id: str) -> dict[str, Answer]:
        return self.answers.get(page_id, {})
    