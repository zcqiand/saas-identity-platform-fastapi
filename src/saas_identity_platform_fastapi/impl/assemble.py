"""成员视图装配（springboot MemberViewAssembler / MemberStatusMapper 镜像，防视图层漂移）。

status 四值字典（ADR-0032）：1=active / 2=invited / 3=suspended / 0 或未知=disabled。
roleIds = tenant_member_role join 行原样返回，不按 sys_role.tenant_id 过滤
（member 绑定即真值；视图层再过滤会把合法跨租户绑定吞成空 roleIds，家族 2026-09-12 教训）。
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.entities import (
    TenantMember,
    t_tenant_member_role,
)
from saas_identity_platform_fastapi.impl.security import as_utc
from saas_identity_platform_fastapi.models.sys_user_status import SysUserStatus
from saas_identity_platform_fastapi.models.tenant_member_status import TenantMemberStatus
from saas_identity_platform_fastapi.models.tenant_membership import TenantMembership


def member_status_from_db(value: object) -> TenantMemberStatus:
    if value == 1:
        return TenantMemberStatus("active")
    if value == 2:
        return TenantMemberStatus("invited")
    if value == 3:
        return TenantMemberStatus("suspended")
    return TenantMemberStatus("disabled")


def user_status_from_db(value: object) -> SysUserStatus:
    if value == 1:
        return SysUserStatus("active")
    if value == 2:
        return SysUserStatus("invited")
    return SysUserStatus("disabled")


def role_ids_of(session: Session, member_id: uuid.UUID) -> list[str]:
    rows = session.execute(
        select(t_tenant_member_role.c.role_id).where(t_tenant_member_role.c.member_id == member_id)
    ).all()
    return [str(row[0]) for row in rows]


def to_membership(session: Session, member: TenantMember) -> TenantMembership:
    """tenant_member 行 → TenantMembership（契约：id/userId/tenantId/roleIds/status/joinedAt）。

    joinedAt = tenant_member.created_at（家族约定）。
    """
    return TenantMembership(
        id=member.id,
        userId=member.user_id,
        tenantId=member.tenant_id,
        roleIds=role_ids_of(session, member.id),
        status=member_status_from_db(member.status),
        joinedAt=as_utc(member.created_at),
    )
