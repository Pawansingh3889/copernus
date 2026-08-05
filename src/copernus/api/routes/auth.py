# This file is the machine door for logging in and out. The auth module does the real work.
"""JSON adapter for auth. The HTML adapter in ui/ calls the same handlers —
two thin skins over one service, never two services (the two-adapter rule)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from copernus.common.types import Event, Result

router = APIRouter(tags=["auth"])

_STATUS_BY_CODE = {
    "email_domain": 400,
    "weak_password": 400,
    "email_exists": 409,
    "invalid_credentials": 401,
    "account_inactive": 403,
    "not_found": 404,
    "module_not_found": 404,
    "module_degraded": 503,
}

COOKIE = "copernus_session"


def error_response(result: Result[Any]) -> JSONResponse:
    status = _STATUS_BY_CODE.get(result.error_code or "", 400)
    return JSONResponse(
        status_code=status, content={"error": result.error, "code": result.error_code}
    )


class RegisterBody(BaseModel):
    email: str
    password: str
    full_name: str


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/auth/register", status_code=201, response_model=None)
async def register(body: RegisterBody, request: Request) -> JSONResponse | dict[str, Any]:
    result = await request.app.state.engine.dispatch(
        Event(type="auth.register", payload=body.model_dump())
    )
    if not result.ok:
        return error_response(result)
    user = result.value
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@router.post("/auth/login", response_model=None)
async def login(
    body: LoginBody, request: Request, response: Response
) -> JSONResponse | dict[str, Any]:
    result = await request.app.state.engine.dispatch(
        Event(type="auth.login", payload=body.model_dump())
    )
    if not result.ok:
        return error_response(result)
    settings = request.app.state.settings
    response.set_cookie(
        COOKIE,
        result.value["token"],
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    user = result.value["user"]
    return {"email": user.email, "role": user.role.value}


@router.post("/auth/logout")
async def logout(request: Request, response: Response) -> dict[str, bool]:
    token = request.cookies.get(COOKIE)
    if token:
        await request.app.state.engine.dispatch(Event(type="auth.logout", payload={"token": token}))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/auth/me", response_model=None)
async def me(request: Request) -> JSONResponse | dict[str, Any]:
    token = request.cookies.get(COOKIE)
    if not token:
        return JSONResponse(status_code=401, content={"error": "Not logged in"})
    result = await request.app.state.engine.dispatch(
        Event(type="auth.whoami", payload={"token": token})
    )
    if result.value is None:
        return JSONResponse(status_code=401, content={"error": "Session expired"})
    user = result.value
    return {"email": user.email, "role": user.role.value}
