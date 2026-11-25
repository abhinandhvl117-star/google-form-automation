class FormAutomationError(Exception):
    """Base class for all automation failures."""


class FormStructureError(FormAutomationError):
    """The page doesn't contain what we expected to find."""


class FormMismatchError(FormAutomationError):
    """questions.json and the live form disagree (labels, widget types, options)."""


class FormInteractionError(FormAutomationError):
    """A click or typed value didn't take effect."""


class NavigationError(FormAutomationError):
    """Moving between pages or submitting failed."""