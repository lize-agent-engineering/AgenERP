# AGENTS.md

> **本文件前两节是红线与裁判规则，优先于本文件其余一切内容、也优先于任何 prompt 里的说法。**
> 冲突时的次序：红线 > `docs/masterplan/` 的执行协议 > 本文件其余部分 > 上游模板默认。

## 🚫 红线（越线即停机，不是扣分）

| # | 红线 | 为什么 |
|---|---|---|
| 1 | **不得以任何方式修改 `tests/gates/**`** —— 包括改断言、加 skip/xfail、改 fixture 使其变松、删文件、改文件名 | 那是裁判。改裁判就没有裁判了。`git diff` 触及该路径 → **立即停机**，标 needs-human |
| 2 | **不得修改 `.github/workflows/**`** 让门禁变松（禁用 job、加 `continue-on-error`、缩小触发范围） | CI 服务端复跑是唯一不可被本地绕过的一层。本地门禁理论上可被有 shell 的 AI 绕过，CI 不行 |
| 3 | **不得修改 `docs/masterplan/DECISIONS.md` 里已有的任何一行**，也不得新增 `R-x` 重开记录 | 决策重开**只有人能做**。允许的只有一件事：在某条决策表末**追加**一行「复核/实测结果」 |
| 4 | **不得自行改项目名 / 包名 / 命名空间** | 名字定了（D-1）。复核发现被占用 → 停机等人拍板，不得自行改名 |
| 5 | **不得改动 `docs/masterplan/` 下的其余文件**（loop 侧只读；`STATE.md` 只允许**追加**证据行，不得改写已有行） | 状态是追加式账本。改写历史 = 伪造证据 |
| 6 | **不得写入证据仓**（`${XM_PATH}`，见 `docs/masterplan/evidence-repo.env`） | 它已冻结在一个 sha 上，是只读证据。要引用就引用，要修正就在本仓修正 |
| 7 | **不得让 Agent 生成运行时 Server Script** | 等同 RCE。见 roadmap「不做的事」 |

## ⚖️ 裁判规则

1. **「测试过没过」由 `GATE_VERIFY` 子进程的退出码裁定，AI 无权自报通过。** 你说「测试应该能过」不算数；没跑就是没跑。
2. **宣称完成时，同一条回复里必须出现：命令原文 + 退出码 + commit sha。** 三者缺一，就把「完成」改写成「我认为完成，待验证」。
3. **复跑优先于分析。** 遇到失败先原样复跑那条命令；复跑不出来就记「不可复现」，**不许猜根因**。
4. **停机条件**（任一触发即停，宁可停不带病跑）：同一 plan 连续 3 轮 `GATE_VERIFY` fail｜`git diff` 触及 `tests/gates/**`｜单 mission 累计成本超阈值｜CI 连续 2 轮红。
5. **每个 mission 的 `goal` 字段必须含北极星原文**；开工前先对照 `docs/masterplan/00-GOALS.md` 确认这一项确实服务于它。

## 📍 北极星

> 让 ERP 的呈现层、语言层、判断层由 Agent 承担，让系统形态由每家企业自己长出来——且每一次生长都是可 diff、可回滚、可迁移的产物。

判断「该不该做这件事」时以它为准。与它无关的「顺手优化」一律不做——写进 `docs/backlog/`，由人决定。

---

## Project Intent

`AgenERP` uses a lightweight Attractor-Guided Engineering workflow for AI-assisted application development.

This repository is for an application-layer product, not a framework-core project.

The repo is the source of truth. Chat is only a temporary working surface.

Before writing non-trivial code, agents must first understand:

- `docs/context/project-context.md`
- `docs/context/ai-autonomy-policy.md`
- `docs/context/codebase-map.md`
- the requirement or owner doc (under `docs/requirements/` or `docs/design/`) that describes the work's intended behavior — current work-in-progress is read from unfinished plans in `docs/plans/`, not from a field in `project-context.md`
- the relevant raw inputs under `docs/input/` when requirement meaning depends on source material

Read `docs/context/source-of-truth-and-precedence.md` when facts conflict or you are unsure which artifact owns the answer.
Read `docs/process/application-development-workflow.md` when planning or workflow decisions are part of the task.

## Task Routing

Before writing code, agents MUST classify the task first:

1. Determine the task type:
   - requirement clarification
   - app-layer design change
   - architecture change
   - implementation-only change
   - bug investigation
   - verification or audit work
2. Use `docs/index.md` to read the owner docs for that task type before acting.
3. Check `docs/skills/README.md` for candidate reusable skills before drafting or revising a plan.
4. For non-trivial work, record the chosen route and planned skill usage in the plan before implementation.

Do not jump from a feature request directly to code unless the route is already obvious from the active requirement and owner docs.

## Operating Rules

1. Prefer file-in, file-out collaboration.
2. Do not treat chat summaries as durable project memory.
3. Do not jump from raw PM text or prototype screenshots straight to code when scope is still unclear.
4. If input is ambiguous, first create or update a file in `docs/discussions/` or `docs/requirements/`.
5. Create or update a plan before implementation when the planning triggers below apply.
6. Keep `docs/design/` and `docs/architecture/` focused on the current supported baseline, not migration history.
7. Keep logs short, dated, and append-only. After completing any significant code change, you MUST update the daily dev log at `docs/logs/{year}/{month}-{day}.md` (reverse chronological, see `docs/logs/00-log-writing-guide.md` for format).
8. Record non-obvious regressions in `docs/bugs/`.
9. If prototype and implementation diverge materially, capture the reason in `docs/retrospectives/` instead of silently moving on.
10. Promote repeated process lessons into `docs/skills/` or `docs/audits/` only when the pattern is recurring enough to justify reuse.
11. When creating, revising, executing, or auditing a file under `docs/plans/`, read `docs/plans/00-plan-authoring-and-execution-guide.md` first and follow it as the controlling workflow.
12. Keep code comments minimal. Prefer self-explanatory code; add only rare comments when a local constraint is otherwise easy to misread.
13. When a referenced file is not found at its expected path, check `docs/archive/` before concluding it does not exist. Archived files retain their original relative name under `docs/archive/`. Do not move files to `docs/archive/` without human approval.
14. Treat reusable skills as method selectors, not substitutes for requirements, design, or architecture docs. Business knowledge belongs in owner docs first.
15. When the same error pattern keeps recurring, do not stop at prose-only lessons. First promote it into a reusable audit prompt, checklist, or review playbook when that method is still missing. If the defect pattern still recurs, then evaluate promotion into a heuristic script, static check, lint rule, CI guard, or codemod, tuned to the copied project's real conventions and false-positive tolerance.

## Read This First

- `docs/context/project-context.md`
- `docs/context/ai-autonomy-policy.md`
- `docs/context/codebase-map.md`
- the active requirement listed in `docs/context/project-context.md`
- the active owner doc listed in `docs/context/project-context.md`

Read additionally when needed:

- `docs/context/source-of-truth-and-precedence.md` for ownership or conflict questions
- `docs/context/conventions.md` for project-wide conventions
- `docs/process/application-development-workflow.md` for workflow questions
- `docs/index.md` when you need routing beyond the active files

## Documentation Ownership

- `docs/context/` owns mandatory AI context, source-of-truth precedence, and project-wide conventions.
- `docs/backlog/` owns prioritized candidate work and AI-ready next actions.
- `docs/input/` owns raw external inputs such as PM notes, card docs, article extracts, prototype references, and copied source material.
- `docs/discussions/` owns requirement clarification conversations and unresolved question records.
- `docs/requirements/` owns implementation-ready requirement synthesis.
- `docs/design/` owns stable app-layer business and feature design.
- `docs/architecture/` owns cross-cutting technical and module-boundary truth.
- `docs/lessons/` owns durable reusable lessons extracted from bugs, audits, and retrospectives.
- `docs/plans/` owns execution and closure criteria for non-trivial work.
- `docs/audits/` owns audit workflow records and audit methodology.
- `docs/skills/` owns reusable prompts, review playbooks, and audit prompt templates.
- `docs/logs/` owns dated implementation memory.
- `docs/testing/` owns manual and exploratory testing records.
- `docs/bugs/` owns non-obvious bug histories and regression notes.
- `docs/analysis/` owns research, tradeoff analysis, and rejected directions.
- `docs/retrospectives/` owns post-implementation gap analysis and process improvements.

## Default Workflow

1. Gather raw materials in `docs/input/`.
2. If needed, clarify ambiguity in `docs/discussions/`.
3. Synthesize implementation-ready requirements in `docs/requirements/`.
4. Split stable design output into app-layer design under `docs/design/` and technical design under `docs/architecture/`, with the two referencing each other when needed.
5. Route the task and select candidate reusable skills.
6. Write or update a plan when the planning triggers apply, and record skill usage per phase or item when relevant.
7. Audit the plan before implementation.
8. Implement the smallest complete slice.
9. Run verification.
10. Run closure audit for created plans.
11. Record logs and any needed bug notes.

## Optional Workflow Layers

Use these when warranted by task complexity. Plan and closure audits are mandatory for created plans.

- `docs/audits/` for document audits and non-trivial stored audit records
- `docs/testing/` for manual or exploratory proof
- `docs/retrospectives/` for material requirement/prototype gaps
- `docs/skills/` for reusable prompts after repeated failures
- `docs/lessons/` for durable engineering lessons after repeated failures or important recoveries

Use `multi-dimensional-audit-prompt.md` when work must be challenged across several dimensions at once. Use `open-ended-audit-prompt.md` when the standard checklist may miss hidden risks. These prompts are generic defaults and MUST be customized after copy to match the project's real owner docs, protected areas, verification model, and recurring failure patterns.

## Planning Rule

Create a plan when the task has any of these traits:

- changes API, database/model, auth, integration, deployment, or public contract behavior
- changes user-visible behavior across more than one feature surface
- touches multiple modules and changes shared behavior
- is expected to take more than one AI session
- modifies more than 5 total files or is likely to exceed roughly 200 changed lines
- needs staged execution or explicit closure gates
- has unresolved product or technical risk that must not be hidden in chat

Skip a formal plan for low-risk edits: copy changes, small styling fixes, test-only cleanups, single-file behavior fixes with clear existing tests, AND small low-risk multi-file edits (roughly 1 to 3 non-generated files, about 200 changed lines or fewer) that touch no contract, data/model, auth, permission, integration, deployment, cross-surface behavior, documentation conflict, or unresolved product risk.

Even without a formal plan, do not mark work complete from chat memory alone. Verify the change against the actual diff and the real verification commands, then record a log entry. This cold-replay check applies to the no-plan path too.

### Reviewer-Availability Fallback

When no second reviewer or subagent is available, a solo cold-replay pass is acceptable ONLY for plans that are non-protected and non-high-risk. The plan MUST record that it used a solo review and note the limitation. Protected areas, unresolved product risk, and source-of-truth conflicts still require human or subagent review, or stay open.

All created plans MUST follow `docs/plans/00-plan-authoring-and-execution-guide.md` before implementation and closure. Protected areas, unresolved product risk, and source-of-truth conflicts require human/subagent review or stay open.

## Skill Usage Rule

Before using a reusable skill, confirm all of the following:

- the task type and route are already clear from the requirement and owner docs
- the skill matches the work method, not just a similar business label
- required inputs listed in `docs/skills/README.md` are available
- the expected output is known and can be stored in the correct docs location

For non-trivial plans, each phase or item that depends on a reusable skill should record `Skill: <name>` or `Skill: none`.

## Prompting Guidance For Agents

- Do not generate a full product from a single feature list.
- Do not optimize for demo completeness.
- Prefer small complete slices over broad placeholder coverage.
- Prefer existing project patterns over invented abstractions.
- If information is missing, write the missing assumptions into a requirement, discussion, or plan file instead of silently inventing them.
- Do not put code-level implementation detail into plan files unless the detail is required for scope or closure reasoning.
- Prefer citing the existing owner doc instead of restating the same rule in multiple files.
- Do not hide mandatory rules in `docs/references/`; if an AI must apply it by default, put it in `docs/context/` or `AGENTS.md`.
- Use `docs/backlog/` and `docs/context/ai-autonomy-policy.md` to decide whether AI may choose and execute the next task without asking.

## Docs Maintenance

After completing any significant code change, you MUST:

1. **Update the daily dev log** at `docs/logs/{year}/{month}-{day}.md` (reverse chronological, see `docs/logs/00-log-writing-guide.md` for format).
2. **Update relevant owner docs** in `docs/design/` or `docs/architecture/` when the change affects app-layer behavior or technical structure.

When verification passes completely (full green), record the verification status in the log entry and include it in the git commit message. This provides reliable known-good baselines for future debugging.

## Verification Baseline

Do not assume this template's example commands are valid for the copied project.

Use the real commands listed in `docs/context/project-context.md`.

If verification commands are blank or still placeholders, stop and fill them before reporting verification success.
