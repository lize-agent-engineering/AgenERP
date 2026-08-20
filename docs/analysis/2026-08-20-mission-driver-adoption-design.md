> **迁入说明**（2026-08-20，WBS `W0.8`）：本文原在 XM 证据仓 `docs/superpowers/specs/`，随 fork 引擎一并迁入本仓。
> 它是 `tools/mission-driver/` 三个补丁（P1/P2/P3）与门禁设计的**决策依据**，主计划的 `REF:GATE-INDEP` 等 14 条引用指向它。
> 原件冻结于证据仓 `1c622c8`。**本文之后如与实现不符，以实现 + 本文的追加修订为准；不要回头改证据仓。**

# 采用 Mission Driver 全自动 Loop 建设 AgenERP — 设计

| | |
|---|---|
| 状态 | 已批准（方案 C · 三条裁决经确认） |
| 日期 | 2026-08-20 |
| 配套 | [ARCHITECTURE.md](../../next/ARCHITECTURE.md) · [implementation-roadmap.md](../backlog/implementation-roadmap.md) · [建设前验证设计](./2026-08-19-agenerp-pre-build-validation-design.md) |
| 上游 | [entropy-cloud/attractor-guided-engineering-template](https://github.com/entropy-cloud/attractor-guided-engineering-template)（MIT） |
| 目的 | 用 AGE / Mission Driver 的自动化循环建设 AgenERP P0–P5，并把该循环缺失的确定性门禁补上 |

---

## 1. 背景与判断

AGE（Attractor Guided Engineering）提供了一套可用的多层 Loop 自动化开发设施。2026-08-20 对其源码做了实读，结论如下。

### 1.1 它的实际形态

`tools/mission-driver.sh` 只是 shim，真身是 `tools/mission-driver/`：

- `src/engine.js` 约 100KB + 25 个模块；Vue 3 监控面板（:9300）
- 零 npm 依赖（`commander` 已 vendored），`web/dist/` 已提交 → 解压即跑
- 三个 Flow DSL（JSON 状态机）：

| 文件 | 循环 |
|---|---|
| `flows/mission-driver.json` | `CHECK → REVIEW_PLANS → EXEC_PLANS → DRAFT_PLANS → DEEP_AUDIT` |
| `flows/plan-execution.json` | `EXECUTE → CLOSURE_SCRIPT_CHECK →(fail)→ CLOSURE_AUDIT → BUILD_VERIFY` |
| `flows/deep-audit-loop.json` | roadmap 无待办项时的审计循环 |

工程细节可用：`maxCycleVisits: 8`、`pingPongWindow: 6`（检测 A→B→A→B 震荡）、`markerAliases`（把模型输出的 `ok`/`success`/`done` 归一为 `pass`）、`reap-orphans.mjs` + `active-run-registry.mjs`（崩溃后回收孤儿进程，7×24 刚需）。

### 1.2 它的承重缺陷（本设计存在的理由）

**整个循环里只有一个 `type: "script"` 步骤**，即 `CLOSURE_SCRIPT_CHECK`。读 `src/plan-check.mjs` 实现，它做的是**纯 markdown 结构检查**：

- 还剩几个 `- [ ]` 未打勾
- 有无 `## Closure` 段
- 该段下有无至少一条非占位符 bullet（排除 `*(pending)*` / `TODO`）

它不验证证据为真，**它数 bullet**。

而 `BUILD_VERIFY` 是 `type: "agent"`：prompt 要求 AI 自己跑 typecheck/build/lint/test、自己诊断、自己修复，然后自行输出 `<AI_STEP_RESULT>pass</AI_STEP_RESULT>`。engine 只解析该 marker。

> **全流程没有任何一步独立复跑测试并比对退出码。「测试过了没有」这一判断，自始至终由被考核者自我汇报。**

这与本项目 Spike 02 实测到的失败模式同构：不加证据门禁时，模型只调 1 次 `doc.get` 就下结论。一个没有门禁的开发循环，会犯它要修的那个错。

### 1.3 我们的不对称优势

[implementation-roadmap.md](../backlog/implementation-roadmap.md) 的验收标准**已经是可机器判定的**，这在同类文档中罕见：

> 「从包中删除 → apply → **字段真的消失**」
> 「**空环境变量下** `docker compose up` 成功」
> 「每个角色的默认首页**渲染元素 > 0，空壳工作台数为 0**」
> 「移除该规则后**能复现漏报**」

因此可以把上游的「AI 自审 + AI 自列证据」这一概率防御，换成确定性判定。本设计即围绕这一点展开。

---

## 2. 三条裁决

### 2.1 fork + 同时提 PR

fork 并钉死版本，立即可用；同时向上游提「让 `SCRIPT_REGISTRY` 可从 mission.json 扩展」的 PR。该改动通用，上游有收的动机。PR 是否被接受**不阻塞**本项目。

### 2.2 执行器起步用 opencode，暂不加 claude driver

`--driver` 当前只认 `opencode`（默认）| `pi` | `cline`，默认模型 `zhipuai-coding-plan/glm-5.2`。engine 的全部错误处理路径（stderr 缓冲、stdin 关闭时序、Windows 子进程处理）都是围绕 opencode 打磨的，pi/cline 是后加分支。我们已需 fork 改 `flow-loader.js`，同时再动 driver 层等于叠加两处偏离。

> ⚠️ **未验证假设（开跑前必须核实）**：opencode 走 Anthropic 是按 token 计费的 API，与 Claude Code 订阅并非同一计费口径。7×24 运行下该差异显著。
> **若订阅不可复用，本条裁决翻案**，改为新增 `--driver claude`（`config.js` 中 pi/cline 的分支模式清晰，差异仅在 prompt 走 stdin 还是位置参数）。

### 2.3 裁掉 OpenSpec，统一到 mission-driver

[implementation-roadmap.md](../backlog/implementation-roadmap.md) 原则 4 原为「每阶段一个 OpenSpec change proposal：proposal → apply → archive」。它与 mission-driver 的 `roadmap → plan → closure` **语义高度重叠但状态机不同**：proposal 与 plan 是同一事物的两个名字，archive 与 closure 是同一动作的两个名字。同时运行两套，模型会在「该建 proposal 还是建 plan」上反复漂移——上游作者正是为规避同类术语碰撞才刻意为 roadmap 另起一套命名。

**成本不对称是决定性的**：OpenSpec 在本仓库尚未落地（无 `openspec/` 目录），它是一条计划而非既成事实，放弃成本约等于零；而 mission-driver 自带引擎、状态机、监控与门禁脚本。

「每阶段一个 proposal」的粒度感由 mission 承载，不丢失：

> **P0–P5 各为一个 mission** → roadmap 的一个 work item = **1–2 个 plan**

（同时满足上游经验：一个 item 不应对应多个 plan，否则关闭时回写打勾会出错。）

**须改动**：[implementation-roadmap.md](../backlog/implementation-roadmap.md) 原则 4 措辞；[implementation-roadmap.md](../backlog/implementation-roadmap.md) P0 交付表中「OpenSpec 初始化」一项替换为「AGE 骨架安装 + mission 配置」。

---

## 3. 阻塞项：项目命名未决

[architecture/open-questions.md](../architecture/open-questions.md) §15 #1：

> **项目命名**｜暂用 AgenERP。风险：口头传达与搜索都会被纠正成 AgentERP，且 `agenerp.com` 已被占用，无法用域名强化拼写。**建议改名，且必须在建仓库前定**——建仓库后改名成本永久化｜决策时点：**建仓库前**

本设计第一步即建新仓库。**该名称未定，§6 Day 0 清单无法起步。** 这是需要人决策的事项，不在本设计的自动化范围内。详细取舍见 `spike/D01-decisions/FINDINGS.md`。

---

## 4. 设计

### 4.1 让门禁从「自报」变为「独立判定」

改动三处：

| # | 文件 | 改法 |
|---|---|---|
| **P1** | `src/flow-loader.js`（上游） | `SCRIPT_REGISTRY` 由硬编码常量改为可扩展：从 mission.json 新增的 `scripts` 字段加载项目侧 `.mjs`。**此即提给上游的 PR 内容** |
| **P2** | `tools/gates/gate-verify.mjs`（项目侧新增） | 由 **engine 自身 spawn 子进程**执行 `mission.commands.{test,lint,typecheck,build}`，**以退出码判定**。AI 不参与该判定 |
| **P3** | `flows/plan-execution.json` | 在 `BUILD_VERIFY` 之后插入 `GATE_VERIFY`（`type: "script"`）：`pass → done: completed`；`fail → retry EXECUTE`，并将真实失败输出 append 进下一轮 prompt |

现状 `SCRIPT_REGISTRY` 为：

```js
const SCRIPT_REGISTRY = {
  "closure-script-check": (delegates, flowVars) => closureScriptCheck(delegates, flowVars),
};
```

`resolveStepScripts` 遇未知 `scriptId` 直接 throw，故 P1 是 P2/P3 的前置。

**保留 `BUILD_VERIFY` 这一 agent 步骤**——AI 的自诊断与自修复有真实价值，不应砍掉。本设计只把**最终判定权**从它手中取走：它若谎报 `pass`，下一步立即被独立复跑打脸。

### 4.2 门禁测试的写保护（三层，只有第三层是真的）

| 层 | 手段 | 强度 |
|---|---|---|
| 1 | `gate-verify.mjs` 中以 `git diff --name-only` 检出触及 `tests/gates/**` → 直接 fail | 挡误改 |
| 2 | pre-commit hook | 挡顺手改 |
| 3 | **GitHub Actions 服务端复跑** | **唯一真正挡得住的一层** |

**如实记录**：AI 拥有 shell，本地任何一层理论上都可被绕过。CI 是唯一本地 AI 篡改不了的裁判。CI 本就是 P0 交付项，顺带完成。

配套红线写入 `AGENTS.md`：**loop 不得修改 `tests/gates/`**。

### 4.3 文档三分层（心因子）

以 `install-age.sh` 安装骨架，再将现有文档迁入：

```
docs/
  architecture/   规范性 · 技术相关 · 只记当前   ← ARCHITECTURE §3,7,8,10,11,12,14
  design/         规范性 · 业务需求 · 技术中立   ← ARCHITECTURE §1,5,6,9
  backlog/        implementation-roadmap.md      ← ROADMAP.md
  context/        project-context / ai-autonomy-policy / codebase-map
  testing/        known-good-baselines.md
  archive/        时效性 · 会过期                ← PRE_BUILD_VALIDATION.md, spike/FINDINGS.md（文件名前缀日期）
  logs/2026/      轨迹留存
  plans/p0-foundation/ ...
```

规范性文档（`architecture/`、`design/`）**只记录当前状态，不记录历史演化**；带时间的文档一律进 `archive/`，且规范性文档不反向引用时效性文档。

⚠️ **`ARCHITECTURE.md`（69KB / 1159 行）必须拆分 —— **已于 `W0.3` 完成****。上游规矩为 >50K 拆分、30K 为宜，当前超标两倍以上，且 `tools/check-oversized-code-files.mjs` 会直接报警。拆分本身有收益：AI 每轮无需通读 1159 行。

### 4.4 验收先行：先写红测试

把 [implementation-roadmap.md](../backlog/implementation-roadmap.md) 中已可机器判定的验收，翻译为 `tests/gates/` 下**先红着**的测试。plan 的 closure gate 即「该测试转绿」，而非 AI 打勾。

P0 一批（Day 0 手写）：

| 测试 | 判据来源 |
|---|---|
| `test_snapshot_diff_structured` | 同站点两次快照 → 输出结构化 diff |
| `test_normalizer_idempotent` | 什么都不改重新导出 → diff 为空（Spike 06 打脸点） |
| `test_customization_roundtrip_delete` | 增字段 → 导出 → `git diff` 干净 → 从包删除 → apply → **字段真的消失** |
| `test_zero_dep_boot` | 空环境变量下 `docker compose config && up -d` + healthcheck + 首页显示「AI 能力未配置」 |

后续阶段同法翻译，各自阶段开跑前写：

| 阶段 | 测试 | 判据来源 |
|---|---|---|
| P1 | `test_evidence_gate_blocks_single_hop` | 复现 Spike 02：无门禁时 1 次 `doc.get` 即下结论，门禁须拦截 |
| P1 | `test_insight_rule_ablation` | 移除规则后能复现漏报 |
| P1 | `test_explain_cost_ceiling` | 单次解释成本 ≤ 基线（Spike 02 无缓存 $0.252/题） |
| P2 | `test_no_empty_workspace` | 每角色首页渲染元素 > 0、空壳工作台数 = 0（Spike 09 基线：老板 `Home` 渲染 0 个链接，20 个工作台中 8 个空壳） |
| P3 | `test_no_commit_in_submit_path` | 提交路径不调 `db.commit`、不 `enqueue` |
| P3 | `test_rollback_clean` | 后置断言失败 → 单据 / SLE / GL / 单号计数器全部回退 |
| P4 | `test_five_layer_permission` | 直接调 `get_desktop_page` 断言渲染元素 > 0 |

### 4.5 门禁分层

| 层 | 内容 | 执行位置 |
|---|---|---|
| **L1 快**（秒级） | `pytest -m "not live"` + ruff + mypy + `docker compose config` | 每个 plan 的 `GATE_VERIFY` |
| **L2 慢**（分钟级） | 起活站点 + `pytest -m live` + verify 脚本 | 阶段关口（在 roadmap 中显式插入审计步） |
| **L3 CI** | 服务端复跑 L1 + L2 | 每次 push |

沿用现有仓库已形成的分法：`tests/` 多为静态契约测试（读 JSON/文件断言，秒级，不需活站点），`scripts/verify-demo.sh` 需 docker + bench + 活站点（分钟级）。

### 4.6 mission 配置

`missions/p0-foundation.json`：

```json
{
  "name": "p0-foundation",
  "flowName": "mission-driver",
  "roadmapPath": "docs/backlog/implementation-roadmap.md",
  "plansDir": "docs/plans/p0-foundation",
  "planGuide": "docs/plans/00-plan-authoring-and-execution-guide.md",
  "auditsDir": "docs/audits",
  "contextDir": "docs/context",
  "commands": {
    "test": "pytest -m 'not live' -q",
    "lint": "ruff check .",
    "typecheck": "mypy <package>",
    "build": "docker compose config -q"
  },
  "scripts": { "gate-verify": "tools/gates/gate-verify.mjs" },
  "commitFormat": "<type>(<scope>): <description>"
}
```

`<package>` 待 §3 命名决策后填入。P1–P5 各自一份同构配置。

### 4.7 prompt 覆盖

`loadPrompt()` 先查项目侧 prompts 目录，同名即覆盖上游（上游宣称的「达尔塔定制」确已实现）。必须重写：

- `prompts/build-verify.md` —— 上游版本是 **Maven + Jira 特化**的：整段「Incremental build guidance (Maven / multi-module projects)」讲 `-pl <module> -am` 与不加 `clean`；commit 策略判断「recent commits contain Jira keys」。须改写为 Python / Frappe 语境。

---

## 5. 停机条件

engine 自带 `maxTotalSteps: 500` / `maxCycleVisits: 8` / `pingPongWindow: 6`，但缺以下几条。实现在 `gate-verify.mjs` 中：

- 同一 plan 连续 3 轮 `GATE_VERIFY` fail → 停机，标记 `needs-human`
- `git diff` 触及 `tests/gates/**` → **立即停机**
- 单 mission 累计成本超阈值 → 停机
- CI 连续 2 轮红 → 停机

---

## 6. Day 0 人工清单（1–2 天，不可外包）

这些是心因子本身，必须由人做或人逐字审：

1. **拍定项目名称**（§3 阻塞项）
2. 建新仓库；`install-age.sh` 安装 AGE 骨架
3. 拆分 `ARCHITECTURE.md` → `docs/architecture/` + `docs/design/`
4. 按 §2.3 改 `ROADMAP.md`：原则 4 措辞、P0 交付表中「OpenSpec 初始化」→「AGE 骨架安装 + mission 配置」
5. 写 `AGENTS.md`，含红线「loop 不得修改 `tests/gates/`」
6. 手写 §4.4 的 P0 红测试
7. 配置 GitHub Actions CI（最终裁判）
8. fork mission-driver，打 P1 / P2 / P3 三个补丁；同步向上游提 PR
9. 写 `missions/p0-foundation.json`
10. 重写 `prompts/build-verify.md`

完成后 `./mission-driver.sh p0-foundation` 接管。

---

## 7. 风险与未验证假设

| # | 风险 / 假设 | 影响 | 处置 |
|---|---|---|---|
| 1 | **opencode 计费口径**：是否可复用现有订阅未核实 | 7×24 成本可能远超预期 | 开跑前核实；不可复用则 §2.2 翻案，改加 `--driver claude` |
| 2 | **项目命名未决** | Day 0 无法起步 | 人决策，见 §3 |
| 3 | AI 拥有 shell，本地门禁理论上可被绕过 | 门禁失效而不自知 | CI 服务端复跑为唯一可靠层（§4.2） |
| 4 | 上游 PR 未被接受 | fork 需长期自维护 | 补丁面小（三处），可接受；不阻塞 |
| 5 | 上游 engine 后续演进与 fork 分叉 | 合并成本累积 | 钉死版本；仅在有明确收益时同步 |
| 6 | L2 慢门禁需活站点，比上游假设的 `mvn package` 重得多 | 循环节奏被拖慢 | 分层：L1 进每个 plan，L2 只进阶段关口 |
| 7 | AGE 方法论本身的效果**未经本项目验证** | 可能不适配 | P0 即为第一次实测；P0 跑完后复盘再决定是否延用至 P1+ |

---

## 8. 参考

- 上游仓库：<https://github.com/entropy-cloud/attractor-guided-engineering-template>（MIT）
- 关键源码：`src/plan-check.mjs`（closure 检查实现）、`src/flow-loader.js`（`SCRIPT_REGISTRY`）、`flows/plan-execution.json`、`prompts/build-verify.md`
- 方法论文章：<https://dev.to/canonical/attractor-guidance-and-trajectory-mining-the-convergence-mechanism-of-ai-native-engineering-456p>
