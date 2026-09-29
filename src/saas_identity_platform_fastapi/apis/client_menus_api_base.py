# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictStr
from typing import Any, List
from saas_identity_platform_fastapi.models.client_menus_move_sys_menu_request import ClientMenusMoveSysMenuRequest
from saas_identity_platform_fastapi.models.create_sys_menu_request import CreateSysMenuRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.reorder_sys_menu_request import ReorderSysMenuRequest
from saas_identity_platform_fastapi.models.sys_menu import SysMenu
from saas_identity_platform_fastapi.models.update_sys_menu_request import UpdateSysMenuRequest


class BaseClientMenusApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseClientMenusApi.subclasses = BaseClientMenusApi.subclasses + (cls,)
    async def client_menus_list_sys_menus(
        self,
        clientId: StrictStr,
    ) -> List[SysMenu]:
        ...


    async def client_menus_create_sys_menu(
        self,
        clientId: StrictStr,
        create_sys_menu_request: CreateSysMenuRequest,
    ) -> SysMenu:
        ...


    async def client_menus_get_sys_menu(
        self,
        clientId: StrictStr,
        menuId: StrictStr,
    ) -> SysMenu:
        ...


    async def client_menus_delete_sys_menu(
        self,
        clientId: StrictStr,
        menuId: StrictStr,
    ) -> None:
        ...


    async def client_menus_update_sys_menu(
        self,
        clientId: StrictStr,
        menuId: StrictStr,
        update_sys_menu_request: UpdateSysMenuRequest,
    ) -> SysMenu:
        ...


    async def client_menus_move_sys_menu(
        self,
        clientId: StrictStr,
        menuId: StrictStr,
        client_menus_move_sys_menu_request: ClientMenusMoveSysMenuRequest,
    ) -> SysMenu:
        ...


    async def client_menus_reorder_sys_menus(
        self,
        clientId: StrictStr,
        menuId: StrictStr,
        reorder_sys_menu_request: ReorderSysMenuRequest,
    ) -> List[SysMenu]:
        ...
