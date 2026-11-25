import config
from automation.browser import browser_session

with browser_session() as driver:
    driver.get(config.FORM_URL)
    input("Form is open. Press Enter to close...")