# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from pydantic import StrictInt, StrictStr
from typing import Any, Optional
from saas_identity_platform_fastapi.models.create_sys_user_request import CreateSysUserRequest
from saas_identity_platform_fastapi.models.error_response import ErrorResponse
from saas_identity_platform_fastapi.models.set_tenant_member_roles_request import SetTenantMemberRolesRequest
from saas_identity_platform_fastapi.models.tenant_member_status import TenantMemberStatus
from saas_identity_platform_fastapi.models.tenant_member_user_view import TenantMemberUserView
from saas_identity_platform_fastapi.models.tenant_member_view import TenantMemberView
from saas_identity_platform_fastapi.models.tenant_members_change_tenant_user_status_request import TenantMembersChangeTenantUserStatusRequest
from saas_identity_platform_fastapi.models.tenant_members_invite_tenant_user_request import TenantMembersInviteTenantUserRequest
from saas_identity_platform_fastapi.models.tenant_members_list_tenant_users200_response import TenantMembersListTenantUsers200Response
from saas_identity_platform_fastapi.models.update_sys_user_request import UpdateSysUserRequest


class BaseTenantMembersApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseTenantMembersApi.subclasses = BaseTenantMembersApi.subclasses + (cls,)
    async def tenant_members_list_tenant_users(
        self,
        tenantId: StrictStr,
        page: Optional[StrictInt],
        page_size: Optional[StrictInt],
        status: Optional[TenantMemberStatus],
    ) -> TenantMembersListTenantUsers200Response:
        ...


    async def tenant_members_create_tenant_user(
        self,
        tenantId: StrictStr,
        create_sys_user_request: CreateSysUserRequest,
    ) -> TenantMemberUserView:
        ...


    async def tenant_members_invite_tenant_user(
        self,
        tenantId: StrictStr,
        tenant_members_invite_tenant_user_request: TenantMembersInviteTenantUserRequest,
    ) -> TenantMemberView:
        ...


    async def tenant_members_get_tenant_user(
        self,
        tenantId: StrictStr,
        userId: StrictStr,
    ) -> TenantMemberUserView:
        ...


    async def tenant_members_delete_tenant_user(
        self,
        tenantId: StrictStr,
        userId: StrictStr,
    ) -> None:
        ...


    async def tenant_members_update_tenant_user(
        self,
        tenantId: StrictStr,
        userId: StrictStr,
        update_sys_user_request: UpdateSysUserRequest,
    ) -> TenantMemberUserView:
        ...


    async def tenant_members_assign_tenant_member_roles(
        self,
        tenantId: StrictStr,
        userId: StrictStr,
        set_tenant_member_roles_request: SetTenantMemberRolesRequest,
    ) -> TenantMemberUserView:
        ...


    async def tenant_members_change_tenant_user_status(
        self,
        tenantId: StrictStr,
        userId: StrictStr,
        tenant_members_change_tenant_user_status_request: TenantMembersChangeTenantUserStatusRequest,
    ) -> TenantMemberUserView:
        ...
