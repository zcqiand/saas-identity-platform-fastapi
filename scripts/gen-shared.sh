#!/usr/bin/env bash
# scripts/gen-shared.sh — 从家族 shared 契约生成 API 面 + DTO（openapi-generator python-fastapi）
#
# 三层生成铁律（2026-09-29 ADR，suite 硬规则 §4「API 面只认生成物」）：
#   API  → src/$PKG/apis/ + security_api.py   （openapi-generator，本脚本）
#   DTO  → src/$PKG/models/                    （openapi-generator，本脚本）
#   实体 → src/$PKG/entities.py               （sqlacodegen 对真库，scripts/scaffold-entities.sh）
#
# 生成区每次 regen 先删后写 —— 手改会被机械抹掉；禁止任何绕过脚本的手工编辑。
# 手写区：impl/（业务实现）、app.py（组合根）。main.py 不拷 —— 其职责由手写 app.py 承担。
#
# 用法：bash scripts/gen-shared.sh   （无 DB 依赖；L4.codegen.idempotent strict 复放本脚本）

set -euo pipefail

# 本仓是 submodule：git rev-parse 返回外层 suite 根，禁用（springboot 同款坑）
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/.."

PKG=saas_identity_platform_fastapi
SHARED_DIR="$(cd ../saas-identity-platform-shared && pwd)"
GEN_TMP=.openapi-tmp/gen
ZONE_ARGS=(-- "src/$PKG/apis" "src/$PKG/models" "src/$PKG/security_api.py")

echo "[gen-shared] step 1/4 — shared 仓 emit:openapi（TypeSpec SSOT 单 emit）"
(cd "$SHARED_DIR" && npm run emit:openapi)

echo "[gen-shared] step 2/4 — openapi-generator python-fastapi（7.24.0，openapitools.json 钉版）"
rm -rf "$GEN_TMP"
npx --yes @openapitools/openapi-generator-cli generate \
  -g python-fastapi \
  -i "$SHARED_DIR/generated/openapi/openapi.yaml" \
  -o "$GEN_TMP" \
  --additional-properties=hideGenerationTimestamp=true,packageName=$PKG

echo "[gen-shared] step 3/4 — 拷贝生成区 → src/$PKG/"
rm -rf "src/$PKG/apis" "src/$PKG/models"
mkdir -p "src/$PKG/apis" "src/$PKG/models"
cp "$GEN_TMP/src/$PKG/apis/"*.py "src/$PKG/apis/"
cp "$GEN_TMP/src/$PKG/models/"*.py "src/$PKG/models/"
cp "$GEN_TMP/src/$PKG/security_api.py" "src/$PKG/security_api.py"

echo "[gen-shared] step 3.5/4 — 符号枚举 sed 改名（≥/≤ 非法 Python 标识符，swift5 同款坑）"
# 只改枚举成员标识符，字面传输值 '≥'/'≤' 不动（线上值不受影响）；契约无符号枚举时为 no-op
sed -i "s/^    ≥ = '≥'/    GE = '≥'/; s/^    ≤ = '≤'/    LE = '≤'/" "src/$PKG/models/"*.py
if grep -rqn "^\s*[≥≤] =" "src/$PKG/models/" 2>/dev/null; then
  echo "[gen-shared] FATAL: 符号枚举改名残留（≥/≤ 仍是标识符）" >&2
  exit 1
fi

echo "[gen-shared] step 4/4 — fail-loud 自检（py_compile 生成区 + 漂移检查）"
python - <<'PYEOF'
import pathlib
import py_compile
import sys

pkg = pathlib.Path("src/saas_identity_platform_fastapi")
pyc_dir = pathlib.Path(".openapi-tmp/pycompile")
pyc_dir.mkdir(parents=True, exist_ok=True)
files = sorted(pkg.glob("apis/*.py")) + sorted(pkg.glob("models/*.py")) + [pkg / "security_api.py"]
bad = []
for i, f in enumerate(files):
    try:
        # cfile 指到 gitignore 的 .openapi-tmp/：不在生成区写 __pycache__
        # （会污染 codegen 幂等门的磁盘态对比；Windows os.devnull 非 regular 文件不可用）
        py_compile.compile(str(f), cfile=str(pyc_dir / f"{i}.pyc"), doraise=True)
    except Exception as exc:  # noqa: BLE001 — 自检要报出每一个坏文件而不是停在第一个
        bad.append(f"{f}: {exc}")
if bad:
    print("\n".join(bad), file=sys.stderr)
    sys.exit(1)
print(f"[gen-shared] py_compile OK（生成区 {len(files)} 文件）")
PYEOF

# 漂移 fail-loud（springboot scaffold-entities.sh 同款）：生成区与 git HEAD 不一致即红。
# untracked 也算 —— 防止生成漏 git add 后门禁读旧产物假绿（池项 5.31 教训）。
if ! git diff --exit-code --quiet "${ZONE_ARGS[@]}" 2>/dev/null \
  || [ -n "$(git ls-files --others --exclude-standard -- "src/$PKG/apis" "src/$PKG/models" "src/$PKG/security_api.py")" ]; then
  echo "[gen-shared] FATAL: 生成区与 git HEAD 不一致（含 untracked 新文件）" >&2
  echo "[gen-shared]        处理：确认 shared .tsp 变更合法后 git add 生成区并 commit，再重跑本脚本核绿" >&2
  exit 1
fi
echo "[gen-shared] OK — 生成区已与 HEAD 同步（API 面只认生成物，硬规则 §4）"
