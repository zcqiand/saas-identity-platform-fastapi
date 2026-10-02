# REQ-2026-007 后端根路径默认跳转 Swagger

| 项 | 值 |
|---|---|
| 提出人 | 用户 |
| 提出日期 | 2026-10-02 |
| 优先级 | P2 |
| 状态 | 开发中 |
| 关联 ADR | ADR-0027（消费树 ⊆ BASE subset invariant，本需求据以不登记功能树，见 §4） |

## 1. 需求描述

**用户原话（照抄）**：

> 所有后端增加一个，后端域名访问默认跳到swagger页面

**我的理解**：

本仓（saas-identity-platform 家族 4 后端之一，FastAPI 栈）在根路径增加浏览器友好默认入口：
匿名访问后端域名根路径时跳转到本仓 Swagger UI（FastAPI 内建 `/docs`），方便 QA 联调与契约复核
从域名直达 API 文档。经澄清（见澄清记录）：

1. 范围 = 两家族全部 8 个后端仓，本文件是本仓一仓的落点；
2. 本仓 Swagger UI 现状：**已有**。`app.py` 的 `FastAPI(...)` 未关 docs，内建 `/docs` 默认开启；
3. 跳转全环境生效（dev/test/prod 同姿态，与 aspnetcore 仓「prod 暂全开」的家族现状一致）；
4. 不进契约面、不同步 contract-test 仓（与 /health 同类基础设施端点）；
5. 不登记功能树（架构约束见 §4）。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| 「所有后端」范围？suite 有两家族 × 4 栈共 8 仓 | 两家族全部 8 仓都做 | 用户 | 2026-10-02 |
| 个别仓没有 Swagger 页可跳怎么办（缺页仓：lab-springboot / 双 rails） | 一并补齐 Swagger UI 再挂跳转，字面义完整实现（本仓已有页，仅挂跳转） | 用户 | 2026-10-02 |
| 跳转在哪些环境生效 | 所有环境统一跳（与现状 Swagger 全环境暴露一致） | 用户 | 2026-10-02 |
| 是否按硬规则同步 contract-test 仓 | 不同步：不在 .tsp 契约面内，与 /health 同类（/health 从未进 CT 断言） | 用户 | 2026-10-02 |
| 工作流要求「新增功能先登记功能树」，本需求如何登记？ | 不登记。基础设施端点进树违反 ADR-0027 subset invariant（消费树必须 ⊆ BASE，extra 即红），BASE 侧「仅后端」交付行又会让前端树违反交付列收口；先例：infra 专属模块段（原 97/98 号段）已全家族退役出树，/health 从未进树。架构判定，随文档送用户追认 | Claude | 2026-10-02 |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | 后端进程已启动 | 匿名 GET 根路径 `/` | 307/302 跳转到 `/docs`，跟随跳转后 Swagger UI 200 可渲染 |
| AC-2 | 任意环境（dev/test/prod 同姿态） | 重复 AC-1 | 行为一致；带不带 Authorization 行为一致 |
| AC-3 | 既有面回归 | 访问任意 `/api/v1/*` 契约端点与 `/health` | 行为与改动前完全一致（跳转只占根路径） |
| AC-4 | openapi 文档面纯净 | GET `/openapi.json` | 跳转端点**不出现**在 schema 里（`include_in_schema=False`） |
| AC-5 | 门禁 | 跑本仓 L1-L4 | 全绿；contract-test 仓 gate 回归不受影响 |

## 3. 任务拆解

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | 根路径跳转：`@app.get("/", include_in_schema=False)` → `RedirectResponse("/docs")`（匿名） | 开发 | claude | XS | 已完成（2026-10-02，red→green：改前 GET / 404，改后 307 Location /docs；tests/test_root_redirect.py 三断言 3 passed，不挂 fn ID） |
| T-2 | L1-L4 门禁回归 + curl 三验（307、跟随 200、/api/v1/* 不回归） | 门禁 | claude | XS | 已完成（2026-10-02，L0-L4 全绿 75 passed/20:30 含新 3 断言；curl 三验：GET / 307 Location /docs、跟随 200 渲染「SaaS 多租户多应用身份平台 - Swagger UI」、/openapi.json 200 且 root 不落 paths、/api/v1/me 裸 401 契约面不回归） |

## 4. 功能影响（需求与功能对齐的唯一位置）

**无 —— 本需求不登记功能树（影响功能数 0）。**

定性：根路径跳转与 Swagger UI 暴露是**基础设施端点**，不是产品功能面。三重依据：

1. **ADR-0027 subset invariant**：消费仓功能树必须 ⊆ shared BASE，BASE 外 M/F/I 即门禁红，
   vertical_extra 白名单已按 ADR-0027 终态全家族归零；BASE 外 ID 必须先 tree-change 进 BASE。
2. **BASE 侧也不可进**：BASE 行按 ADR-0024 §3 全家族照抄，「仅后端」交付行会让前端树
   违反前端树交付列收口（前端树只准 仅前端/前端+后端）。后端专属基础设施在 BASE 无合法挂位。
3. **先例**：infra 专属模块段（原 97/98 号段）已全家族退役出树，/health 从未进树。
   本需求与 /health 同类，同待遇。

功能影响表因此为空——没有 ID 即无悬空引用，不违反「ID 必须存在于功能树」。

## 5. 流程影响

无。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| prod 暴露面认知：裸域名直达 API 文档 | 安全姿态认知 | /docs 本就全环境暴露（FastAPI 默认，家族现状「prod 暂全开」），本需求不改变暴露姿态；后续 prod 收口时跳转随 UI gating 同步收口 | revert 跳由 commit，恢复 404 现状 |
| 根路径被既有路由占用 | 启动/路由冲突 | 已核：当前无任何根路由定义，GET / 现为 404 | revert |

无数据面、无契约面变更。
