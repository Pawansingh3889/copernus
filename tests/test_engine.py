"""Engine behaviour: routing, permissions, audit, and failure isolation."""

from __future__ import annotations

import pytest

from copernus.common.errors import PermissionDeniedError
from copernus.common.types import Event, Result


@pytest.fixture
def engine():
    from copernus.engine import Engine

    return Engine()


def test_dispatch_routes_to_the_registered_handler(engine):
    engine.register("demo.query", lambda event, state: Result.success("routed"))

    result = engine.dispatch(Event(type="demo.query"))

    assert result.ok
    assert result.value == "routed"


def test_unknown_event_returns_an_error_not_an_exception(engine):
    result = engine.dispatch(Event(type="nobody.home"))

    assert not result.ok
    assert result.error_code == "module_not_found"
    assert "nobody.home" in result.error


def test_duplicate_registration_is_refused(engine):
    engine.register("demo.query", lambda event, state: Result.success(1))

    with pytest.raises(ValueError, match="already registered"):
        engine.register("demo.query", lambda event, state: Result.success(2))


def test_permission_is_enforced_when_required(engine):
    engine.register(
        "demo.secret", lambda event, state: Result.success("ok"), permission="demo.view"
    )

    with pytest.raises(PermissionDeniedError):
        engine.dispatch(Event(type="demo.secret"), granted=set())

    result = engine.dispatch(Event(type="demo.secret"), granted={"demo.view"})
    assert result.ok


def test_a_module_crash_is_isolated_and_does_not_propagate(engine):
    """Constraint C-09: one module's failure must not take the others down."""

    def exploding(event, state):
        raise RuntimeError("boom")

    engine.register("bad.query", exploding)
    engine.register("good.query", lambda event, state: Result.success("fine"))

    result = engine.dispatch(Event(type="bad.query"))

    assert not result.ok
    assert result.error_code == "module_degraded"
    assert engine.is_degraded("bad")
    # The healthy module keeps serving — that is the whole point.
    assert engine.dispatch(Event(type="good.query")).ok


def test_a_degraded_module_stops_serving_until_recovered(engine):
    def exploding(event, state):
        raise RuntimeError("boom")

    engine.register("bad.query", exploding)
    engine.dispatch(Event(type="bad.query"))

    assert not engine.dispatch(Event(type="bad.query")).ok
    engine.recover("bad")
    assert not engine.is_degraded("bad")


def test_every_dispatch_is_audited(engine):
    """Rule §7.3 — no request without audit, including the ones that fail."""
    engine.register("demo.query", lambda event, state: Result.success(1))

    engine.dispatch(Event(type="demo.query", user_id="u1", correlation_id="c1"))
    engine.dispatch(Event(type="nobody.home", user_id="u2"))

    trail = engine.audit_trail()
    assert [entry["event"] for entry in trail] == ["demo.query", "nobody.home"]
    assert trail[0]["user_id"] == "u1"
    assert trail[0]["correlation_id"] == "c1"


def test_the_audit_trail_cannot_be_mutated_by_a_caller(engine):
    engine.register("demo.query", lambda event, state: Result.success(1))
    engine.dispatch(Event(type="demo.query"))

    engine.audit_trail().clear()

    assert len(engine.audit_trail()) == 1


def test_event_module_is_the_first_segment_of_the_type():
    assert Event(type="auth.login").module == "auth"
    assert Event(type="bare").module == "bare"


def test_a_result_error_must_carry_a_message():
    """Rule §7.7 — "Something went wrong" is not a failure message."""
    with pytest.raises(ValueError, match="must carry a message"):
        Result.err("")
