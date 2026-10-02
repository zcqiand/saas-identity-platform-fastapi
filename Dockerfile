# saas-identity-platform-fastapi — prod 容器（X07 段 5107，host=container）
#
# 家族 deploy 链同款（rails/springboot/aspnetcore 先例）：
#   VPS nginx 终结 TLS → proxy_pass http://127.0.0.1:5107 → 容器 uvicorn。
#   CI deploy job build & push（latest + tag 双份）→ VPS deploy 脚本拉镜像起容器。
#
# 端口是家族契约（docs/conventions/multi-repo-family.md §6 saas X07=5107），钉死在
# CMD 里不走 env 兜底（suite 硬规则 §1 同款口径：fail-fast，不留静默默认）。
#
# psycopg2-binary 在这里是显式运行时依赖：impl/config.normalize_database_url 把
# DATABASE_URL 归一成 postgresql+psycopg2 方言，驱动必须随镜像（pyproject 主依赖
# 暂只有 [dev] 组带它——L4 真库测试走 dev 通道；日后若升进主依赖，此处可去掉）。
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir . "psycopg2-binary>=2.9"

EXPOSE 5107
CMD ["uvicorn", "saas_identity_platform_fastapi.app:app", "--host", "0.0.0.0", "--port", "5107"]
