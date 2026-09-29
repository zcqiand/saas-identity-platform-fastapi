# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.tenant_members_api_base import BaseTenantMembersApi
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
from saas_identity_platform_fastapi.models.create_sys_user_request import CreateSysUserRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.set_tenant_member_roles_request import SetTenantMemberRolesRequest
from saas_identity_platform_fastapi.models.tenant_member_status import TenantMemberStatus
from saas_identity_platform_fastapi.models.tenant_member_user_view import TenantMemberUserView
from saas_identity_platform_fastapi.models.tenant_member_view import TenantMemberView
from saas_identity_platform_fastapi.models.tenant_members_change_tenant_user_status_request import TenantMembersChangeTenantUserStatusRequest
from saas_identity_platform_fastapi.models.tenant_members_invite_tenant_user_request import TenantMembersInviteTenantUserRequest
from saas_identity_platform_fastapi.models.tenant_members_list_tenant_users200_response import TenantMembersListTenantUsers200Response
from saas_identity_platform_fastapi.models.update_sys_user_request import UpdateSysUserRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/tenants/{tenantId}/members",
    responses={
        200: {"model": TenantMembersListTenantUsers200Response, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_list_tenant_users(
    tenantId: StrictStr = Path(..., description=""),
    page: Optional[StrictInt] = Query(None, description="", alias="page"),
    page_size: Optional[StrictInt] = Query(None, description="", alias="pageSize"),
    status: Optional[TenantMemberStatus] = Query(None, description="", alias="status"),
) -> TenantMembersListTenantUsers200Response:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_list_tenant_users(tenantId, page, page_size, status)


@router.post(
    "/api/v1/tenants/{tenantId}/members",
    responses={
        200: {"model": TenantMemberUserView, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_create_tenant_user(
    tenantId: StrictStr = Path(..., description=""),
    create_sys_user_request: CreateSysUserRequest = Body(None, description=""),
) -> TenantMemberUserView:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_create_tenant_user(tenantId, create_sys_user_request)


@router.post(
    "/api/v1/tenants/{tenantId}/members/invitations",
    responses={
        200: {"model": TenantMemberView, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_invite_tenant_user(
    tenantId: StrictStr = Path(..., description=""),
    tenant_members_invite_tenant_user_request: TenantMembersInviteTenantUserRequest = Body(None, description=""),
) -> TenantMemberView:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_invite_tenant_user(tenantId, tenant_members_invite_tenant_user_request)


@router.get(
    "/api/v1/tenants/{tenantId}/members/{userId}",
    responses={
        200: {"model": TenantMemberUserView, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_get_tenant_user(
    tenantId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
) -> TenantMemberUserView:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_get_tenant_user(tenantId, userId)


@router.delete(
    "/api/v1/tenants/{tenantId}/members/{userId}",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_delete_tenant_user(
    tenantId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
) -> None:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_delete_tenant_user(tenantId, userId)


@router.patch(
    "/api/v1/tenants/{tenantId}/members/{userId}",
    responses={
        200: {"model": TenantMemberUserView, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_update_tenant_user(
    tenantId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
    update_sys_user_request: UpdateSysUserRequest = Body(None, description=""),
) -> TenantMemberUserView:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_update_tenant_user(tenantId, userId, update_sys_user_request)


@router.put(
    "/api/v1/tenants/{tenantId}/members/{userId}/roles",
    responses={
        200: {"model": TenantMemberUserView, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_assign_tenant_member_roles(
    tenantId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
    set_tenant_member_roles_request: SetTenantMemberRolesRequest = Body(None, description=""),
) -> TenantMemberUserView:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_assign_tenant_member_roles(tenantId, userId, set_tenant_member_roles_request)


@router.patch(
    "/api/v1/tenants/{tenantId}/members/{userId}/status",
    responses={
        200: {"model": TenantMemberUserView, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-members"],
    response_model_by_alias=True,
)
async def tenant_members_change_tenant_user_status(
    tenantId: StrictStr = Path(..., description=""),
    userId: StrictStr = Path(..., description=""),
    tenant_members_change_tenant_user_status_request: TenantMembersChangeTenantUserStatusRequest = Body(None, description=""),
) -> TenantMemberUserView:
    if not BaseTenantMembersApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantMembersApi.subclasses[0]().tenant_members_change_tenant_user_status(tenantId, userId, tenant_members_change_tenant_user_status_request)
