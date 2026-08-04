"""FastAPI app factory — the composition root.

The one place allowed to import both adapters: it sits above api|ui in the
layers contract, so neither peer ever imports the other."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from copernus.common.db import make_engine, make_session_factory
from copernus.common.logging import configure
from copernus.config import Settings, load_settings
from copernus.engine import Engine
from copernus.modules import audit, auth, identity
from copernus.modules.audit.repository import make_sink


def build_engine(session_factory: Any, settings: Settings) -> Engine:
    """Every module registered, audit sink attached. One place, one wiring."""
    engine = Engine(
        state={"session_factory": session_factory, "settings": settings},
        audit_sink=make_sink(session_factory),
    )
    for module in (auth, identity, audit):
        for event_type, permission in module.PERMISSIONS.items():
            engine.register(event_type, module.handle, permission=permission)
    for event_type in ("auth.register", "auth.login", "auth.logout", "auth.whoami"):
        engine.register(event_type, auth.handle)
    return engine


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure(settings.log_level)

    db_engine = make_engine(settings.database_url)
    session_factory = make_session_factory(db_engine)

    app = FastAPI(title="Copernus", version="0.1.0")
    app.state.engine = build_engine(session_factory, settings)
    app.state.settings = settings

    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    from copernus.api.routes import auth as auth_api
    from copernus.ui.views import pages

    app.include_router(auth_api.router, prefix="/api/v1")
    app.include_router(pages.router)
    static_dir = Path(__file__).parent / "ui" / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    return app
