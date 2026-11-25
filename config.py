from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
QUESTIONS_FILE = DATA_DIR / "questions.json"
RESPONDENTS_FILE = DATA_DIR / "respondents.json"

LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

FORM_URL = ""
TEST_FORM_URL = "" 
DEFAULT_WAIT_TIMEOUT = 10
HEADLESS = False