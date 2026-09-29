from typing import Optional
import datetime
import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKeyConstraint, Index, Integer, PrimaryKeyConstraint, SmallInteger, String, Table, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class DrizzleMigrations(Base):
    __tablename__ = '__drizzle_migrations'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='__drizzle_migrations_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[int]] = mapped_column(BigInteger)


class OauthClient(Base):
    __tablename__ = 'oauth_client'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='oauth_client_pkey'),
        UniqueConstraint('client_id', name='uk_oauth_client_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    client_secret: Mapped[str] = mapped_column(String(255), nullable=False)
    client_name: Mapped[str] = mapped_column(String(128), nullable=False)
    grant_types: Mapped[str] = mapped_column(String(255), nullable=False)
    redirect_uris: Mapped[str] = mapped_column(Text, nullable=False)
    access_token_validity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('7200'))
    refresh_token_validity: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('2592000'))
    auto_approve: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    scopes: Mapped[Optional[str]] = mapped_column(String(255))

    oauth_access_token: Mapped[list['OauthAccessToken']] = relationship('OauthAccessToken', back_populates='client')
    oauth_code: Mapped[list['OauthCode']] = relationship('OauthCode', back_populates='client')
    sys_menu: Mapped[list['SysMenu']] = relationship('SysMenu', back_populates='client')
    sys_role: Mapped[list['SysRole']] = relationship('SysRole', back_populates='client')
    tenant_application: Mapped[list['TenantApplication']] = relationship('TenantApplication', back_populates='client')
    oauth_refresh_token: Mapped[list['OauthRefreshToken']] = relationship('OauthRefreshToken', back_populates='client')


class SysUser(Base):
    __tablename__ = 'sys_user'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='sys_user_pkey'),
        Index('uk_sys_user_email', 'email', unique=True),
        Index('uk_sys_user_mobile', 'mobile', unique=True),
        Index('uk_sys_user_username', 'username', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    email: Mapped[Optional[str]] = mapped_column(String(128))
    mobile: Mapped[Optional[str]] = mapped_column(String(32))
    locked_until: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    oauth_access_token: Mapped[list['OauthAccessToken']] = relationship('OauthAccessToken', back_populates='user')
    oauth_code: Mapped[list['OauthCode']] = relationship('OauthCode', back_populates='user')
    tenant_member: Mapped[list['TenantMember']] = relationship('TenantMember', back_populates='user')
    oauth_refresh_token: Mapped[list['OauthRefreshToken']] = relationship('OauthRefreshToken', back_populates='user')


class Tenant(Base):
    __tablename__ = 'tenant'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='tenant_pkey'),
        Index('uk_tenant_key', 'tenant_key', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))

    oauth_access_token: Mapped[list['OauthAccessToken']] = relationship('OauthAccessToken', back_populates='tenant')
    oauth_code: Mapped[list['OauthCode']] = relationship('OauthCode', back_populates='tenant')
    sys_role: Mapped[list['SysRole']] = relationship('SysRole', back_populates='tenant')
    tenant_application: Mapped[list['TenantApplication']] = relationship('TenantApplication', back_populates='tenant')
    tenant_member: Mapped[list['TenantMember']] = relationship('TenantMember', back_populates='tenant')
    oauth_refresh_token: Mapped[list['OauthRefreshToken']] = relationship('OauthRefreshToken', back_populates='tenant')


class OauthAccessToken(Base):
    __tablename__ = 'oauth_access_token'
    __table_args__ = (
        ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ondelete='CASCADE', name='oauth_access_token_client_id_oauth_client_client_id_fk'),
        ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='SET NULL', name='oauth_access_token_tenant_id_tenant_id_fk'),
        ForeignKeyConstraint(['user_id'], ['sys_user.id'], ondelete='SET NULL', name='oauth_access_token_user_id_sys_user_id_fk'),
        PrimaryKeyConstraint('id', name='oauth_access_token_pkey'),
        Index('idx_access_token_expires', 'expires_at'),
        Index('idx_access_token_user_tenant', 'user_id', 'tenant_id'),
        Index('uk_access_token_id', 'token_id', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    token_id: Mapped[str] = mapped_column(String(128), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    token_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'Bearer'::character varying"))
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    scope: Mapped[Optional[str]] = mapped_column(String(255))

    client: Mapped['OauthClient'] = relationship('OauthClient', back_populates='oauth_access_token')
    tenant: Mapped[Optional['Tenant']] = relationship('Tenant', back_populates='oauth_access_token')
    user: Mapped[Optional['SysUser']] = relationship('SysUser', back_populates='oauth_access_token')
    oauth_refresh_token: Mapped[list['OauthRefreshToken']] = relationship('OauthRefreshToken', back_populates='access_token')


class OauthCode(Base):
    __tablename__ = 'oauth_code'
    __table_args__ = (
        ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ondelete='CASCADE', name='oauth_code_client_id_oauth_client_client_id_fk'),
        ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE', name='oauth_code_tenant_id_tenant_id_fk'),
        ForeignKeyConstraint(['user_id'], ['sys_user.id'], ondelete='CASCADE', name='oauth_code_user_id_sys_user_id_fk'),
        PrimaryKeyConstraint('id', name='oauth_code_pkey'),
        Index('idx_oauth_code_client_user_tenant', 'client_id', 'user_id', 'tenant_id'),
        Index('idx_oauth_code_expires', 'expires_at'),
        Index('uk_oauth_code', 'code', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    redirect_uri: Mapped[Optional[str]] = mapped_column(String(500))
    scope: Mapped[Optional[str]] = mapped_column(String(255))
    code_challenge: Mapped[Optional[str]] = mapped_column(String(128))
    code_challenge_method: Mapped[Optional[str]] = mapped_column(String(16))

    client: Mapped['OauthClient'] = relationship('OauthClient', back_populates='oauth_code')
    tenant: Mapped['Tenant'] = relationship('Tenant', back_populates='oauth_code')
    user: Mapped['SysUser'] = relationship('SysUser', back_populates='oauth_code')


class SysMenu(Base):
    __tablename__ = 'sys_menu'
    __table_args__ = (
        ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ondelete='CASCADE', name='sys_menu_client_id_oauth_client_client_id_fk'),
        PrimaryKeyConstraint('id', name='sys_menu_pkey'),
        Index('idx_sys_menu_client_parent', 'client_id', 'parent_id'),
        Index('idx_sys_menu_client_type', 'client_id', 'type')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, server_default=text("'00000000-0000-0000-0000-000000000000'::uuid"))
    title: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'))
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    path: Mapped[Optional[str]] = mapped_column(String(255))
    component: Mapped[Optional[str]] = mapped_column(String(255))
    perms: Mapped[Optional[str]] = mapped_column(String(128))
    icon: Mapped[Optional[str]] = mapped_column(String(128))

    client: Mapped['OauthClient'] = relationship('OauthClient', back_populates='sys_menu')
    role: Mapped[list['SysRole']] = relationship('SysRole', secondary='sys_role_menu', back_populates='menu')


class SysRole(Base):
    __tablename__ = 'sys_role'
    __table_args__ = (
        ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ondelete='CASCADE', name='sys_role_client_id_oauth_client_client_id_fk'),
        ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE', name='sys_role_tenant_id_tenant_id_fk'),
        PrimaryKeyConstraint('id', name='sys_role_pkey'),
        Index('idx_sys_role_tenant_client', 'tenant_id', 'client_id'),
        Index('uk_tenant_client_role_code', 'tenant_id', 'client_id', 'role_code', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    role_code: Mapped[str] = mapped_column(String(64), nullable=False)
    role_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_preset: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    description: Mapped[Optional[str]] = mapped_column(String(255))

    menu: Mapped[list['SysMenu']] = relationship('SysMenu', secondary='sys_role_menu', back_populates='role')
    client: Mapped['OauthClient'] = relationship('OauthClient', back_populates='sys_role')
    tenant: Mapped['Tenant'] = relationship('Tenant', back_populates='sys_role')
    member: Mapped[list['TenantMember']] = relationship('TenantMember', secondary='tenant_member_role', back_populates='role')


class TenantApplication(Base):
    __tablename__ = 'tenant_application'
    __table_args__ = (
        ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ondelete='CASCADE', name='tenant_application_client_id_oauth_client_client_id_fk'),
        ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE', name='tenant_application_tenant_id_tenant_id_fk'),
        PrimaryKeyConstraint('id', name='tenant_application_pkey'),
        Index('idx_tenant_application_client_id', 'client_id'),
        Index('uk_tenant_client', 'tenant_id', 'client_id', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    expire_time: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True))

    client: Mapped['OauthClient'] = relationship('OauthClient', back_populates='tenant_application')
    tenant: Mapped['Tenant'] = relationship('Tenant', back_populates='tenant_application')


class TenantMember(Base):
    __tablename__ = 'tenant_member'
    __table_args__ = (
        ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE', name='tenant_member_tenant_id_tenant_id_fk'),
        ForeignKeyConstraint(['user_id'], ['sys_user.id'], ondelete='CASCADE', name='tenant_member_user_id_sys_user_id_fk'),
        PrimaryKeyConstraint('id', name='tenant_member_pkey'),
        Index('idx_tenant_member_tenant_id', 'tenant_id'),
        Index('idx_tenant_member_user_id', 'user_id'),
        Index('uk_tenant_user', 'tenant_id', 'user_id', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    is_owner: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text('1'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    member_name: Mapped[Optional[str]] = mapped_column(String(64))

    tenant: Mapped['Tenant'] = relationship('Tenant', back_populates='tenant_member')
    user: Mapped['SysUser'] = relationship('SysUser', back_populates='tenant_member')
    role: Mapped[list['SysRole']] = relationship('SysRole', secondary='tenant_member_role', back_populates='member')


class OauthRefreshToken(Base):
    __tablename__ = 'oauth_refresh_token'
    __table_args__ = (
        ForeignKeyConstraint(['access_token_id'], ['oauth_access_token.id'], ondelete='CASCADE', name='oauth_refresh_token_access_token_id_oauth_access_token_id_fk'),
        ForeignKeyConstraint(['client_id'], ['oauth_client.client_id'], ondelete='CASCADE', name='oauth_refresh_token_client_id_oauth_client_client_id_fk'),
        ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='SET NULL', name='oauth_refresh_token_tenant_id_tenant_id_fk'),
        ForeignKeyConstraint(['user_id'], ['sys_user.id'], ondelete='SET NULL', name='oauth_refresh_token_user_id_sys_user_id_fk'),
        PrimaryKeyConstraint('id', name='oauth_refresh_token_pkey'),
        Index('idx_refresh_token_access_id', 'access_token_id'),
        Index('idx_refresh_token_user_tenant', 'user_id', 'tenant_id'),
        Index('uk_refresh_token', 'refresh_token', unique=True)
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, server_default=text('uuid_generate_v4()'))
    refresh_token: Mapped[str] = mapped_column(String(128), nullable=False)
    access_token_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text('false'))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(True), nullable=False, server_default=text('CURRENT_TIMESTAMP'))
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid)

    access_token: Mapped['OauthAccessToken'] = relationship('OauthAccessToken', back_populates='oauth_refresh_token')
    client: Mapped['OauthClient'] = relationship('OauthClient', back_populates='oauth_refresh_token')
    tenant: Mapped[Optional['Tenant']] = relationship('Tenant', back_populates='oauth_refresh_token')
    user: Mapped[Optional['SysUser']] = relationship('SysUser', back_populates='oauth_refresh_token')


t_sys_role_menu = Table(
    'sys_role_menu', Base.metadata,
    Column('role_id', Uuid, primary_key=True),
    Column('menu_id', Uuid, primary_key=True),
    ForeignKeyConstraint(['menu_id'], ['sys_menu.id'], ondelete='CASCADE', name='sys_role_menu_menu_id_sys_menu_id_fk'),
    ForeignKeyConstraint(['role_id'], ['sys_role.id'], ondelete='CASCADE', name='sys_role_menu_role_id_sys_role_id_fk'),
    PrimaryKeyConstraint('role_id', 'menu_id', name='sys_role_menu_role_id_menu_id_pk'),
    Index('idx_sys_role_menu_menu_id', 'menu_id')
)


t_tenant_member_role = Table(
    'tenant_member_role', Base.metadata,
    Column('member_id', Uuid, primary_key=True),
    Column('role_id', Uuid, primary_key=True),
    ForeignKeyConstraint(['member_id'], ['tenant_member.id'], ondelete='CASCADE', name='tenant_member_role_member_id_tenant_member_id_fk'),
    ForeignKeyConstraint(['role_id'], ['sys_role.id'], ondelete='CASCADE', name='tenant_member_role_role_id_sys_role_id_fk'),
    PrimaryKeyConstraint('member_id', 'role_id', name='tenant_member_role_member_id_role_id_pk'),
    Index('idx_tenant_member_role_role_id', 'role_id')
)
