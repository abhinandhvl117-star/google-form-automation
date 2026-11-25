from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

import config
from automation.errors import FormInteractionError, FormMismatchError
from automation.form_reader import (CHECKBOX, LISTBOX, OPTION, RADIO, TEXT_INPUT,
                                    ScrapedQuestion, option_text)
from models.question import Question
from utils.logger import get_logger

logger = get_logger(__name__)


class FormHandler:
    """Writes answers into the widgets of one question block."""

    def __init__(self, driver: WebDriver, timeout: int = config.DEFAULT_WAIT_TIMEOUT):
        self.driver = driver
        self.timeout = timeout

    def fill(self, live: ScrapedQuestion, question: Question, answer: str | list[str]) -> None:
        if live.widget != question.type:
            raise FormMismatchError(
                f"{question.id}: questions.json says '{question.type}' but the live form "
                f"uses '{live.widget}' for {live.label!r}"
            )
        values = [answer] if isinstance(answer, str) else list(answer)

        if live.widget in ("checkbox", "radio"):
            self._set_choices(live.element, live.widget, values, question.id)
        elif live.widget == "text":
            self._set_text(live.element, values[0], question.id)
        elif live.widget == "dropdown":
            self._set_dropdown(live.element, values[0], question.id)
        logger.debug("Filled %s with %s", question.id, values)

    #choices (checkbox / radio) 
    def _set_choices(self, block: WebElement, widget: str, values: list[str], qid: str) -> None:
        selector = CHECKBOX if widget == "checkbox" else RADIO
        options = block.find_elements(By.CSS_SELECTOR, selector)
        wanted = set(values)

        missing = wanted - {option_text(o) for o in options}
        if missing:
            raise FormMismatchError(f"{qid}: option(s) {sorted(missing)} not found on the live form")

        for option in options:
            want = option_text(option) in wanted
            is_on = option.get_attribute("aria-checked") == "true"
            if want == is_on:
                continue                       
            if widget == "radio" and not want:
                continue                       
            self._click(option)
            expected = "true" if want else "false"
            if not self._state_reached(option, "aria-checked", expected, seconds=2):
                logger.warning("%s: click had no effect, retrying with a JS click", qid)
                self.driver.execute_script("arguments[0].click();", option)
            self._wait_attribute(option, "aria-checked", expected, qid)

    # text
    def _set_text(self, block: WebElement, value: str, qid: str) -> None:
        field = block.find_element(By.CSS_SELECTOR, TEXT_INPUT)
        self._scroll_to(field)
        field.clear()
        field.send_keys(value)
        if field.get_attribute("value") != value:
            raise FormInteractionError(f"{qid}: typed {value!r} but the field shows "
                                       f"{field.get_attribute('value')!r}")

    #dropdown 
    def _set_dropdown(self, block: WebElement, value: str, qid: str) -> None:
        listbox = block.find_element(By.CSS_SELECTOR, LISTBOX)
        self._click(listbox)

        def visible_option(_):
            for opt in block.find_elements(By.CSS_SELECTOR, OPTION):
                if (opt.get_attribute("data-value") or "").strip() == value and opt.is_displayed():
                    return opt
            return False

        try:
            option = WebDriverWait(self.driver, self.timeout).until(visible_option)
        except TimeoutException as exc:
            raise FormMismatchError(f"{qid}: dropdown option {value!r} not found") from exc
        self._click(option)
        try:
            WebDriverWait(self.driver, self.timeout).until(lambda _: value in listbox.text)
        except TimeoutException as exc:
            raise FormInteractionError(f"{qid}: dropdown did not show {value!r} after selecting") from exc

    #helpers 
    def _scroll_to(self, element: WebElement) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    def _click(self, element: WebElement) -> None:
        self._scroll_to(element)
        try:
            element.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", element)

    def _state_reached(self, element, attr: str, expected: str, seconds: int) -> bool:
        try:
            WebDriverWait(self.driver, seconds).until(
                lambda _: element.get_attribute(attr) == expected
            )
            return True
        except TimeoutException:
            return False

    def _wait_attribute(self, element: WebElement, attr: str, expected: str, qid: str) -> None:
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda _: element.get_attribute(attr) == expected
            )
        except TimeoutException as exc:
            self._dump_debug(element, qid)
            raise FormInteractionError(
                f"{qid}: {attr} never became {expected!r} after clicking"
            ) from exc

    def _dump_debug(self, element: WebElement, qid: str) -> None:
        try:
            logger.error("%s option HTML: %s", qid, (element.get_attribute("outerHTML") or "")[:600])
            parent = self.driver.execute_script("return arguments[0].parentElement.outerHTML;", element)
            logger.error("%s parent HTML: %s", qid, (parent or "")[:900])
            config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
            shot = config.REPORT_DIR / f"fail_{qid}.png"
            self.driver.save_screenshot(str(shot))
            logger.error("Screenshot saved: %s", shot)
        except Exception:  # a debugging aid must never hide the real error
            logger.exception("Could not collect debug info")