"""GET /health 基建探针冒烟（REQ-2026-006 T-2）。

不入功能树（rails 先例：健康探针是基建非业务功能），不挂 fn ID；
contract-test fnReporter 探活 DEFAULT_HEALTH=/health 依赖本端点。
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_anonymous_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    assert client.get("/health", headers={"Authorization": "Bearer garbage"}).status_code == 200
