# REQ-2026-001 shared 契约全量对齐总纲

| 项 | 值 |
|---|---|
| 提出人 | zcqiand |
| 提出日期 | 2026-09-29 |
| 优先级 | P0 |
| 状态 | 已评审 |
| 关联 ADR | ADR-0041（suite：fastapi codegen 选型三层全生成） |

## 1. 需求描述

### 用户原话

> 需求就是shared所有需求

### 我的理解

本仓（saas-identity-platform-fastapi）把 saas 家族 shared 契约（saas-identity-platform-shared，
TypeSpec SSOT）定义的**全部业务面**实现到与家族既有后端（springboot / aspnetcore / rails）
功能对等：`docs/functions/function-tree.md` 全部 3 模块 13 功能从「规划」逐批转为「已上线」，
生成骨架里所有端点从「未实现 500 兜底」变为真实现。

口径（2026-09-29 用户三项拍板）：

1. **范围**：saas + lab 双 fastapi 仓都做（lab 仓另立镜像 REQ）。
2. **REQ 形态**：本文件是**总纲**——只立范围、验收与分批计划；实现按批次拆后续
   `/req` 逐批进门（届时才拆 I 级子项 + red-first 补测试）。
3. **验收口径**：家族 contract-test 收录 fastapi target，live 模式对本仓全部断言绿。

### 澄清记录

| 疑问 | 澄清结论 | 澄清人 | 日期 |
|---|---|---|---|
| 落单仓还是双仓 | 双仓都做，各自立 REQ | zcqiand | 2026-09-29 |
| 一份 REQ 做完还是总纲+分批 | 总纲 REQ + 分批实现（后续 /req 逐批进门） | zcqiand | 2026-09-29 |
| 验收对齐什么 | 家族 contract-test 全绿（fastapi target，live 模式） | zcqiand | 2026-09-29 |

## 2. 验收标准

| 编号 | 场景（给定） | 操作（当） | 预期（则） |
|---|---|---|---|
| AC-1 | contract-test 仓 CONTRACT_TARGETS 已含本仓 target | 跑 live 模式全量套件 | 本仓相关断言全绿（0 fail / 0 skip） |
| AC-2 | 任一批次实现完成 | 跑 `python scripts/gate.py -p saas-identity-platform-fastapi` | L1-L4 全绿（L4 由该批 red-first 测试转绿） |
| AC-3 | shared 契约演进或 DB 演进 | 跑 `check_codegen_idempotent.py --strict` 与 `scripts/scaffold-entities.sh` | 均 PASS（生成区零手改，API/DTO/实体仍全生成） |
| AC-4 | shared 契约 `generated/openapi/openapi.yaml` 全部 path | 对照本仓 `app.routes` | 端点一一对应：无缺口、无私加（硬规则 §4） |
| AC-5 | 全部分批完成 | 查 function-tree | 13 功能全部「已上线」，本 REQ 关闭为「已验收」 |

## 3. 任务拆解（分批计划，每批一道后续 /req）

| 任务 ID | 任务描述 | 类型 | 负责人 | 预估 | 状态 |
|---|---|---|---|---|---|
| T-1 | 批1 认证底座：密码登录/失败锁定/登出（M01.F04）+ OAuth authorize/token/refresh（M04.F03）+ whoami（M01.F01）——其余一切的前置 | 开发 | claude | 大 | 待开始 |
| T-2 | 批2 租户面：租户维护（M00.F01）+ 租户成员（M00.F02）+ 租户应用（M00.F05） | 开发 | claude | 大 | 待开始 |
| T-3 | 批3 权限与菜单：租户角色（M00.F03）+ 角色权限矩阵（M00.F04）+ 菜单管理（M04.F04） | 开发 | claude | 大 | 待开始 |
| T-4 | 批4 应用与用户关系网收尾：应用维护/启停（M04.F01、M04.F02）+ 角色成员/跨租户（M01.F02、M01.F03） | 开发 | claude | 中 | 待开始 |
| T-5 | 批5 contract-test 接入本仓 target + live 全绿收口（AC-1） | 开发 | claude | 中 | 待开始 |

## 4. 功能影响（需求与功能对齐的唯一位置）

> 13 个 ID 全部已存在于 `docs/functions/function-tree.md`（状态=规划），无需新登记；
> 状态翻转在各批实现 /req 内完成，本总纲不改树。

| 功能 ID | 功能名称 | 影响类型 | 说明 | 关联任务 |
|---|---|---|---|---|
| M01.F04 | SSO 登录 | 新增 | 本仓首次实现（密码登录+失败锁定+OIDC+登出） | T-1 |
| M04.F03 | 身份认证 | 新增 | 本仓首次实现（authorize + token + refresh） | T-1 |
| M01.F01 | 用户维护 | 新增 | 本仓首次实现（whoami） | T-1 |
| M00.F01 | 租户维护 | 新增 | 本仓首次实现 | T-2 |
| M00.F02 | 租户成员 | 新增 | 本仓首次实现 | T-2 |
| M00.F05 | 租户应用 | 新增 | 本仓首次实现 | T-2 |
| M00.F03 | 租户角色 | 新增 | 本仓首次实现 | T-3 |
| M00.F04 | 角色权限 | 新增 | 本仓首次实现 | T-3 |
| M04.F04 | 菜单管理 | 新增 | 本仓首次实现 | T-3 |
| M04.F01 | 应用维护 | 新增 | 本仓首次实现 | T-4 |
| M04.F02 | 应用启用/停用 | 新增 | 本仓首次实现 | T-4 |
| M01.F02 | 角色成员 | 新增 | 本仓首次实现 | T-4 |
| M01.F03 | 租户成员 | 新增 | 本仓首次实现（跨租户关系+切换） | T-4 |

变更：0；删除：0。

## 5. 流程影响

无（本仓无流程图；OAuth/登录流程形状以 shared 契约与家族参照实现为准）。

## 6. 风险与回滚

| 风险 | 影响面 | 缓解 | 回滚方式 |
|---|---|---|---|
| python-fastapi 生成器为官方 beta，升级可能破产物模板 | 生成区 | 7.24.0 钉版（openapitools.json），升级走 ADR | git revert 生成区 commit |
| contract-test 尚无 fastapi target | AC-1 | 批5 专项接入；接入前各批以本仓 L4 + AC-4 端点对照为过渡验收 | target 开关独立，不影响既有四后端断言 |
| 体量大（13 功能）跨多会话 | 账本一致性 | 每批独立 /req + 独立验收 + session.json 交接 | 批次间互不阻塞，任一批可独立回退 |
| 实现手改生成区抄近路 | 硬规则 §4 | 生成区 regen 先删后写 + 幂等门 strict（AC-3） | regen 即抹掉手改，漂移必红 |
