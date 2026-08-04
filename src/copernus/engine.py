"""The event engine.

Routes an event to a module handler and returns the result. That is all it
does. It stays under 100 lines because everything it might grow into belongs
to a module — and `scripts/check_module_size.py` enforces the limit rather
than trusting anyone to notice.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from copernus.common.errors import PermissionDeniedError
from copernus.common.logging import get_logger
from copernus.common.types import Event, Result

Handler = Callable[[Event, dict[str, Any]], Result[Any]]

logger = get_logger(__name__)


class Engine:
    """In-process event bus.

    Responsibilities, and nothing beyond them: route, check permission, log to
    audit, isolate module failures.
    """

    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self._handlers: dict[str, Handler] = {}
        self._permissions: dict[str, str] = {}
        self._degraded: set[str] = set()
        self._audit: list[dict[str, Any]] = []
        self.state: dict[str, Any] = state or {}

    def register(self, event_type: str, handler: Handler, permission: str | None = None) -> None:
        if event_type in self._handlers:
            raise ValueError(f"Handler already registered for {event_type!r}")
        self._handlers[event_type] = handler
        if permission:
            self._permissions[event_type] = permission

    def dispatch(self, event: Event, granted: set[str] | None = None) -> Result[Any]:
        """Route one event. Never raises — failures come back as Result.err."""
        self._audit.append(
            {
                "event": event.type,
                "user_id": event.user_id,
                "correlation_id": event.correlation_id,
            }
        )

        handler = self._handlers.get(event.type)
        if handler is None:
            return Result.err(f"No handler registered for event {event.type!r}", "module_not_found")

        if event.module in self._degraded:
            return Result.err(
                f"Module {event.module!r} is degraded and not serving requests",
                "module_degraded",
            )

        required = self._permissions.get(event.type)
        if required and required not in (granted or set()):
            # Logged, not silent — an access denial nobody can see is an
            # access denial nobody can debug (§7.7).
            logger.warning("Permission denied for %s (needs %s)", event.type, required)
            raise PermissionDeniedError(f"Event {event.type!r} requires permission {required!r}")

        try:
            return handler(event, self.state)
        except Exception as exc:  # the isolation boundary (C-09)
            # One module's unhandled exception must not take the others down.
            # Mark it degraded, log the traceback in full, keep serving.
            self._degraded.add(event.module)
            logger.exception("Module %r raised handling %s", event.module, event.type)
            return Result.err(
                f"Module {event.module!r} failed handling {event.type!r}: {exc}",
                "module_degraded",
            )

    def audit_trail(self) -> list[dict[str, Any]]:
        """Append-only view of every dispatch (§7.3). Returns a copy."""
        return list(self._audit)

    def is_degraded(self, module: str) -> bool:
        return module in self._degraded

    def recover(self, module: str) -> None:
        """Clear the degraded mark after the cause has been fixed."""
        self._degraded.discard(module)
