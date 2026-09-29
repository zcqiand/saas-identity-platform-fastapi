"""pytest 适配器：@pytest.mark.fn -> suite 契约的 .state/trace.json。"""

from __future__ import annotations

import json
import os
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import bcrypt
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session

from saas_identity_platform_fastapi.app import create_app
from saas_identity_platform_fastapi.entities import (
    Base,
    OauthClient,
    SysMenu,
    SysRole,
    SysUser,
    Tenant,
    TenantApplication,
    TenantMember,
    t_sys_role_menu,
    t_tenant_member_role,
)
from saas_identity_platform_fastapi.impl.config import AppConfig, normalize_database_url


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "fn(id, ...): 该测试验证的功能子项 ID，如 @pytest.mark.fn('M01.F01.I14')"
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("TRACE_MAP") != "1":
        return
    entries = []
    for item in items:
        fns: list[str] = []
        for marker in item.iter_markers(name="fn"):
            fns.extend(str(a) for a in marker.args)
        inert = any(item.get_closest_marker(n) is not None for n in ("skip", "skipif", "xfail"))
        entries.append(
            {"test": item.nodeid, "fns": [] if inert else sorted(set(fns)), "inert": inert}
        )
    out = Path(str(config.rootpath)) / ".state" / "trace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"schema": 1, "tests": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


SCRATCH_DB = "saas_fastapi_scratch"

_JWT_KEY = "test-signing-key-32-bytes-minimum!"
_JWT_ISSUER = "saas-identity-platform"
_JWT_AUDIENCE = "saas-identity-platform-clients"

CLIENT_ID = "saas-console"
REDIRECT = "http://localhost:5101/callback"
SECOND_CLIENT_ID = "second-app"

TENANT1 = uuid.uuid4()
TENANT2 = uuid.uuid4()
ALICE = uuid.uuid4()
BOB = uuid.uuid4()
CAROL = uuid.uuid4()
BOB_MEMBER = uuid.uuid4()
MEM_ALICE_T1 = uuid.uuid4()
MEM_ALICE_T2 = uuid.uuid4()
MEM_CAROL_T2 = uuid.uuid4()
ROLE1 = uuid.uuid4()
ROLE2 = uuid.uuid4()

# 批3 增补：菜单树 + 角色菜单授权（sys_menu.parent_id 无 FK；零值 UUID = 根约定）
ZERO_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")
MENU_DIR = uuid.uuid4()  # directory 根（sortOrder 2）
MENU_USERS = uuid.uuid4()  # MENU_DIR 的子菜单（sortOrder 0）
MENU_DASH = uuid.uuid4()  # 根菜单（sortOrder 1）
MENU_ORPHAN = uuid.uuid4()  # parent 是未播种的孤儿菜单（me/menus 孤儿当根用例）
MENU_ORPHAN_PARENT = uuid.uuid4()  # 只当 parent_id 用，不建行
MENU_SECOND = uuid.uuid4()  # 第二个 client 的菜单（list 隔离断言用）

_T0 = datetime(2026, 9, 29, 8, 0, 0, tzinfo=UTC)


def _sql_exec(engine: Engine, statement: str) -> None:
    """DDL 专用（CREATE/DROP DATABASE 不能进事务块）：AUTOCOMMIT 直发。"""
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(text(statement))


def _scratch_urls() -> tuple[object, object]:
    """fail-fast 在 fixture 内而非 import 期：pytest 收集（trace collect-only）不碰 env。"""
    raw = os.environ.get("DATABASE_URL")
    if raw is None or raw == "":
        raise RuntimeError(
            "env DATABASE_URL required —— L4 打 PG 真库（scratch 库与其同服务器）；"
            "gate 表驱动注入 saas_test URL，手工跑先显式 export（suite 硬规则 §1）"
        )
    server = make_url(normalize_database_url(raw))
    # scratch 与测试库同服务器：借 DATABASE_URL 的 host/凭据，库名换成 scratch
    return server.set(database="postgres"), server.set(database=SCRATCH_DB)


@pytest.fixture(scope="session")
def scratch_engine() -> Iterator[Engine]:
    """每轮测试独占 scratch 库：DROP→CREATE→uuid 扩展→真实 schema create_all→收工 DROP。

    WITH (FORCE) 兜底上次异常退出残留的连接（PG 13+，本服务器 16.14）。
    """
    admin_url, scratch_url = _scratch_urls()  # fail-fast：无 DATABASE_URL 即红
    admin = create_engine(admin_url)
    _sql_exec(admin, f'DROP DATABASE IF EXISTS "{SCRATCH_DB}" WITH (FORCE)')
    _sql_exec(admin, f'CREATE DATABASE "{SCRATCH_DB}"')
    engine = create_engine(scratch_url, pool_pre_ping=True)
    # uuid-ossp 扩展建在 scratch 库内（admin 连接落在 postgres 库，别搞混）
    _sql_exec(engine, 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    _sql_exec(admin, f'DROP DATABASE "{SCRATCH_DB}" WITH (FORCE)')
    admin.dispose()


def _truncate_all(engine: Engine) -> None:
    tables = ", ".join(f'"{t}"' for t in sorted(Base.metadata.tables))
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def _seed(engine: Engine) -> None:
    """家族 dev 种子镜像（nextjs seed-db.mjs 约定）：alice/dev123456 + saas-console。

    批2 增补：SECOND_CLIENT_ID 是「已注册未订阅」应用（订阅面测试用）。
    批3 增补：CLIENT_ID 菜单树四条（根 DIR/子 USERS/根 DASH/孤儿 ORPHAN）+ 第二应用菜单
    一条；ROLE1 授权 DIR/USERS/DASH/ORPHAN 四条（嵌套+根排序+孤儿当根全覆盖）。
    """
    values: dict[type[Any], list[dict[str, Any]]] = {
        Tenant: [
            {
                "id": TENANT1,
                "tenant_key": "t1",
                "name": "租户一",
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": TENANT2,
                "tenant_key": "t2",
                "name": "租户二",
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        SysUser: [
            {
                "id": ALICE,
                "username": "alice",
                "password": "plain:dev123456",
                "status": 1,
                "failed_attempts": 0,
                "email": "alice@example.com",
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": BOB,
                "username": "bob",
                "password": bcrypt.hashpw(b"bobpass123", bcrypt.gensalt(rounds=4)).decode(),
                "status": 1,
                "failed_attempts": 0,
                "email": "bob@example.com",
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": CAROL,
                "username": "carol",
                "password": "plain:carolpass",
                "status": 1,
                "failed_attempts": 0,
                "email": "carol@example.com",
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        OauthClient: [
            {
                "id": uuid.uuid4(),
                "client_id": CLIENT_ID,
                "client_secret": "dev-secret",
                "client_name": "SaaS Console",
                "grant_types": "authorization_code,refresh_token",
                "redirect_uris": f"{REDIRECT},http://localhost:3000/callback",
                "access_token_validity": 7200,
                "refresh_token_validity": 2592000,
                "auto_approve": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": uuid.uuid4(),
                "client_id": SECOND_CLIENT_ID,
                "client_secret": "dev-secret-2",
                "client_name": "Second App",
                "grant_types": "authorization_code",
                "redirect_uris": "http://localhost:5201/callback",
                "access_token_validity": 7200,
                "refresh_token_validity": 2592000,
                "auto_approve": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        TenantApplication: [
            {
                "id": uuid.uuid4(),
                "tenant_id": TENANT1,
                "client_id": CLIENT_ID,
                "status": 1,
                "created_at": _T0,
            },
            {
                "id": uuid.uuid4(),
                "tenant_id": TENANT2,
                "client_id": CLIENT_ID,
                "status": 1,
                "created_at": _T0,
            },
        ],
        TenantMember: [
            {
                "id": BOB_MEMBER,
                "tenant_id": TENANT1,
                "user_id": BOB,
                "is_owner": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": MEM_ALICE_T1,
                "tenant_id": TENANT1,
                "user_id": ALICE,
                "is_owner": True,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": MEM_ALICE_T2,
                "tenant_id": TENANT2,
                "user_id": ALICE,
                "is_owner": False,
                "status": 1,
                "created_at": _T0 + timedelta(seconds=1),
                "updated_at": _T0,
            },
            {
                "id": MEM_CAROL_T2,
                "tenant_id": TENANT2,
                "user_id": CAROL,
                "is_owner": False,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        SysRole: [
            {
                "id": ROLE1,
                "tenant_id": TENANT1,
                "client_id": CLIENT_ID,
                "role_code": "admin",
                "role_name": "管理员",
                "is_preset": True,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
            {
                "id": ROLE2,
                "tenant_id": TENANT2,
                "client_id": CLIENT_ID,
                "role_code": "member",
                "role_name": "成员",
                "is_preset": True,
                "status": 1,
                "created_at": _T0,
                "updated_at": _T0,
            },
        ],
        t_tenant_member_role: [
            # 跨租户绑定原样吐出（家族约定：member 绑定即真值，视图层不按 tenant_id 过滤）
            {"member_id": MEM_ALICE_T1, "role_id": ROLE1},
            {"member_id": MEM_ALICE_T1, "role_id": ROLE2},
            {"member_id": MEM_CAROL_T2, "role_id": ROLE2},
        ],
        SysMenu: [
            # type 字典：1=directory 2=menu 3=button（springboot TypeMapper）
            {
                "id": MENU_DIR,
                "client_id": CLIENT_ID,
                "parent_id": ZERO_UUID,
                "title": "权限管理",
                "type": 1,
                "sort_order": 2,
                "status": 1,
                "created_at": _T0,
            },
            {
                "id": MENU_USERS,
                "client_id": CLIENT_ID,
                "parent_id": MENU_DIR,
                "title": "用户列表",
                "type": 2,
                "sort_order": 0,
                "status": 1,
                "created_at": _T0,
                "path": "/users",
                "component": "users/index",
                "perms": "sys:user:list",
            },
            {
                "id": MENU_DASH,
                "client_id": CLIENT_ID,
                "parent_id": ZERO_UUID,
                "title": "仪表盘",
                "type": 2,
                "sort_order": 1,
                "status": 1,
                "created_at": _T0,
                "path": "/dash",
            },
            {
                "id": MENU_ORPHAN,
                "client_id": CLIENT_ID,
                "parent_id": MENU_ORPHAN_PARENT,  # parent 行不存在 → me/menus 孤儿当根
                "title": "孤儿菜单",
                "type": 2,
                "sort_order": 5,
                "status": 1,
                "created_at": _T0,
            },
            {
                "id": MENU_SECOND,
                "client_id": SECOND_CLIENT_ID,
                "parent_id": ZERO_UUID,
                "title": "第二应用菜单",
                "type": 2,
                "sort_order": 0,
                "status": 1,
                "created_at": _T0,
            },
        ],
        t_sys_role_menu: [
            # ROLE1（alice@T1）授权四条：嵌套（DIR+USERS）+ 根（DASH）+ 孤儿（ORPHAN）
            {"role_id": ROLE1, "menu_id": MENU_DIR},
            {"role_id": ROLE1, "menu_id": MENU_USERS},
            {"role_id": ROLE1, "menu_id": MENU_DASH},
            {"role_id": ROLE1, "menu_id": MENU_ORPHAN},
        ],
    }
    member_role_rows = values.pop(t_tenant_member_role)
    role_menu_rows = values.pop(t_sys_role_menu)
    with Session(engine) as session:
        for model, rows in values.items():
            for row in rows:
                session.add(model(**row))
        # join 表是 secondary Table（无 ORM 类），走核心 insert
        session.execute(t_tenant_member_role.insert(), member_role_rows)
        session.execute(t_sys_role_menu.insert(), role_menu_rows)
        session.commit()


@pytest.fixture()
def client(scratch_engine: Engine) -> Iterator[TestClient]:
    config = AppConfig(
        database_url=str(scratch_engine.url),
        jwt_signing_key=_JWT_KEY,
        jwt_issuer=_JWT_ISSUER,
        jwt_audience=_JWT_AUDIENCE,
        jwt_ttl_seconds=3600,
    )
    _truncate_all(scratch_engine)
    _seed(scratch_engine)
    yield TestClient(create_app(config, engine=scratch_engine))


def _login(
    client: TestClient,
    username: str = "alice",
    password: str = "dev123456",
    client_id: str = CLIENT_ID,
) -> httpx.Response:
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password, "clientId": client_id},
    )


def _bearer(
    client: TestClient,
    username: str = "alice",
    password: str = "dev123456",
    client_id: str = CLIENT_ID,
) -> dict[str, str]:
    resp = _login(client, username=username, password=password, client_id=client_id)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['accessToken']}"}
