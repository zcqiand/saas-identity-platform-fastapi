# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.admin_clients_api_base import BaseAdminClientsApi
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
from pydantic import StrictInt, StrictStr
from typing import Any, Optional
from saas_identity_platform_fastapi.models.admin_clients_list_clients200_response import AdminClientsListClients200Response
from saas_identity_platform_fastapi.models.admin_clients_set_client_status_request import AdminClientsSetClientStatusRequest
from saas_identity_platform_fastapi.models.create_o_auth_client_request import CreateOAuthClientRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.o_auth_client import OAuthClient
from saas_identity_platform_fastapi.models.update_o_auth_client_request import UpdateOAuthClientRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/admin/clients",
    responses={
        200: {"model": AdminClientsListClients200Response, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-clients"],
    response_model_by_alias=True,
)
async def admin_clients_list_clients(
    page: Optional[StrictInt] = Query(None, description="", alias="page"),
    page_size: Optional[StrictInt] = Query(None, description="", alias="pageSize"),
) -> AdminClientsListClients200Response:
    if not BaseAdminClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminClientsApi.subclasses[0]().admin_clients_list_clients(page, page_size)


@router.post(
    "/api/v1/admin/clients",
    responses={
        200: {"model": OAuthClient, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-clients"],
    response_model_by_alias=True,
)
async def admin_clients_create_client(
    create_o_auth_client_request: CreateOAuthClientRequest = Body(None, description=""),
) -> OAuthClient:
    if not BaseAdminClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminClientsApi.subclasses[0]().admin_clients_create_client(create_o_auth_client_request)


@router.get(
    "/api/v1/admin/clients/{clientId}",
    responses={
        200: {"model": OAuthClient, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-clients"],
    response_model_by_alias=True,
)
async def admin_clients_get_client(
    clientId: StrictStr = Path(..., description=""),
) -> OAuthClient:
    if not BaseAdminClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminClientsApi.subclasses[0]().admin_clients_get_client(clientId)


@router.delete(
    "/api/v1/admin/clients/{clientId}",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-clients"],
    response_model_by_alias=True,
)
async def admin_clients_delete_client(
    clientId: StrictStr = Path(..., description=""),
) -> None:
    if not BaseAdminClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminClientsApi.subclasses[0]().admin_clients_delete_client(clientId)


@router.patch(
    "/api/v1/admin/clients/{clientId}",
    responses={
        200: {"model": OAuthClient, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-clients"],
    response_model_by_alias=True,
)
async def admin_clients_update_client(
    clientId: StrictStr = Path(..., description=""),
    update_o_auth_client_request: UpdateOAuthClientRequest = Body(None, description=""),
) -> OAuthClient:
    if not BaseAdminClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminClientsApi.subclasses[0]().admin_clients_update_client(clientId, update_o_auth_client_request)


@router.patch(
    "/api/v1/admin/clients/{clientId}/status",
    responses={
        200: {"model": OAuthClient, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-clients"],
    response_model_by_alias=True,
)
async def admin_clients_set_client_status(
    clientId: StrictStr = Path(..., description=""),
    admin_clients_set_client_status_request: AdminClientsSetClientStatusRequest = Body(None, description=""),
) -> OAuthClient:
    if not BaseAdminClientsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminClientsApi.subclasses[0]().admin_clients_set_client_status(clientId, admin_clients_set_client_status_request)
