# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.tenant_role_menus_api_base import BaseTenantRoleMenusApi
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
from typing import Any, Optional
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.role_menu_grant import RoleMenuGrant
from saas_identity_platform_fastapi.models.set_sys_role_menus_request import SetSysRoleMenusRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/tenants/{tenantId}/roles/{roleId}/menus",
    responses={
        200: {"model": RoleMenuGrant, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-role-menus"],
    response_model_by_alias=True,
)
async def tenant_role_menus_list_sys_role_menus(
    tenantId: StrictStr = Path(..., description=""),
    roleId: StrictStr = Path(..., description=""),
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
) -> RoleMenuGrant:
    if not BaseTenantRoleMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRoleMenusApi.subclasses[0]().tenant_role_menus_list_sys_role_menus(tenantId, roleId, client_id)


@router.put(
    "/api/v1/tenants/{tenantId}/roles/{roleId}/menus",
    responses={
        200: {"model": RoleMenuGrant, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-role-menus"],
    response_model_by_alias=True,
)
async def tenant_role_menus_set_sys_role_menus(
    tenantId: StrictStr = Path(..., description=""),
    roleId: StrictStr = Path(..., description=""),
    set_sys_role_menus_request: SetSysRoleMenusRequest = Body(None, description=""),
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
) -> RoleMenuGrant:
    if not BaseTenantRoleMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRoleMenusApi.subclasses[0]().tenant_role_menus_set_sys_role_menus(tenantId, roleId, set_sys_role_menus_request, client_id)


@router.delete(
    "/api/v1/tenants/{tenantId}/roles/{roleId}/menus",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-role-menus"],
    response_model_by_alias=True,
)
async def tenant_role_menus_clear_sys_role_menus(
    tenantId: StrictStr = Path(..., description=""),
    roleId: StrictStr = Path(..., description=""),
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
) -> None:
    if not BaseTenantRoleMenusApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRoleMenusApi.subclasses[0]().tenant_role_menus_clear_sys_role_menus(tenantId, roleId, client_id)
