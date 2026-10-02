# saas-identity-platform-fastapi — prod 容器（X07 段 5107，host=container）
#
# 家族 deploy 链同款（rails/springboot/aspnetcore 先例）：
#   VPS nginx 终结 TLS → proxy_pass http://127.0.0.1:5107 → 容器 uvicorn。
#   CI deploy job build & push（latest + tag 双份）→ VPS deploy 脚本拉镜像起容器。
#
# 端口是家族契约（docs/conventions/multi-repo-family.md §6 saas X07=5107），钉死在
# CMD 里不走 env 兜底（suite 硬规则 §1 同款口径：fail-fast，不留静默默认）。
#
# 运行时依赖（sqlalchemy / psycopg2-binary）已升进 pyproject 主依赖（2026-10-02
# 首航事故：sqlalchemy 只经 dev 组传递带入，镜像首航容器 import 即炸 ModuleNotFoundError；
# psycopg2 原靠本文件 build 补丁——两处一并归位主依赖，此处只装包本体）。
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir .

EXPOSE 5107
CMD ["uvicorn", "saas_identity_platform_fastapi.app:app", "--host", "0.0.0.0", "--port", "5107"]
