# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from saas_identity_platform_fastapi.apis.tenant_applications_api_base import BaseTenantApplicationsApi
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
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.subscribe_tenant_application_request import SubscribeTenantApplicationRequest
from saas_identity_platform_fastapi.models.tenant_application import TenantApplication
from saas_identity_platform_fastapi.models.tenant_applications_list_tenant_applications200_response import TenantApplicationsListTenantApplications200Response
from saas_identity_platform_fastapi.models.update_tenant_application_request import UpdateTenantApplicationRequest


router = APIRouter()

ns_pkg = saas_identity_platform_fastapi.impl
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/api/v1/tenants/{tenantId}/applications",
    responses={
        200: {"model": TenantApplicationsListTenantApplications200Response, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-applications"],
    response_model_by_alias=True,
)
async def tenant_applications_list_tenant_applications(
    tenantId: StrictStr = Path(..., description=""),
    page: Optional[StrictInt] = Query(None, description="", alias="page"),
    page_size: Optional[StrictInt] = Query(None, description="", alias="pageSize"),
) -> TenantApplicationsListTenantApplications200Response:
    if not BaseTenantApplicationsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantApplicationsApi.subclasses[0]().tenant_applications_list_tenant_applications(tenantId, page, page_size)


@router.post(
    "/api/v1/tenants/{tenantId}/applications",
    responses={
        200: {"model": TenantApplication, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-applications"],
    response_model_by_alias=True,
)
async def tenant_applications_subscribe_tenant_application(
    tenantId: StrictStr = Path(..., description=""),
    subscribe_tenant_application_request: SubscribeTenantApplicationRequest = Body(None, description=""),
) -> TenantApplication:
    if not BaseTenantApplicationsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantApplicationsApi.subclasses[0]().tenant_applications_subscribe_tenant_application(tenantId, subscribe_tenant_application_request)


@router.delete(
    "/api/v1/tenants/{tenantId}/applications/{clientId}",
    responses={
        204: {"description": "There is no content to send for this request, but the headers may be useful. "},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-applications"],
    response_model_by_alias=True,
)
async def tenant_applications_remove_tenant_application(
    tenantId: StrictStr = Path(..., description=""),
    clientId: StrictStr = Path(..., description=""),
) -> None:
    if not BaseTenantApplicationsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantApplicationsApi.subclasses[0]().tenant_applications_remove_tenant_application(tenantId, clientId)


@router.patch(
    "/api/v1/tenants/{tenantId}/applications/{clientId}",
    responses={
        200: {"model": TenantApplication, "description": "The request has succeeded."},
        "default": {"model": ErrorResponse, "description": "An unexpected error response."},
    },
    tags=["tenant-applications"],
    response_model_by_alias=True,
)
async def tenant_applications_update_tenant_application(
    tenantId: StrictStr = Path(..., description=""),
    clientId: StrictStr = Path(..., description=""),
    update_tenant_application_request: UpdateTenantApplicationRequest = Body(None, description=""),
) -> TenantApplication:
    if not BaseTenantApplicationsApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseTenantApplicationsApi.subclasses[0]().tenant_applications_update_tenant_application(tenantId, clientId, update_tenant_application_request)
