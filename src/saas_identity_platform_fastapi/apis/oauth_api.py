# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.oauth_api_base import BaseOauthApi
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
from saas_identity_platform_fastapi.models.authorize_code_request import AuthorizeCodeRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.o_auth_authorize200_response import OAuthAuthorize200Response
from saas_identity_platform_fastapi.models.token_request import TokenRequest
from saas_identity_platform_fastapi.models.token_response import TokenResponse


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.post(
    "/api/v1/oauth/authorize",
    responses={
        200: {"model": OAuthAuthorize200Response, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["oauth"],
    response_model_by_alias=True,
)
async def o_auth_authorize(
    authorize_code_request: AuthorizeCodeRequest = Body(None, description=""),
) -> OAuthAuthorize200Response:
    if not BaseOauthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOauthApi.subclasses[0]().o_auth_authorize(authorize_code_request)


@router.post(
    "/api/v1/oauth/token",
    responses={
        200: {"model": TokenResponse, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["oauth"],
    response_model_by_alias=True,
)
async def o_auth_token(
    token_request: TokenRequest = Body(None, description=""),
) -> TokenResponse:
    if not BaseOauthApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseOauthApi.subclasses[0]().o_auth_token(token_request)
