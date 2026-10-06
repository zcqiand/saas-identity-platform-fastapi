"""GET /health 基建探针冒烟（REQ-2026-006 T-2）。

不入功能树（rails 先例：健康探针是基建非业务功能），不挂 fn ID；
contract-test fnReporter 探活 DEFAULT_HEALTH=/health 依赖本端点。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from saas_identity_platform_fastapi.app import create_app
from saas_identity_platform_fastapi.impl.config import AppConfig


def test_health_anonymous_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    assert client.get("/health", headers={"Authorization": "Bearer garbage"}).status_code == 200


# === CORS 预检（基建，不挂 fn；lab test_cors_preflight 镜像，REQ-2026-002 Phase 2） ===
# saas-flutter dev origin 5108 进白名单——flutter web 直连后端联调的前提。
# 预检被 CORSMiddleware 短路、不落 _request_context，全程不碰库：dummy URL 即可。


@pytest.fixture()
def cors_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    env = {
        "DATABASE_URL": "postgresql://saas:pw@localhost:5432/saas_unused_cors",
        "JWT_SIGNING_KEY": "test-key-32-bytes-minimum-length!",
        "JWT_ISSUER": "saas-identity-platform",
        "JWT_AUDIENCE": "saas-identity-platform-clients",
        "JWT_TTL_SECONDS": "3600",
        "SAAS_CORS_ALLOWED_ORIGINS": (
            "http://localhost:5101,http://localhost:5102,"
            "http://localhost:5103,http://localhost:5108"
        ),
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return TestClient(create_app(AppConfig.from_env()))


def test_cors_preflight_whitelisted(cors_client: TestClient) -> None:
    resp = cors_client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5108",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5108"
    assert resp.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_not_whitelisted(cors_client: TestClient) -> None:
    """非白名单 origin 不回 allow-origin 头（白名单语义，非放行所有）。"""
    resp = cors_client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5999",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in resp.headers
