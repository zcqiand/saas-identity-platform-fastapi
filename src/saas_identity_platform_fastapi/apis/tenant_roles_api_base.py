# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictInt, StrictStr
from typing import Any, Optional
from saas_identity_platform_fastapi.models.create_sys_role_request import CreateSysRoleRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.sys_role import SysRole
from saas_identity_platform_fastapi.models.tenant_roles_list_sys_roles200_response import TenantRolesListSysRoles200Response
from saas_identity_platform_fastapi.models.update_sys_role_request import UpdateSysRoleRequest


class BaseTenantRolesApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTenantRolesApi.subclasses = BaseTenantRolesApi.subclasses + (cls,)
    async def tenant_roles_list_sys_roles(
        self,
        tenantId: StrictStr,
        client_id: Optional[StrictStr],
        page: Optional[StrictInt],
        page_size: Optional[StrictInt],
    ) -> TenantRolesListSysRoles200Response:
        ...


    async def tenant_roles_create_sys_role(
        self,
        tenantId: StrictStr,
        create_sys_role_request: CreateSysRoleRequest,
    ) -> SysRole:
        ...


    async def tenant_roles_get_sys_role(
        self,
        tenantId: StrictStr,
        roleId: StrictStr,
    ) -> SysRole:
        ...


    async def tenant_roles_delete_sys_role(
        self,
        tenantId: StrictStr,
        roleId: StrictStr,
    ) -> None:
        ...


    async def tenant_roles_update_sys_role(
        self,
        tenantId: StrictStr,
        roleId: StrictStr,
        update_sys_role_request: UpdateSysRoleRequest,
    ) -> SysRole:
        ...
