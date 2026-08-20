# AgenERP 主计划 · 引导扇区

> 你正在读的是 **AgenERP 项目的唯一入口**。任何会话、任何时候，从这里进。
> 本目录只拥有三样东西：**状态**（现在到哪了）、**次序**（下一步做什么）、**仪式**（怎么做才算数）。
> **验收判据不在这里**——判据在路线图与门禁测试里，本目录只负责指过去（§5）。

---

## §1 第一次来（冷启动，约 10 分钟）

按顺序读，**不要跳**：

1. [00-GOALS.md](./00-GOALS.md) §1 —— 北极星一句话。**记住它，之后每个会话都要背。**
2. [STATE.md](./STATE.md) §1 —— 现在到哪了。
3. [02-WBS.md](./02-WBS.md) —— 全量工作分解，找到「下一个未阻塞项」。
4. [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §1 —— 你是角色 A 还是角色 B，能做什么、不能做什么。
5. [04-RUNBOOK.md](./04-RUNBOOK.md) §1 —— 开跑前的预检。

其余按需：[DECISIONS.md](./DECISIONS.md)（已锁的决定，别重开）、[03-SKILL-GATE-MAP.md](./03-SKILL-GATE-MAP.md)（关口怎么过）。

---

## §2 恢复监督会话（RESUME 协议）

**人只需要打这一句：**

```bash
claude "按 docs/masterplan/README.md §2 恢复监督会话"
```

**收到这句话的会话（角色 A），必须在同一条回复里完成四件事，然后停下来等人说做什么：**

| # | 动作 | 数据来自 |
|---|---|---|
| 1 | **逐字复述北极星** | [00-GOALS.md](./00-GOALS.md) §1 |
| 2 | 报出当前阶段 / 当前 mission / 最后一条证据行 | [STATE.md](./STATE.md) §1 + §2 末行 |
| 3 | 指出**下一个未阻塞工作项的 ID 与标题** | [02-WBS.md](./02-WBS.md)（跳过 `done`，避开 `blocked`，遇 §3 有 `open` 的 needs-human 则优先处理它） |
| 4 | 给出该项的**验收命令原文** | 同上，该行的「验收」列 |

回复格式（照抄）：

```
北极星：<原文>
现在：<阶段> · mission <名> · 最后证据行 <时间 · WBS行ID · 命令→退出码>
下一项：<ID> <标题>
验收：<命令原文>
```

**四件事缺一件，就说明上下文没建立起来**——不要开始干活，回到 §1 重读。

启动 7×24 循环（Day 0 完成后可用）：

```bash
./mission-driver.sh p0-foundation
```

---

## §3 文档地图

| 文件 | 拥有什么 | 什么时候看 |
|---|---|---|
| [README.md](./README.md)（本文） | 入口、协议、引用登记表、迁移映射 | 每次开始 |
| [STATE.md](./STATE.md) | 状态投影、证据行日志、needs-human 队列 | 每次开始 / 每次收工 |
| [00-GOALS.md](./00-GOALS.md) | 北极星、S1–S6 成功判据、措辞纪律 | 每次开场背诵；复盘 |
| [02-WBS.md](./02-WBS.md) | Day -1 / Day 0 / P0–P5 全量工作项与验收绑定 | 找下一项时 |
| [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) | 双角色职权、needs-human 五步、LoopX 分层、执行器沙箱 | 动手前；出事时 |
| [DECISIONS.md](./DECISIONS.md) | D-1…D-6 台账、翻案条款登记簿、重开记录 | 想改主意时（先看有没有翻案条件） |
| [03-SKILL-GATE-MAP.md](./03-SKILL-GATE-MAP.md) | CP1–CP10 检查点 + 无技能时的内置等效清单 | 过关口时 |
| [04-RUNBOOK.md](./04-RUNBOOK.md) | 预检、监控、配额、崩溃恢复、停机响应、日/周仪式 | 每天；出事时 |
| `evidence-repo.env` | 证据仓位置与钉死的 sha | 换机器时改这一个文件 |
| `../../tools/check-masterplan-links.sh` | T2 断链校验（长期资产） | 每次改引用后；Day 0 `W0.13` 必跑 |

---

## §4 防跑偏机制索引

七道防线，**每一道都是确定性的**（不靠提示词里的自觉）：

| # | 机制 | 挡住什么 | 在哪 |
|---|---|---|---|
| 1 | 背诵条款 | 会话重启后目标漂移 | [00-GOALS.md](./00-GOALS.md) §6 |
| 2 | 每行绑定验收命令 | 「差不多做完了」 | [02-WBS.md](./02-WBS.md) 表规 |
| 3 | `GATE_VERIFY` 独立复跑判退出码 | **AI 自报通过** | `REF:GATE-INDEP` |
| 4 | 门禁测试写保护三层（CI 是唯一真的那层） | 改裁判 | `REF:GATE-PROTECT` |
| 5 | 四条停机条件 | 带病狂奔 | `REF:HALT` |
| 6 | 单会话单工作项 + 强制证据行 | 顺手改别的、无痕跑偏 | [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §3 |
| 7 | 决策台账 + 翻案条件 | 反复重开已定的事 | [DECISIONS.md](./DECISIONS.md) |

---

## §5 引用登记表（**唯一间接层**）

**规矩：正文里一律写 `REF:‹名›`，绝不写具体路径与节号。** 路径只在下表出现一次。
Day 0 会拆分 `ARCHITECTURE.md`、改写 `ROADMAP.md`——那时**只改这张表**，然后跑 `tools/check-masterplan-links.sh` 复验，其余七份文档一个字都不用动。

`${XM}` 由 `evidence-repo.env` 的 `XM_PATH` 解析。类别：**M** = Day 0 随仓迁移（路径会变）｜ **E** = 只读引证，长期留在证据仓。

| REF | 类 | 目标 | 锚串 |
|---|---|---|---|
| `REF:PROBLEM` | M | `${XM}/docs/next/ARCHITECTURE.md` | `### 1.1 我们解决什么问题` |
| `REF:AXIOMS` | M | `${XM}/docs/next/ARCHITECTURE.md` | `### 1.2 三条设计公理` |
| `REF:NONGOAL` | M | `${XM}/docs/next/ARCHITECTURE.md` | `### 1.3 明确的非目标` |
| `REF:ANTI-SPIRAL` | M | `${XM}/docs/next/ARCHITECTURE.md` | `### 11.2 为什么这是防死亡螺旋的关键` |
| `REF:LICENSE` | M | `${XM}/docs/next/ARCHITECTURE.md` | `## 16. 许可与商业化` |
| `REF:PENDING` | M | `${XM}/docs/next/ARCHITECTURE.md` | `## 15. 待定项` |
| `REF:ROADMAP-PRINCIPLES` | M | `${XM}/docs/next/ROADMAP.md` | `## 原则` |
| `REF:ROADMAP-DONT` | M | `${XM}/docs/next/ROADMAP.md` | `## 不做的事（避免踩已知的坑）` |
| `REF:ROADMAP-SPIKE1112` | M | `${XM}/docs/next/ROADMAP.md` | `## 待补 Spike（阻塞对应阶段）` |
| `REF:ROADMAP-P0` | M | `${XM}/docs/next/ROADMAP.md` | `## P0 · 地基（无 Agent）` |
| `REF:ROADMAP-P1` | M | `${XM}/docs/next/ROADMAP.md` | `## P1 · 解释与洞察（②端只读）` |
| `REF:ROADMAP-P2` | M | `${XM}/docs/next/ROADMAP.md` | `## P2 · 视图生成与新前端（②③端）` |
| `REF:ROADMAP-P3` | M | `${XM}/docs/next/ROADMAP.md` | `## P3 · 操作 Agent（③端写入）` |
| `REF:ROADMAP-P4` | M | `${XM}/docs/next/ROADMAP.md` | `## P4 · 形态 Agent（①端）` |
| `REF:ROADMAP-P5` | M | `${XM}/docs/next/ROADMAP.md` | `## P5 · 评测与编排` |
| `REF:REVOKE-DRIVER` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 2.2 执行器起步用 opencode，暂不加 claude driver` |
| `REF:CUT-OPENSPEC` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 2.3 裁掉 OpenSpec，统一到 mission-driver` |
| `REF:GATE-INDEP` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.1 让门禁从「自报」变为「独立判定」` |
| `REF:GATE-PROTECT` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.2 门禁测试的写保护` |
| `REF:DOCLAYER` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.3 文档三分层（心因子）` |
| `REF:REDTESTS` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.4 验收先行：先写红测试` |
| `REF:GATE-TIER` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.5 门禁分层` |
| `REF:MISSION-CFG` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.6 mission 配置` |
| `REF:PROMPTS` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `### 4.7 prompt 覆盖` |
| `REF:HALT` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `## 5. 停机条件` |
| `REF:DAY0` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `## 6. Day 0 人工清单` |
| `REF:RISK` | M | `${XM}/docs/superpowers/specs/2026-08-20-mission-driver-adoption-design.md` | `## 7. 风险与未验证假设` |
| `REF:PBV-SUMMARY` | M | `${XM}/docs/next/PRE_BUILD_VALIDATION.md` | `## 一、结论摘要` |
| `REF:PBV-RESIDUAL` | M | `${XM}/docs/next/PRE_BUILD_VALIDATION.md` | `## 五、未排除的残余风险` |
| `REF:D01-NAMING` | E | `${XM}/spike/D01-decisions/FINDINGS.md` | `## D-1 项目命名` |
| `REF:SPIKE02` | E | `${XM}/spike/02-constrained-agent` | - |
| `REF:SPIKE02-MODELS` | E | `${XM}/spike/02-constrained-agent/models.py` | `SCAFFOLD_TOKENS = 1561` |
| `REF:SPIKE04-INJECTION` | E | `${XM}/spike/04-injection` | - |
| `REF:SPIKE06-PACK` | E | `${XM}/spike/06-customization-pack` | - |
| `REF:SPIKE09-PERM` | E | `${XM}/spike/09-permission-layers` | - |

校验：

```bash
tools/check-masterplan-links.sh
```

---

## §6 证据仓指针

XM 是 AgenERP 的**只读证据仓**：花边制造 ERP 演示栈（真实 ERPNext v16，816 DocType / 完整业务链）+ 10 个 spike 的可复跑代码与 trace。位置与 sha 见 `evidence-repo.env`，**换机器只改那一个文件**。

XM 必须伴随存在的硬理由：[02-WBS.md](./02-WBS.md) 里四个 🚪 阶段入口关口实验（P1.0 L3 门禁重跑、P2.0 Spike 11、P3.0 写权限注入复测、P4.0 Spike 12）**都要跑在那套演示栈上**，新仓在 P2 之前没有等价环境。

本机没有 XM 时：

```bash
git clone <XM 远端或本地路径> ../xm-evidence
git -C ../xm-evidence checkout <evidence-repo.env 里的 XM_SHA>
# 然后把 evidence-repo.env 的 XM_PATH 改成 ../xm-evidence 的绝对路径
```

---

## §7 Day 0 迁移映射

两类引用，**处置方式不同，不要混为一谈**：

| 类 | 内容 | Day 0 怎么处理 | 之后 |
|---|---|---|---|
| **M · 随仓迁移** | `ARCHITECTURE.md`（拆分为 `docs/architecture/` + `docs/design/`）、`ROADMAP.md`（→ `docs/backlog/implementation-roadmap.md`，并改原则 4 与 P0 交付表）、`PRE_BUILD_VALIDATION.md`（→ `docs/archive/`，文件名加日期前缀）、方案 C 设计（→ `docs/archive/`） | 迁入本仓并**继续演进**；`W0.13` 更新 §5 表中这些行的路径与锚串 | 本仓是它们的新家，XM 里的副本即刻**作废** |
| **E · 只读引证** | `spike/**` 的代码、数据与 trace；ERPNext 演示栈本身 | **不迁移**。永远经 `${XM}` + 钉死的 sha 访问 | XM 保持只读；需要复跑实验时 checkout 那个 sha |

分层目标结构见 `REF:DOCLAYER`。

> ⚠️ **`W0.13` 不是收尾工作，是 Day 0 的出口门禁之一。** W0.3 拆分文档、W0.4 改写路线图之后，§5 表里 M 类的锚串会集体失效——不修就等于主计划失去了全部判据来源。

---

## §8 本文档集自身的验收（T1–T4，判据事先写死）

| # | 测试 | 通过判据 | 结果 |
|---|---|---|---|
| **T1** | **冷启动**：全新会话只给 §2 的 RESUME 命令 | 单条回复完成四件事（背诵北极星 / 报状态 / 指出下一未阻塞项 / 给出验收命令原文）。**缺一即失败** | ✅ 2026-08-20 |
| **T2** | **断链**：`tools/check-masterplan-links.sh` | 退出码 0 | ✅ 2026-08-20 |
| **T3** | **Day 0 演练**：全新会话只读本目录，干跑 `W0.1` | **不提问**即产出完整步骤 + 证据行格式 | ✅ 2026-08-20 |
| **T4** | **needs-human 演习**：在 STATE §3 手工塞一条模拟停机，命令用 RESUME **加一句「处置那条 open」**（只给 RESUME 会正确地停下来等人，那是 §2 的规定，不是失败） | 新会话按 [01-EXECUTION-MODEL.md](./01-EXECUTION-MODEL.md) §2 五步处置，**第 3 步必须是「先原样复跑失败命令」** | ✅ 2026-08-20 |
| 硬约束 | 每份文档 `wc -c` | < 30720（上游规矩 >50K 必拆、30K 为宜） | ✅ 最大 02-WBS 17.4KB |
