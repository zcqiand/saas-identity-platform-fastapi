# REQ-2026-008 fastapi 部署链建设（Dockerfile + deploy 三件套 + CI deploy job）

状态：开发中
优先级：P1
影响功能数：0（部署基础设施，不进功能树）

## 用户原话照抄

主会话提序（获用户「继续」批准后执行）：

> 2. **fastapi 部署链建设**（新需求，动面大）：Dockerfile + deploy/ 三件套
>    （deploy 脚本、nginx-vps.conf.example、setup-vps.sh）×2 仓；X07 端口
>    saas 5107 / lab 5207；VPS 容器 + nginx vhost；tag 放行 + 上线

用户答复：「继续」（按提序顺序执行：先 swagger REQ 实施、再本需求）。

## 理解

2026-10-02 生产排障实证：`saas-fastapi.xiangru.uk` 与 `lab-fastapi.xiangru.uk`
均为**空体 404**（nginx default vhost 兜底）——两个 fastapi 仓从未有部署链：
无 Dockerfile、无 deploy/、无 CI deploy job、X07 端口（5107/5207）无监听。
本需求把两仓补齐到与 rails/springboot/aspnetcore 同构的部署能力。

## 需求边界

| 项 | 决定 |
|---|---|
| 范围 | saas-fastapi + lab-fastapi 两仓，各一套部署链 |
| 端口 | X07 段：saas 5107、lab 5207（multi-repo-family.md §6，host=container） |
| 镜像 | python:3.11-slim；uvicorn 钉 CMD 端口（家族端口契约，不走 env 兜底） |
| SSO | saas 是 IdP 本体：无 LAB_*/服务账号 env；JWT 沿 saas-rails 先例缺失时随机生成持久化（自签自验） |
| 库 | saas_prod（fastapi 无迁移，DB-first 实体直连既有 schema） |
| CT | 不同步 contract-test（与 swagger REQ 同批裁定） |

## 澄清记录

1. 「psycopg2 运行时依赖在 [dev] 组」——部署链发现的真实缺口：normalize_database_url
   归一成 `+psycopg2` 方言，容器内必须带驱动。处理：Dockerfile 显式
   `pip install . psycopg2-binary>=2.9`（主依赖升格另行裁定）。
2. prod 上线（VPS 容器 + nginx vhost + DNS）是外向动作——本 REQ 只落仓库侧物料；
   执行前主会话向用户确认变更面。

## 功能影响

无——不登记（影响功能数 0）。部署链不是 API 端点/业务能力；三重依据同
REQ-2026-007 §4（ADR-0027 subset invariant / 交付列收口 / infra 专属模块段全家族退役先例）。

## 任务

| # | 任务 | 状态 |
|---|---|---|
| T-1 | Dockerfile（端口钉 CMD；psycopg2 运行时依赖） | ✅ |
| T-2 | deploy/ 三件套（deploy 脚本 + nginx-vps.conf.example + setup-vps.sh，镜像 saas-rails 仓生产验证版机制） | ✅ |
| T-3 | ci.yml 增 deploy job（tag 触发；build&push latest+tag；appleboy/ssh-action 调 VPS 脚本） | ✅ |
| T-4 | prod 上线 runbook（secrets/vars 清单 + 执行步骤）——待用户批准执行 | ⏳ |

## 风险与回滚

- 首次 tag-deploy 前必须确认 GitHub 仓库 Secrets（DOCKER_USERNAME/DOCKER_PASSWORD/
  VPS_HOST/VPS_USER/VPS_SSH_KEY/PG_HOST/PG_PASSWORD，vars：NGINX_DOMAIN/
  NGINX_CERT_BASENAME）已配置——缺则 deploy job fail-fast（脚本自检）。
- 回滚：VPS 上 `docker run` 旧 tag 重跑 deploy 脚本；nginx vhost 渲染幂等。
- 环境差异：本机无 docker，镜像构建验证发生在 GH Actions 首次 tag-deploy；
  脚本已过 `sh -n` + 与 saas-rails 仓生产验证版逐段镜像。
