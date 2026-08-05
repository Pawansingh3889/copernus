# This file draws the web pages. It asks the same modules as the machine door,
# but answers with HTML instead of JSON.
"""HTML adapter: server-rendered pages, HTMX for the fragments.

Calls the same engine handlers as the JSON adapter. Renders HTML instead of
JSON; sets the same cookie. Validation lives once, in the service.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from copernus.common.types import Event

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

COOKIE = "copernus_session"


async def _current_user(request: Request):
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    result = await request.app.state.engine.dispatch(
        Event(type="auth.whoami", payload={"token": token})
    )
    return result.value


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = await _current_user(request)
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "home.html", {"user": user})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
async def login(request: Request, email: str = Form(), password: str = Form()):
    result = await request.app.state.engine.dispatch(
        Event(type="auth.login", payload={"email": email, "password": password})
    )
    if not result.ok:
        # HTMX swaps this into #message; the form and what was typed survive.
        return HTMLResponse(f'<p class="error">{result.error}</p>')
    settings = request.app.state.settings
    response = Response(headers={"HX-Redirect": "/"})
    response.set_cookie(
        COOKIE,
        result.value["token"],
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(COOKIE)
    if token:
        await request.app.state.engine.dispatch(Event(type="auth.logout", payload={"token": token}))
    response = Response(headers={"HX-Redirect": "/login"})
    response.delete_cookie(COOKIE)
    return response
