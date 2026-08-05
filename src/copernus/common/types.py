# This file holds the small data shapes (like Event and Result) that every part of the app shares.
"""Shared types. No I/O, no domain logic — just the vocabulary every module speaks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class Event:
    """A request routed through the engine.

    ``type`` is a dotted name, ``<module>.<action>``, which is how the engine
    picks a handler. ``correlation_id`` threads through logs and the audit
    trail so one user action can be reconstructed end to end.
    """

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    user_id: str | None = None
    correlation_id: str | None = None

    @property
    def module(self) -> str:
        """The module half of the event type."""
        return self.type.split(".", 1)[0]


@dataclass(frozen=True, slots=True)
class Result[T]:
    """Success or failure, without raising across a module boundary.

    Modules return this rather than raising, so that one module's failure
    cannot unwind another module's call stack (constraint C-09). The engine
    still catches exceptions as a backstop, but a module that returns
    ``Result.err`` has failed deliberately and can say why.
    """

    ok: bool
    value: T | None = None
    error: str | None = None
    error_code: str | None = None

    @classmethod
    def success(cls, value: T) -> Result[T]:
        return cls(ok=True, value=value)

    @classmethod
    def err(cls, message: str, code: str | None = None) -> Result[T]:
        # A failure with no message is the "Something went wrong" that rule
        # §7.7 exists to prevent, so the message is required, not optional.
        if not message:
            raise ValueError("A Result error must carry a message (ARCHITECTURE.md §7.7)")
        return cls(ok=False, error=message, error_code=code)
