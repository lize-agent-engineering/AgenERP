# 决策台账

> **规则：本文件只增不改。** 已登记的决策不得被任何会话（包括你）擅自重开——重开只有一条路：人明确说要重开，然后在 §3 追加一条 `R-x` 记录，写清新证据。
> 「我觉得换个做法更好」不是新证据。**只有触发了该决策自带的翻案条件，才允许重开。**

---

## 1. 已锁定决策

### D-1 · 项目名 = AgenERP

| | |
|---|---|
| 决策 | 沿用 **AgenERP** |
| 依据 | 用户 2026-08-20 拍板（原话：「项目名就叫AgenERP」） |
| 风险 | D01 建议改名：口头传达与搜索会被纠正成 AgentERP；`agenerp.com` 已被占用，无法用域名强化拼写（`REF:D01-NAMING`） |
| **显式记录** | **已知晓上述拼写风险并接受。** 这是主动选择，不是默认继承——D01 要求的正是这一句 |
| 未完成动作 | 建仓库当天**重新核验** GitHub 组织名 / PyPI 包名 / 域名可得性。§15 与 D01 记录的可得性是 2026-08-19 的快照，不能当作现在仍成立 → WBS `W0.1` |
| 翻案条件 | 仅当 W0.1 复核发现名称**已被他人占用**（GitHub org 或 PyPI 名不可得）。届时由人重新拍板，不得由 loop 自行改名 |

### D-2 · OpenSpec 维持裁掉

| | |
|---|---|
| 决策 | 不引入 OpenSpec，统一到 mission-driver 的 `roadmap → plan → closure` 单一状态机 |
| 依据 | 方案 C §2.3（`REF:CUT-OPENSPEC`），用户已「认可方案 C」 |
| 理由摘要 | proposal 与 plan 是同一事物的两个名字，archive 与 closure 是同一动作的两个名字。**同时跑两套状态机，模型会在「该建 proposal 还是建 plan」上反复漂移。** OpenSpec 在仓里尚未落地，放弃成本约等于零 |
| **需注意的口径冲突** | 2026-08-20 的建计划指令里仍把 openspec 列在「请综合使用的 skills」中。本台账按**后者服从前者**处理：方案 C 是经确认的裁决，建计划指令是方法建议。其纪律不丢——proposal→apply→archive 三态吸收为 plan 模板 front-matter 的 `status: draft/active/closed` |
| 翻案条件 | 单一状态机在 P0 实跑中出现「plan 粒度承不住阶段级提案」的实例（同一阶段被迫拆出 >8 个 plan 且互相引用）。届时先考虑调 mission 粒度，仍不行才重开 |
| 遗留动作 | 路线图原则 4 现仍写着「每阶段一个 OpenSpec change proposal」，Day 0 必须改（→ `W0.4`） |

### D-3 · 执行驱动 = mission-driver + 新增 `--driver claude`

| | |
|---|---|
| 决策 | fork mission-driver、钉死版本、打三个补丁；**并新增 `--driver claude`**，用 Claude Code 订阅驱动 loop |
| 依据 | 方案 C §2.2 自带翻案条款：「若订阅不可复用，本条裁决翻案，改为新增 `--driver claude`」（`REF:REVOKE-DRIVER`）；D-5 已明确执行者是 Claude Code Opus 5 |
| ⚠️ **前提尚未核实** | 方案 C 的原文是「**开跑前必须核实** opencode 走 Anthropic 的计费口径与 Claude Code 订阅是否同一条管道」。本台账登记的是**结论先行**：按 D-5 走订阅。核实动作单列为 `W0.0`，**不做完不得进入 7×24** |
| 实现参照 | `REF:SPIKE02-MODELS` 的 `claude -p` 用法。**必须复用其 HOME/cwd 隔离对策**：在本仓目录直接跑 `claude -p` 会加载 CLAUDE.md / SessionStart hook / skills，单轮多出约 37,000 token 的无关上下文并干扰协议遵守（`spike/02-constrained-agent/models.py:78` 注释）。详见 [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §5 |
| ⚠️ **本机实测（2026-08-20）** | `claude -p` 与子代理**当前都跑不起来**：`~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL=http://127.0.0.1:3002` + `ANTHROPIC_MODEL=deepseek.local`（含 `CLAUDE_CODE_SUBAGENT_MODEL`）把调用全部路由到一个不可用的本地模型。**loop 会原样继承这份配置** → 新增 `W0.0b`，且 §5 沙箱规范里「隔离 HOME/环境」从优化项升为前置项 |
| 翻案条件 | W0.0 实测出现下列任一：① 订阅额度在 7×24 下不足以支撑一个 mission 走完 P0；② headless 调用被判定为违反订阅使用条款。届时改回 opencode + API 计费，并把成本阈值写进停机条件 |

### D-4 · 技能：Day -1 尽力安装 + 映射到固定关口 + 每个关口内置等效清单

| | |
|---|---|
| 决策 | 技能只在**监督侧**（角色 A）触发；loop 内（角色 B）零外部技能依赖，一律走 fork 的 `prompts/` |
| 依据 | 本机实测：`~/.claude/plugins` 只装了 superpowers 6.2.0 与 frontend-design；mattpocock / grill-me / tospec / openspec **均未安装**（2026-08-20 核验） |
| 硬要求 | [03-SKILL-GATE-MAP.md](./03-SKILL-GATE-MAP.md) 的每个检查点 **必须同时给出内置等效清单**。技能装不上 → 走清单，**不阻塞** |
| 翻案条件 | 无需翻案。技能可随时补装，补装后仍走同一关口 |

### D-5 · 持续执行者 = Claude Code Opus 5，双角色模型

| | |
|---|---|
| 决策 | 角色 A = 交互式监督会话（有人在场，可用技能、可决策）；角色 B = loop 内无头执行步骤（无人在场，只认门禁退出码） |
| 依据 | 用户明示：「我后续将使用 opus 5 完整持续的执行这份计划」 |
| 职权与禁区 | [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §1 |
| 翻案条件 | 无。这是人的选择 |

### D-6 · LoopX 采用（试点，严格分层）

| | |
|---|---|
| 决策 | 采用 **LoopX** 作监督侧状态内核，**严格分层**：LoopX 拥有 WBS 项级/跨会话状态；mission-driver 拥有 mission 内执行状态。写回单向、由脚本写、不经 AI 转述 |
| 依据 | 用户 2026-08-20 追加调研项。它补上方案 C 两个真实缺口：① **配额感知续跑**（Opus 5 订阅在 7×24 下必然撞限流窗口，mission-driver 没有配额模型）；② **监督态的确定性维护**（原设计靠 STATE.md 的 markdown 纪律，本质仍是「AI 自报状态」） |
| 本机实测 | `pip3 install --user loopx` → **loopx 0.5.0 装成功**；`loopx doctor` → `ok: True`；`loopx quota should-run` 命令存在；`loopx slash-commands --install` 向 `~/.claude/skills` 写入 50 个技能文件（含 `/loopx`）。2026-08-20 实测 |
| 分层契约 | [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §4。**这是防止重蹈 D-2 双状态机覆辙的唯一保障，违反即等于翻案** |
| **事先写死的退出判据** | Day 0 的 `W0.12` 给 LoopX 集成 **2 小时上限**。超时仍未跑通「建 goal → 建 todo → `quota should-run` 决策 → 门禁退出码写回证据」这一闭环 → **当场退回 STATE.md 手工纪律，不再重试**，并在 §3 追加 `R-x` 记录 |
| 复评时点 | 与 AGE 方法论一起纳入 **CP9 · P0 阶段复盘**：「是否续用」二选一，判据事先写死于 [04-RUNBOOK.md](./04-RUNBOOK.md) §7 |
| 翻案条件 | 上面两条任一触发；或 LoopX 与 mission-driver 出现「谁说了算」的实例冲突 ≥2 次 |

---

## 2. 翻案条款登记簿

方案 C §7 的七条风险（`REF:RISK`）在此各占一行。**每条都预先写死了触发信号与处置**，不留「到时候再看」。

| # | 风险 / 假设 | 触发信号（客观可观测） | 处置 | 归属关口 |
|---|---|---|---|---|
| R-1 | 计费口径未核实 | `W0.0` 实测结果 | 见 D-3 翻案条件 | Day 0 出口 |
| R-2 | 项目命名未决 | 已由 D-1 关闭 | 仅 W0.1 复核发现被占用时重开 | Day 0 出口 |
| R-3 | AI 有 shell，本地门禁可被绕过 | `git log` 出现触及 `tests/gates/**` 的提交 | **立即停机**；CI 服务端复跑是唯一可靠层 | 每次 push |
| R-4 | 上游 PR 未被接受 | 无（不阻塞） | 长期自维护 fork，补丁面仅三处 | — |
| R-5 | fork 与上游分叉 | 上游发版 | 钉死版本；仅在有明确收益时同步 | CP9 |
| R-6 | L2 慢门禁拖慢节奏 | 单轮 plan 墙钟时间 > 30 分钟 | 分层：L1 进每个 plan，L2 只进阶段关口 | CP9 |
| R-7 | AGE 方法论本身未经本项目验证 | P0 跑完 | **P0 即第一次实测**；复盘决定是否延用至 P1+ | CP9 · P0 |
| R-8 | **LoopX 未经本项目验证**（本台账新增） | 见 D-6 退出判据 | 无损退回 STATE.md 手工纪律 | `W0.12` / CP9 |

---

## 3. 重开记录（Reopen Log）

> 格式：`R-x · 日期 · 被重开的决策 · 触发的翻案条件 · 新证据（命令 + 退出码 / commit sha） · 新裁决 · 拍板人`
> **只有人能新增本节记录。** loop 与无头会话一律无权重开，只能把请求写进 [STATE.md](./STATE.md) §3。

（暂无）
