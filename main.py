import argparse
import sys
import time

import config
from automation.browser import browser_session
from automation.review import auto_confirm, confirm_submission
from automation.runner import FormRunner
from models.question_bank import QuestionBank, QuestionDataError
from models.respondent_manager import RespondentDataError, RespondentManager
from models.validator import RespondentValidator
from utils.ledger import LedgerError, record_submission, was_submitted
from utils.logger import get_logger
from utils.report import write_report

logger = get_logger("main")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fill my own Google Form from respondent profiles.")
    p.add_argument("--list", action="store_true", help="list respondent IDs and exit")
    p.add_argument("-r", "--respondent", help="respondent ID, e.g. TEST_001")
    p.add_argument("--all", action="store_true", help="run every respondent, one after another")
    p.add_argument("--validate-only", action="store_true", help="validate answers, no browser")
    p.add_argument("--submit", action="store_true",
                   help="actually submit (default is a dry run that stops before Submit)")
    p.add_argument("--auto-submit", action="store_true",
                   help="with --submit: skip the typed confirmation")
    p.add_argument("--test-form", action="store_true",
                   help="use config.TEST_FORM_URL (a copy of the form)")
    p.add_argument("--headless", action="store_true", help="run Chrome without a window")
    p.add_argument("--force", action="store_true",
                   help="submit even if the ledger says this respondent was already submitted")
    p.add_argument("--delay", type=float, default=5.0,
                   help="seconds to wait between respondents in a batch (default 5)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    bank = QuestionBank(config.QUESTIONS_FILE)
    manager = RespondentManager(config.RESPONDENTS_FILE)
    try:
        bank.load()
        manager.load()
    except (QuestionDataError, RespondentDataError) as exc:
        logger.error("Startup failed: %s", exc)
        return 2

    if args.list:
        print("\n".join(manager.list_ids()))
        return 0

    if args.all:
        ids = manager.list_ids()
    elif args.respondent:
        ids = [args.respondent]
    else:
        logger.error("Pass --respondent <ID> or --all (see --list)")
        return 2

    respondents = []
    for rid in ids:
        respondent = manager.get_by_id(rid)
        if respondent is None:
            logger.error("Unknown respondent %r. Available: %s", rid, manager.list_ids())
            return 2
        respondents.append(respondent)

    # Validate everyone before opening a browser
    validator = RespondentValidator(bank)
    any_invalid = False
    for respondent in respondents:
        issues = validator.validate(respondent)
        if issues:
            any_invalid = True
            logger.error("%s has %d validation problem(s):", respondent.id, len(issues))
            for issue in issues:
                logger.error("  %s", issue)
        else:
            logger.info("%s: all answers valid", respondent.id)
    if any_invalid:
        logger.error("Fix the problems above, browser not opened")
        return 1
    if args.validate_only:
        return 0

    # Mode checks
    if args.auto_submit and not args.submit:
        logger.error("--auto-submit only makes sense together with --submit")
        return 2
    form_url = config.TEST_FORM_URL if args.test_form else config.FORM_URL
    if not form_url:
        logger.error("The form URL for this mode is empty in config.py")
        return 2
    if args.submit and not args.test_form:
        blocked = [r.id for r in respondents if r.source != "consented"]
        if blocked:
            logger.error(
                "Refusing to submit synthetic profiles to the live form: %s. "
                'Use --test-form, or set "source": "consented" on genuine consented responses.',
                blocked)
            return 1

    # Never submit the same respondent twice to the same form
    target = "test" if args.test_form else "live"
    if args.submit and not args.force:
        try:
            pending = []
            for respondent in respondents:
                if was_submitted(respondent.id, target):
                    logger.info("%s already submitted to the %s form, skipping (--force to repeat)",
                                respondent.id, target)
                else:
                    pending.append(respondent)
        except LedgerError as exc:
            logger.error("%s", exc)
            return 2
        respondents = pending
        if not respondents:
            logger.info("Nothing left to submit")
            return 0

    results = []
    for index, respondent in enumerate(respondents):
        with browser_session(headless=args.headless) as driver:
            result = FormRunner(
                driver, bank,
                dry_run=not args.submit,
                confirm=auto_confirm if args.auto_submit else confirm_submission,
                form_url=form_url,
            ).run(respondent)
        report = write_report(result)
        results.append(result)
        logger.info("%s -> %s (report: %s)", respondent.id, result.status, report.name)

        if result.status == "submitted":
            record_submission(respondent.id, target)
        if result.status == "failed":
            logger.error("Stopping batch after failure: %s", result.error)
            break
        if index < len(respondents) - 1 and args.delay:
            time.sleep(args.delay)

    print("\nSUMMARY")
    for r in results:
        print(f"  {r.respondent_id:<10} {r.status:<18} {r.error or ''}")
    ok = {"dry_run_complete", "submitted", "cancelled"}
    return 0 if all(r.status in ok for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())