# REQ-2026-002 批1 认证底座：密码登录 + 失败锁定 + 登出 + OAuth authorize/token/refresh + whoami

| 项 | 值 |
|---|---|
| 提出人 | zcqiand |
| 提出日期 | 2026-09-29 |
| 优先级 | P0 |
| 状态 | 已评审 |
| 关联 ADR | REQ-2026-001（总纲 T-1）；ADR-0041（三层全生成） |

## 1. 需求描述

### 用户原话

> 继续

（承接 REQ-2026-001 总纲三项拍板：本批 = 总纲任务表 T-1「批1 认证底座——其余一切的前置」，
用户以「继续」批准按总纲进入第一批实现。）

### 我的理解

在生成区骨架上，把总纲 T-1 圈定的三组端点从「未实现 500 兜底」落成真实现，
语义逐条对齐家族参照实现（saas-identity-platform-springboot，contract-test live 全绿的 oracle 侧）：

| 端点 | 功能 ID | 家族语义要点（springboot 参照） |
|---|---|---|
| POST /api/v1/auth/login | M01.F04.I01/I02 | 未知用户与错密码同语义 401 INVALID_CREDENTIALS；`plain:` 密码前缀家族约定；连续 5 次错 → 锁 15 分钟（423）；成功重置计数；tenantId=首个 active membership 且租户 active；availableTenants 按 tenant_application 订阅过滤（空集不过滤）；token 对落库 |
| POST /api/v1/auth/logout | M01.F04.I06 | 204 |
| POST /api/v1/oauth/authorize | M04.F03.I01 | Bearer sub + tenant_id claim 必需（无 → 401）；redirect 白名单 csv 精确/前缀+`?`边界；code 一次性、5 分钟过期 |
| POST /api/v1/oauth/token | M04.F03.I02/I03 | 按 grantType 路由：authorization_code 一次性消费+过期+redirectUri 一致校验；refresh_token rotate（未知/已撤销 → 400）；clientId/userId/tenantId 三件回显 |
| GET /api/v1/me/whoami | M01.F01.I01 | 扁平 CurrentUser：id/email/memberships（roleIds 真 join，不按 tenant 过滤）/currentTenantId（JWT claim 优先，落首个 membership） |

硬约束：API/DTO/实体仍是生成物零手改；实现只写 impl/ 缝 + app.py 组合根；
env（DATABASE_URL/JWT_SIGNING_KEY/JWT_ISSUER/JWT_AUDIENCE/JWT_TTL_SECONDS）fail-fast 无兜底（硬规则 §1）。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| 无（范围/口径已在总纲拍板） | — | — | — |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | 种子数据（alice/dev123456 + saas-console，家族 dev 约定） | 正确凭据 POST /auth/login | 200：accessToken(HS256 可解码 sub/tenant_id)/refreshToken/availableTenants/currentTenantId |
| AC-2 | 同一用户连续 5 次错密码 | 第 5 次后再登录 | 401 逐次累计；第 5 次后 423 ACCOUNT_LOCKED；正确密码在锁定窗口内仍 423 |
| AC-3 | 有效 Bearer + 白名单 redirect | POST /oauth/authorize → /oauth/token | code 一次性：首换 200 TokenResponse（三件回显），重放 → 400 |
| AC-4 | 有效 refreshToken | grantType=refresh_token | 200 新 token 对；旧 refreshToken 复用 → 400 |
| AC-5 | 有效 Bearer | GET /me/whoami | 200 CurrentUser（无 Bearer/坏 token → 401） |
| AC-6 | 全部实现完成 | suite 门禁 L1-L5 | 全绿（red-first：测试先红后绿，trace 挂功能 ID） |

## 3. 任务拆解

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | red-first：批1 全部断言测试（httpx ASGITransport + sqlite 内存种子，挂 M01.F01.I01/M01.F04.I01/I02/I06/M04.F03.I01/I02/I03） | 测试 | claude | 中 | 待开始 |
| T-2 | impl/ 基座：config（env fail-fast）/ context（每请求 session+request contextvar）/ errors（家族 ErrorResponse {code,message} 映射）/ security（HS256 JwtIssuer + TokenIssuer 落库对 + 密码校验）| 开发 | claude | 中 | 待开始 |
| T-3 | AuthApiImpl + OauthApiImpl + MeApiImpl(whoami) 对齐 springboot 语义逐条落实现 | 开发 | claude | 大 | 待开始 |
| T-4 | app.py 组合根重写：create_app(config, engine) 工厂 + 中间件 + 异常 handler；CI 装配冒烟显式 env | 开发 | claude | 小 | 待开始 |
| T-5 | 功能树同 commit：3 个 F 翻「已上线」+ I 级子项登记（镜像 springboot 编号）；门禁 L1-L5 全绿 | 收口 | claude | 小 | 待开始 |

## 4. 功能影响

| 功能 ID | 功能名称 | 影响类型 | 说明 | 关联任务 |
|---|---|---|---|---|
| M01.F04 | SSO 登录 | 变更 | 状态 规划→已上线；新增 I 级子项 I01/I02/I06（实现）+ I04/I05/I07（已废弃，镜像 springboot 编号，OIDC/refresh 合并到 M04.F03.I02） | T-1/T-3/T-5 |
| M04.F03 | 身份认证 | 变更 | 状态 规划→已上线；新增 I 级子项 I01/I02/I03 | T-1/T-3/T-5 |
| M01.F01 | 用户维护 | 变更 | 状态 规划→已上线；新增 I 级子项 I01（whoami；完整用户 CRUD 归后续批） | T-1/T-3/T-5 |

新增：0（I 级子项随 F 行登记，编号镜像 springboot）；变更：3；删除：0。

## 5. 流程影响

无（登录/授权流程形状以家族参照实现与 shared 契约为准；本仓无流程图）。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| 语义与家族分叉（错误码/锁定阈值/白名单规则） | contract-test 批5 接入 | 逐条对照 springboot 源码实现，注释标注参照行 | git revert 本批 commit |
| sqlite 测试种子与 PG 行为差异（uuid 默认值/时区） | L4 假绿 | 种子显式赋全部列值；aware datetime 全链统一 | 断言失败即红，无静默 |
| env fail-fast 破坏 CI 装配冒烟 | CI | CI 步骤显式 export dev 值（非代码兜底，硬规则 §1 合规） | CI yaml 独立可回退 |
| mypy strict 与生成区 Any 缝隙 | L3 | 生成区 follow_imports=skip 既有接线；impl 不显式 Any/type: ignore | 既有 pyproject 配置 |
