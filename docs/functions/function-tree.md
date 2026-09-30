# 功能清单（Function Tree）— SaaS 多租户多应用身份平台

> **全体系唯一锚点。** 需求、流程、设计、测试都引用这里的 ID。
> 不在这里的 ID 是悬空引用，L5 门会拦。**改功能，先改这份表。**

## 本仓角色

FastAPI 后端 —— saas 家族第 5 种后端（springboot / aspnetcore / rails / nextjs 之后），对接 PostgreSQL。
本表只登记**本仓要交付**的功能；模块编号与家族各后端仓对齐（M/F ID 跨仓同义）。

## 编号规则

| 层级 | 名称 | 格式 | 含义 |
|---|---|---|---|
| 一级 | 功能模块 | `M01` | 业务域边界，通常对应一级菜单 |
| 二级 | 功能 | `M01.F01` | 一个完整业务步骤 / 独立闭环流程 / 数据管理页面 |
| 三级 | 功能子项 | `M0x.F0y.I0z` | 技术交付单元 / 权限挂载点。对应一个 API 接口、页面组件、图表区块或权限控制点 |

**硬规则**

1. 编号单调递增，永不复用。废弃改状态，不删行。
2. 子项编号必须以父级为前缀。
3. 一个子项 = 一个权限点。权限码即 ID，不另起一套编码。
4. 拆不出子项的功能 → 它其实是子项，往上并。子项超 20 个 → 它其实是模块，往下拆。

**状态**：`规划` | `开发中` | `已上线` | `已废弃`
**子项类型**：`页面` | `标签页` | `查询` | `按钮` | `报表` | `接口`
**交付**：`前端+后端` | `仅前端` | `仅后端` | `后端`

---

## 模块总览

| 模块 ID | 模块名称 | 说明 | 状态 |
|---|---|---|---|
| M00 | 租户管理 | tenant-admin 配置面：5 F（租户维护 / 租户成员 / 租户角色 / 角色权限 / 租户应用） | 规划 |
| M01 | 用户管理 | 当前用户视图 + 自然人关系网：4 F（用户维护 / 角色成员 / 租户成员 / SSO 登录） | 规划 |
| M04 | 应用管理 | 应用 / OAuth client 维度：4 F（应用维护 / 应用启用停用 / 身份认证 / 菜单管理） | 规划 |

---

## M00 租户管理

| 功能 ID | 功能名称 | 说明 | 状态 |
|---|---|---|---|
| M00.F01 | 租户维护 | 平台 admin 范围管理租户 | 已上线 |
| M00.F02 | 租户成员 | tenant-scoped 成员 CRUD + 邀请/接受/状态 | 已上线 |
| M00.F03 | 租户角色 | tenant × client 作用域角色 CRUD | 已上线 |
| M00.F04 | 角色权限 | role↔permission 矩阵 + 角色菜单授权 | 已上线 |
| M00.F05 | 租户应用 | `tenant_application` 订阅管理 | 已上线 |

### M00.F01 租户维护

> 端点路径：`/admin/tenants`（平台域，dev 简化不挂租户守卫）。语义参照：springboot AdminTenantsController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M00.F01.I01 | 租户列表 | 接口 | 前端+后端 | 平台 admin 分页查看全部租户 | 已上线 |
| M00.F01.I02 | 创建租户 | 接口 | 前端+后端 | 注册新租户（tenantKey 撞 unique → 400 constraint violation） | 已上线 |
| M00.F01.I03 | 租户详情 | 接口 | 前端+后端 | 查看单个租户（不存在 → 404） | 已上线 |
| M00.F01.I04 | 更新租户 | 接口 | 前端+后端 | 部分更新（PATCH，null 字段跳过；ACTIVE→1/其他→0） | 已上线 |
| M00.F01.I05 | 删除租户 | 接口 | 前端+后端 | 幂等删除（不存在也 204；级联靠 DB FK） | 已上线 |

### M00.F02 租户成员

> op 落表：`sys_user` + `tenant_member` + `tenant_member_role`。API 路径用 `userId`，内部按
> `(userId, tenant_id)` 解析为 `member_id`；删除只断 membership，不删全局 `sys_user`。
> 语义参照：springboot TenantMembersController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M00.F02.I01 | 成员列表 | 接口 | 前端+后端 | 查看租户内全部成员（分页 + status 过滤 DB 级分页前；排序 created_at DESC + id ASC） | 已上线 |
| M00.F02.I02 | 创建成员 | 接口 | 前端+后端 | 同时建 sys_user + tenant_member（plain: 密码家族约定；unique 撞 → 400） | 已上线 |
| M00.F02.I03 | 成员详情 | 接口 | 前端+后端 | 查看成员完整信息（寻不到 member 行 → 404） | 已上线 |
| M00.F02.I04 | 更新成员 | 接口 | 前端+后端 | 只改 email/mobile（PATCH，null 跳过；status 唯一通道是 /status 端点） | 已上线 |
| M00.F02.I05 | 删除成员 | 接口 | 前端+后端 | 只断 membership 不删 sys_user（先 resolve，不存在 → 404） | 已上线 |
| M00.F02.I06 | 邀请成员 | 接口 | 前端+后端 | 建 user（username=email、password=""、status=invited）+ member（status=active）；返回嵌套视图 | 已上线 |
| M00.F02.I08 | 状态切换 | 接口 | 前端+后端 | 双写 member.status 与 sys_user.status（四值字典） | 已上线 |

> I07（接受邀请）镜像 springboot 保持「规划」——shared 契约无对应端点（ADR：邀请即建号生效）。

### M00.F05 租户应用

> op 落表：`tenant_application`。订阅状态和到期时间参与授权上下文。语义参照：springboot TenantApplicationsController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M00.F05.I01 | 列出租户应用 | 接口 | 前端+后端 | 查看租户当前订阅的全部应用（分页） | 已上线 |
| M00.F05.I02 | 订阅应用 | 接口 | 前端+后端 | 绑定 clientId（未知 clientId → 404；重复订阅 → 400 constraint violation） | 已上线 |
| M00.F05.I03 | 更新应用订阅 | 接口 | 前端+后端 | 部分更新 status/expireTime（寻不到 → 404） | 已上线 |
| M00.F05.I04 | 移除应用订阅 | 接口 | 前端+后端 | 幂等退订（不存在也 204；不删除应用本体） | 已上线 |

### M00.F03 租户角色

> op 落表：`sys_role`（uk: tenant_id+client_id+role_code）。删除级联清 `sys_role_menu` +
> `tenant_member_role`（DB FK CASCADE）。语义参照：springboot TenantRolesController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M00.F03.I01 | 角色列表 | 接口 | 前端+后端 | 分页查看租户角色（排序 created_at ASC + id ASC；query clientId 接收但不过滤，镜像参照） | 已上线 |
| M00.F03.I02 | 创建角色 | 接口 | 前端+后端 | status=1、isPreset 缺省 false（clientId FK 冲突/roleCode 撞 unique → 400 constraint violation） | 已上线 |
| M00.F03.I03 | 角色详情 | 接口 | 前端+后端 | 查看单个角色（不存在或跨租户一律 404，不泄露存在性） | 已上线 |
| M00.F03.I04 | 更新角色 | 接口 | 前端+后端 | PATCH 只应用 roleName/description 非空字段（status 字段被忽略，镜像参照） | 已上线 |
| M00.F03.I05 | 删除角色 | 接口 | 前端+后端 | 先 resolve（不存在 → 404）；级联清理所有成员角色绑定与权限关联（DB FK） | 已上线 |

### M00.F04 角色权限

> op 落表：`sys_role_menu`（role_id+menu_id 复合主键）。PUT 全量替换（差量删 +
> ON CONFLICT DO NOTHING）。语义参照：springboot TenantRoleMenusController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M00.F04.I01 | 权限矩阵绑定 | 接口 | 前端+后端 | 权限码全量替换——shared 契约无对应生成端点，保持规划（镜像 M00.F02「接受邀请」条目的先例，见其表后注） | 规划 |
| M00.F04.I02 | 角色已授权菜单查询 | 查询 | 前端+后端 | RoleMenuGrant{roleId,tenantId,menuIds sorted,updatedAt=sys_role.updated_at} | 已上线 |
| M00.F04.I03 | 整批设置角色菜单 | 接口 | 前端+后端 | 全量替换（空 menuIds=合法清空；touch role.updatedAt；不存在 menuId 撞 FK → 400） | 已上线 |
| M00.F04.I04 | 清空角色菜单 | 接口 | 前端+后端 | 纯 bulk delete 幂等 204（不 resolve role、不 touch updatedAt） | 已上线 |

> I01（权限矩阵绑定·权限码全量替换）镜像 springboot 保持「规划」——shared 契约无对应端点。

## M01 认证管理

| 功能 ID | 功能名称 | 说明 | 状态 |
|---|---|---|---|
| M01.F01 | 用户维护 | 当前用户 whoami | 已上线 |
| M01.F02 | 角色成员 | 给 member 分配角色（member→role binding；与 M00.F02 字段维护是不同维度） | 已上线 |
| M01.F03 | 租户成员 | 当前用户的跨租户成员关系 + 切换 | 已上线 |
| M01.F04 | SSO 登录 | 密码登录 + 失败锁定 + OIDC + 登出 | 已上线 |

### M01.F03 租户成员

> 当前用户跨租户成员关系与租户切换。语义参照：springboot MeController（me/tenants + switch）。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M01.F03.I01 | 列出我的租户成员关系 | 查询 | 前端+后端 | created_at ASC + id ASC、不过滤 status、roleIds 跨租户原样吐出、query clientId 收但忽略（REQ-2026-005） | 已上线 |
| M01.F03.I02 | 切换当前租户 | 接口 | 前端+后端 | 校验链 401/400/404；非 disabled 成员即可切（否则 404 not an active member）；新签 access 带 tenant_id claim、refresh 不落库、无 DB 写幂等（REQ-2026-005） | 已上线 |

### M01.F01 用户维护

> 当前用户身份视图。落表：`sys_user` + `tenant_member`。语义参照：springboot MeController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M01.F01.I01 | 当前用户 whoami | 查询 | 前端+后端 | 返回当前会话用户的基础身份信息（id/email/memberships/currentTenantId，JWT claim 优先） | 已上线 |

### M01.F04 SSO 登录

> 鉴权入口：密码登录 + 失败锁定 + 登出。语义参照：springboot AuthController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M01.F04.I01 | 密码登录 API | 接口 | 仅后端 | 用邮箱+密码换取 access_token + refresh_token（JWT，token 对落库） | 已上线 |
| M01.F04.I02 | 失败锁定 | 接口 | 仅后端 | 连续 5 次密码错误锁定账户 15 分钟，窗口内拒绝登录（423 空体） | 已上线 |
| M01.F04.I06 | 登出（本地清理） | 接口 | 前端+后端 | 登出当前会话（204 空体） | 已上线 |

> I03（密码登录 UI，仅前端）不进本后端树；I04/I05/I07 见下方「已废弃功能子项」。

### M01.F02 角色成员

> op 落表：`tenant_member_role`。**与 M00.F02 字段维护不同维度**——M00.F02 管 member 自身字段/状态/邀请；M01.F02 管 member↔role 关系。语义参照：springboot TenantMembersController PUT /roles。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M01.F02.I01 | 分配角色 | 接口 | 前端+后端 | 用角色 ID 集合全量覆盖该成员的当前角色绑定（外来租户 roleId 静默忽略） | 已上线 |

## M04 应用管理

| 功能 ID | 功能名称 | 说明 | 状态 |
|---|---|---|---|
| M04.F01 | 应用维护 | 应用 CRUD + 公共元数据 | 已上线 |
| M04.F02 | 应用启用/停用 | `status` 字段切换 | 已上线 |
| M04.F03 | 身份认证 | OAuth authorize + token + refresh | 已上线 |
| M04.F04 | 菜单管理 | 菜单 CRUD + 结构 + 当前用户菜单 | 已上线 |

### M04.F01 应用维护

> 平台应用（oauth_client）维护与公共元数据。语义参照：springboot AdminClientsController + ClientsController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M04.F01.I01 | OAuth 应用列表 | 接口 | 前端+后端 | 仅有效 JWT（无角色门，镜像参照）；分页缺省 0/20、无排序无过滤（REQ-2026-005） | 已上线 |
| M04.F01.I02 | 创建 OAuth 应用 | 接口 | 前端+后端 | validity 缺省或 ≤0 → 3600/86400（应用层口径，非 DB 列默认）、autoApprove 缺省 false、status=1、clientId 撞 unique → 400、返回 200（REQ-2026-005） | 已上线 |
| M04.F01.I03 | OAuth 应用详情 | 接口 | 前端+后端 | findByClientId → 404；响应不含 clientSecret（DTO 无此字段，照参照实现修正原「回指纹」描述） | 已上线 |
| M04.F01.I04 | 更新 OAuth 应用 | 接口 | 前端+后端 | PATCH 只应用 clientName/redirectUris/scopes 三字段（其余 DTO 字段忽略）、不 touch updatedAt | 已上线 |
| M04.F01.I05 | 删除 OAuth 应用 | 接口 | 前端+后端 | 先 resolve → 404 非幂等；级联靠 DB FK ON DELETE CASCADE 清订阅/角色/菜单/token（应用层无吊销代码，照实修正原描述）；204 | 已上线 |
| M04.F01.I06 | 公共 client 元数据 | 接口 | 前端+后端 | 匿名可读（permitAll 严格匹配 /api/v1/clients/*）；仅 clientId/clientName/status 三字段；未知 → 404 | 已上线 |

### M04.F02 应用启用/停用

> oauth_client.status 字段切换。语义参照：springboot AdminClientsController set-status。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M04.F02.I01 | 启用/停用应用 | 接口 | 前端+后端 | status 必填、无值域校验任意 int 直写 smallint（镜像参照）；未知 client → 404；200 回更新后应用 | 已上线 |

### M04.F03 身份认证

> OAuth 2.0 authorization_code + refresh_token。语义参照：springboot OauthController。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M04.F03.I01 | 授权码签发 | 接口 | 前端+后端 | 校验 Bearer + redirect_uri 白名单（精确或 `?` 边界）后签发一次性 authorization_code（5 分钟过期） | 已上线 |
| M04.F03.I02 | 令牌交换 | 接口 | 前端+后端 | 用 authorization_code 换取 access_token + refresh_token（一次性消费，redirectUri 一致性校验） | 已上线 |
| M04.F03.I03 | 令牌刷新 | 接口 | 前端+后端 | 用 refresh_token 换取新对（rotate：旧 token 即标 revoked，重放被拒） | 已上线 |

### M04.F04 菜单管理

> op 落表：`sys_menu`（parent_id 无 FK，零值 UUID=根；级联只清 `sys_role_menu`）。
> admin 授权入口在 M00.F04。语义参照：springboot ClientMenusController + MeController.menus。

| 子项 ID | 名称 | 类型 | 交付 | 说明 | 状态 |
|---|---|---|---|---|---|
| M04.F04.I01 | 菜单列表 | 查询 | 前端+后端 | 按 client 查扁平菜单清单（含 parentId，不组树、不分页，镜像参照） | 已上线 |
| M04.F04.I02 | 创建菜单 | 接口 | 前端+后端 | parentId 缺省零值 UUID、sortOrder 缺省 0、status=1（不校验 parent 存在；契约 type 必填，参照的 directory 缺省在本仓不可达） | 已上线 |
| M04.F04.I03 | 菜单详情 | 接口 | 前端+后端 | 查看单个菜单（不存在 → 404；不比对 clientId，镜像参照） | 已上线 |
| M04.F04.I04 | 更新菜单 | 接口 | 前端+后端 | PATCH 只应用 title/path/component/perms/icon/sortOrder（parentId/type/status 忽略） | 已上线 |
| M04.F04.I05 | 删除菜单 | 接口 | 前端+后端 | 幂等删除（不存在也 204；级联只清 sys_role_menu 授权，子菜单不级联——镜像参照实现） | 已上线 |
| M04.F04.I06 | 同级排序 | 接口 | 前端+后端 | reorder：目标 menu 的 sortOrder=其在 orderedMenuIds 中的下标，返回该 client 全量扁平列表 | 已上线 |
| M04.F04.I07 | 切换父级 | 接口 | 前端+后端 | move：parentId 非 null 才改（坏 UUID → 400；不校验存在/成环，镜像参照） | 已上线 |
| M04.F04.I08 | 当前用户有效菜单 | 查询 | 前端+后端 | 四跳 join（member→member_role→role_menu→menu）按 clientId 组树；零值 parent→根、孤儿当根、roots 按 sortOrder 升序 | 已上线 |

---

## 已废弃功能子项

> 所有 `已废弃` / `已迁移` 状态的功能子项统一汇总到这里，**按子项 ID 顺序排列**。本节只收 I 级。

| 子项 ID | 名称 | 模块归属 | 迁移去向 | 状态 |
|---|---|---|---|---|
| M01.F04.I04 | OIDC Code 换取 | M01.F04 | 合并到 M04.F03.I02 authorization_code grant（saas-2026-09-16-001+003） | 已废弃 |
| M01.F04.I05 | refresh token | M01.F04 | 合并到 M04.F03.I02 refresh_token grant（saas-2026-09-16-001+003） | 已废弃 |
| M01.F04.I07 | 登出（全局 SSO） | M01.F04 | 预留位；待 ADR 决策 | 已废弃 |

---

## 维护约定

- 谁改功能，谁改表，同一个 commit。
- `规划` → `开发中`：必须先有需求文档引用它。
- 开发中 → 已上线：L5 会警告它缺设计映射与测试引用。警告不阻断，由人裁量。
- 本仓初始拆到 **M/F 级**；I 级等第一个需求落地时，按该需求涉及范围再拆（避免一次性虚构 60+ 子项）。
