# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.auth_api_base import BaseAuthApi
import saas_identity_platform_fastapi.impl

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from saas_identity_platform_fastapi.models.extra_models import TokenModel  # noqa: F401
from typing import Any
from saas_identity_platform_fastapi.models.login_request import LoginRequest
from saas_identity_platform_fastapi.models.login_response import LoginResponse
from saas_identity_platform_fastapi.models.sessions_login_default_response import SessionsLoginDefaultResponse


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/api/v1/auth/login",
    responses={
        200: {"model": LoginResponse, "description": "The request has succeeded."},
        "default": {"model": SessionsLoginDefaultResponse, "description": "An unexpected error response."},
    },
    tags=["auth"],
    response_model_by_alias=True,
)
async def sessions_login(
    login_request: LoginRequest = Body(None, description=""),
) -> LoginResponse:
    if not BaseAuthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuthApi.subclasses[0]().sessions_login(login_request)


@router.post(
    "/api/v1/auth/logout",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
    },
    tags=["auth"],
    response_model_by_alias=True,
)
async def sessions_logout(
) -> None:
    if not BaseAuthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAuthApi.subclasses[0]().sessions_logout()
