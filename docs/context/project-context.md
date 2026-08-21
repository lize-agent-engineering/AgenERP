# Project Context

## Purpose

The shortest static baseline an AI agent needs before doing useful work: identity, documentation freshness, technical stack, and verification commands.

Update it in place. Do not create dated copies.

This file intentionally does **not** track "what is being worked on right now". That is found by scanning unfinished plans in `docs/plans/`. Keeping high-churn active-work state here makes the file hard to maintain and prone to staleness.

## Companion Context Files

This file is the AI entry point. The following `docs/context/` companions are read on demand — most mission-driver flow steps load this file first, then route to them:

| File | When to read |
|---|---|
| `ai-autonomy-policy.md` | Before any task that changes code, model, or product behavior — autonomy levels, Protected Areas, reviewer availability |
| `codebase-map.md` | When locating code, making cross-module changes, or entering an unfamiliar area — entry points, common change routes, fragile files |
| `source-of-truth-and-precedence.md` | When facts conflict or it is unclear which doc is authoritative |

## Project Identity

- Project name: AgenERP
- Product type: 应用层产品 —— Agent 驱动的 ERP，长在 Frappe / ERPNext 之上（不重造会计与制造内核，见 `docs/masterplan/DECISIONS.md` D-7）
- Primary users: 中小企业的 ERP 实施者与业务管理员——他们要改的是自己企业的系统形态，而不是写代码
- Documentation freshness: `partially stale`

**Freshness gating:**

- If freshness is `stale` or `unknown`, agents may research, audit, and draft alignment docs, but must not implement product behavior until the baseline is re-established or a human confirms intended behavior.
- If freshness is `partially stale`, agents may implement only slices whose requirement, owner doc, codebase-map route, and touched code area have been verified fresh; otherwise treat the slice as `plan-first` or `research-only`.
- AI may not mark stale docs fresh without human confirmation or human-approved owner-doc evidence.

## Current Technical Baseline

- Frontend stack: 暂无自有前端。呈现层由 Frappe / ERPNext 的 Desk 与 Web 视图承担；自有呈现层是 P2 的事。
- Backend stack: Python 3.12.9（`pyproject.toml` 声明 `requires-python >= 3.11`）· 宿主为 Frappe / ERPNext · `agenerp` 是仓库根目录的扁平包，**零第三方依赖可导入**（CI 的 `gates-l1` job 只 `pip install pytest`）
- Database/model source: DocType —— Frappe 的模型定义即 schema 源。定制以可 diff 的「定制包」形式落盘（`agenerp.pack`），站点状态以快照 + 结构化 diff 表达（`agenerp.snapshot`）。

## Verification Commands

下表每一行都是在本机实测跑得出退出码的真命令（2026-08-20 定表，Contract tests 一行 2026-08-21 补入并实测）；
跑不起来的写 `none` 并注明它是 P0 的交付物。

| Purpose                   | Command                                       |
| ------------------------- | --------------------------------------------- |
| Install dependencies      | `python3 -m pip install pytest`                |
| Run app locally           | `docker compose up -d`（仓根 `docker-compose.yml`，roadmap 工作项 3 交付。**验证到哪一步，三件事分开说**：① **起栈与健康判定已实证**——2026-08-21 由 plan `2026-08-21-1634-2` 冷起实测，`AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 300` → exit 0（68 秒），`db`/`redis-cache`/`redis-queue`/`backend`/`websocket`/`frontend` 六个 healthy，首页 `/api/method/ping` → 200，并做过变异验证（探针改成必然失败的地址 → exit 1 并指名 unhealthy 的服务）；判定口径写在 `docs/architecture/system-baseline.md` §14.2，**三个 worker 的健康不可判，「全部 healthy」是收窄过的集合**。② **首页降级文案已落地**——2026-08-21 由 plan `2026-08-21-2220-2` 交付：compose 一次性服务 `bootstrap-homepage` 在建站后把「AI 能力未配置」写进 `Website Settings.banner_html`，`down -v` 冷起后 `up -d --wait --wait-timeout 300` → exit 0（62 秒），`curl -H "Host: frontend" http://127.0.0.1:18080/` → 200 且正文含该文案，重复 `up -d` 幂等；口径与残余风险见 `docs/architecture/system-baseline.md` §14.3。③ **L2 门禁在 live 判定环境下已全绿，但名单不动**——`AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_zero_dep_boot.py -q` → exit 0，3 passed；**`compose_stack` fixture 已由人在 `ede5440` 实现**（`tests/gates/conftest.py` 全文零 `NotImplementedError`，阻塞已在 `3fed439` 关闭）。三条仍留在 `tools/gates/expected-red.txt` 名单内，因为**默认判定环境没有 `AGENERP_LIVE`，L2 在那里恒红**，而人裁定过「名单必须反映判定器实际看到的」（`STATE.md` §2 11:20Z）。①**不等于**②③，不得把工作项 8 报成「名单已划掉」。命令原文与退出码见 `docs/logs/2026/08-21.md`） |
| Typecheck / compile check | `none`（mypy 未安装；装机后由人接进 mission commands） |
| Build                     | `none`（纯 Python 包，无构建步骤）              |
| Lint / static check       | `ruff check agenerp tests/unit tests/contracts` |
| Unit tests                | `python3 -m pytest tests/unit -q`              |
| Contract tests            | `python3 -m pytest tests/contracts -q`（工具契约层 v0 的判据，取自 `docs/masterplan/02-WBS.md` P0.2 的验收列。⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它——该缺口由 plan `2026-08-21-1022-2-tool-contract-layer-v0.md` 就地裁定，代偿控制是独立关闭审计；`missions/**` 是角色 B 禁区，要补得由人把这条命令加进 `commands.test`） |
| Seed dataset acceptance   | `python3 -m agenerp.seed --seed 42 --verify`（roadmap 工作项 7 的验收命令，取自 `docs/masterplan/02-WBS.md` P0.6 的验收列。语义：同种子两次生成 `diff` 为空**且**内置荒谬场景的断言全过 → 退 0。⚠️ WBS 原文写的是 `python -m …`，本机没有 `python` 这个可执行名，实际形态是 `python3`。⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它——与上面 Contract tests 那一行同样的处理，理由相同（`missions/**` 是角色 B 禁区，要补由人做）；代偿控制是变异验证 + 独立关闭审计，见 `docs/architecture/module-boundaries.md` §12.7） |
| E2E / integration tests   | `python3 tools/gates/check_expected_red.py`（门禁判定器，L1；L2 live 门禁需活站点/docker，属 P0 交付物） |
| L2 live 门禁（快照）      | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q`（2026-08-21 由 plan `2026-08-21-1922-1` 实测：**exit 0，3 passed**，含 `test_field_addition_shows_up_as_structured_change`）。**三处口径必须一起看，缺一条就跑不出这个结果**：① **端口 18080** —— 8080 被本机另一套常驻 ERPNext 栈占着，`compose_stack` 有端口预检并会直接 fail；② **`AGENERP_SITE=frontend` 必须由命令给** —— `tests/gates/conftest.py` 全文不设这个变量，它自己文档化的跑法 `AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q` **跑不绿这条门禁**（无参 `capture()` 会走离线来源 → 两次空快照 → 断言失败），详见 `docs/masterplan/STATE.md` §3 的补充事实行；③ **必须先起栈** —— 那两条 L1 快照门禁不取任何 fixture，栈没预起时它们在 `compose_stack` 之前就跑完并红在 connection refused（实测 exit 1 `FF.`，两次复跑一致）。⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它——与 Contract tests / Seed dataset 两行同样的处理，代偿控制是变异验证（实测有牙齿：把 `SiteSnapshotSource.read` 改成返回空元组 → exit 1 并逐字红在 `test_field_addition_shows_up_as_structured_change`）+ 独立关闭审计；`missions/**` 是角色 B 禁区，要补由人做 |
| L2 live 门禁（定制包往返） | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`（2026-08-21 由 plan `2026-08-21-2220-1` 实测：**exit 0，4 passed in 10.29s**）。**env 与上一行完全相同**，三处口径（端口 18080 / `AGENERP_SITE=frontend` 必须由命令给 / 必须先起栈）同样适用——此前本表**只收录了 `test_snapshot_diff_structured.py` 那一行**，本行是补上的。⚠️ 同样**不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它；代偿控制是变异验证 + 独立关闭审计。**变异验证的结论要连着读**：把清列改成 no-op → 逐字转红「留下了孤儿列：…」（**有牙齿**）；但把 `schema_drift` 改成返回空 → 门禁**绿**而物理列一列没删（**假绿**：空巡检 → 空交集 → 什么都没删，断言拿到的 `orphans` 也是空的）。**这条门禁对「巡检坏掉」零覆盖**，补偿证据是 `information_schema` 的一次性交叉验证，见 `docs/architecture/module-boundaries.md` §11.8 |
| L2 live 门禁（零依赖启动） | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_zero_dep_boot.py -q`（2026-08-21 由 plan `2026-08-21-2220-2` 实测：**exit 0，3 passed**）。⚠️ **本仓唯一一条在 CI 上真跑过的 L2**：`gates.yml` 的 `gates-l2` job 在 runner 上起栈跑同一组断言，run `32499273158`（sha `6ac1005`）结论 `success`，日志逐字 `3 passed in 2.68s`；runner 是 Docker 28.0.4 / Compose v2.38.2，本机是 29.2.1 / v5.0.2，**两边表现一致**。上面两条 L2（快照 / 定制包往返）**仍是本机独证**，别混为一谈。**env 与上面两行不同，别照抄**：这条门禁只取 `compose_stack`、**不取 `live_site`**，因此**不需要 `AGENERP_SITE` / `AGENERP_SITE_URL`**；端口 18080 与「必须先起栈」两条口径同样适用（不先起栈时 `compose_stack` 会自己 `up -d --wait`，慢但能跑；`test_compose_config_valid_with_empty_env` 不取任何 fixture）。⚠️ 同样**不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它；代偿控制是变异验证（实测有牙齿：把引导脚本的文案改成不含「AI 能力未配置」→ exit 1 并逐字红在「首页没有说明 AI 能力未配置」；改回后复跑 exit 0）+ 独立关闭审计 |
| 带外容器命令（本仓第二条站点传输） | 读：`docker compose -f docker-compose.yml exec -T backend bench --site frontend execute frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"`（**`--kwargs` 是 Python 字面量不是 JSON**，喂 `json.dumps` 会红在 `NameError: name 'true' is not defined`）；读：`docker compose -f docker-compose.yml exec -T backend cat sites/frontend/site_config.json`（**DDL 拿库名的唯一来源**，`db` 服务不设 `MYSQL_DATABASE`，库名推不出来）；**写**：`docker compose -f docker-compose.yml exec -T db sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" <db_name> -e '\''ALTER TABLE `tabItem` DROP COLUMN `col`;'\'''`（SQL 用**单引号**包，反引号落在双引号里会被 shell 当成命令替换）。落点 `agenerp/oob.py`，能调什么被 `ALLOWED_CALLS` 钉到**参数一级**；与红线 7 的界线见 §11.8。**`ALTER TABLE … DROP COLUMN` 不可逆**，动它之前先 `docker compose exec -T backend bench --site frontend backup` |

**这就是当前可跑的全部**：本仓此刻没有全量套件（无 build、无 typecheck，L2 门禁未解锁）。
不要把上面几条可跑命令的绿说成「全量验证通过」——那是 scoped verification。

门禁的判定权归 `tools/gates/check_expected_red.py`：名单内红 = 正常，名单内绿 = 名单过期，
名单外红 = 真的坏了，出现 skip = 有人放松裁判。ruff 与它无关，且 `tests/gates/**` 已按红线 1
排除在 lint 作用域外（`pyproject.toml` 的 `[tool.ruff].exclude`）。

## Optional Layers Currently In Use

Mark only the optional layers this project actually maintains.

- [x] `docs/discussions/`
- [x] `docs/audits/`
- [x] `docs/testing/`
- [x] `docs/skills/`
- [x] `docs/analysis/`
- [x] `docs/retrospectives/`
- [x] `docs/lessons/`

**本仓七个可选层均在用**，一个未勾也没有。2026-08-21 实测各层文件数：
`discussions` 2 / `audits` 4 / `testing` 3 / `skills` 16 / `analysis` 3 / `retrospectives` 2 / `lessons` 1。
此前七格全部未勾是**起模板时留下的漂移**，不是「这些层没在用」的声明——
`docs/skills/README.md` 的 Skill Routing Rule、`docs/audits/` 的关闭审计记录、
`docs/analysis/2026-08-19-pre-build-validation.md` 都已是被其他文档正式引用的真相源。

## AI Block Conditions

AI MUST stop and wait for human input before proceeding when:

- verification commands are all placeholders and cannot be inferred from the project
- any change touches payment or data-deletion paths with no existing test coverage and no owner doc describing expected behavior
- no requirement or owner doc describes the intended behavior of the change — do not implement into a vacuum (this replaces the old "active requirement is none" gate; whether a requirement/owner doc exists is checked against `docs/requirements/` and `docs/design/`, not a field here)

These are project-specific hard stops in addition to `AGENTS.md`, `docs/context/ai-autonomy-policy.md`, source-of-truth conflict rules, and required plan/closure audit rules.

For ambiguity that does not affect user-visible behavior, contracts, protected areas, or closure evidence, resolve by writing assumptions into the relevant doc and proceed according to the autonomy policy. Mark uncertain assumptions explicitly so humans can review later.

## Notes For AI Agents

- If this file is empty or stale, ask for or create a context update before large implementation work.
- **Current work in progress**: inspect unfinished plans in `docs/plans/`, not this file.
- AI autonomy defaults to `implement`; it is gated by freshness (above) and Protected Areas (`ai-autonomy-policy.md`). No per-slice autonomy value is maintained here — autonomy labels live on backlog/roadmap work items, not in this file.
- AI may correct factual context from live repo evidence, but must not mark stale docs fresh or downgrade protected areas without human confirmation.
- Do not report verification success while commands still contain `<fill real command>` placeholders.
