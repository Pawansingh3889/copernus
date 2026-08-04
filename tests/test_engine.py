"""Engine behaviour: routing, permissions, audit, and failure isolation."""

from __future__ import annotations

from typing import Any

import pytest

from copernus.common.errors import PermissionDeniedError
from copernus.common.types import Event, Result


@pytest.fixture
def engine():
    from copernus.engine import Engine

    return Engine()


async def ok_handler(event: Event, state: dict[str, Any]) -> Result[str]:
    return Result.success("routed")


async def exploding(event: Event, state: dict[str, Any]) -> Result[str]:
    raise RuntimeError("boom")


async def test_dispatch_routes_to_the_registered_handler(engine):
    engine.register("demo.query", ok_handler)

    result = await engine.dispatch(Event(type="demo.query"))

    assert result.ok
    assert result.value == "routed"


async def test_unknown_event_returns_an_error_not_an_exception(engine):
    result = await engine.dispatch(Event(type="nobody.home"))

    assert not result.ok
    assert result.error_code == "module_not_found"
    assert "nobody.home" in result.error


async def test_duplicate_registration_is_refused(engine):
    engine.register("demo.query", ok_handler)

    with pytest.raises(ValueError, match="already registered"):
        engine.register("demo.query", ok_handler)


async def test_permission_is_enforced_when_required(engine):
    engine.register("demo.secret", ok_handler, permission="demo.view")

    with pytest.raises(PermissionDeniedError):
        await engine.dispatch(Event(type="demo.secret"), granted=set())

    result = await engine.dispatch(Event(type="demo.secret"), granted={"demo.view"})
    assert result.ok


async def test_a_module_crash_is_isolated_and_does_not_propagate(engine):
    """Constraint C-09: one module's failure must not take the others down."""
    engine.register("bad.query", exploding)
    engine.register("good.query", ok_handler)

    result = await engine.dispatch(Event(type="bad.query"))

    assert not result.ok
    assert result.error_code == "module_degraded"
    assert engine.is_degraded("bad")
    # The healthy module keeps serving — that is the whole point.
    assert (await engine.dispatch(Event(type="good.query"))).ok


async def test_a_degraded_module_stops_serving_until_recovered(engine):
    engine.register("bad.query", exploding)
    await engine.dispatch(Event(type="bad.query"))

    assert not (await engine.dispatch(Event(type="bad.query"))).ok
    engine.recover("bad")
    assert not engine.is_degraded("bad")


async def test_every_dispatch_is_audited(engine):
    """Rule §7.3 — no request without audit, including the ones that fail."""
    engine.register("demo.query", ok_handler)

    await engine.dispatch(Event(type="demo.query", user_id="u1", correlation_id="c1"))
    await engine.dispatch(Event(type="nobody.home", user_id="u2"))

    trail = engine.audit_trail()
    assert [entry["event"] for entry in trail] == ["demo.query", "nobody.home"]
    assert trail[0]["user_id"] == "u1"
    assert trail[0]["correlation_id"] == "c1"


async def test_the_audit_sink_receives_every_dispatch():
    """The sink is how the audit module persists the trail (§7.3)."""
    from copernus.engine import Engine

    seen: list[dict[str, Any]] = []

    async def sink(entry: dict[str, Any]) -> None:
        seen.append(entry)

    engine = Engine(audit_sink=sink)
    engine.register("demo.query", ok_handler)
    await engine.dispatch(Event(type="demo.query", user_id="u1"))

    assert seen == [{"event": "demo.query", "user_id": "u1", "correlation_id": None}]


async def test_the_audit_trail_cannot_be_mutated_by_a_caller(engine):
    engine.register("demo.query", ok_handler)
    await engine.dispatch(Event(type="demo.query"))

    engine.audit_trail().clear()

    assert len(engine.audit_trail()) == 1


def test_event_module_is_the_first_segment_of_the_type():
    assert Event(type="auth.login").module == "auth"
    assert Event(type="bare").module == "bare"


def test_a_result_error_must_carry_a_message():
    """Rule §7.7 — "Something went wrong" is not a failure message."""
    with pytest.raises(ValueError, match="must carry a message"):
        Result.err("")
