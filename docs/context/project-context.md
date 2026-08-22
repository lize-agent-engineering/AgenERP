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
| L2 live 门禁（快照）      | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_snapshot_diff_structured.py -q`（2026-08-21 由 plan `2026-08-21-1922-1` 实测：**exit 0，3 passed**，含 `test_field_addition_shows_up_as_structured_change`）。**三处口径必须一起看，缺一条就跑不出这个结果**：① **端口 18080** —— 8080 被本机另一套常驻 ERPNext 栈占着，`compose_stack` 有端口预检并会直接 fail；② **`AGENERP_SITE=frontend` 必须由命令给** —— ⚠️ **2026-08-22 改准（确认的漂移）**：此处此前写的是「`tests/gates/conftest.py` 全文不设这个变量」，**那句话是错的** —— 实测 `conftest.py:274` 在 `live_site` fixture 内部**会**设它。正确的说法更窄：`test_snapshot_diff_structured.py` 里那两条**不取任何 fixture**、直接调 `capture()`，永远走不到那行代码，所以必须由命令给。结论不变：它自己文档化的跑法 `AGENERP_LIVE=1 python3 -m pytest tests/gates -m live -q` **跑不绿这条门禁**（无参 `capture()` 会走离线来源 → 两次空快照 → 断言失败），详见 `docs/masterplan/STATE.md` §3 的补充事实行；③ **必须先起栈** —— 那两条 L1 快照门禁不取任何 fixture，栈没预起时它们在 `compose_stack` 之前就跑完并红在 connection refused（实测 exit 1 `FF.`，两次复跑一致）。⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它——与 Contract tests / Seed dataset 两行同样的处理，代偿控制是变异验证（实测有牙齿：把 `SiteSnapshotSource.read` 改成返回空元组 → exit 1 并逐字红在 `test_field_addition_shows_up_as_structured_change`）+ 独立关闭审计；`missions/**` 是角色 B 禁区，要补由人做 |
| L2 live 门禁（定制包往返） | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_customization_roundtrip_delete.py -q`（2026-08-21 由 plan `2026-08-21-2220-1` 实测：**exit 0，4 passed in 10.29s**）。**env 与上一行完全相同**，三处口径（端口 18080 / `AGENERP_SITE=frontend` 必须由命令给（**理由按上一行 2026-08-22 改准后的窄说法读**：`conftest.py:274` 在 `live_site` 内会设它，但不取 fixture 的那几条走不到那行）/ 必须先起栈）同样适用——此前本表**只收录了 `test_snapshot_diff_structured.py` 那一行**，本行是补上的。⚠️ 同样**不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它；代偿控制是变异验证 + 独立关闭审计。**变异验证的结论要连着读**：把清列改成 no-op → 逐字转红「留下了孤儿列：…」（**有牙齿**）；但把 `schema_drift` 改成返回空 → 门禁**绿**而物理列一列没删（**假绿**：空巡检 → 空交集 → 什么都没删，断言拿到的 `orphans` 也是空的）。**这条门禁对「巡检坏掉」零覆盖**，补偿证据是 `information_schema` 的一次性交叉验证，见 `docs/architecture/module-boundaries.md` §11.8 **⚠️ 2026-08-22 三次补记，就地改准**：上面「本行是补上的」那段说的「变异验证的结论要连着读」仍然成立，但本行此前隐含的「本机 4 条全绿 = 这条门禁没问题」**不成立**——它在**全新站点**上会红，红因不是清列坏了而是**巡检表达不出「零孤儿列」**（`bench execute` 对假值返回不打印，`trim_table` 回 `[]` 时 stdout 是零字节，旧 `run_json` 判成「载荷不是 JSON」）。已由 plan [`2026-08-22-0228-2`](../plans/p0-foundation/2026-08-22-0228-2-orphan-column-clearance-fresh-site.md) 修好（`agenerp/oob.py` 的 `FALSY_RESULT` 哨兵）。**CI 上已 4 条全绿**：run `32533449466`，job `gates-l2-live`（`96929876654`）`success`。 |
| L2 live 门禁（零依赖启动） | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_zero_dep_boot.py -q`（2026-08-21 由 plan `2026-08-21-2220-2` 实测：**exit 0，3 passed**）。⚠️ **本仓唯一一条在 CI 上真跑过的 L2**：`gates.yml` 的 `gates-l2` job 在 runner 上起栈跑同一组断言，run `32499273158`（sha `6ac1005`）结论 `success`，日志逐字 `3 passed in 2.68s`；runner 是 Docker 28.0.4 / Compose v2.38.2，本机是 29.2.1 / v5.0.2，**两边表现一致**。上面两条 L2（快照 / 定制包往返）**仍是本机独证**，别混为一谈。**⚠️ 2026-08-22 二次补记，就地改准**：「本仓唯一一条在 CI 上真跑过的 L2」这句**已经不成立**——plan `2026-08-22-0027-2` 的新 job `gates-l2-live` 在 CI 上对**全部 19 条**跑过整目录 live 判定（run `32509351108`，PR #1）。**但那次结论是红**（`::test_no_orphan_column_left_behind`，两次 attempt 都红、可复现），**PR 未合并，`main` 上没有这个 job**，所以「定制包往返」那条**在 `main` 上仍是本机独证**，而它在 CI 上已经被证明**不成立**。详见下一行与 `docs/masterplan/STATE.md` §3 的 2026-08-22 `[open]` 行。**⚠️ 2026-08-22 四次补记，就地改准（确认的 owner-doc 漂移）**：上面那句「**PR 未合并，`main` 上没有这个 job**」与「**在 `main` 上仍是本机独证**」**均已不成立**——plan `2026-08-22-1206-2` 已把 `gates-l2-live` 与 `verdict-tool-untouched` 两个 job 经 PR #3 `--ff-only` 落进 `main`（**落地 sha `3503f2c`**），`main` push 权威运行 **`32572618933`** 九个 job 全绿，`gates-l2-live`（job `97030229667`）日志逐字 `门禁 19 项：红 0，绿 19，跳过 0`。**因此「定制包往返」那条在 `main` 上已由 CI 判过并为绿，不再是本机独证。**⚠️ 那次可复现的红（run `32509351108`）是**永久证据，未被抹掉**，只是不再是当前状态。**env 与上面两行不同，别照抄**：这条门禁只取 `compose_stack`、**不取 `live_site`**，因此**不需要 `AGENERP_SITE` / `AGENERP_SITE_URL`**；端口 18080 与「必须先起栈」两条口径同样适用（不先起栈时 `compose_stack` 会自己 `up -d --wait`，慢但能跑；`test_compose_config_valid_with_empty_env` 不取任何 fixture）。⚠️ 同样**不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它；代偿控制是变异验证（实测有牙齿：把引导脚本的文案改成不含「AI 能力未配置」→ exit 1 并逐字红在「首页没有说明 AI 能力未配置」；改回后复跑 exit 0）+ 独立关闭审计 |
| L2 live 门禁（**整目录判定**） | `AGENERP_HTTP_PORT=18080 docker compose -f docker-compose.yml up -d --wait --wait-timeout 300` **先起栈**，再跑 `AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 tools/gates/check_expected_red.py`（2026-08-22 由 plan `2026-08-22-0027-1` 交付并实测）。**这是上面三行的合并跑法**：判定器在 `AGENERP_LIVE=1` 下走 **live 判定模式**，契约是「全部门禁绿、零 red、零 skip」，**不读** `tools/gates/expected-red.txt`；口径见 `docs/architecture/system-baseline.md` §14.4。三处口径（端口 18080 / `AGENERP_SITE=frontend` 必须由命令给 / 必须先起栈）对它**同样成立**——它只是换个进程去跑同一组 pytest。**实测（本机，2026-08-22，共六跑）**：`门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip` → **exit 0**，五跑如此。⚠️ **但第一跑是 exit 1，照实记**：那一跑打的是 `门禁 19 项：红 1，绿 18，跳过 0` 并逐字点名 `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`；**原样复跑四次全绿，不可复现**（`AGENTS.md` 裁判规则 3：复跑不出来就记「不可复现」，不许猜根因）。把这条门禁当**间歇性**看待，别当稳定绿。**变异验证有牙齿**：把 `agenerp/apply.py` 的删除路径改成 no-op → exit 1 且点名集合**恰好**多出 `::test_removing_from_pack_actually_deletes_on_site` 一条；复原后回 exit 0。⚠️ 同样**不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它（且**不该**接进去：`commands.test` 每轮都跑，塞一条要起 docker 栈的命令会让每轮 `GATE_VERIFY` 依赖活栈）；`missions/**` 是角色 B 禁区，要补由人做。**验证范围：live 只在本机做过，CI 未验证**。**⚠️ 2026-08-22 二次补记，就地改准（确认的 owner-doc 漂移，Minimum Rule 14 不降级）**：上面那句「**验证范围**：live 只在本机做过，CI 未验证」**已经不成立**——plan [`2026-08-22-0027-2`](../plans/p0-foundation/2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md) 在 CI 上真跑了整目录 live 判定（新 job `gates-l2-live`，run `32509351108`，PR #1，head `9a8832f`）。**结论是红，不是绿，红因是 `::test_no_orphan_column_left_behind`**：两次 attempt（第二次是 `gh run rerun --failed` 原样复跑）**都**打出 `门禁 19 项：红 1，绿 18，跳过 0` 并逐字点名 `tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind`。**可复现，因此不是「不可复现」，更不是「CI 已验证」。** 红在**实现**（`apply_pack` 的物理列清除面在 runner 的全新站点上不成立），不是红在判据；修它要动 `agenerp/**`，需要一个专门的 successor plan（带「实跑前后全量 `capture` 对照」证据）。**PR #1 未合并，`main` 上没有这个 job。** 详见 `docs/masterplan/STATE.md` §3 的 2026-08-22 `[open]` 行。⚠️ **本机与 runner 的差异照实记**：同一条门禁本机 6 跑红 1 次，runner **2 跑红 2 次**——起草时「runner 全新站点方向更有利」的推理**被实测证伪**，**不猜根因**（裁判规则 3）。 **⚠️ 2026-08-22 三次补记，就地改准（本 plan 推翻上一条补记的结论）**：上面「**结论是红，不是绿**」「红在**实现**（`apply_pack` 的物理列清除面在 runner 的全新站点上不成立）」「同一条门禁本机 6 跑红 1 次、runner 2 跑红 2 次……**不猜根因**」三处**均已被本轮取证推翻或补全**——plan [`2026-08-22-0228-2`](../plans/p0-foundation/2026-08-22-0228-2-orphan-column-clearance-fresh-site.md)：① **清除面从来没坏过**（实跑前后全量 `capture` 对照 `entries/columns added+removed` 全空，`information_schema` 独立确认探针列不在 `tabItem` 上，且非空累积站点上别的门禁留下的孤儿列原样保留）；② 真红因是 `agenerp/oob.py` `run_json` 把「exit 0 且 stdout 全空」判成「载荷不是 JSON」——`bench execute` 只在返回值为真时才打印（`frappe/commands/utils.py:285` 的 `if ret:`，容器内实读），而全新站点上清干净之后孤儿列集合必然归零，于是 **`trim_table` 回 `[]` → 零字节 → 必然红**；③ **本机/runner 的差异不再是未知**：本机常驻站点长期躺着别的门禁留下的残留（冷起前实测 `["agenerp_gate_probe"]`），清完自己的探针后集合仍非空 → 绿；全新站点没有残留 → 必然红。方向、频次、站点形态三者全部对得上。**修法**：`run_json` 返回哨兵 `FALSY_RESULT`，调用方按自身返回类型翻译；不吞异常、不放宽收窄，三种真故障（函数不存在 / 函数内部抛错 / 站点不存在）实测**全部非零退出**。**CI 已转绿，`验证范围` 那句现在成立**：run `32533449466`（PR #1，head `c2c688b`），`gates-l2-live`（job `96929876654`）**`success`**，日志逐字 `门禁 19 项：红 0，绿 19，跳过 0`；`verdict-tool-untouched`（`96929876658`）仍 `success`。**本机三面证明**：全新站点连跑 3 次 exit 0 · 多轮累积站点第 4 跑 exit 0 · 变异（冷起全新站点上删掉该分支）exit 1 且点名集合**恰好一条**，与 run `32509351108` 的输出逐字一致。**⚠️ 2026-08-22 四次补记，就地改准（确认的 owner-doc 漂移，Minimum Rule 14 不降级）**：此前本行写「**PR #1 仍未合并，`main` 上仍没有这个 job**——因此 `main` 上这条门禁**仍是本机独证**」，**该陈述已不成立**。plan `2026-08-22-1206-2` 把两个 job 经新 PR #3 `--ff-only` 落进 `main`，**落地 sha `3503f2c89d78f44f94e0e0ff9f6061ca72e90b89`**（= PR #3 上跑绿的那个 sha）；`main` push 权威运行 **`32572618933`**（event `push`）**九个 job 全部 `success`**，`gates-l2-live`（job `97030229667`）日志逐字 `门禁 19 项：红 0，绿 19，跳过 0` / `✅ live 判定：全部门禁绿，零 red、零 skip`。**这条整目录 live 判定此刻在 `main` 上由 CI 服务端复跑，不再是本机独证。**⚠️ **仍要照实读的两条**：① 它**不在** `missions/p0-foundation.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到它，服务端判定的入口只有 `gates.yml`；② PR #1 与 PR #2 已 `CLOSED`（留有说明评论），其历史 run（`32509351108` 红 / `32533449466` 绿 / 四条变异实验）**仍可 `gh run view`，一条都没被抹掉**。 |
| 带外容器命令（本仓第二条站点传输） | 读：`docker compose -f docker-compose.yml exec -T backend bench --site frontend execute frappe.model.meta.trim_table --kwargs "{'doctype':'Item','dry_run':True}"`（**`--kwargs` 是 Python 字面量不是 JSON**，喂 `json.dumps` 会红在 `NameError: name 'true' is not defined`）；读：`docker compose -f docker-compose.yml exec -T backend cat sites/frontend/site_config.json`（**DDL 拿库名的唯一来源**，`db` 服务不设 `MYSQL_DATABASE`，库名推不出来）；**写**：`docker compose -f docker-compose.yml exec -T db sh -c 'mariadb -uroot -p"$MYSQL_ROOT_PASSWORD" <db_name> -e '\''ALTER TABLE `tabItem` DROP COLUMN `col`;'\'''`（SQL 用**单引号**包，反引号落在双引号里会被 shell 当成命令替换）。落点 `agenerp/oob.py`，能调什么被 `ALLOWED_CALLS` 钉到**参数一级**；与红线 7 的界线见 §11.8。**`ALTER TABLE … DROP COLUMN` 不可逆**，动它之前先 `docker compose exec -T backend bench --site frontend backup` **⚠️ 2026-08-22 补记，效力范围具体化（不是改判对错）**：上面那句「动它之前先 `bench backup`」**没有错，也不弱化**——`DROP COLUMN` 确实不可逆，作为操作建议它完全成立。补的是**它约束谁**：它是给**手敲这些命令的人**的前置动作，**`apply_pack` 自动跑那条链上没有任何东西执行它**（链路 `agenerp/pack.py:153` `apply_pack` → `agenerp/apply.py:251` `execute_plan` → `:254` `drop_orphan_columns` → `agenerp/oob.py:255` `drop_columns`；实测 `grep -rn "backup" agenerp/*.py` → **零命中**，`agenerp/tools_readonly.py:63` 的「取证」是别的词义）。**别把它读成一条全局前置条件**：代码侧此刻零备份、零取证。这条真实风险已登记进 [`docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`](../backlog/irreversible-ddl-has-no-code-level-precondition.md)，带触发条件，**交人裁定，本轮不实现**（出处 plan [`2026-08-22-1041-1`](../plans/p0-foundation/2026-08-22-1041-1-destructive-write-owner-doc-alignment.md)）。 |

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
