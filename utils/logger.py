import logging
from config import LOG_DIR

ROOT_NAME = "forms_automation"
_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

def _configure_root() -> logging.Logger:
    root = logging.getLogger(ROOT_NAME)
    if root.handlers:
        return root
    
    root.setLevel(logging.DEBUG)
    formatter = logging.Formatter(_FORMAT)
    
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)
    
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(LOG_DIR / "automation.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    root.addHandler(console)
    root.addHandler(file_handler)
    return root

def get_logger(name: str) -> logging.Logger:
    _configure_root()
    return logging.getLogger(f"{ROOT_NAME}.{name}")