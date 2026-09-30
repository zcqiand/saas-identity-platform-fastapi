# REQ-2026-003 批2 租户面：租户维护 + 租户成员 + 租户应用

| 项 | 值 |
|---|---|
| 提出人 | zcqiand |
| 提出日期 | 2026-09-29 |
| 优先级 | P0 |
| 状态 | 已验收（2026-09-30） |
| 关联 ADR | REQ-2026-001（总纲 T-2）；REQ-2026-002（批1 认证底座，impl 基座已就位） |

## 1. 需求描述

### 用户原话

> 继续

（承接 REQ-2026-001 总纲任务表 T-2「批2 租户面：租户维护（M00.F01）+ 租户成员（M00.F02）
+ 租户应用（M00.F05）」，用户以「继续」批准按总纲顺序进入第二批实现。）

### 我的理解

在批1 的 impl 基座（config/context/errors/security/assemble + app.py 组合根）之上，把三组
租户面端点（生成骨架 `admin_tenants_api` / `tenant_members_api` / `tenant_applications_api`，
共 17 条）从「未实现 500 兜底」落成真实现，语义逐条镜像 saas-identity-platform-springboot：

| 端点（生成路径） | 功能 ID | 家族语义要点（springboot 参照） |
|---|---|---|
| GET/POST /api/v1/admin/tenants；GET/DELETE/PATCH /api/v1/admin/tenants/{id} | M00.F01.I01-I05 | 平台域不挂 TenantGuard（dev 简化：任何有效 JWT 可访问）；list 无排序、page 0-based 默认 0/20；create 写 status=1、tenantKey 撞 unique → 400 constraint violation（全家族无 409）、返回 200；PATCH 部分更新（null 跳过，ACTIVE→1 / 其他→0）；DELETE 幂等 204（级联靠 DB FK） |
| GET/POST /api/v1/tenants/{tenantId}/members；POST .../members/invitations；GET/DELETE/PATCH .../members/{userId}；PATCH .../status；PUT .../roles | M00.F02.I01-I06/I08 + M01.F02.I01 | 路径 tenantId 必须 = JWT tenant_id claim（不等 → 403 FORBIDDEN）；list status 过滤 DB 级分页前、排序 created_at DESC + id ASC、user 行缺失的 member 静默滤掉；create 同时建 sys_user（plain: 密码、status=1）+ tenant_member（memberName=username、isOwner=false、status=1），username/email 撞 unique → 400；invite 建 user.username=email、password=""、status=2(invited)、member.status=1，返回嵌套视图 roles 恒 []；寻址 {userId}=sys_user.id 经 (tenant,user) 解析 member 行，寻不到 → 404；PATCH 只改 email/mobile；DELETE 只断 membership 不删 sys_user、先 resolve → 不存在 404；PATCH status 双写 member+user（四值字典 1/2/3/0）；PUT roles 全量替换、外来租户 roleId 静默忽略；扁平视图 status 读 member 行、roleIds 真 join 不按租户过滤、createdAt/updatedAt user 行优先 |
| GET/POST /api/v1/tenants/{tenantId}/applications；DELETE/PATCH /api/v1/tenants/{tenantId}/applications/{clientId} | M00.F05.I01-I04 | TenantGuard 同上；subscribe 先查 oauth_client 存在（未知 clientId → 404）、写 status=1/createdAt=now（expireTime 不落库→null）、重复订阅 → 400 constraint violation；PATCH 部分更新（寻不到 → 404）；DELETE 幂等 204 |

横切：分页响应 {items, page, pageSize, total}（total=过滤后计数）；重复/冲突一律 400
BAD_REQUEST（不 409）；DELETE 语义不对称——租户/订阅幂等 204、成员先 resolve 404。

**范围裁决（一处对总纲 T-4 的前吸收）**：`PUT /members/{userId}/roles` 端点在生成区归属
tenant_members_api（与成员 CRUD 同文件同生命周期），本批一并实现并挂 **M01.F02.I01**
（springboot 树中该端点就是 M01.F02 唯一子项「分配角色」）。M01.F02 的 F 行随实现同批翻转
「已上线」；总纲 T-4 余下范围只剩 M01.F03（我的租户关系/切换，另两条端点）。

硬约束：生成区零手改；实现只写 impl/ 缝 + app.py 组合根；测试 PG 真库 scratch（REQ-2026-002
既定架构）；env fail-fast 无兜底（硬规则 §1）；契约面未动（shared TypeSpec 无增改，
contract-test 断言面不变——硬规则 §2 不触发）。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| PUT roles 端点归 M00.F02 还是 M01.F02 | 按 springboot 树归 M01.F02.I01，随本批实现并翻转（前吸收，理由见上） | claude（照抄参照实现账本，无人工介入点） | 2026-09-29 |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | 种子含 2 租户 | GET /admin/tenants 分页 | 200 {items,page,pageSize,total}；create → 200；GET {id} → 200；PATCH name/status 部分更新生效；DELETE 幂等 204 |
| AC-2 | 有效 JWT（tenant_id=T1） | 访问 tenantId=T2 的成员/应用端点 | 403 FORBIDDEN；tenantId=T1 时 200 |
| AC-3 | 有效 JWT + 种子成员 | GET members 分页/status 过滤 | total=过滤后数、created_at DESC 排序；create 成员后 sys_user+tenant_member 各一行（plain: 密码）；重复 username → 400 |
| AC-4 | 有效 JWT | POST invitations | 200 嵌套视图（user.status=invited、member.status=active、roles=[]）；email 空 → 400 |
| AC-5 | 有效 JWT | PATCH status / PUT roles / DELETE member | status 双写 member+user；roles 全量替换且外来 roleId 被忽略；DELETE 后 member 行消失而 sys_user 保留 |
| AC-6 | 有效 JWT + 种子应用订阅 | subscribe/patch/remove | 未知 clientId → 404；重复订阅 → 400；PATCH status/expireTime 部分更新；remove 幂等 204 |
| AC-7 | 全部实现完成 | suite 门禁 L1-L5 | 全绿（red-first：批2 测试先红后绿，trace 挂功能 ID；功能树 4 F 翻转同 commit） |

## 3. 任务拆解

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | 功能树登记 I 级子项（M00.F01.I01-I05 / M00.F02.I01-I08 / M00.F05.I01-I04 / M01.F02.I01，镜像 springboot 编号，状态=开发中）+ 本 REQ | 文档 | claude | 小 | 已完成 |
| T-2 | red-first：批2 全部断言测试（tests/test_tenant_plane.py，PG scratch 复用批1 配方，挂上表 ID） | 测试 | claude | 大 | 已完成 |
| T-3 | impl/tenants_impl.py（admin 租户 + 租户守卫 helper）+ impl/members_impl.py（成员/邀请/状态/角色）+ impl/applications_impl.py（订阅面） | 开发 | claude | 大 | 已完成 |
| T-4 | app.py 组合根：三个 DELETE 200→204 收口（生成区未声明 status_code，批1 logout 同款） | 开发 | claude | 小 | 已完成 |
| T-5 | 功能树 4 F 翻「已上线」+ I 级转正；门禁 L1-L5 全绿；commit/push/gitlink | 收口 | claude | 小 | 已完成 |

## 4. 功能影响

| 功能 ID | 功能名称 | 影响类型 | 说明 | 关联任务 |
|---|---|---|---|---|
| M00.F01 | 租户维护 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I05 | T-1/T-2/T-3/T-5 |
| M00.F02 | 租户成员 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I08（I07 接受邀请镜像 springboot 保持规划——契约无对应端点） | T-1/T-2/T-3/T-5 |
| M00.F05 | 租户应用 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I04 | T-1/T-2/T-3/T-5 |
| M01.F02 | 角色成员 | 变更 | 状态 规划→已上线；新增 I 级子项 I01（PUT roles，本批前吸收，理由见 §1 范围裁决） | T-1/T-2/T-3/T-5 |

新增：0（I 级子项随 F 行登记，编号镜像 springboot）；变更：4；删除：0。

## 5. 流程影响

无（本仓无流程图；成员邀请流程形状以家族参照实现与 shared 契约为准）。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| 语义与家族分叉（403 守卫/400 冲突口径/幂等 DELETE/双写状态） | contract-test 批5 接入 | 逐条对照 springboot controller 行号实现，注释标注参照；差异清单见实现文件头 | git revert 本批 commit |
| 批2 测试量增大拖慢 L4（批1 17 测试 ≈100s） | gate 时长 | 断言合并进用例函数（家族断言密度先例）；远程 PG 假红先 ping（react 先例） | 无静默，红即修 |
| IntegrityError 捕获过宽吞真 bug | 数据面 | 只包 create/subscribe 显式写入点，捕获后 raise BadRequestError("constraint violation: ...") 保留原消息 | 捕获范围独立可回退 |
| M01.F02 前吸收与总纲 T-4 冲突 | 账本一致性 | REQ §1 范围裁决明示；总纲 T-4 描述不改动（M01.F03 仍在 T-4） | 功能树单行可回退 |
