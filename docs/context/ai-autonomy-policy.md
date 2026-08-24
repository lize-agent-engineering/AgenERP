# AI Autonomy Policy

## Purpose

This file defines when AI agents may proceed without asking and when they must stop for human input.

Keep it short and project-specific. Update it whenever the team wants AI to take more or less initiative.

AI may make this file stricter by marking work more constrained, but AI must not loosen protected areas, change `ask-first`/`blocked`/`research-only` work to `implement`, or remove blockers without explicit human confirmation or owner-doc evidence marked as human-approved.

AI-authored or AI-modified docs, including owner docs, cannot be used as evidence to loosen autonomy, clear blockers, mark docs fresh, or downgrade protected areas unless a human explicitly approves that evidence.

## Autonomy Levels

Use these labels on backlog/roadmap work items (they are per-item, not a global field in `project-context.md`):

- `implement` - AI may implement after reading the listed requirement, owner doc, and verification commands.
- `plan-first` - AI may draft or update the plan, but implementation waits for plan audit and any protected-area approval required by the table below.
- `ask-first` - AI must ask before changing code or user-visible behavior.
- `research-only` - AI may inspect, summarize, and propose options, but must not modify product behavior.
- `blocked` - AI must not proceed until the blocker is resolved in files or by human confirmation.

The default level is `implement` for work items with no explicit label. The default is gated by documentation freshness (`project-context.md`) and the Protected Areas below. A human may tighten the project default by editing this file; AI may tighten (never loosen) it based on evidence.

## Reviewer Availability

Set one value for the copied project:

- Reviewer availability: `subagent`

本仓的实际做法：草案评审与关闭审计都走独立子代理（fresh session，不带实现上下文）。
出处：`docs/context/conventions.md` §Review Rule 与 `AGENTS.md` §Reviewer-Availability Fallback 均以此为前提；
`docs/plans/` 下各 plan 的 `## Draft Review Record` 是它已在运行的证据。

If this value is still a placeholder, treat reviewer availability as `none` and treat protected-area or high-risk plans as blocked until human/subagent review is configured.

Rules:

- `human` or `subagent` - use that reviewer for required plan and closure audits.
- `none` - cold replay may be used only for non-protected, non-high-risk plans. Cold replay is not a second reviewer; it is a documented self-check performed after implementation context is set aside.
- Protected areas, unresolved product risk, or source-of-truth conflicts still require human/subagent review or must remain blocked.

## AI May Proceed Without Asking When

- the work item is marked `implement` (or has no label and defaults to `implement`) or the user directly requests a local low-risk change
- a requirement or owner doc describes the work's intended behavior with concrete acceptance criteria
- for backlog-selected work, the backlog row is `ready`, has no stale links, and does not require a missing plan
- verification commands in `docs/context/project-context.md` are real commands, not placeholders
- protected-area placeholders in this file have been replaced with real entries or explicit `none`
- documentation freshness in `docs/context/project-context.md` is `fresh`, or the active slice has explicitly verified fresh requirement, owner doc, codebase-map route, and touched code area
- the task does not touch a protected area below
- open questions are explicitly non-blocking

## AI Must Ask Or Stop Before

- changing product scope when the requirement or owner doc is ambiguous
- changing database/model shape, data deletion, payment, auth, permission, deployment, or external integration behavior without an owner doc and test strategy
- inventing behavior for an external system that is not described in committed integration docs or tests
- skipping required verification because commands are missing, broken, or too slow
- closing a plan whose audit, verification, docs, or checklist evidence is missing
- proceeding when live code and owner docs conflict and resolving the conflict would change user-visible behavior or public contracts
- loosening autonomy labels, protected-area rules, or blockers without human confirmation or human-approved owner-doc evidence
- proceeding with implementation when documentation freshness is `stale`, `unknown`, or `partially stale` for the active slice; first perform baseline research or a plan-first alignment slice

## Protected Areas

Fill these for the copied project.

If this table still contains placeholders, AI must treat payment, auth/permissions, data deletion, database/model shape, deployment, and external integrations as `ask-first` or `blocked` until the table is replaced with real entries or explicit `none`.

本项目此刻**没有**支付面，也没有自有认证/权限面（权限由 Frappe / ERPNext 宿主承担）。
下表前八条全部照抄 `AGENTS.md` 的红线表——**此处不新增、不放宽任何一条**；
「对活站点的破坏性写」那一行是 2026-08-21 新增的**加严**行（本仓第一次出现对活站点的破坏性写实现面，见其 Required Evidence）；
「门禁判定器本体」是 2026-08-22 新增的**加严**行（见表下说明）；
最后一行「对活站点的**非破坏性写**（建 / 改）」是 2026-08-22 新增的**加严**行（见表下说明）。

| Area | Rule | Required Evidence |
| --- | --- | --- |
| `tests/gates/**`（测试代码 = 裁判） | blocked | 人工批准：提交信息含 `Gates-Change-Approved-By:`（`AGENTS.md` 红线 1；`.github/workflows/gates.yml` 的 `gates-untouched` job 服务端复核） |
| `tools/gates/expected-red.txt`（预期红名单 = 账本） | **allowed（只能变短）** | 2026-08-21 由人裁定：账本不是裁判。测试转绿时 loop 应在同一提交里划掉对应行；名单**变长**仍需 `Gates-Change-Approved-By:`（服务端复核是 `expected-red-ratchet`（行数不得变大）**与** `expected-red-superset`（条目集合不得新增）**两个 job**，两者合取、任一红即拦下）。**2026-08-23 由 plan `2026-08-23-0337-2` 就地改准**：在它之前本列只写 `expected-red-ratchet` 一个 job，而那个 job 判的是「行数不得变大」，兑现不了同一行里「只能变短」这个词 ——「删一行 + 加一行」的等长交换对它完全隐形（CI 实证 run `32605108419`：`expected-red-ratchet` `success` 而 `expected-red-superset` `failure`）。**这是加严（补上一个此前缺失的判据），不是放宽**；本行的 Rule 值 `allowed（只能变短）` 一个字未改。出处：`docs/architecture/system-baseline.md` §14.8，落地 sha `f756f504fa0ed09390bf43e27ca35a4feaa2fb08`，`main` 权威运行 `32607062968`（14 job 全绿） |
| `.github/workflows/**` | blocked | 人工批准（`AGENTS.md` 红线 2：不得让门禁变松） |
| `docs/masterplan/DECISIONS.md` | blocked | 决策重开只有人能做；loop 仅可在某条决策表末**追加**「复核/实测结果」（红线 3） |
| `docs/masterplan/` 其余文件 | blocked | loop 侧只读；`STATE.md` 只允许**追加**证据行，不得改写已有行（红线 5） |
| 证据仓 `${XM_PATH}`（`docs/masterplan/evidence-repo.env`） | blocked | 已冻结在一个 sha 上，只读引用（红线 6） |
| 项目名 / 包名 / 命名空间 | ask first | 名字由 D-1 定；复核发现被占用须停机等人拍板（红线 4） |
| 运行时 Server Script 生成 | blocked | 等同 RCE，产品上不做（红线 7） |
| `missions/*.json` | blocked | 角色 B 禁区（`docs/masterplan/01-EXECUTION-MODEL.md` §1 禁止项 ③），由人编辑 |
| 对活站点的破坏性写（删除 Custom Field：`agenerp/site.py` · `SiteClient.delete_custom_field`、`agenerp/apply.py` · `execute_plan` 的删除路径；**直发物理 DDL**：`agenerp/oob.py` · `drop_columns`（`ALTER TABLE … DROP COLUMN`，经 `agenerp/apply.py` · `drop_orphan_columns` 挂在同一条调用链上）） | plan-first | 独立草案评审 + 独立关闭审计 + **实跑前后全量 `capture` 对照**（差集必须只含本次探针）+ **对「删错了能不能回来」说话的一条**：动 `agenerp/oob.py` · `drop_columns` 这条**不可逆**路径的 plan，必须在 plan 里逐字写明本次改动之后**站点侧回滚仍然只能手工做**（含手工前置动作的原文命令），或写明它交付了什么代码级前置/取证并给出实跑证据；**两者取其一，不许略过不谈**。2026-08-21 由 plan `2026-08-21-1922-3-execute-plan-site-delete.md` 补行——该 plan 落地前本表此行不存在，本行是**加严**（此前默认 `implement`）。**2026-08-22 由 plan `2026-08-22-1041-1-destructive-write-owner-doc-alignment.md` 就地加严第二次**：落点列表点名 `drop_columns`，Required Evidence 增上面那一条，旧的三条**逐字未动** |
| `tools/gates/check_expected_red.py`（**门禁判定器本体**） | plan-first | 独立草案评审 + 独立关闭审计 + **「默认判定环境输出逐字节不变」的前后两次实跑** + **判定器自身的变异验证**（改坏它必须让 `tests/unit` 红）。2026-08-22 由 plan `2026-08-22-0027-1-live-mode-gate-verdict.md` 补行，本行是**加严**（此前默认 `implement`）。**边界：本行只覆盖 `check_expected_red.py`，不覆盖 `tools/gates/expected-red.txt`** —— 账本允许在同一提交里划短，出处是 `AGENTS.md` 红线 1 的「边界」句（「预期红名单 `tools/gates/expected-red.txt` 不在此列——它是账本不是裁判，测试转绿时应当在同一提交里划掉对应行（只能变短）」）与本表第 2 行（`allowed（只能变短）`，名单**变长**才需 `Gates-Change-Approved-By:`，服务端控制是 `expected-red-ratchet`（行数不得变大）**与** `expected-red-superset`（条目集合不得新增）**两个 job**；**2026-08-23 由 plan `2026-08-23-0337-2` 就地改准，同上，是加严不是放宽**，出处 `docs/architecture/system-baseline.md` §14.8 / 权威运行 `32607062968`）。把账本圈进守卫会让每一次合法的划短在 CI 上失败 |
| 对活站点的**非破坏性写**（建 / 改）（`agenerp/site.py` · `SiteClient.create_doc` / `SiteClient.ensure_doc`；`agenerp/seedsite.py` 的主数据装载路径 —— 目前是这两个写方法的**唯一调用方**） | plan-first | 独立草案评审 + 独立关闭审计 + **一条对可逆性说话的**：动这条路径的 plan 必须逐字写明**本次改动之后站点侧回滚是否仍然只能手工做**（是则连手工命令原文一起写；否则写它交付了什么代码级 teardown 并给出实跑证据），**不许略过不谈**。2026-08-22 由 plan `2026-08-22-2107-1-seed-site-write-surface-and-masters.md` 补行——该 plan 落地前本表没有任何一行覆盖「建」，本行是**加严**（此前默认 `implement`） |

**2026-08-22 · 「对活站点的破坏性写」那一行为什么被加严第二次（Decision，照实记，不粉饰）**：

**先说清本次不是「发现了一处漏掉的落点」。** `agenerp/apply.py` · `execute_plan` 早已在该行的落点列表里，
而 `execute_plan`（`apply.py:251`）→ `drop_orphan_columns`（`:254`）→ `agenerp/oob.py` · `drop_columns`（`:304`）
是**一条调用链**——`drop_columns` **在「区域」意义上本来就被那一行罩住了**。
本次补的是两件更具体的事：① **落点的名字**（读这一行的将来会话此前看不出链条末端有一处
**直发 `ALTER TABLE … DROP COLUMN`、绕过 Frappe 一切执行面、且不可逆**的写动作——
该行原先点名的两处都是**经 Frappe** 的删除，删 Custom Field 甚至不删物理列）；
② **一条对不可逆性说话的 Required Evidence**（原先三条逐字是「独立草案评审 + 独立关闭审计 +
实跑前后全量 `capture` 对照（差集必须只含本次探针）」，
那三条**只回答「删对了没有」，一条都不回答「删错了能不能回来」**）。
**把它写成「补一处漏洞」是不诚实的**，本段不这么写。

**候选与否决理由**（三选一，取 (a)）：

| 候选 | 说明 | 结论 |
|---|---|---|
| **(a)** 在现有行的落点列表里点名 `agenerp/oob.py` · `drop_columns`，并补一条对不可逆性说话的 Required Evidence；Rule 格仍是 `plan-first` | 只把要求写具体，不改变谁能动这条路径 | **取此** |
| **(b)** 另起一行「不可逆的物理 DDL」，定级 `ask first` | 任何后继 plan 动这条链之前都必须先等人 | 否决 |
| **(c)** 同上但定级 `blocked` | AI 不得改动这条链的产品行为 | 否决 |

**否决 (b)/(c) 的理由（必须落在本文件里，不能只落在 plan 里）**：`apply_pack` 的物理列清除面
**不是一段闲置代码**——它是工作项 5/6 已交付的活路径，门禁
`tests/gates/test_customization_roundtrip_delete.py::test_no_orphan_column_left_behind` **正在判它**。
把它锁进 `ask first` / `blocked`，等于让**一条绿着的门禁的实现面**进入不可维护状态：
门禁一旦转红，修它的每一步都要先停机等人。(a) 保持 `plan-first` 不变、只把证据要求写具体，
是**能加严又不制造死锁**的那一档。**这是取舍，不是「(b)/(c) 更严所以更好」**。

**残余风险（沿用本表下方「门禁判定器本体」那段的同一措辞，不发明新说法）**：
**文档级约束对拿着 shell 的执行器没有强制力**，真正的强制力在 CI 侧守卫。
本行加严之后，`drop_columns` 这条路径在**代码侧**仍然零备份、零取证——
`grep -rn "backup" agenerp/*.py` → **零命中**（实测 2026-08-22）。
那条真实风险**不由本行处置**，它登记在
[`docs/backlog/irreversible-ddl-has-no-code-level-precondition.md`](../backlog/irreversible-ddl-has-no-code-level-precondition.md)，
带触发条件，**由人裁定**。**本行不假装已经把它解决了。**

**为什么「门禁判定器本体」这一行此前不存在，以及它此刻还缺什么（照实记，不粉饰）**：
2026-08-22 逐条实测过三层既有保护，**没有一层覆盖判定器**——
`gates-untouched` job 只 diff `tests/gates/**`；`tools/gates/gate-verify.mjs:22` 的
`PROTECTED = ["tests/gates/"]`；`expected-red-ratchet` job 只数 `tools/gates/expected-red.txt` 的行数。
而 `gates.yml` 的 `gates-l1` job 跑的**就是判定器本身**——判定器被改废之后会在 CI 上**自证为绿**。
`AGENTS.md` 裁判规则 1 把「测试过没过」的裁定权交给 `GATE_VERIFY` 的退出码，
产出那个退出码的脚本却三层皆无保护。本行先在**文档层**加严。
**残余风险**：文档级约束对拿着 shell 的执行器没有强制力，真正的强制力在 CI 侧守卫，
而它由 plan `2026-08-22-0027-2-ci-l2-full-live-gate-coverage.md` 承接（新增 `verdict-tool-untouched` job），
**在本行落地时还没上线**。这段空窗期写在 `docs/architecture/system-baseline.md` §14.4，不藏着。
**不夸大本行**：它列的 Required Evidence 恰好就是补行那个 plan 自己已经在做的事，
因此它对**那一次**改动没有增量约束，只对**将来的会话**有约束。

**2026-08-22 · 为什么要新增「对活站点的非破坏性写（建 / 改）」这一行（Decision，照实记，不粉饰）**：

**这不是把旧行改宽，是补一个此前字面上不存在的区域。** 上面那一行的标题逐字是「对活站点的**破坏性写**」，
落点也全是删除与 DDL。**「建」不在它的字面内**——2026-08-22 之前本仓对活站点根本没有「建」的实现面，
所以此前默认落在 `implement`（无需 plan、无需证据）。plan `2026-08-22-2107-1` 第一次交付了
`SiteClient.create_doc` / `SiteClient.ensure_doc` 与 `agenerp/seedsite.py` 的主数据装载路径，
靠读者「从破坏性写那一行推断建也受约束」等于没有约束，因此补一行。

**候选与否决理由**（三选一，取 (c)）：

| 候选 | 说明 | 结论 |
|---|---|---|
| **(a)** 不补行，靠现有「破坏性写」那一行覆盖 | 标题逐字是「破坏性」，靠推断 | 否决 |
| **(b)** 补行并定级 `blocked` | AI 不得对活站点建任何文档 | 否决：会让补行的那个 plan 自身无法执行，且会阻断 P1/P2 全部站点侧工作 |
| **(c)** 补行并定级 `plan-first`，Required Evidence 三条 | 加严一档，且不制造死锁 | **取此** |

**加严的两件具体事**：① **区域本身**——「建 / 改」从 `implement` 提到 `plan-first`，此后动它必须先有 plan；
② **一条对可逆性说话的证据**——因为「建」这条路径**在代码侧同样零 teardown**：
`agenerp/seedsite.py` 装进站点的对象**删不掉**，复位手段只有 `docker compose down -v` 冷起
（丢整站数据）或事前 `bench backup` + **人工** `restore`。这条代价写在
`docs/architecture/module-boundaries.md` §12.9，**不由本行假装解决**。

**残余风险（沿用本表上面两段的同一措辞，不发明新说法）**：
**文档级约束对拿着 shell 的执行器没有强制力**，真正的强制力在 CI 侧守卫。
本行落地时，「建」这条路径在 CI 侧**没有**对应守卫；代码侧唯一有牙齿的那道是
`tests/unit/test_site_client.py` 的 `WRITE_METHOD_ALLOWLIST`（登记式，不是禁止式），
它只保证「新增写方法必须留痕」，**不保证写的是什么**。**本行不假装已经把这件事解决了。**

支付、认证/权限：`none`（本项目当前无自有实现面）。将来出现时，先在本表补行再动手。
**数据删除**：不再是 `none` —— 2026-08-21 起本仓有了自有实现面（上表最后一行）。它删的是**结构定制**（Custom Field），不是业务数据；业务数据删除面仍为 `none`。
**数据创建**：不再是 `none` —— 2026-08-22 起本仓有了自有实现面（上表最后一行）。它建的是**业务主数据**（公司 / 科目 / 仓库 / 物料 / BOM 等），**唯一调用方是 `agenerp/seedsite.py` 的种子装载路径**；业务**单据**创建面仍为 `none`。

Protected-area rule meanings:

- `ask first` - human approval is required before planning or implementation.
- `plan-first` - AI may draft the plan, but implementation requires plan audit plus the required evidence in the table. If reviewer availability is `none`, implementation stays blocked.
- `research-only` or `blocked` - AI may not change product behavior.

## Backlog Selection Rule

If the user asks AI to continue work without naming a task, choose the highest-priority item in `docs/backlog/README.md` whose autonomy is `implement` and whose blockers are `none`.

Before implementing the selected item, re-check planning triggers. `Plan: none` does not waive the plan guide.

Direct user requests for local low-risk edits do not require a backlog row, but they still must satisfy the no-plan path and verification rules.

If no safe `implement` item exists, summarize the top blocked, `plan-first`, or `ask-first` item and ask for a decision.
