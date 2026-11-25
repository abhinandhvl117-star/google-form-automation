from dataclasses import dataclass, field
from datetime import datetime

from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver

import config
from automation.errors import FormAutomationError, FormMismatchError
from automation.form_handler import FormHandler
from automation.form_navigator import FormNavigator
from automation.form_reader import FormReader
from automation.review import confirm_submission, render_summary
from models.question_bank import QuestionBank
from models.respondent import Respondent
from utils.logger import get_logger
from utils.text import normalize_label

logger = get_logger(__name__)


@dataclass
class PageResult:
    page_id: str
    answered: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class RunResult:
    respondent_id: str
    status: str = "started"      
    pages: list[PageResult] = field(default_factory=list)
    error: str | None = None
    started_at: str = ""
    finished_at: str = ""


class FormRunner:
    def __init__(self, driver: WebDriver, bank: QuestionBank, dry_run: bool = True, confirm=confirm_submission, form_url=config.FORM_URL):
        self.bank = bank
        self.dry_run = dry_run
        self.confirm = confirm
        self.form_url = form_url
        self.reader = FormReader(driver)
        self.handler = FormHandler(driver)
        self.navigator = FormNavigator(driver)

    def run(self, respondent: Respondent) -> RunResult:
        result = RunResult(respondent.id, started_at=datetime.now().isoformat(timespec="seconds"))
        try:
            self.navigator.open(config.FORM_URL)
            page_ids = self.bank.page_ids()
            for index, page_id in enumerate(page_ids):
                result.pages.append(self._fill_page(respondent, page_id))
                if index < len(page_ids) - 1:
                    self.navigator.next()

            if self.dry_run:
                print(render_summary(respondent, self.bank))
                logger.info("Dry run complete, nothing submitted")
                result.status = "dry_run_complete"
            elif self.confirm(respondent, self.bank):
                self.navigator.submit()
                result.status = "submitted"
            else:
                logger.info("Submission cancelled by user")
                result.status = "cancelled"
        except (FormAutomationError, WebDriverException) as exc:
            logger.error("Run failed for %s: %s", respondent.id, exc)
            result.status, result.error = "failed", str(exc).splitlines()[0]
        finally:
            result.finished_at = datetime.now().isoformat(timespec="seconds")
        return result

    def _fill_page(self, respondent: Respondent, page_id: str) -> PageResult:
        page = PageResult(page_id)
        expected = self.bank.get_page(page_id)
        live = {normalize_label(s.label): s for s in self.reader.read_current_page()}

        # Fail before touching anything if the live page doesn't match questions.json
        missing = [q.label for q in expected.values() if normalize_label(q.label) not in live]
        if missing:
            raise FormMismatchError(f"{page_id}: labels not found on the live page: {missing}")

        expected_keys = {normalize_label(q.label) for q in expected.values()}
        for key, scraped in live.items():
            if key not in expected_keys:
                page.warnings.append(f"live question not in questions.json: {scraped.label!r}")
                logger.warning("%s: %s", page_id, page.warnings[-1])

        for qid, question in expected.items():
            answer = respondent.get_answer(page_id, qid)
            if answer in (None, "", []):
                page.skipped += 1
                continue
            self.handler.fill(live[normalize_label(question.label)], question, answer)
            page.answered += 1
        logger.info("%s: %d answered, %d skipped", page_id, page.answered, page.skipped)
        return page