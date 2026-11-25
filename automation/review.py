from models.question_bank import QuestionBank
from models.respondent import Respondent


def render_summary(respondent: Respondent, bank: QuestionBank) -> str:
    lines = [f"\nREVIEW: {respondent.id} ({respondent.name})"]
    for page_id in bank.page_ids():
        lines.append(f"\n== {page_id} ==")
        for qid, question in bank.get_page(page_id).items():
            answer = respondent.get_answer(page_id, qid)
            lines.append(f"  {qid}: {question.label}\n      -> {answer}")
    return "\n".join(lines)


def confirm_submission(respondent: Respondent, bank: QuestionBank, input_fn=input) -> bool:
    print(render_summary(respondent, bank))
    expected = f"SUBMIT {respondent.id}"
    typed = input_fn(f"\nType '{expected}' to submit for real (anything else cancels): ").strip()
    return typed == expected

def auto_confirm(respondent: Respondent, bank: QuestionBank) -> bool:
    """Print the review (it also lands in the log), then approve without asking."""
    print(render_summary(respondent, bank))
    return True