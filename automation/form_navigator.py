from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import config
from automation.errors import NavigationError
from automation.form_reader import HEADING, QUESTION_BLOCK
from utils.logger import get_logger

logger = get_logger(__name__)


class FormNavigator:
    """Opens the form, moves between pages, submits."""

    def __init__(self, driver: WebDriver, timeout: int = config.DEFAULT_WAIT_TIMEOUT):
        self.driver = driver
        self.timeout = timeout

    def open(self, url: str) -> None:
        if not url:
            raise NavigationError("config.FORM_URL is empty")
        self.driver.get(url)
        logger.info("Opened form")

    def next(self) -> None:
        before = self._page_signature()
        self._click_button("Next")
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda _: (sig := self._page_signature()) and sig != before
            )
        except TimeoutException as exc:
            errors = self.visible_errors()
            detail = f" Form shows: {errors}" if errors else ""
            raise NavigationError("Page did not change after clicking Next." + detail) from exc
        logger.info("Moved to next page")

    def submit(self) -> None:
        self._click_button("Submit")
        try:
            WebDriverWait(self.driver, self.timeout).until(
                lambda d: "formResponse" in d.current_url or "has been recorded" in d.page_source
            )
        except TimeoutException as exc:
            raise NavigationError("No confirmation after clicking Submit. "
                                  f"Form shows: {self.visible_errors()}") from exc
        logger.info("Form submitted")

    def visible_errors(self) -> list[str]:
        texts = []
        for el in self.driver.find_elements(By.CSS_SELECTOR, '[role="alert"]'):
            if el.is_displayed() and el.text.strip():
                texts.append(el.text.strip())
        return texts

    # helpers 
    def _click_button(self, label: str) -> None:
        xpath = f'//div[@role="button"][.//span[normalize-space()="{label}"]]'
        try:
            button = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
        except TimeoutException as exc:
            raise NavigationError(f"'{label}' button not found or not clickable") from exc
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        button.click()

    def _page_signature(self) -> tuple[str, ...]:
        """Headings of the questions currently visible: changes when the page changes."""
        try:
            blocks = self.driver.find_elements(By.CSS_SELECTOR, QUESTION_BLOCK)
            return tuple(
                h.text for b in blocks if b.is_displayed()
                for h in b.find_elements(By.CSS_SELECTOR, HEADING)[:1]
            )
        except StaleElementReferenceException:
            return ()