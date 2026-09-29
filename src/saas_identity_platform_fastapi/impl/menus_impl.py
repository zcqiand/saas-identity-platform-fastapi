"""M04.F04 菜单管理·client menus（springboot ClientMenusController 镜像，REQ-2026-004）。

语义锚点（对照 springboot ClientMenusController.java）：
- **仅有效 JWT**（SecurityConfig authenticated()）：无 TenantGuard、无 clientId 归属校验
- list：扁平 List<SysMenu>（含 parentId）不组树、无显式排序、不分页（:28-33）
- create：parentId null → 零值 UUID；type null → directory(1)；sortOrder null → 0；
  status 固定 1；**不校验 parent 存在**（parent_id 无 FK）；未注册 clientId 撞 FK → 400
- get/update/delete **不比对 clientId**（跨 client 可读，镜像参照；:53-81）
- PATCH：只应用 title/path/component/perms/icon/sortOrder 五字段——parentId/type/status 忽略
- DELETE：deleteById 幂等 204（不 resolve 404）；级联只清 sys_role_menu 授权，子菜单不级联
- reorder：目标 menu 的 sortOrder = 其在 orderedMenuIds 中的下标（不在列表 → 不动），
  列表内其他 menu 的 sortOrder 不写库；返回该 client 全量扁平列表；目标不存在 → 404
- move（PATCH .../parent）：parentId 非 null 才改（坏 UUID → 400）；不校验存在/成环
"""

# ruff: noqa: N803, ARG002 —— Base*Api 缝方法形参名镜像生成契约（clientId/menuId camelCase）
# 不可改名也不可删（生成 router 位置传参）；语义未用的形参（如 get/delete 的 clientId，
# 参照实现就不校验归属）是镜像行为，不是遗漏。

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.apis.client_menus_api_base import BaseClientMenusApi
from saas_identity_platform_fastapi.entities import SysMenu
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import commit_or_bad_request, uuid_or_bad_request
from saas_identity_platform_fastapi.impl.errors import NotFoundError
from saas_identity_platform_fastapi.impl.security import (
    as_utc,
    now_utc,
    require_bearer,
)
from saas_identity_platform_fastapi.models.client_menus_move_sys_menu_request import (
    ClientMenusMoveSysMenuRequest,
)
from saas_identity_platform_fastapi.models.create_sys_menu_request import CreateSysMenuRequest
from saas_identity_platform_fastapi.models.reorder_sys_menu_request import ReorderSysMenuRequest
from saas_identity_platform_fastapi.models.sys_menu import SysMenu as SysMenuDto
from saas_identity_platform_fastapi.models.sys_menu_type import SysMenuType
from saas_identity_platform_fastapi.models.update_sys_menu_request import UpdateSysMenuRequest

ZERO_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")

# type 字典（springboot TypeMapper.java:17-34）：1=directory 2=menu 3=button；未知 → menu
_MENU_TYPE_TO_DB: dict[str, int] = {"directory": 1, "menu": 2, "button": 3}


def menu_type_to_db(value: SysMenuType) -> int:
    return _MENU_TYPE_TO_DB[value.value]


def menu_type_from_db(value: object) -> SysMenuType:
    if value == 1:
        return SysMenuType("directory")
    if value == 3:
        return SysMenuType("button")
    return SysMenuType("menu")  # 2 与未知值都落 menu（TypeMapper.fromShort 镜像）


def _menu_dto(row: SysMenu) -> SysMenuDto:
    return SysMenuDto(
        id=row.id,
        clientId=row.client_id,
        parentId=row.parent_id,
        title=row.title,
        type=menu_type_from_db(row.type),
        path=row.path,
        component=row.component,
        perms=row.perms,
        icon=row.icon,
        sortOrder=row.sort_order,
        status=row.status,
        createdAt=as_utc(row.created_at),
    )


def _resolve_menu(session: Session, menu_id: str) -> SysMenu:
    """findById 镜像：不比对 clientId（跨 client 可读）；不存在 → 404。"""
    row = session.get(SysMenu, uuid_or_bad_request(menu_id))
    if row is None:
        raise NotFoundError(f"menu not found: {menu_id}")
    return row


class ClientMenusApiImpl(BaseClientMenusApi):
    async def client_menus_list_sys_menus(self, clientId: str) -> list[SysMenuDto]:  # noqa: N803
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        rows = ctx.session.query(SysMenu).filter_by(client_id=clientId).all()
        return [_menu_dto(row) for row in rows]  # 扁平不组树、无排序、不分页

    async def client_menus_create_sys_menu(
        self,
        clientId: str,
        create_sys_menu_request: CreateSysMenuRequest,  # noqa: N803
    ) -> SysMenuDto:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        req = create_sys_menu_request
        row = SysMenu(
            id=uuid.uuid4(),
            client_id=clientId,
            parent_id=req.parent_id if req.parent_id is not None else ZERO_UUID,
            title=req.title,
            type=menu_type_to_db(req.type) if req.type is not None else 1,
            sort_order=req.sort_order if req.sort_order is not None else 0,
            status=1,
            created_at=now_utc(),
            path=req.path,
            component=req.component,
            perms=req.perms,
            icon=req.icon,
        )
        ctx.session.add(row)
        # 不校验 parent 存在；未注册 clientId 撞 FK → 400 constraint violation
        commit_or_bad_request(ctx.session, "menu create")
        return _menu_dto(row)

    async def client_menus_get_sys_menu(self, clientId: str, menuId: str) -> SysMenuDto:  # noqa: N803
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        return _menu_dto(_resolve_menu(ctx.session, menuId))

    async def client_menus_update_sys_menu(
        self,
        clientId: str,
        menuId: str,
        update_sys_menu_request: UpdateSysMenuRequest,  # noqa: N803
    ) -> SysMenuDto:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        row = _resolve_menu(ctx.session, menuId)
        req = update_sys_menu_request
        # 只应用五字段；parentId/type/status 忽略（不动父子结构，springboot 参照 :67-72）
        if req.title is not None:
            row.title = req.title
        if req.path is not None:
            row.path = req.path
        if req.component is not None:
            row.component = req.component
        if req.perms is not None:
            row.perms = req.perms
        if req.icon is not None:
            row.icon = req.icon
        if req.sort_order is not None:
            row.sort_order = req.sort_order
        ctx.session.commit()
        return _menu_dto(row)

    async def client_menus_delete_sys_menu(self, clientId: str, menuId: str) -> None:  # noqa: N803
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        # deleteById 幂等 204：不 resolve 404（不存在也 204，springboot 参照 :73-76 镜像）
        row = ctx.session.get(SysMenu, uuid_or_bad_request(menuId))
        if row is not None:
            ctx.session.delete(row)
            ctx.session.commit()
        return None

    async def client_menus_move_sys_menu(
        self,
        clientId: str,
        menuId: str,
        client_menus_move_sys_menu_request: ClientMenusMoveSysMenuRequest,  # noqa: N803,E501
    ) -> SysMenuDto:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        row = _resolve_menu(ctx.session, menuId)
        parent_id = client_menus_move_sys_menu_request.parent_id
        if parent_id is not None:  # null → 不改（springboot 参照 :103）
            row.parent_id = uuid_or_bad_request(parent_id)
        ctx.session.commit()
        return _menu_dto(row)

    async def client_menus_reorder_sys_menus(
        self,
        clientId: str,
        menuId: str,
        reorder_sys_menu_request: ReorderSysMenuRequest,  # noqa: N803
    ) -> list[SysMenuDto]:
        ctx = get_context()
        require_bearer(ctx, ctx.request.app.state.jwt)
        row = _resolve_menu(ctx.session, menuId)
        # 只更新目标 menu 的 sortOrder = 其在列表中的下标；idx<0（不在列表）→ 不动
        index = (
            reorder_sys_menu_request.ordered_menu_ids.index(menuId)
            if menuId in reorder_sys_menu_request.ordered_menu_ids
            else -1
        )
        if index >= 0:
            row.sort_order = index
            ctx.session.commit()
        return [
            _menu_dto(m)
            for m in ctx.session.query(SysMenu).filter_by(client_id=row.client_id).all()
        ]
