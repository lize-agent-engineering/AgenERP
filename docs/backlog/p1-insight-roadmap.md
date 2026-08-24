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

## Work Item Status

> **这是唯一的动态状态块。** 状态只在这里改。
> 顺序即执行顺序，引擎取第一个 `todo`。

- 1. 工具执行层：10 个只读契约的执行体（P1.0a）: `done`（2026-08-24，sha `5a712a7`；⚠️ WBS §4 第 78 行的 🔴 门禁判据**那一半仍未满足**——提升进 `tests/gates/` 与 CI 接线在红线内，已挂 STATE §3 needs-human）
- 2. 入口关口实验：门禁能否补偿模型能力（P1.0 🚪）: `done`（2026-08-24；结论 **`被削弱`** —— 弱模型 `qwen-plus` 门禁 off 0/3 → on 2/3，但强模型 `qwen3.6-plus` **无门禁** 3/3，门禁没让弱模型追上强模型。判定见 `docs/audits/p1-insight/2026-08-24-P1.0-entry-gate.md`，14 份轨迹与判定表见 `docs/evidence/p1-entry-gate/`。⚠️ 结论只覆盖这一道题、两个模型、每格 3 次有效运行，不得外推）
- 3. 模型路由 v0：OpenAI 兼容 adapter + 能力声明按任务分档（P1.1）: `todo`
- 4. 上下文层 v0：即时上下文注入 + 会话落 DocType（P1.2）: `todo`
- 5. 导航的编排行为：permission.scope 开场自动注入（P1.3）: `todo`
- 6. 解释 Agent + 证据充分性门禁（P1.4）: `todo`
- 7. 巡检器（纯规则引擎）+ 洞察 Agent（归因）（P1.5，见 D-15）: `todo`
- 8. 行业包 v0（离散制造），每条规则带 test_case（P1.6）: `todo`
- 9. 单次解释成本上限（P1.7）: `todo`
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
