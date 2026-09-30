# REQ-2026-004 批3 权限与菜单：租户角色 + 角色权限 + 菜单管理

| 项 | 值 |
|---|---|
| 提出人 | zcqiand |
| 提出日期 | 2026-09-29 |
| 优先级 | P0 |
| 状态 | 已验收（2026-09-30） |
| 关联 ADR | REQ-2026-001（总纲 T-3）；REQ-2026-002/003（批1 基座 + 批2 租户面已收口） |

## 1. 需求描述

### 用户原话

> 继续

（承接 REQ-2026-001 总纲任务表 T-3「批3 权限与菜单：租户角色（M00.F03）+ 角色权限矩阵
（M00.F04）+ 菜单管理（M04.F04）」，用户以「继续」批准按总纲顺序进入第三批实现。）

### 我的理解

在批1/批2 的 impl 基座之上，把三组权限菜单端点（生成骨架 `tenant_roles_api` /
`tenant_role_menus_api` / `client_menus_api`，共 14 条）+ me/menus（批1 留缝的
`me_get_my_menus`，共 15 条）从「未实现 500 兜底」落成真实现，语义逐条镜像
saas-identity-platform-springboot：

| 端点（生成路径） | 功能 ID | 家族语义要点（springboot 参照） |
|---|---|---|
| GET/POST /api/v1/tenants/{tenantId}/roles；GET/PATCH/DELETE .../roles/{roleId} | M00.F03.I01-I05 | TenantGuard（路径 tenantId ≠ JWT claim → 403）；list 分页 0-based 默认 0/20、排序 **created_at ASC + id ASC**（与成员面 DESC 相反）、query clientId 接收但**不过滤**、total=全租户计数；create status=1、isPreset 缺省 false、clientId 不校验归属（FK 冲突 → 400）、roleCode 撞 uk(tenant,client,code) → 400、返回 200；get/update/delete 经 findRoleInTenant——**不存在或跨租户一律 404**（不泄露存在性）；PATCH 只应用 roleName/description 非空字段（**status 被忽略**）；DELETE 先 resolve → 404 非幂等，级联清 sys_role_menu + tenant_member_role（DB FK CASCADE） |
| GET/PUT/DELETE /api/v1/tenants/{tenantId}/roles/{roleId}/menus | M00.F04.I02-I04 | TenantGuard；role **只 findById 不校验租户归属**（404 口径与 roles 组不同，镜像参照）；GET 返回 RoleMenuGrant{roleId,tenantId,menuIds sorted,updatedAt=sys_role.updated_at}；PUT **全量替换**（差量删不在新集合的行 + INSERT ON CONFLICT DO NOTHING 幂等）、touch role.updatedAt、响应直接从请求集合构造（sorted、不回读）、坏 menuId UUID → 400、不存在 menuId 撞 FK → 400、外 client 的 menu 静默接受、空 menuIds=合法清空；DELETE 纯 bulk delete **幂等 204**、不 resolve role、不 touch updatedAt |
| GET/POST /api/v1/clients/{clientId}/menus；GET/PATCH/DELETE .../{menuId}；PUT .../{menuId}/reorder；PATCH .../{menuId}/parent | M04.F04.I01-I07 | **仅有效 JWT**（无 TenantGuard、无 clientId 归属校验）；list 扁平 List<SysMenu> 不组树、无显式排序、不分页；create parentId null → 零值 UUID、type null → directory(1)、sortOrder null → 0、status=1、**不校验 parent 存在**（parent_id 无 FK）；get/update/delete **不比对 clientId**（跨 client 可读，镜像参照）；PATCH 只应用 title/path/component/perms/icon/sortOrder（parentId/type/status 忽略）；DELETE 幂等 204（级联只清 sys_role_menu，**子菜单不级联**）；reorder 只更新目标 menu 的 sortOrder=其在 orderedMenuIds 中的下标（不在列表 → 不动）、返回该 client 全量扁平列表、目标不存在 → 404；move parentId 非 null 才改（坏 UUID → 400）、不校验存在/成环 |
| GET /api/v1/me/menus | M04.F04.I08 | 有效 JWT；四跳 join：member(me) → member_role → role_menu → sys_menu，任何一环空 → 空 Map；按 clientId 分组组树（Map<clientId, List<EffectiveMenuNode>>）；零值 UUID parentId → null；**孤儿（parent 不在授权集合）也当 root**；roots 按 sortOrder 升序（children 不排）；type 从 smallint 反查（未知 → menu） |

横切：冲突/约束一律 400 BAD_REQUEST "constraint violation"（无 409）；DELETE 语义不对称
——role 删除先 resolve 404、role-menus clear 与 menu 删除幂等 204。

**范围裁决（三处）**：
1. **M00.F04.I01 权限矩阵绑定（权限码全量替换）不在本批**——shared 契约无对应生成端点
   （镜像批2「接受邀请」条目保持规划的先例，见功能树 M00.F02 表后注）；
   M00.F04 的 F 行仍随 I02-I04 翻转「已上线」。
2. **M04.F04.I05 描述「级联清理子菜单」与 springboot 实现不符**（实现只清 sys_role_menu，
   子菜单因 parent_id 无 FK 孤儿保留）——以参照实现为准（家族 oracle 原则），树描述照实修正。
3. **me/tenants + switch-tenant 仍归批4**（M01.F03，总纲 T-4）；批1 遗留的 me_impl 注释
   「me/tenants 归批2」系笔误，本批顺手修正为「归批4」。

硬约束：生成区零手改；实现只写 impl/ 缝 + app.py 组合根；测试 PG 真库 scratch
（REQ-2026-002 既定架构）；env fail-fast 无兜底（硬规则 §1）；契约面未动（shared TypeSpec
无增改，contract-test 断言面不变——硬规则 §2 不触发）。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| M00.F04.I01（权限矩阵）契约无端点，F 行能否翻已上线 | I01 保持规划（镜像 I07 先例），I02-I04 实现后 F 行翻转——树交付以契约端点为准 | claude（照抄参照实现账本，无人工介入点） | 2026-09-29 |
| I05 树描述「级联清理子菜单」vs 参照实现只清 role_menu | 以 springboot 实现为准（oracle 原则），树说明照实修正 | claude（同上） | 2026-09-29 |
| roles 组 404 口径（跨租户 404）与 role-menus 组（不校验归属）不一致 | 两组口径不同是参照实现的真实现状，逐组镜像不"修复" | claude（同上） | 2026-09-29 |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | 有效 JWT（tenant_id=T1）+ 种子角色 | GET roles 分页/clientId 参数 | 200 {items,page,pageSize,total}；created_at ASC 排序；clientId 参数不影响结果；create → 200（status=1）；重复 roleCode → 400 |
| AC-2 | 有效 JWT | 访问 tenantId=T2 的 roles 端点 | 403 FORBIDDEN；role 存在于 T2、路径带 T1 → 404（跨租户不泄露）；PATCH roleName/description 生效、status 字段被忽略 |
| AC-3 | 有效 JWT + 角色 | DELETE roles/{roleId} | 204；role_menu + tenant_member_role 子行级联消失；再 DELETE → 404（非幂等） |
| AC-4 | 有效 JWT + 角色 + 菜单 | GET/PUT/DELETE role menus | GET menuIds sorted；PUT 全量替换（含删旧）、响应=请求集合 sorted；不存在 menuId → 400；空 menuIds 合法；DELETE 幂等 204 |
| AC-5 | 有效 JWT | client menus CRUD + reorder + move | create 缺省补齐（parentId=零值 UUID/type=directory/sortOrder=0/status=1）；PATCH 五字段生效；DELETE 幂等 204；reorder 只改目标 sortOrder 且返回全量；move 换父生效 |
| AC-6 | 种子成员+角色+菜单授权 + JWT | GET /me/menus | Map<clientId, 嵌套树>；零值 parent → root；孤儿当 root；roots 按 sortOrder 升序 |
| AC-7 | 全部实现完成 | suite 门禁 L1-L5 | 全绿（red-first：批3 测试先红后绿，trace 挂功能 ID；功能树 3 F 翻转同 commit） |

## 3. 任务拆解

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | 功能树登记 I 级子项（M00.F03.I01-I05 / M00.F04.I02-I04 / M04.F04.I01-I08，镜像 springboot 编号，状态=开发中）+ 本 REQ | 文档 | claude | 小 | 已完成 |
| T-2 | red-first：批3 全部断言测试（tests/test_permission_menu.py，PG scratch 复用批2 配方，挂上表 ID） | 测试 | claude | 大 | 已完成 |
| T-3 | impl/roles_impl.py + impl/role_menus_impl.py + impl/menus_impl.py + me_impl.me_get_my_menus 对齐 springboot 语义逐条落实现 | 开发 | claude | 大 | 已完成 |
| T-4 | app.py 组合根：新增 DELETE 200→204 收口核对（roles/{roleId} 与 roles/{roleId}/menus 均声明 204） | 开发 | claude | 小 | 已完成 |
| T-5 | 功能树 3 F 翻「已上线」+ I 级转正；门禁 L1-L5 全绿；commit/push/gitlink | 收口 | claude | 小 | 已完成 |

## 4. 功能影响

| 功能 ID | 功能名称 | 影响类型 | 说明 | 关联任务 |
|---|---|---|---|---|
| M00.F03 | 租户角色 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I05 | T-1/T-2/T-3/T-5 |
| M00.F04 | 角色权限 | 变更 | 状态 规划→已上线；新增 I 级子项 I02-I04（I01 权限矩阵镜像契约缺端点保持规划，见 §1 范围裁决 1） | T-1/T-2/T-3/T-5 |
| M04.F04 | 菜单管理 | 变更 | 状态 规划→已上线；新增 I 级子项 I01-I08（I08=me/menus，批1 留缝本批收口；I05 说明照参照实现修正，见 §1 范围裁决 2） | T-1/T-2/T-3/T-5 |

新增：0（I 级子项随 F 行登记，编号镜像 springboot）；变更：3；删除：0。

## 5. 流程影响

无（本仓无流程图；角色菜单授权流程形状以家族参照实现与 shared 契约为准）。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| 三组 404/幂等口径不对称（roles 严、role-menus 松、menus 无归属校验）实现时互相"污染" | contract-test 批5 接入 | 三组分文件实现（roles_impl/role_menus_impl/menus_impl），组级注释锚定参照行号 | git revert 本批 commit |
| reorder 语义反直觉（只写目标行）被"顺手修好" | 家族分叉 | 参照 oracle 原则，测试断言锁定反直觉行为 | 测试即回退锚 |
| me/menus 组树递归在深层菜单退化 | 数据面 | 家族种子菜单深度 ≤3，镜像 springboot 同款一层组树实现即可 | 无静默，红即修 |
| IntegrityError 捕获过宽吞真 bug | 数据面 | 只包 create/set 显式写入点，捕获后 raise BadRequestError("constraint violation: ...") 保留原消息 | 捕获范围独立可回退 |
