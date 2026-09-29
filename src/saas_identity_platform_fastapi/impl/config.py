"""应用配置 —— env fail-fast，无默认值兜底（suite 硬规则 §1；ADR-0019 同款口径）。"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _require_env(key: str) -> str:
    value = os.environ.get(key)
    if value is None or value == "":
        raise RuntimeError(f"env {key} required（禁默认值兜底，suite 硬规则 §1）")
    return value


def normalize_database_url(url: str) -> str:
    """家族 DATABASE_URL 方言归一：剥 ``jdbc:`` 前缀，``postgresql://`` → ``+psycopg2``。

    与 scaffold-entities.sh 同一套归一规则（sqlacodegen 4.x 默认 psycopg3，须显式指回）。
    """
    value = url[len("jdbc:") :] if url.startswith("jdbc:") else url
    if value.startswith("postgresql://"):
        value = "postgresql+psycopg2://" + value[len("postgresql://") :]
    return value


@dataclass(frozen=True)
class AppConfig:
    database_url: str
    jwt_signing_key: str
    jwt_issuer: str
    jwt_audience: str
    jwt_ttl_seconds: int

    @classmethod
    def from_env(cls) -> AppConfig:
        return cls(
            database_url=_require_env("DATABASE_URL"),
            jwt_signing_key=_require_env("JWT_SIGNING_KEY"),
            jwt_issuer=_require_env("JWT_ISSUER"),
            jwt_audience=_require_env("JWT_AUDIENCE"),
            jwt_ttl_seconds=int(_require_env("JWT_TTL_SECONDS")),
        )
