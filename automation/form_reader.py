from dataclasses import dataclass, field

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from automation.errors import FormStructureError
from utils.logger import get_logger
from utils.text import clean_label

logger = get_logger(__name__)

QUESTION_BLOCK = '[role="listitem"]'
HEADING = '[role="heading"]'
CHECKBOX = '[role="checkbox"]'
RADIO = '[role="radio"]'
LISTBOX = '[role="listbox"]'
OPTION = '[role="option"]'
TEXT_INPUT = 'input[type="text"], input[type="number"], textarea'


@dataclass
class ScrapedQuestion:
    label: str
    widget: str                      
    options: list[str]
    element: WebElement = field(repr=False, compare=False)


def option_text(element: WebElement) -> str:
    return (
        element.get_attribute("data-answer-value")
        or element.get_attribute("data-value")
        or element.get_attribute("aria-label")
        or ""
    ).strip()


class FormReader:
    """Read-only: reports which questions are on the page currently shown."""

    def __init__(self, driver: WebDriver, timeout: int = config.DEFAULT_WAIT_TIMEOUT):
        self.driver = driver
        self.timeout = timeout

    def wait_for_questions(self) -> None:
        try:
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, QUESTION_BLOCK))
            )
        except TimeoutException as exc:
            raise FormStructureError("No question blocks found on the page") from exc

    def read_current_page(self) -> list[ScrapedQuestion]:
        self.wait_for_questions()
        scraped = []
        for block in self.driver.find_elements(By.CSS_SELECTOR, QUESTION_BLOCK):
            if not block.is_displayed():          
                continue
            question = self._read_block(block)
            if question:
                scraped.append(question)
        logger.info("Read %d questions from the current page", len(scraped))
        for q in scraped:
            logger.debug("  [%s] %s -> %s", q.widget, q.label, q.options)
        return scraped

    @staticmethod
    def _read_block(block: WebElement) -> ScrapedQuestion | None:
        headings = block.find_elements(By.CSS_SELECTOR, HEADING)
        if not headings:
            return None
        label = clean_label(headings[0].text)
        if not label:
            return None

        if choices := block.find_elements(By.CSS_SELECTOR, CHECKBOX):
            widget, options = "checkbox", [option_text(c) for c in choices]
        elif choices := block.find_elements(By.CSS_SELECTOR, RADIO):
            widget, options = "radio", [option_text(c) for c in choices]
        elif block.find_elements(By.CSS_SELECTOR, LISTBOX):
            widget = "dropdown"
            options = [option_text(o) for o in block.find_elements(By.CSS_SELECTOR, OPTION)]
            options = [o for o in options if o]
        elif block.find_elements(By.CSS_SELECTOR, TEXT_INPUT):
            widget, options = "text", []
        else:
            return None
        return ScrapedQuestion(label=label, widget=widget, options=options, element=block)