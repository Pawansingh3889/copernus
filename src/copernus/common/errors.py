"""Domain errors.

Every error carries a code so the API can map it to a status without matching
on message text, and a message a human can act on (ARCHITECTURE.md §7.7).
"""

from __future__ import annotations


class CopernusError(Exception):
    """Base for every domain error."""

    code = "copernus_error"


class ModuleNotFoundError_(CopernusError):
    """No module registered for an event type."""

    code = "module_not_found"


class ModuleDegradedError(CopernusError):
    """The module raised and has been marked degraded.

    The engine isolates this so one module's failure does not take the others
    down with it (constraint C-09).
    """

    code = "module_degraded"


class PermissionDeniedError(CopernusError):
    """The caller lacks the permission this event requires."""

    code = "permission_denied"


class DataIntegrityError(CopernusError):
    """The source data is self-contradictory.

    Raised rather than silently corrected. A negative giveaway or a lot code
    that parses as a run number means something upstream is wrong, and papering
    over it produces a plausible number with no basis.
    """

    code = "data_integrity"
