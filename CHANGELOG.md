# 更新日志

格式照 `v<MAJOR>.<MINOR>.<PATCH>-<YYYYMMDD>`（tag 即放行：全量回归绿后打 tag）。

历史版本（tag 底账，明细见 git log）：

- `v0.1.8-20261011`（2026-10-11）— fix(ci): 冒烟步骤补 SAAS_CORS_ALLOWED_ORIGINS——c7db722 fail-fast 必读键漏配
- `v0.1.7-20261007`（2026-10-07）— feat(cors): SAAS_CORS_ALLOWED_ORIGINS 接线 CORSMiddleware——saas-flutter dev 5108 直连前提（Phase 2 T4）
- `v0.1.6-20261006`（2026-10-06）— chore(env): 补 .env.example/.env.test 两件套——5.104 L0.5 三件套对齐
- `v0.1.5-20261004`（2026-10-04）— chore(gitignore): 补 .env/.env.*.local 屏蔽——env 泄漏纪律
- `v0.1.4-20261003`（2026-10-03）— fix: /me/menus 单路由豁免 exclude_none——根 sentinel parentId:null 是家族已裁决形状
- `v0.1.3-20261002`（2026-10-02）— fix(deploy): sqlalchemy/psycopg2 升进主依赖——prod 首航镜像炸根因
- `v0.1.2-20261002`（2026-10-02）— fix(ci): workflow 触发器补 tags: ["v*"]——首署 tag 未触发根因
- `v0.1.0-20261002`（2026-10-02）— docs(req): REQ-2026-007 根路径跳转 Swagger 对齐文档——功能影响 0（基础设施端点不进树，待评审）
