# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictStr
from typing import Dict, List, Optional
from saas_identity_platform_fastapi.models.current_user import CurrentUser
from saas_identity_platform_fastapi.models.effective_menu_node import EffectiveMenuNode
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.switch_tenant_response import SwitchTenantResponse
from saas_identity_platform_fastapi.models.tenant_membership import TenantMembership


class BaseMeApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseMeApi.subclasses = BaseMeApi.subclasses + (cls,)
    async def me_whoami(
        self,
    ) -> CurrentUser:
        ...


    async def me_get_my_menus(
        self,
        client_id: Optional[StrictStr],
    ) -> Dict[str, List[EffectiveMenuNode]]:
        ...


    async def me_list_my_tenants(
        self,
        client_id: Optional[StrictStr],
    ) -> List[TenantMembership]:
        ...


    async def me_switch_tenant(
        self,
        tenantId: StrictStr,
        client_id: Optional[StrictStr],
    ) -> SwitchTenantResponse:
        ...
