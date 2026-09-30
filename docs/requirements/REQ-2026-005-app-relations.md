# REQ-2026-005 批4 应用与关系网：应用维护 + 应用启停 + 我的租户/切换

| 项 | 值 |
|---|---|
| 提出人 | zcqiand |
| 提出日期 | 2026-09-30 |
| 优先级 | P0 |
| 状态 | 已验收（2026-09-30） |
| 关联 ADR | REQ-2026-001（总纲 T-4）；REQ-2026-002/003/004（批1-批3 已收口） |

## 1. 需求描述

### 用户原话

> 继续

（承接 REQ-2026-001 总纲任务表 T-4「批4 应用与关系网」，用户以「继续」批准按总纲顺序进入第四批实现。）

### 我的理解

在批1-批3 的 impl 基座之上，把三组端点（生成骨架 `admin_clients_api` 6 条 +
`clients_api` 1 条 + 批1 留缝的 `me_impl.me_list_my_tenants / me_switch_tenant`
2 条，共 **9 条**）从「未实现 500 兜底」落成真实现，语义逐条镜像
saas-identity-platform-springboot（AdminClientsController / ClientsController /
MeController，Explore 精读锚点见各行）：

| 端点（生成路径） | 功能 ID | 家族语义要点（springboot 参照） |
|---|---|---|
| GET/PATCH/DELETE /api/v1/admin/clients/{clientId}；GET/POST /api/v1/admin/clients；PATCH .../{clientId}/status | M04.F01.I01-I05 + M04.F02.I01 | **仅有效 Bearer JWT**（SecurityConfig :79-86 anyRequest authenticated，**无角色要求、无 TenantGuard**）；寻址用 clientId 字符串非行 UUID；list 分页 0/20 缺省、**无排序**（无 Sort）、无过滤；create 全必填字段直拷、validity 应用层缺省（null 或 ≤0 → **3600/86400**，非 DB 列默认 7200/2592000）、autoApprove null→false、status=1、clientId 撞 unique → **400** constraint violation、**返回 200 非 201**；get/delete 经 findByClientId → 404；PATCH **只应用 clientName/redirectUris/scopes 三字段**（grantTypes/validity/autoApprove/status 忽略）、**不 touch updatedAt**；delete **204**、级联靠 DB FK ON DELETE CASCADE（tenant_application/sys_role/sys_menu/oauth_code/两 token 表）、再删 404 非幂等；set-status **无值域校验**（任意 int 直写 smallint） |
| GET /api/v1/clients/{clientId} | M04.F01.I06 | **匿名可读**（SecurityConfig :60-61 permitAll 严格匹配 /api/v1/clients/*）；findByClientId → 404；响应 OAuthClientPublicInfo 仅 **clientId/clientName/status 三字段**（绝不含 secret/redirectUris） |
| GET /api/v1/me/tenants | M01.F03.I01 | 有效 JWT；query clientId 收但**忽略**；排序 **created_at ASC + id ASC**（MemberRepository :30-31）；**不过滤 status**（四值全回）；roleIds=member_role 全量 join **跨租户原样吐出**、空→[]；复用 assemble.to_membership |
| POST /api/v1/me/tenants/{tenantId}/switch | M01.F03.I02 | 无 body；校验链：无 sub → 401；坏 tenantId UUID → 400；租户不存在 → 404；**非 disabled（status≠0 且非 NULL）成员**即可切（invited/suspended 可，:125-135 S5 口径）、否则 404 **"is not an active member"**（不是 403）；响应=新签 access（tenant_id claim=目标租户）+ **不落库的 opaque refresh**（springboot "saas-rt-…" 口径）；**无 DB 写天然幂等**；租户自身 status 不校验 |

### 生成契约与 springboot DTO 的差异点（§4 API 面只认生成物，以契约为准）

1. CreateOAuthClientRequest 的 clientId/clientName/clientSecret/grantTypes/redirectUris
   契约必填（缺 → 422 fastapi 校验层；springboot @Valid → 400，校验层差异不改语义）。
   其余 DTO（OAuthClient 响应含 id/createdAt/updatedAt、SwitchTenantResponse 四字段、
   OAuthClientPublicInfo 三字段）与参照 toDto 逐字段一致，无裁剪。

### 范围裁决（一处）

**M04.F01.I03 树描述「密钥仅回指纹，不返明文」与参照实现不符**——实现是 OAuthClient
DTO **整行不含 clientSecret 字段**（无指纹概念，AdminClientsController:115-132 toDto）；
树描述照实修正为「响应不含 clientSecret」。I05 描述「吊销 token」实为 DB 级联清
oauth_access_token/oauth_refresh_token（无应用层吊销逻辑），描述照实修正。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| admin/clients 是否要求平台管理员角色 | 参照实现 anyRequest authenticated，**无角色门**（prod 恢复方案注释保留未启用）——逐字镜像不加门 | claude（照抄参照实现账本，无人工介入点） | 2026-09-30 |
| switch-tenant 的 refresh token 落不落库 | 参照**不落库**（generateRefreshToken 纯构造，rotate 语义归 /auth/refresh）——镜像不调 TokenIssuer.persist_token_pair | claude（同上） | 2026-09-30 |
| 公共元数据端点带不带 Bearer | 都行（permitAll）——测试覆盖匿名 200 + 未知 404 | claude（同上） | 2026-09-30 |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | 有效 JWT | admin clients list/create | 200 {items,page,pageSize,total}、分页缺省 0/20 回显缺省值；create → 200、validity 缺省 3600/86400、autoApprove 缺省 false、status=1；重复 clientId → 400 |
| AC-2 | 有效 JWT + 存在应用 | PATCH update / set-status | update 只 clientName/redirectUris/scopes 生效（grantTypes/status 等被忽略）；set-status 任意 int 直写生效；get → 200 响应无 clientSecret |
| AC-3 | 有效 JWT + 应用存在订阅/角色 | DELETE admin client | 204；tenant_application/sys_role 行级联消失；再 DELETE → 404（非幂等） |
| AC-4 | 无 token / 任意 JWT | GET /api/v1/clients/{clientId} | 匿名 200 三字段（clientId/clientName/status）；未知 → 404；带 Bearer 同样 200 |
| AC-5 | alice（T1 owner + T2 成员） | GET /me/tenants | 200 数组 created_at ASC 排序、含 T1/T2 两条、roleIds 跨租户原样、clientId 参数不影响 |
| AC-6 | bob（仅 T1）+ 种子 | POST switch 到 T2 | 404 "not an active member"；switch 回 T1 → 200 新 access 的 tenant_id claim=T1、refresh 不落库、重复调用幂等；坏 UUID → 400；无 sub → 401 |
| AC-7 | 全部实现完成 | suite 门禁 L1-L5 | 全绿（red-first：批4 测试先红后绿，trace 挂功能 ID；功能树 3 F 翻转同 commit） |

## 3. 任务拆解

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | 功能树登记 I 级子项（M04.F01.I01-I06 / M04.F02.I01 / M01.F03.I01-I02，镜像 springboot 编号，状态=开发中；两处树描述照参照实现修正）+ 本 REQ | 文档 | claude | 小 | 已完成 |
| T-2 | red-first：批4 全部断言测试（tests/test_app_relations.py，PG scratch 复用批2 配方，挂上表 ID） | 测试 | claude | 大 | 已完成 |
| T-3 | impl/clients_impl.py（公共元数据）+ impl/admin_clients_impl.py + me_impl 两方法对齐 springboot 语义逐条落实现 | 开发 | claude | 大 | 已完成 |
| T-4 | app.py 组合根：DELETE 200→204 收口补 /api/v1/admin/clients/ 前缀 | 开发 | claude | 小 | 已完成 |
| T-5 | 功能树 3 F 翻「已上线」+ I 级转正；门禁 L1-L5 全绿；commit/push/gitlink | 收口 | claude | 小 | 已完成 |

## 4. 功能影响

| 功能 ID | 功能名称 | 影响类型 | 说明 | 关联任务 |
|---|---|---|---|---|
| M04.F01 | 应用维护 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I06（I03/I05 描述照参照实现修正，见 §1 范围裁决） | T-1/T-2/T-3/T-5 |
| M04.F02 | 应用启用/停用 | 变更 | 状态 规划→已上线；新增 I 级子项 I01 | T-1/T-2/T-3/T-5 |
| M01.F03 | 租户成员 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I02（批1 留缝 me_impl 本批收口） | T-1/T-2/T-3/T-5 |

新增：0（I 级子项随 F 行登记，编号镜像 springboot）；变更：3；删除：0。

## 5. 流程影响

无（本仓无流程图；应用与租户切换流程形状以家族参照实现与 shared 契约为准）。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| admin/clients 无角色门（镜像参照）被误读为越权漏洞 | 审查观感 | REQ 澄清记录留账：prod 恢复方案在参照 SecurityConfig 注释，本批不启用 | revert commit |
| switch 签发的新 token 与登录 token 并存 | token 面语义 | 参照即如此（旧 token 不失效）；批5 contract-test live 验证跨端点 tenant_id claim 流转 | revert commit |
