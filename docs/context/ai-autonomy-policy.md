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
真正的保护区是下表这八条，全部照抄 `AGENTS.md` 的红线表——**此处不新增、不放宽任何一条**。

| Area | Rule | Required Evidence |
| --- | --- | --- |
| `tests/gates/**`（含 `EXPECTED_RED.txt`） | blocked | 人工批准：提交信息含 `Gates-Change-Approved-By:`（`AGENTS.md` 红线 1；`.github/workflows/gates.yml` 的 `gates-untouched` job 服务端复核） |
| `.github/workflows/**` | blocked | 人工批准（`AGENTS.md` 红线 2：不得让门禁变松） |
| `docs/masterplan/DECISIONS.md` | blocked | 决策重开只有人能做；loop 仅可在某条决策表末**追加**「复核/实测结果」（红线 3） |
| `docs/masterplan/` 其余文件 | blocked | loop 侧只读；`STATE.md` 只允许**追加**证据行，不得改写已有行（红线 5） |
| 证据仓 `${XM_PATH}`（`docs/masterplan/evidence-repo.env`） | blocked | 已冻结在一个 sha 上，只读引用（红线 6） |
| 项目名 / 包名 / 命名空间 | ask first | 名字由 D-1 定；复核发现被占用须停机等人拍板（红线 4） |
| 运行时 Server Script 生成 | blocked | 等同 RCE，产品上不做（红线 7） |
| `missions/*.json` | blocked | 角色 B 禁区（`docs/masterplan/01-EXECUTION-MODEL.md` §1 禁止项 ③），由人编辑 |

支付、数据删除、认证/权限：`none`（本项目当前无自有实现面）。将来出现时，先在本表补行再动手。

Protected-area rule meanings:

- `ask first` - human approval is required before planning or implementation.
- `plan-first` - AI may draft the plan, but implementation requires plan audit plus the required evidence in the table. If reviewer availability is `none`, implementation stays blocked.
- `research-only` or `blocked` - AI may not change product behavior.

## Backlog Selection Rule

If the user asks AI to continue work without naming a task, choose the highest-priority item in `docs/backlog/README.md` whose autonomy is `implement` and whose blockers are `none`.

Before implementing the selected item, re-check planning triggers. `Plan: none` does not waive the plan guide.

Direct user requests for local low-risk edits do not require a backlog row, but they still must satisfy the no-plan path and verification rules.

If no safe `implement` item exists, summarize the top blocked, `plan-first`, or `ask-first` item and ask for a decision.
