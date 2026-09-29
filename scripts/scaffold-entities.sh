#!/usr/bin/env bash
# scripts/scaffold-entities.sh — sqlacodegen 反向工程从真库生成 SQLAlchemy 2.0 实体（DB-First）
#
# 先例：springboot 仓 scaffold-entities.sh（JDBC 反推 JPA，ADR-0025）。
# DB-First 漂移不是 trade-off：DB 没改产物必同 HEAD，有 diff = DB 真演进，commit 生成物。
#
# 产物：src/saas_identity_platform_fastapi/entities.py（生成区，禁手改；
#       每次 regen 整文件重写 —— 手改会被机械抹掉）
#
# 用法（DATABASE_URL 必填显式传入，禁默认值兜底 —— suite 硬规则 §1）：
#   DATABASE_URL=postgresql://user:pass@host/saas_dev bash scripts/scaffold-entities.sh
#   家族三库分层约定：entity scaffold 对 _dev 库（memory: db-three-tier-convention）

set -euo pipefail

# 本仓是 submodule：git rev-parse 返回外层 suite 根，禁用
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

PKG=saas_identity_platform_fastapi
ENT="src/$PKG/entities.py"

: "${DATABASE_URL:?必须显式 export DATABASE_URL（postgresql:// 形态，指向本族库）——禁默认兜底（硬规则 §1）}"

# 家族 DATABASE_URL 三方言（memory: database-url-three-dialects-per-backend）：
# springboot .env.local 是 jdbc: 前缀形态 —— 剥掉；sqlacodegen 4.x 默认 psycopg3
# 驱动，统一改写 +psycopg2（2026-09-29 spike 实证 4.0.4）
DB_URL="${DATABASE_URL#jdbc:}"
DB_URL="${DB_URL/postgresql:\/\//postgresql+psycopg2://}"

echo "[scaffold-entities] step 1/3 — sqlacodegen（4.0.4）→ entities.py"
SQLACODEGEN=".venv/Scripts/sqlacodegen"
[ -x "$SQLACODEGEN" ] || SQLACODEGEN="sqlacodegen"
"$SQLACODEGEN" "$DB_URL" --outfile "$ENT"

echo "[scaffold-entities] step 2/3 — py_compile 自检"
python -c "import py_compile; py_compile.compile('$ENT', doraise=True)"

echo "[scaffold-entities] step 3/3 — 漂移检查（tracked diff ∪ untracked，池项 5.31）"
if ! git diff --exit-code --quiet -- "$ENT" 2>/dev/null \
  || [ -n "$(git ls-files --others --exclude-standard -- "$ENT")" ]; then
  echo "[scaffold-entities] FATAL: entities.py 与 git HEAD 不一致" >&2
  echo "[scaffold-entities]        处理：确认 DB 演进合法（shared 已 migrate 到本族库）后" >&2
  echo "[scaffold-entities]        git add $ENT && commit" >&2
  exit 1
fi
echo "[scaffold-entities] OK — 实体层已与 DB 同步（DB-First 绿）"
