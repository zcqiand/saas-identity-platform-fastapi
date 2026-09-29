# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.tenant_roles_api_base import BaseTenantRolesApi
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
from saas_identity_platform_fastapi.models.create_sys_role_request import CreateSysRoleRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.sys_role import SysRole
from saas_identity_platform_fastapi.models.tenant_roles_list_sys_roles200_response import TenantRolesListSysRoles200Response
from saas_identity_platform_fastapi.models.update_sys_role_request import UpdateSysRoleRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/tenants/{tenantId}/roles",
    responses={
        200: {"model": TenantRolesListSysRoles200Response, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-roles"],
    response_model_by_alias=True,
)
async def tenant_roles_list_sys_roles(
    tenantId: StrictStr = Path(..., description=""),
    client_id: Optional[StrictStr] = Query(None, description="", alias="clientId"),
    page: Optional[StrictInt] = Query(None, description="", alias="page"),
    page_size: Optional[StrictInt] = Query(None, description="", alias="pageSize"),
) -> TenantRolesListSysRoles200Response:
    if not BaseTenantRolesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRolesApi.subclasses[0]().tenant_roles_list_sys_roles(tenantId, client_id, page, page_size)


@router.post(
    "/api/v1/tenants/{tenantId}/roles",
    responses={
        200: {"model": SysRole, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-roles"],
    response_model_by_alias=True,
)
async def tenant_roles_create_sys_role(
    tenantId: StrictStr = Path(..., description=""),
    create_sys_role_request: CreateSysRoleRequest = Body(None, description=""),
) -> SysRole:
    if not BaseTenantRolesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRolesApi.subclasses[0]().tenant_roles_create_sys_role(tenantId, create_sys_role_request)


@router.get(
    "/api/v1/tenants/{tenantId}/roles/{roleId}",
    responses={
        200: {"model": SysRole, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-roles"],
    response_model_by_alias=True,
)
async def tenant_roles_get_sys_role(
    tenantId: StrictStr = Path(..., description=""),
    roleId: StrictStr = Path(..., description=""),
) -> SysRole:
    if not BaseTenantRolesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRolesApi.subclasses[0]().tenant_roles_get_sys_role(tenantId, roleId)


@router.delete(
    "/api/v1/tenants/{tenantId}/roles/{roleId}",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-roles"],
    response_model_by_alias=True,
)
async def tenant_roles_delete_sys_role(
    tenantId: StrictStr = Path(..., description=""),
    roleId: StrictStr = Path(..., description=""),
) -> None:
    if not BaseTenantRolesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRolesApi.subclasses[0]().tenant_roles_delete_sys_role(tenantId, roleId)


@router.patch(
    "/api/v1/tenants/{tenantId}/roles/{roleId}",
    responses={
        200: {"model": SysRole, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-roles"],
    response_model_by_alias=True,
)
async def tenant_roles_update_sys_role(
    tenantId: StrictStr = Path(..., description=""),
    roleId: StrictStr = Path(..., description=""),
    update_sys_role_request: UpdateSysRoleRequest = Body(None, description=""),
) -> SysRole:
    if not BaseTenantRolesApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantRolesApi.subclasses[0]().tenant_roles_update_sys_role(tenantId, roleId, update_sys_role_request)
