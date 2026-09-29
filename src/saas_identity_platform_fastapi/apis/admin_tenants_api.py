# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.admin_tenants_api_base import BaseAdminTenantsApi
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
from saas_identity_platform_fastapi.models.admin_tenants_list_tenants200_response import AdminTenantsListTenants200Response
from saas_identity_platform_fastapi.models.create_tenant_request import CreateTenantRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.tenant import Tenant
from saas_identity_platform_fastapi.models.update_tenant_request import UpdateTenantRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/admin/tenants",
    responses={
        200: {"model": AdminTenantsListTenants200Response, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-tenants"],
    response_model_by_alias=True,
)
async def admin_tenants_list_tenants(
    page: Optional[StrictInt] = Query(None, description="", alias="page"),
    page_size: Optional[StrictInt] = Query(None, description="", alias="pageSize"),
) -> AdminTenantsListTenants200Response:
    if not BaseAdminTenantsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminTenantsApi.subclasses[0]().admin_tenants_list_tenants(page, page_size)


@router.post(
    "/api/v1/admin/tenants",
    responses={
        200: {"model": Tenant, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-tenants"],
    response_model_by_alias=True,
)
async def admin_tenants_create_tenant(
    create_tenant_request: CreateTenantRequest = Body(None, description=""),
) -> Tenant:
    if not BaseAdminTenantsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminTenantsApi.subclasses[0]().admin_tenants_create_tenant(create_tenant_request)


@router.get(
    "/api/v1/admin/tenants/{id}",
    responses={
        200: {"model": Tenant, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-tenants"],
    response_model_by_alias=True,
)
async def admin_tenants_get_tenant(
    id: StrictStr = Path(..., description=""),
) -> Tenant:
    if not BaseAdminTenantsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminTenantsApi.subclasses[0]().admin_tenants_get_tenant(id)


@router.delete(
    "/api/v1/admin/tenants/{id}",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-tenants"],
    response_model_by_alias=True,
)
async def admin_tenants_delete_tenant(
    id: StrictStr = Path(..., description=""),
) -> None:
    if not BaseAdminTenantsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminTenantsApi.subclasses[0]().admin_tenants_delete_tenant(id)


@router.patch(
    "/api/v1/admin/tenants/{id}",
    responses={
        200: {"model": Tenant, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["admin-tenants"],
    response_model_by_alias=True,
)
async def admin_tenants_update_tenant(
    id: StrictStr = Path(..., description=""),
    update_tenant_request: UpdateTenantRequest = Body(None, description=""),
) -> Tenant:
    if not BaseAdminTenantsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseAdminTenantsApi.subclasses[0]().admin_tenants_update_tenant(id, update_tenant_request)
