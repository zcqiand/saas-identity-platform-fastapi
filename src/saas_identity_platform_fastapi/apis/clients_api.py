# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.clients_api_base import BaseClientsApi
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
from pydantic import StrictStr
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.o_auth_client_public_info import OAuthClientPublicInfo


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/clients/{clientId}",
    responses={
        200: {"model": OAuthClientPublicInfo, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["clients"],
    response_model_by_alias=True,
)
async def clients_get_client(
    clientId: StrictStr = Path(..., description=""),
) -> OAuthClientPublicInfo:
    if not BaseClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseClientsApi.subclasses[0]().clients_get_client(clientId)
