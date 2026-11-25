from contextlib import contextmanager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webdriver import WebDriver

import config
from utils.logger import get_logger

logger = get_logger(__name__)


def create_driver(headless: bool = config.HEADLESS) -> WebDriver:
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1280,1000")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(0)   # we use explicit waits only; mixing the two causes odd delays
    logger.info("Chrome started (headless=%s)", headless)
    return driver


@contextmanager
def browser_session(headless: bool = config.HEADLESS):
    driver = create_driver(headless)
    try:
        yield driver
    finally:
        driver.quit()
        logger.info("Chrome closed")