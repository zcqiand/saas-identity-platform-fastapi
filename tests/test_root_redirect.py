"""根路径默认跳转 Swagger 基建冒烟（REQ-2026-007 T-1，red-first）。

不入功能树、不挂 fn ID（REQ §4 + ADR-0027 subset invariant：基建端点进树即红，
/health 同类先例，test_health.py 同款走 conftest ``client`` fixture）。
三断言覆盖 REQ AC-1/AC-2/AC-4：307→/docs、Swagger UI 可渲染、openapi schema
纯净（跳转端点不落 schema）。
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_redirects_to_docs(client: TestClient) -> None:
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 307, resp.text
    assert resp.headers["location"] == "/docs"


def test_docs_renders_swagger_ui(client: TestClient) -> None:
    resp = client.get("/docs")
    assert resp.status_code == 200, resp.text
    assert "swagger-ui" in resp.text or "Swagger UI" in resp.text


def test_openapi_json_exposed_and_root_absent(client: TestClient) -> None:
    resp = client.get("/openapi.json")
    assert resp.status_code == 200, resp.text
    schema = resp.json()
    assert "openapi" in schema
    # AC-4：跳转端点 include_in_schema=False，不落 openapi paths
    assert "/" not in schema["paths"]
