# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.me_api_base import BaseMeApi
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
from typing import Dict, List, Optional
from saas_identity_platform_fastapi.models.current_user import CurrentUser
from saas_identity_platform_fastapi.models.effective_menu_node import EffectiveMenuNode
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.switch_tenant_response import SwitchTenantResponse
from saas_identity_platform_fastapi.models.tenant_membership import TenantMembership


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/me",
    responses={
        200: {"model": CurrentUser, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["me"],
    response_model_by_alias=True,
)
async def me_whoami(
) -> CurrentUser:
    if not BaseMeApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseMeApi.subclasses[0]().me_whoami()


@router.get(
    "/api/v1/me/menus",
    responses={
        200: {"model": Dict[str, List[EffectiveMenuNode]], "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["me"],
    response_model_by_alias=True,
)
async def me_get_my_menus(
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
) -> Dict[str, List[EffectiveMenuNode]]:
    if not BaseMeApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseMeApi.subclasses[0]().me_get_my_menus(client_id)


@router.get(
    "/api/v1/me/tenants",
    responses={
        200: {"model": List[TenantMembership], "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["me"],
    response_model_by_alias=True,
)
async def me_list_my_tenants(
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
) -> List[TenantMembership]:
    if not BaseMeApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseMeApi.subclasses[0]().me_list_my_tenants(client_id)


@router.post(
    "/api/v1/me/tenants/{tenantId}/switch",
    responses={
        200: {"model": SwitchTenantResponse, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["me"],
    response_model_by_alias=True,
)
async def me_switch_tenant(
    tenantId: StrictStr = Path(..., description=""),
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
) -> SwitchTenantResponse:
    if not BaseMeApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseMeApi.subclasses[0]().me_switch_tenant(tenantId, client_id)
