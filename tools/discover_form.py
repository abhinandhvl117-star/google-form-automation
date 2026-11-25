import json
import re
from collections import Counter

from selenium.webdriver.support.ui import WebDriverWait

import config
from automation.browser import browser_session
from utils.logger import get_logger

logger = get_logger("discover")

WIDGETS = {0: "text", 1: "text", 2: "radio", 3: "dropdown", 4: "checkbox"}
PAGE_BREAK = 8
OUTPUT = config.DATA_DIR / "questions.generated.json"


def extract_items(html: str) -> list:
    match = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(.*?);\s*</script>", html, re.S)
    if not match:
        raise SystemExit("Could not find form data in the page source")
    return json.loads(match.group(1))[1][1]


def split_pages(items: list) -> list[list[tuple]]:
    pages, current = [], []
    for item in items:
        kind = item[3]
        if kind == PAGE_BREAK:
            pages.append(current)
            current = []
            continue
        if kind not in WIDGETS:
            logger.warning("Skipping unsupported item type %s: %r", kind, item[1])
            continue
        entry = item[4][0]
        options = [o[0] for o in (entry[1] or []) if o[0]]
        current.append((item[1] or "", WIDGETS[kind], options, bool(entry[2])))
    pages.append(current)
    return [p for p in pages if p]


def build(pages: list[list[tuple]]) -> dict:
    counts = Counter(tuple(opts) for page in pages for _, _, opts, _ in page if opts)
    scales, names = {}, {}
    for opts, n in counts.items():
        if n >= 2:
            name = f"scale_{len(scales) + 1}"
            scales[name], names[opts] = list(opts), name

    out_pages = {}
    for p, page in enumerate(pages, 1):
        questions = {}
        for q, (label, widget, options, required) in enumerate(page, 1):
            entry = {"label": label, "type": widget, "required": required}
            if widget == "text":
                entry["validation"] = {}
            else:
                entry["max_selections"] = 1
                key = tuple(options)
                if key in names:
                    entry["scale"] = names[key]
                else:
                    entry["options"] = options
            questions[f"p{p}_q{q}"] = entry
        out_pages[f"page_{p}"] = {"title": f"Page {p}", "questions": questions}
    return {"scales": scales, "pages": out_pages}


def main() -> None:
    with browser_session() as driver:
        driver.get(config.FORM_URL)
        WebDriverWait(driver, config.DEFAULT_WAIT_TIMEOUT).until(
            lambda d: "FB_PUBLIC_LOAD_DATA_" in d.page_source)
        items = extract_items(driver.page_source)

    data = build(split_pages(items))
    OUTPUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(p["questions"]) for p in data["pages"].values())
    logger.info("Wrote %s (%d pages, %d questions, %d scales)",
                OUTPUT.name, len(data["pages"]), total, len(data["scales"]))


if __name__ == "__main__":
    main()