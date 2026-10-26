# SaaS 多租户多应用身份平台

SaaS 多租户多应用身份平台（`saas-identity-platform-fastapi`）——一句话系统定位（待补）。

本仓为《（书稿信息待补）》案例（待补）的可运行配套工程，是书稿代码块的 **source of truth**。

## 快速开始

```bash
# 前置：python 3.11+，仓内 .venv 就绪（L4 用 .venv\Scripts\python.exe）
.venv/Scripts/pip install -e ".[dev]"                # 安装依赖（pyproject 主依赖 + dev 组）
ruff format --check src tests                        # L1 格式
ruff check src tests                                 # L2 静态
mypy --strict src                                    # L3 类型（strict）
.venv/Scripts/python.exe -m pytest -q --tb=short     # L4 测试
PYTHONPATH=src uvicorn saas_identity_platform_fastapi.app:app --port 5107   # 本地起服务（入口 src/saas_identity_platform_fastapi/app.py）
```

## 功能特性

按特性分点描述核心功能（见 `docs/functions/function-tree.md`）。

## 技术栈

| 技术 | 版本 |
| :--- | :--- |
| Python | 3.11（pyproject target） |
| FastAPI | ≥0.115 + uvicorn + SQLAlchemy 2 + psycopg2 |
| ruff / mypy | suite 钉版全局工具链（gate.py RUFF_PINNED_VERSION，项目 venv 禁装遮蔽版） |

> 依赖版本与 `version-lock.json` 的 `version_lock` 一致，不引入 lock 外的库。

## 配套书籍及章节映射

| 章 | 主题 | 对应源文件 |
| :--- | :--- | :--- |
| （待补） | | |

## 快速链接

- [CLAUDE.md](CLAUDE.md) — 开发约定与编码规范
- [系统架构.md](docs/ARCHITECTURE.md) — 结构 / 边界 / 数据流 / 决策
- [功能规格.md](docs/functions/function-tree.md) — 功能名称、描述与验收标准
- [未来开发计划](PLAN.md) — 待办与迭代方向
- [更新日志](CHANGELOG.md) — 版本变更记录
