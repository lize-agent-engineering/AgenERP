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
| Run app locally           | `docker compose up -d`（仓根 `docker-compose.yml`，roadmap 工作项 3 交付。**验证到哪一步**：`docker compose config -q` 在空环境下已绿并由门禁把守；「栈起得来且全部 healthy」**尚未验证**，归工作项 8，起栈尝试的原文与退出码见 `docs/logs/2026/08-21.md`） |
| Typecheck / compile check | `none`（mypy 未安装；装机后由人接进 mission commands） |
| Build                     | `none`（纯 Python 包，无构建步骤）              |
| Lint / static check       | `ruff check agenerp tests/unit tests/contracts` |
| Unit tests                | `python3 -m pytest tests/unit -q`              |
| Contract tests            | `python3 -m pytest tests/contracts -q`（工具契约层 v0 的判据，取自 `docs/masterplan/02-WBS.md` P0.2 的验收列。⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它——该缺口由 plan `2026-08-21-1022-2-tool-contract-layer-v0.md` 就地裁定，代偿控制是独立关闭审计；`missions/**` 是角色 B 禁区，要补得由人把这条命令加进 `commands.test`） |
| Seed dataset acceptance   | `python3 -m agenerp.seed --seed 42 --verify`（roadmap 工作项 7 的验收命令，取自 `docs/masterplan/02-WBS.md` P0.6 的验收列。语义：同种子两次生成 `diff` 为空**且**内置荒谬场景的断言全过 → 退 0。⚠️ WBS 原文写的是 `python -m …`，本机没有 `python` 这个可执行名，实际形态是 `python3`。⚠️ **它不在 `missions/p0-foundation.json` 的 `commands.test` 里**，`GATE_VERIFY` 复跑不到它——与上面 Contract tests 那一行同样的处理，理由相同（`missions/**` 是角色 B 禁区，要补由人做）；代偿控制是变异验证 + 独立关闭审计，见 `docs/architecture/module-boundaries.md` §12.7） |
| E2E / integration tests   | `python3 tools/gates/check_expected_red.py`（门禁判定器，L1；L2 live 门禁需活站点/docker，属 P0 交付物） |

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
