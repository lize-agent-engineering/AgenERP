# P1 · 解释与洞察（②端只读） — mission roadmap

> Last updated: 2026-08-24
> Sources: [`docs/masterplan/02-WBS.md`](../masterplan/02-WBS.md) §4（判据的真相源）·
> [`tests/gates/`](../../tests/gates/README.md)（判据的可执行形式）

## Purpose

这是 **`p1-insight` mission 自己的 roadmap**，由引擎在 closure 审计通过后回写。
全局阶段索引在 [`implementation-roadmap.md`](./implementation-roadmap.md)，由人维护。

P1 的目标一句话：**让 Agent 能看懂这套 ERP，并且能证明它真的看懂了。**
**②端只读**——本阶段 Agent 不写任何业务数据。

## 本阶段的三条硬约束（违反即停机，不是风格建议）

**① 判据不许只验「调得通」。**（CP9 继承项①）
退出码 0 与「跑了且过」不是一回事。P1 尤其危险：**「Agent 答对了」与
「Agent 蒙对了」在结果层面长得一模一样**。每条判据都要能区分这两者。

**② 预测在前、结果在后、逐条吻合。**（CP9 继承项②）
凡实验性质的工作项，假设**在跑之前逐字写死**，事后逐条对照，不许事后改写。

**③ 规则能覆盖的流程不 Agent 化。**（D-15）
面对任一环节先问：**「这一步的判断能不能写成确定性规则？」** 能写就写成规则。
只有输入模糊、路径不可预先枚举、或需按中间结果动态改变后续动作时，才交给模型。
**反向边界**：自然语言理解、多跳路径选择、归因叙述的组织**枚举不完**，
强行规则化会退化成脆弱的关键词匹配。判据是「路径能否预先枚举」，不是「看起来复不复杂」。

**④ 以本项目的实测为准。**（D-16）
外部基准、他人评测、厂商声明，只能作**假设的来源**，不能作**结论的依据**。
引用任何数字前先问：**「这个数字是在本项目、本数据集、本任务上跑出来的吗？」**
不是，就写成「据某处，推测……，待复验」，不写成结论。
**已发生的实例**：外部基准给 `qwen3.6-plus` 84.1%，**本项目任务上 **4/6**（`门禁off 3/3` + `门禁on 1/3`）⚠️ 此数经两次更正：先记 2/6、后记 1/6，均因判定正则漏掉一种拆法，见 STATE §2 同日更正行**。

## Work Item Status

> **这是唯一的动态状态块。** 状态只在这里改。
> 顺序即执行顺序，引擎取第一个 `todo`。

- 1. 工具执行层：10 个只读契约的执行体（P1.0a）: `done`（2026-08-24，sha `5a712a7`；独立收口审计 2026-08-24 通过，见 plan `## Closure`。WBS §4 第 78 行的 🔴 门禁那一半**已由人补齐**——`tests/gates/test_tool_execution_live.py`，commit `f76b07c`，`Gates-Change-Approved-By: lize`，STATE §3 `[resolved] 2026-08-24T05:49Z`。⚠️ 仍待人做：`tests/tools` 本身未进 `gates.yml` 的 `unit-and-contracts` / `lint` 两个 job）
- 2. 入口关口实验：门禁能否补偿模型能力（P1.0 🚪）: `done`（2026-08-24；结论 **`被削弱`** —— 弱模型 `qwen-plus` 门禁 off 0/3 → on 2/3，但强模型 `qwen3.6-plus` **无门禁** 3/3，门禁没让弱模型追上强模型。判定见 `docs/audits/p1-insight/2026-08-24-P1.0-entry-gate.md`，14 份轨迹与判定表见 `docs/evidence/p1-entry-gate/`。⚠️ 结论只覆盖这一道题、两个模型、每格 3 次有效运行，不得外推）
- 3. 模型路由 v0：OpenAI 兼容 adapter + 能力声明按任务分档（P1.1）: `done`（2026-08-24，sha `b6f4a5a`；plan `docs/plans/p1-insight/2026-08-24-1457-1-model-routing-v0.md`，独立收口审计见其 `## Closure`。`agenerp/routing/` 五个模块 + `tests/routing` **132 passed, 1 skipped**；分档表落 `docs/architecture/model-management.md` **§12.5**（新增落点节），§12.3 那处「或由更强的循环门禁补偿」按 P1.0 **人侧独立复核**的判定改准。活端点冒烟跑过一次：`usage={'prompt':15,'completion':194,'reasoning':188}`，与开工前写死的预期 `reasoning > 0`（D-11）吻合。⚠️ **verification scope limited**：`tests/routing` 既不在 `commands.test` 也不在任何 CI job 里，与 `tests/tools` 同形态，**不得读成 CI 已覆盖**；已随收口在 STATE §3 追加 needs-human。⚠️ 另有两条 needs-human：`qwen3.6-plus` 的 `multi_hop` 声明建立在本项目 2/6 的实测上；本文件工作项 2 的逐格计数与下方 P1.7 警示表不一致，loop 未代改）
- 4. 上下文层 v0：即时上下文注入 + 会话落 DocType（P1.2）: `done`（2026-08-24；plan `docs/plans/p1-insight/2026-08-24-1457-2-context-layer-v0.md`。`agenerp/context/` 三个模块 + 会话 DocType **声明** + `tests/context` **53 passed**（WBS §4 P1.2 的验收原文 `pytest tests/context -q` 退 0；首次收口时 51 条，补 M9 判据后 53 条）。落点节 `module-boundaries.md` **§7.7**（新增），`context-and-memory.md` §8.2 的 ① / ② 两行补上落点指针（③ / ④ 一个字未动）。变异自查 **M1–M8 八个全部被打红**，无一需要就地补断言；**独立关闭审计**（sha `3337d69`）另出 A1–A5 五个变异，A5 打出一处判据缺口（② 档只有常量声明断言、没有行为断言），已回 EXECUTE 补上正向 + 反测两条并登记为 **M9**，复跑确认 M9 被打红，判据 **51 → 53 passed**。⚠️ **只做 ① 即时与 ② 会话两层**，③ 记忆 / ④ 检索是起草期显式定界的 Non-Goals，重开事件见 plan §9。⚠️ **会话在活站点上尚未建表** —— 那是风险档 L3 强制人批的动作，本 plan 未发出任何 DDL；已随收口在 STATE §3 追加 needs-human（含手工回滚命令原文）。**`closure audit was independent` 已勾** —— 独立关闭审计已于 sha `3337d69` 补做，结论 `issues`（见 plan §12.8）；⚠️ 但 **A5 的补齐（M9 两条断言）做在那轮审计之后、只经执行者自查**，不得读作「补齐也被独立复核过」。⚠️ **verification scope limited**：`tests/context` 在**首次**收口那一刻既不在 `commands.test` 也不在任何 CI job 里；此后由另一条工作线的 `b7fc902` 接进 CI 的 `unit-and-contracts`，本轮的 53 条会被 CI 复跑，**但那笔改动不属本 plan**）
- 5. 导航的编排行为：permission.scope 开场自动注入（P1.3）: `done`（2026-08-24，权威 sha `e55d985`；⚠️ **代码产物的首次进仓 commit 是人的 CI 提交 `90ccb4b` / `d3b9213`**——同一工作树上被 `git add` 扫进去的，归属照实记在 plan `## Closure` 的表里；plan `docs/plans/p1-insight/2026-08-24-1601-2-navigation-orchestration-v0.md`。`agenerp/orchestration/` 三个模块（`opening.py` / `navigation.py` / `circuit.py`）+ `tests/tools/test_navigation.py` **32 passed**（WBS §4 第 82 行的验收原文 `pytest tests/tools/test_navigation.py -q` 退 0，其中 `test_opening_injection_really_happens_on_the_site` 就是「有一条断言开场注入真的发生」那一条，判据落在 `FakeSite.requests` 上、不落在标志位上）。落点节 `module-boundaries.md` **§7.6a**（新增）+ §7.4 末尾追加熔断落点，且 §7.6 那句「熔断仍未做…归 P1.0 的控制循环」的**失效归属已改准**。变异自查 **M1–M8 八个全部被打红**；⚠️ **M6 第一轮是绿的**（相等断言挡不住「装配路径上写死成正确值」），已就地补同一性断言与「不许凭空补一个」两条，M6a/M6b 复跑均 exit 1。§6 的 **H1–H4 四条全部吻合**，假设一个字未改、题一道未换。⚠️ **导航数字是本仓夹具实测，非站点实测**（① 题 on 1 次 / off 5 次 `execute()`），与 owner doc 里 Spike 01/02 的「35 次」「35 → 1」**不是同一个量，不得互相引用为佐证**；且**站点请求那一栏 on 组净亏**（10 对 5），「更省」只在 `execute()` 次数这一栏成立。⚠️ **熔断尚未接到任何真实控制循环上**（接线归 P1.4），§7.4 的「写入审计」那一行同样未落地。⚠️ `tools_readonly.py` 的 `injected_at_session_start` **仍是调用方自证的软断言**，本期加强的是编排面不是契约面。⚠️ **独立关闭审计未做** —— 本轮执行环境不具备独立子代理，`closure audit was independent` 这条 gate **留白**，详见 plan `## Closure`。⚠️ **verification scope limited**：`tests/tools` 已在 CI 的 `unit-and-contracts` / `lint` 里（`b7fc902`，不属本 plan），但仍不在 `missions/p1-insight.json` 的 `commands.test` 里，`GATE_VERIFY` 复跑不到；已随收口在 STATE §3 追加 needs-human）
- 6. 解释 Agent + 证据充分性门禁（P1.4）: `todo`
- 7. 巡检器（纯规则引擎）+ 洞察 Agent（归因）（P1.5，见 D-15）: `todo`
- 8. 行业包 v0（离散制造），每条规则带 test_case（P1.6）: `todo`
- 9. **单次解释成本记账**（记账但不拦截，D-18）（P1.7）: `todo`
- 10. Agent 侧边栏嵌 Desk（P1.8）: `todo`

## 已经就绪的前置（不要重做）

- **样板公司**：恒锐动力科技有限公司（HRD）· 户用储能电池包。数据集 15 个
  DocType **全部为原生 ERPNext**，无自建表（D-9）
- **固定测例**：成品仓积压 **1,010 台 / ¥3,110,200**。账面全绿——订单被人工
  置为 `Closed`，系统按完成计，达成率 100% 而实发 990 台
- **外协四步链**：采购订单(外协) → 外协订单 → 发料 → 外协收货，全部由服务端
  工厂方法派生（D-12）
- **证据充分性门禁**：L1/L2（Spike 02 产出）+ **L3**（入库来源的覆盖，P1.0 T1 已定义，
  含过拟合反测）
- **站点侧对账 30 项**：财务/库存 9 + 文档图条数 9 + 跨单据 Link 字段 12
- **LLM**：DashScope（`qwen3.6-plus` 默认，D-11）。⚠️ 它是推理模型，
  回两个字也烧约 195 reasoning token，成本上限须按 reasoning token 计

## P1.7 已按 D-18 改为「记账但不拦截」（动手前必读）

原设计是「单次解释成本**上限**」，前提是「便宜模型 + 强门禁」可用。
P1.0 两轮实测都不支持这个前提（第一轮 5/12、第二轮 11/12，**可用的是更强的
模型，不是门禁补偿**）。实测单次解释 **9.7 万–12.8 万 token**。

用户 2026-08-24 裁定：**记账但不拦截**。

- 判据从「成本 ≤ X」变成「**成本可观测**」：prompt / completion / **reasoning**
  三项分开记，可按一次解释汇总
- ⚠️ **不许退化成「跑通就算」**：要能挡住「只记 completion 不记 reasoning」的
  假实现（D-11：回两个字也烧约 195 reasoning token）
- ⚠️ **不拦成本 ≠ 不拦失控**：工具调用轮数上限仍要有。一个陷入循环的 Agent
  会无限调工具 —— 那不是「贵」，是**坏**。两者判据**分开写，不许合并**

## ⚠️ 判自由文本答案之前，先跑通标注集（P1.4 / P1.5 动手前必读）

**`tests/fixtures/p1_entry_gate_labels.jsonl`**（24 条，人工标注，每条带 `reason`）
**`tests/unit/test_answer_judging_fixture.py`**（判据的判据）

### 为什么它存在

人侧判 P1.0 那道题的答案时，用关键词正则判了**四次，四次都判错**：

| 第几次 | 漏掉的 |
|---|---|
| 1 | 要求字面 `2000`，认不出 `1000 + 1000 - 990` |
| 2 | 根因词列了「重复生产」，漏了「重复记录」 |
| 3 | 认不出 `10 台尾数 + 1000 台外协` 这第三种拆法 —— 第一轮整体从 5/12 误判成 2/12 |
| 4 | 「没有任何销售订单来消化」「无单可发」「额外的外协收货」都不在词表里 |

**每次都是读原文才发现，而每次修完都以为修干净了。**
→ 结论不是「再补一版词表」，是**正则判自由文本这条路走不通**。

### 对 P1.4 / P1.5 的要求

P1.4 判「解释 Agent 答得对不对」、P1.5 判「洞察 Agent 找没找到」，
**比 P1.0 那道题更难判**。三条：

1. **动手写判定器之前，先让它跑通那 24 条标注。** 跑不通就别往下写 ——
   那说明判定方法有问题，不是答案有问题
2. **标签只能由人读原文定**，不能由任何判定器产生 —— 否则是让判据给自己判卷
3. **反例比正例值钱**：集子里 4 条「不完全」+ 1 条「截断」是刻意留的，
   只有正例的集子挡不住「一律判正确」的假实现

⚠️ 若判的是**结构化事实**（例如「给定事实集，三条门禁规则怎么判」），
本节不适用 —— 那是可枚举的，正则/条件求值没问题。
**本节针对的是判自由文本。** 两者别混。

## 已知的坑（照抄，不要重新发现）

- ~~**`permission.scope` 的判别力在当前站点上验不出来**~~ —— **2026-08-24 已解决**：
  `agenerp/seedusers.py` 幂等建出受限身份「车间工人」（只读 3 个 DocType），
  以它实跑得到**可读 3、不可读 3**。⚠️ **新坑照实记**：stock Frappe 只把 `DocType`
  的读权限给 System Manager / Administrator，且对它建 `Custom DocPerm` **不生效**，
  因此**受限身份枚举不出 DocType 清单**——`permission.scope` 的候选集必须由调用方给，
  **不要靠给工人发 System Manager 绕过去**（那等于把「受限」取消掉）
- **`lineage.trace` 必须扫子表**：21 个指向 `Sales Order` 的 Link 里 14 个在子表
- **`doc.links` 的下游筛选是「排除已取消」**，不是「只要已提交」——
  滤掉草稿会把 L2 门禁架空
- **外协订单在 ERPNext v15 结构上挂不回销售订单**（没有 `sales_order` 字段），
  这是 P1.0 实验陷阱的来源，**不是缺陷，不要去"修"它**
- **Python 直连 HTTPS 需显式 certifi**：本机 python.org 版未装 CA 根证书
