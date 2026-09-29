# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictInt, StrictStr
from typing import Any, Optional
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.subscribe_tenant_application_request import SubscribeTenantApplicationRequest
from saas_identity_platform_fastapi.models.tenant_application import TenantApplication
from saas_identity_platform_fastapi.models.tenant_applications_list_tenant_applications200_response import TenantApplicationsListTenantApplications200Response
from saas_identity_platform_fastapi.models.update_tenant_application_request import UpdateTenantApplicationRequest


class BaseTenantApplicationsApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTenantApplicationsApi.subclasses = BaseTenantApplicationsApi.subclasses + (cls,)
    async def tenant_applications_list_tenant_applications(
        self,
        tenantId: StrictStr,
        page: Optional[StrictInt],
        page_size: Optional[StrictInt],
    ) -> TenantApplicationsListTenantApplications200Response:
        ...


    async def tenant_applications_subscribe_tenant_application(
        self,
        tenantId: StrictStr,
        subscribe_tenant_application_request: SubscribeTenantApplicationRequest,
    ) -> TenantApplication:
        ...


    async def tenant_applications_remove_tenant_application(
        self,
        tenantId: StrictStr,
        clientId: StrictStr,
    ) -> None:
        ...


    async def tenant_applications_update_tenant_application(
        self,
        tenantId: StrictStr,
        clientId: StrictStr,
        update_tenant_application_request: UpdateTenantApplicationRequest,
    ) -> TenantApplication:
        ...
