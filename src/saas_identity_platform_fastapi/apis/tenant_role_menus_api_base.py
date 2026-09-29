# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictStr
from typing import Any, Optional
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.role_menu_grant import RoleMenuGrant
from saas_identity_platform_fastapi.models.set_sys_role_menus_request import SetSysRoleMenusRequest


class BaseTenantRoleMenusApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTenantRoleMenusApi.subclasses = BaseTenantRoleMenusApi.subclasses + (cls,)
    async def tenant_role_menus_list_sys_role_menus(
        self,
        tenantId: StrictStr,
        roleId: StrictStr,
        client_id: Optional[StrictStr],
    ) -> RoleMenuGrant:
        ...


    async def tenant_role_menus_set_sys_role_menus(
        self,
        tenantId: StrictStr,
        roleId: StrictStr,
        set_sys_role_menus_request: SetSysRoleMenusRequest,
        client_id: Optional[StrictStr],
    ) -> RoleMenuGrant:
        ...


    async def tenant_role_menus_clear_sys_role_menus(
        self,
        tenantId: StrictStr,
        roleId: StrictStr,
        client_id: Optional[StrictStr],
    ) -> None:
        ...
