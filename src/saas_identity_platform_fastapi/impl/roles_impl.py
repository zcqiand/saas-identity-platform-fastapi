"""M00.F03 租户角色（springboot TenantRolesController 镜像，REQ-2026-004）。

语义锚点（对照 springboot TenantRolesController.java）：
- TenantGuard：路径 tenantId ≠ JWT tenant_id claim → 403（security.py verify_path_tenant）
- list：分页 0-based 默认 0/20；排序 created_at ASC + id ASC（SysRoleRepository.java:23-24，
  与成员面 DESC 相反）；query clientId 接收但完全不过滤（:35-37 只按 path tenantId 过滤）；
  total = 全租户角色总数（不分页截断）
- create：status 固定 1、isPreset 缺省 false（:58-59）；clientId 不校验租户订阅——
  未注册 clientId 撞 FK、roleCode 撞 uk(tenant,client,role_code) → 400 constraint violation；
  返回 200 非 201
- get/update/delete 经 findRoleInTenant（:78-87）：id 不存在**或跨租户**一律 404（不泄露存在性）
- PATCH：只应用 roleName/description 非空字段；UpdateSysRoleRequest.status 被忽略（:95-96）；
  roleCode/clientId/isPreset 不可改
- DELETE：先 resolve → 404 非幂等；子行级联（sys_role_menu + tenant_member_role，DB FK CASCADE）
"""

# ruff: noqa: N803, ARG002 —— Base*Api 缝方法形参名镜像生成契约（tenantId/roleId camelCase）
# 不可改名也不可删（生成 router 位置传参）；query clientId 参照实现就未参与过滤。

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.apis.tenant_roles_api_base import BaseTenantRolesApi
from saas_identity_platform_fastapi.entities import SysRole
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import (
    commit_or_bad_request,
    page_window,
    uuid_or_bad_request,
)
from saas_identity_platform_fastapi.impl.errors import NotFoundError
from saas_identity_platform_fastapi.impl.security import as_utc, now_utc, verify_path_tenant
from saas_identity_platform_fastapi.models.create_sys_role_request import CreateSysRoleRequest
from saas_identity_platform_fastapi.models.sys_role import SysRole as SysRoleDto
from saas_identity_platform_fastapi.models.tenant_roles_list_sys_roles200_response import (
    TenantRolesListSysRoles200Response,
)
from saas_identity_platform_fastapi.models.update_sys_role_request import UpdateSysRoleRequest


def _role_dto(row: SysRole) -> SysRoleDto:
    return SysRoleDto(
        id=row.id,
        tenantId=row.tenant_id,
        clientId=row.client_id,
        roleCode=row.role_code,
        roleName=row.role_name,
        description=row.description,
        isPreset=row.is_preset,
        status=row.status,
        createdAt=as_utc(row.created_at),
        updatedAt=as_utc(row.updated_at),
    )


def _resolve_role_in_tenant(session: Session, tenant_id: uuid.UUID, role_id: str) -> SysRole:
    """findRoleInTenant 镜像：id 不存在或 role.tenantId ≠ path tenantId → 一律 404。"""
    row = session.get(SysRole, uuid_or_bad_request(role_id))
    if row is None or row.tenant_id != tenant_id:
        raise NotFoundError(f"role not found in tenant: {role_id}")
    return row


class TenantRolesApiImpl(BaseTenantRolesApi):
    async def tenant_roles_list_sys_roles(
        self,
        tenantId: str,  # noqa: N803
        client_id: str | None,  # noqa: N803
        page: int | None,
        page_size: int | None,
    ) -> TenantRolesListSysRoles200Response:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        # query clientId 被接收但完全未用于过滤（springboot 参照，镜像不"修复"）
        query = session.query(SysRole).filter_by(tenant_id=tenant_id)
        total = query.count()
        p, ps = page_window(page, page_size)
        rows = (
            query.order_by(SysRole.created_at.asc(), SysRole.id.asc())
            .offset(p * ps)
            .limit(ps)
            .all()
        )
        return TenantRolesListSysRoles200Response(
            items=[_role_dto(row) for row in rows], page=p, pageSize=ps, total=total
        )

    async def tenant_roles_create_sys_role(
        self,
        tenantId: str,
        create_sys_role_request: CreateSysRoleRequest,  # noqa: N803
    ) -> SysRoleDto:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        req = create_sys_role_request
        row = SysRole(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=req.client_id,
            role_code=req.role_code,
            role_name=req.role_name,
            description=req.description,
            is_preset=bool(req.is_preset),
            status=1,
            created_at=now_utc(),
            updated_at=now_utc(),
        )
        ctx.session.add(row)
        # roleCode 撞 uk / 未注册 clientId 撞 FK → 400（不校验订阅关系，镜像参照）
        commit_or_bad_request(ctx.session, "role create")
        return _role_dto(row)

    async def tenant_roles_get_sys_role(
        self,
        tenantId: str,
        roleId: str,  # noqa: N803
    ) -> SysRoleDto:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        return _role_dto(_resolve_role_in_tenant(ctx.session, tenant_id, roleId))

    async def tenant_roles_update_sys_role(
        self,
        tenantId: str,
        roleId: str,
        update_sys_role_request: UpdateSysRoleRequest,  # noqa: N803
    ) -> SysRoleDto:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        row = _resolve_role_in_tenant(ctx.session, tenant_id, roleId)
        req = update_sys_role_request
        # 只应用 roleName/description 非空字段；status 字段被忽略（springboot 参照 :95-96）
        if req.role_name is not None:
            row.role_name = req.role_name
        if req.description is not None:
            row.description = req.description
        row.updated_at = now_utc()
        ctx.session.commit()
        return _role_dto(row)

    async def tenant_roles_delete_sys_role(
        self,
        tenantId: str,
        roleId: str,  # noqa: N803
    ) -> None:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        row = _resolve_role_in_tenant(ctx.session, tenant_id, roleId)
        # ORM 删 secondary 关联行 + role 行；role_menu/member_role 子行由 DB FK CASCADE 兜底
        ctx.session.delete(row)
        ctx.session.commit()
        return None
