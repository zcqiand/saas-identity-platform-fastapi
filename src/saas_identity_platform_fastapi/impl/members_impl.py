"""M00.F02 租户成员 + M01.F02.I01 分配角色（springboot TenantMembersController 镜像）。

语义锚点（对照 springboot TenantMembersController.java）：
- TenantGuard：路径 tenantId 必须 = JWT tenant_id claim，不等 → 403 FORBIDDEN
- list：status 过滤 DB 级分页前；排序 created_at DESC + id ASC；user 行缺失的 member 静默滤掉
- create：同时建 sys_user（password="plain:"+密码、status=1、failed_attempts=0）
  + tenant_member（memberName=username、isOwner=false、status=1）；username/email 非空校验缺 → 400
- invite：email trim 后空 → 400；建 user（username=email、password=""、status=2 invited）
  + member（memberName=email、status=1 active 立即生效）；返回嵌套视图 roles 恒 []
- 寻址 {userId} = sys_user.id，经 (tenant, user) 解析 member 行，寻不到 → 404
- PATCH：只改 user.email/mobile（null 跳过）；status 唯一通道是 /status 端点（双写 member+user）
- DELETE：先 resolve → 404；只删 member_role + member 行，sys_user 保留
- PUT roles：全量替换（先清后插）；只接受本租户 sys_role，外来/坏 roleId 静默忽略
- 扁平视图：status 读 member 行；roleIds 真 join 不按租户过滤；时间戳 user 行优先
"""

# ruff: noqa: N803 —— Base*Api 缝方法形参名镜像生成契约（tenantId/userId camelCase），不可改名

from __future__ import annotations

import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.apis.tenant_members_api_base import BaseTenantMembersApi
from saas_identity_platform_fastapi.entities import (
    SysRole,
    SysUser,
    TenantMember,
    t_tenant_member_role,
)
from saas_identity_platform_fastapi.impl.assemble import (
    member_status_from_db,
    member_status_to_db,
    role_ids_of,
    user_status_from_db,
)
from saas_identity_platform_fastapi.impl.context import get_context
from saas_identity_platform_fastapi.impl.crud import commit_or_bad_request, page_window
from saas_identity_platform_fastapi.impl.errors import BadRequestError, NotFoundError
from saas_identity_platform_fastapi.impl.security import (
    as_utc,
    now_utc,
    uuid_or_none,
    verify_path_tenant,
)
from saas_identity_platform_fastapi.models.create_sys_user_request import CreateSysUserRequest
from saas_identity_platform_fastapi.models.set_tenant_member_roles_request import (
    SetTenantMemberRolesRequest,
)
from saas_identity_platform_fastapi.models.sys_user import SysUser as SysUserDto
from saas_identity_platform_fastapi.models.tenant_member import TenantMember as TenantMemberDto
from saas_identity_platform_fastapi.models.tenant_member_status import TenantMemberStatus
from saas_identity_platform_fastapi.models.tenant_member_user_view import TenantMemberUserView
from saas_identity_platform_fastapi.models.tenant_member_view import TenantMemberView
from saas_identity_platform_fastapi.models.tenant_members_change_tenant_user_status_request import (
    TenantMembersChangeTenantUserStatusRequest,
)
from saas_identity_platform_fastapi.models.tenant_members_invite_tenant_user_request import (
    TenantMembersInviteTenantUserRequest,
)
from saas_identity_platform_fastapi.models.tenant_members_list_tenant_users200_response import (
    TenantMembersListTenantUsers200Response,
)
from saas_identity_platform_fastapi.models.update_sys_user_request import UpdateSysUserRequest


def _user_dto(user: SysUser) -> SysUserDto:
    return SysUserDto(
        id=user.id,
        username=user.username,
        email=user.email,
        mobile=user.mobile,
        status=user_status_from_db(user.status),
        failedAttempts=user.failed_attempts,
        lockedUntil=as_utc(user.locked_until) if user.locked_until is not None else None,
        createdAt=as_utc(user.created_at),
        updatedAt=as_utc(user.updated_at),
    )


def _member_dto(member: TenantMember) -> TenantMemberDto:
    return TenantMemberDto(
        id=member.id,
        tenantId=member.tenant_id,
        userId=member.user_id,
        memberName=member.member_name,
        isOwner=member.is_owner,
        status=member_status_from_db(member.status),
        createdAt=as_utc(member.created_at),
        updatedAt=as_utc(member.updated_at),
    )


def _flat_view(session: Session, member: TenantMember, user: SysUser) -> TenantMemberUserView:
    """扁平 TenantMemberUserView：status 读 member 行（S1）；时间戳 user 行优先。"""
    created = user.created_at if user.created_at is not None else member.created_at
    updated = user.updated_at if user.updated_at is not None else member.updated_at
    return TenantMemberUserView(
        id=user.id,
        tenantId=member.tenant_id,
        username=user.username,
        email=user.email,
        status=member_status_from_db(member.status),
        roleIds=role_ids_of(session, member.id),
        createdAt=as_utc(created),
        updatedAt=as_utc(updated),
    )


def _resolve_member(
    session: Session, tenant_id: uuid.UUID, user_id: str
) -> tuple[TenantMember, SysUser]:
    """{userId}（=sys_user.id）→ (member, user)；任一环节寻不到 → 404。"""
    user = session.get(SysUser, uuid.UUID(user_id))
    if user is None:
        raise NotFoundError(f"member not found: {user_id}")
    member = (
        session.query(TenantMember).filter_by(tenant_id=tenant_id, user_id=user.id).one_or_none()
    )
    if member is None:
        raise NotFoundError(f"member not found: {user_id}")
    return member, user


def _new_user_and_member(
    tenant_id: uuid.UUID,
    username: str,
    password: str,
    email: str,
    mobile: str | None,
    user_status: int,
    member_status: int,
) -> tuple[SysUser, TenantMember]:
    now = now_utc()
    user = SysUser(
        id=uuid.uuid4(),
        username=username,
        password=password,
        status=user_status,
        failed_attempts=0,
        email=email,
        mobile=mobile,
        created_at=now,
        updated_at=now,
    )
    member = TenantMember(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        user_id=user.id,
        member_name=username,
        is_owner=False,
        status=member_status,
        created_at=now,
        updated_at=now,
    )
    return user, member


class TenantMembersApiImpl(BaseTenantMembersApi):
    async def tenant_members_list_tenant_users(
        self,
        tenantId: str,  # noqa: N803
        page: int | None,
        page_size: int | None,
        status: TenantMemberStatus | None,
    ) -> TenantMembersListTenantUsers200Response:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        query = session.query(TenantMember).filter_by(tenant_id=tenant_id)
        if status is not None:
            # status 过滤 DB 级分页前（total = 过滤后计数，springboot 参照）
            query = query.filter_by(status=member_status_to_db(status))
        total = query.count()
        p, ps = page_window(page, page_size)
        rows = (
            query.order_by(TenantMember.created_at.desc(), TenantMember.id.asc())
            .offset(p * ps)
            .limit(ps)
            .all()
        )
        users: dict[uuid.UUID, SysUser] = {}
        if rows:
            users = {
                u.id: u
                for u in session.query(SysUser)
                .filter(SysUser.id.in_([r.user_id for r in rows]))
                .all()
            }
        items = []
        for row in rows:
            user = users.get(row.user_id)
            if user is None:
                continue  # user 行缺失的 member 静默滤掉（springboot 参照）
            items.append(_flat_view(session, row, user))
        return TenantMembersListTenantUsers200Response(
            items=items, page=p, pageSize=ps, total=total
        )

    async def tenant_members_create_tenant_user(
        self,
        tenantId: str,
        create_sys_user_request: CreateSysUserRequest,  # noqa: N803
    ) -> TenantMemberUserView:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        req = create_sys_user_request
        # username 由契约 min_length=1 挡；email 可空 → 家族校验缺 email → 400（springboot 参照）
        if req.email is None or req.email == "":
            raise BadRequestError("username and email are required")
        session = ctx.session
        user, member = _new_user_and_member(
            tenant_id,
            username=req.username,
            password="plain:" + req.password,  # plain: 密码家族约定（批1 参照）
            email=req.email,
            mobile=req.mobile,
            user_status=1,
            member_status=1,
        )
        session.add(user)
        session.add(member)
        commit_or_bad_request(session, "member create")
        return _flat_view(session, member, user)

    async def tenant_members_invite_tenant_user(
        self,
        tenantId: str,  # noqa: N803
        tenant_members_invite_tenant_user_request: TenantMembersInviteTenantUserRequest,
    ) -> TenantMemberView:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        req = tenant_members_invite_tenant_user_request
        email = (req.email or "").strip()
        if email == "":
            raise BadRequestError("email is required")
        session = ctx.session
        user, member = _new_user_and_member(
            tenant_id,
            username=email,  # user.username = email（springboot 参照）
            password="",  # 邀请未设密；登录 plain: 前缀分支必然失配 → 401
            email=email,
            mobile=req.mobile,
            user_status=2,  # invited
            member_status=1,  # active 立即生效（邀请即建号，家族 ADR）
        )
        session.add(user)
        session.add(member)
        commit_or_bad_request(session, "member invite")
        return TenantMemberView(member=_member_dto(member), user=_user_dto(user), roles=[])

    async def tenant_members_get_tenant_user(
        self,
        tenantId: str,
        userId: str,  # noqa: N803
    ) -> TenantMemberUserView:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        member, user = _resolve_member(ctx.session, tenant_id, userId)
        return _flat_view(ctx.session, member, user)

    async def tenant_members_delete_tenant_user(self, tenantId: str, userId: str) -> None:  # noqa: N803
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        member, _user = _resolve_member(session, tenant_id, userId)
        # 只断 membership：先清 role 绑定再删 member 行；sys_user 保留（springboot 参照）
        session.execute(
            delete(t_tenant_member_role).where(t_tenant_member_role.c.member_id == member.id)
        )
        session.delete(member)
        session.commit()
        return None

    async def tenant_members_update_tenant_user(
        self,
        tenantId: str,
        userId: str,
        update_sys_user_request: UpdateSysUserRequest,  # noqa: N803
    ) -> TenantMemberUserView:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        member, user = _resolve_member(session, tenant_id, userId)
        if update_sys_user_request.email is not None:
            user.email = update_sys_user_request.email
        if update_sys_user_request.mobile is not None:
            user.mobile = update_sys_user_request.mobile
        user.updated_at = now_utc()
        session.commit()
        return _flat_view(session, member, user)

    async def tenant_members_assign_tenant_member_roles(
        self,
        tenantId: str,  # noqa: N803
        userId: str,  # noqa: N803
        set_tenant_member_roles_request: SetTenantMemberRolesRequest,
    ) -> TenantMemberUserView:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        member, user = _resolve_member(session, tenant_id, userId)
        requested = [
            u
            for u in (uuid_or_none(r) for r in set_tenant_member_roles_request.role_ids)
            if u is not None
        ]
        kept: list[uuid.UUID] = []
        if requested:
            # 只接受本租户 sys_role：外来 roleId 静默忽略（springboot 参照）
            rows = (
                session.query(SysRole)
                .filter(SysRole.tenant_id == tenant_id, SysRole.id.in_(requested))
                .all()
            )
            kept = [row.id for row in rows]
        # 全量替换：先清后插
        session.execute(
            delete(t_tenant_member_role).where(t_tenant_member_role.c.member_id == member.id)
        )
        for role_id in kept:
            session.execute(
                t_tenant_member_role.insert().values(member_id=member.id, role_id=role_id)
            )
        session.commit()
        return _flat_view(session, member, user)

    async def tenant_members_change_tenant_user_status(
        self,
        tenantId: str,  # noqa: N803
        userId: str,  # noqa: N803
        tenant_members_change_tenant_user_status_request: TenantMembersChangeTenantUserStatusRequest,  # noqa: E501
    ) -> TenantMemberUserView:
        ctx = get_context()
        tenant_id = verify_path_tenant(ctx, tenantId)
        session = ctx.session
        member, user = _resolve_member(session, tenant_id, userId)
        # 双写 member.status + user.status（springboot 参照：成员可见性与账号状态联动）
        db_status = member_status_to_db(tenant_members_change_tenant_user_status_request.status)
        member.status = db_status
        user.status = db_status
        user.updated_at = now_utc()
        session.commit()
        return _flat_view(session, member, user)
