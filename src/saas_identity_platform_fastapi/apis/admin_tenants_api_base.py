# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import Field, StrictInt, StrictStr
from typing import Any, Optional
from typing_extensions import Annotated
from saas_identity_platform_fastapi.models.admin_tenants_list_tenants200_response import AdminTenantsListTenants200Response
from saas_identity_platform_fastapi.models.create_tenant_request import CreateTenantRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.tenant import Tenant
from saas_identity_platform_fastapi.models.update_tenant_request import UpdateTenantRequest


class BaseAdminTenantsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseAdminTenantsApi.subclasses = BaseAdminTenantsApi.subclasses + (cls,)
    async def admin_tenants_list_tenants(
        self,
        page: Annotated[Optional[StrictInt], Field(description="页码，0 基（Spring Data Pageable）：首页 page=0。")],
        page_size: Annotated[Optional[StrictInt], Field(description="每页条数。")],
    ) -> AdminTenantsListTenants200Response:
        ...


    async def admin_tenants_create_tenant(
        self,
        create_tenant_request: CreateTenantRequest,
    ) -> Tenant:
        ...


    async def admin_tenants_get_tenant(
        self,
        id: StrictStr,
    ) -> Tenant:
        ...


    async def admin_tenants_delete_tenant(
        self,
        id: StrictStr,
    ) -> None:
        ...


    async def admin_tenants_update_tenant(
        self,
        id: StrictStr,
        update_tenant_request: UpdateTenantRequest,
    ) -> Tenant:
        ...
