# REQ-2026-006 批5 contract-test live 接入：/health 探针 + saas_dev 运行面 + 2-way 全绿

| 项 | 值 |
|---|---|
| 提出人 | zcqiand |
| 提出日期 | 2026-09-30 |
| 优先级 | P0 |
| 状态 | 已验收（2026-09-30） |
| 关联 ADR | REQ-2026-001（总纲 T-5）；REQ-2026-002/003/004/005（批1-批4 已收口）；跨仓 REQ-2026-011（contract-test 仓 targets 接入档） |

## 1. 需求描述

### 用户原话

> 继续

（承接 REQ-2026-001 总纲任务表 T-5「contract-test 接入 fastapi target，live 全绿」，用户以「继续」批准按总纲顺序进入第五批。）

### 我的理解

批1-批4 已把 shared 契约 9+34 端点的 impl 全部落地且单测绿，但「同输出 = 前端不可
区分」的家族验收还没跑过本仓——contract-test live 档（springboot 参照 + fastapi 被
测 2-way，2026-09-29 人裁上限 2）需要本仓：

1. **GET /health 健康探针**（组合根 `app.py`）——contract-test fnReporter 探活
   `DEFAULT_HEALTH=/health`，没有它 probeLive 判死 → 整个 run 塌缩 mode=unit，
   require_live 红。rails 先例 `health_controller.rb`：「家族健康探针（contract-test
   healthcheck 目标）」，匿名 200。**不进功能树**（rails 树无此行，家族口径：探针是
   基建非业务功能）。
2. **saas_dev 运行面**——`.env.local`（gitignored）：`DATABASE_URL` 指家族共享 PG
   saas_dev（V016 种子：alice/dev123456、固定 tenant UUID、oauth clients
   lab-management/erp/crm）+ 家族 dev JWT 三件套（JWT_ISSUER / JWT_AUDIENCE /
   JWT_SIGNING_KEY 与 springboot 同值，TTL 3600）。uvicorn 显式 `--port 5107`
   （conventions §6 X07 已分配，server 显式字面量非 env 兜底）。
3. **live 2-way 全绿**——`CONTRACT_TARGETS=springboot,fastapi TRACE_MAP=1 npx
   vitest run`：status 全等 + schema 校验 + `normalize()` 后全等。

### 范围裁决（三处）

1. **CT 仓 `.harness/stack.json` trace_env 不纳入 fastapi**——纳入即 gate 档要求
   fastapi 可达，属 live 上限升档，需人裁；本批 live 验证走显式 shell env
   `CONTRACT_TARGETS=springboot,fastapi`（contract-test-run-live.md :25 既有预案）。
2. **schemathesis/run.py、check_ssot_coverage.mjs、start-family.sh 不动**——rails
   接入先例：三者均未含 rails；start-family.sh 是全家族 4-way 一键工具，与
   2026-09-29「live 常态 2」人裁方向相反，不扩。
3. **tests/fnReporter.ts HEALTH_PATHS 不加 fastapi 条目**——本仓实现 `/health` 落
   DEFAULT_HEALTH，与 rails 同款（先例：不加条目）。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| /health 要不要登记功能树 | 不登记——rails 先例树无此行，家族口径探针=基建非业务功能；pytest 冒烟用例不挂 fn ID | claude（镜像先例，无人工介入点） | 2026-09-30 |
| fastapi 的 token 要不要与 springboot 互认 | CT 每目标独立 login 不跨后端带 token；但家族共库 + 前端不可区分口径下三件套对齐 springboot 同值（镜像 .env.local） | claude（同上） | 2026-09-30 |
| live 写比对会不会撞唯一约束 | CT 仓铁律「写操作用唯一化前缀 + teardown」（cleanup 走 HTTP DELETE），共库互踩由 CT 串行化（fileParallelism:false）+ 唯一化前缀兜住，本仓无需额外处理 | claude（同上） | 2026-09-30 |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | fastapi 进程起在 :5107（连 saas_dev） | GET /health | 匿名 200（无 body 契约要求，rails `health#show` 镜像） |
| AC-2 | springboot(:5105) + fastapi(:5107) 双活于 saas_dev | `CONTRACT_TARGETS=springboot,fastapi TRACE_MAP=1 npx vitest run` | live 档全绿：每用例 status 全等 + normalize 后全等；fnReporter mode=live、contract_targets=springboot,fastapi |
| AC-3 | live run 完成 | trace.json | mode=live 且 live_floor 执行面三值=声明值（无塌缩降级告警） |
| AC-4 | 全部完成 | suite 门禁 | fastapi 仓 L0-L5 全绿；CT 仓门禁全绿（unit 档） |

## 3. 任务拆解

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | 本 REQ + CT 仓 REQ-2026-011 双仓落档；CT 仓「目标端口声明」树行描述照实修正（端口名单过期，见其 REQ-2026-011） | 文档 | claude | 小 | 已完成 |
| T-2 | app.py 组合根 GET /health + pytest 冒烟用例（不挂 fn ID）；.env.local 脚本化生成（从 springboot .env.local 镜像，值不回显） | 开发 | claude | 小 | 已完成 |
| T-3 | CT 仓 src/targets.ts 加 fastapi:5107 条目 + 仓内文档同步（CLAUDE.md / ARCHITECTURE.md） | 开发 | claude | 小 | 已完成 |
| T-4 | 双后端起 saas_dev 栈（springboot 5105 + fastapi 5107）+ live 2-way 全绿 + trace 三值核验 | 验收 | claude | 大 | 已完成 |
| T-5 | 双仓门禁 + commit/push/gitlink + session.json | 收口 | claude | 小 | 已完成 |

## 4. 功能影响

无业务功能变更：**新增 0、变更 0、删除 0**。/health 为基建探针不入功能树（rails
先例）；live 接入是运维面验收，消费的是批1-批4 已登记端点的既有功能行。CT 仓侧
targets 条目属其「目标声明与可达性」功能域已上线行的实例化，亦无新功能。

## 5. 流程影响

无（本仓无流程图）。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| fastapi 连 saas_dev 后撞 schema/种子差异（entities 从 scratch 库 scaffold） | live 红 | springboot 同库已验证可行；schema 同源 migrations；红了按 systematic-debugging 走根因 | revert commit；.env.local 本地文件直接删 |
| live 写比对在共库互踩 | 比对结果失真 | CT 仓唯一化前缀 + teardown + fileParallelism:false 既有机制 | 同上 |
| /health 匿名暴露运行面信息 | 安全观感 | 返回无 body（探针纯 200），与 rails/springboot actuator 同款无信息泄露 | revert commit |
