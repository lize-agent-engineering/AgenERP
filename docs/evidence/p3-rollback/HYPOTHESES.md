# P3.2 回滚前提探测 · **跑之前写死的预测**

> 2026-08-29 · 分支 `main` · plan `p3-swirling-wombat.md` 阶段 A
> 探测设施：`tools/experiments/p3_rollback/`
> 结果落点：`docs/evidence/p3-rollback/premises.json` · `mutation-check.json`

**这个文件的全部意义是它的落库时间。** 它必须在 `premises.json` 之前单独 commit，
判据 `tests/tools/test_rollback_premises_body.py::test_hypotheses_were_frozen_before_the_result`
比对两者的**首次落库**时间（`git log --diff-filter=A --format=%ct`）——
用首次落库而不是最近一次，是因为后者会被一次 `--amend` 或一次改错别字挪到结果之后去。

CP9 继承项②逐字：**假设事先写死**。不写死的话，「预测对了」与「照着结果编了一份预测」
在文档上长得一模一样。

---

## 0. 哪几条是**盲的**，哪几条不是 —— 先说这个，否则「预测命中率」是假的

规划与本轮开工时已经实读过站点与容器源码，那些事实**不能算预测命中**。逐条分开：

| # | 预测 | 盲？ | 若非盲，先前看到了什么 |
|---|---|---|---|
| H1 | 前提 1 · 提交路径 `db.commit()` 次数 | ✅ 盲 | — |
| H2 | 前提 2 · 提交路径 `enqueue` 次数与携带的值 | ✅ 盲 | — |
| H3 | 前提 3 · 提交过程中的事务外副作用 | 🟡 半盲 | 静态行数已读（见 H3a），**提交过程中派发与否未读** |
| H4 | A3 · `before_submit` 链实际是哪几道 | ✅ 盲 | — |
| H5 | savepoint 回滚在**进程内**是否仍成立 | ❌ **不盲** | 2026-08-29 冻结前跑过一次探索性 submit + rollback，见下 |
| H6 | 前提 0 · 跨连接够不着 savepoint | ❌ **不盲** | 容器内已实读 `frappe/app.py:415-417` |
| H7 | 站点指纹会不会咬人 | ✅ 盲 | — |

🔴 **H5 的坦白**：冻结本文件之前，我在容器里跑过一次探索性的
`insert → submit → frappe.db.rollback()`，看见站点上 `Stock Entry` 仍是 4 行、
`tabSeries` 的 `current` 仍是 4。**因此 H5 命中不构成证据强度**，它只是把那次
一次性观测固化成可复跑的形态。真正含信息的是 H1/H2/H4/H7。

---

## 1. 逐条预测（**每条都给证伪面，不给「大致会怎样」**）

### H1 · 前提 1：提交路径不自行 `db.commit()`

**预测：两个场景（当日 / 倒填）各 0 次。** 且 `raw_txn_sql` 里不出现裸 `COMMIT`。

- 依据：Spike 05 在外部栈上实测 0 次；frappe 的设计把 commit 留在请求边界
  （`frappe/app.py::sync_database`），控制器不该自己 commit。
- **证伪面**：任何一个场景的 `premise_1_commit_calls > 0`，或 `premise_1_raw_txn_sql` 非空。
- 若被证伪：该 DocType 退出可回滚集合，且 🔴 **门禁冻结那个数字、不删断言**
  （plan 的坏消息分支表第 2 行）。

### H2 · 前提 2：提交路径不 `enqueue` 后台任务

**这条我预测会被证伪，而且正是在倒填那一格。**

| 场景 | 预测 |
|---|---|
| 当日 (`posting_date = today`) | `enqueue` **0 次** |
| 倒填 (`posting_date = 2026-01-05`) | `enqueue` **≥ 1 次**，且 `Repost Item Valuation` **新增 ≥ 1 行** |

- 依据：`Stock Reposting Settings.item_based_reposting = 1`（2026-08-29 实读），
  站点上 `Repost Item Valuation` 现有 **0 行**；倒填到 `agenerp.seed.model.BASE_DATE`
  （2026-02-02）之前会让既有 SLE 全部落在其后 ⇒ 重估值链路应当被触发。
- **这正是 `docs/architecture/open-questions.md:92` 那条已知缺口**：Spike 05 的倒填
  **没有真正触发** `Repost Item Valuation`，所以它测出的「0 次」覆盖不到这条路径。
- **证伪面**：倒填场景 `enqueue == 0` **且** `Repost Item Valuation` 计数不变。
  真出现这个，逐字记「重估值链路仍未测到」，`open-questions.md:92` **不许划掉**
  （plan 的坏消息分支表末行）。

### H3 · 前提 3：事务外副作用

**H3a（已实读，不算预测）**：站点上 `Workflow` 0 · `Notification` 2 · `Webhook` 0 ·
`Server Script` 0 · `Client Script` 0；两条 Notification 分别挂 `Material Request`
与 `Fiscal Year`，**都不是 Stock Entry**。

**H3b（预测）**：提交 Stock Entry 的过程中——

- `frappe.sendmail` **0 次**；
- `evaluate_alert` **0 次**（没有挂在 Stock Entry 上的 Notification）；
- `run_webhooks` / `run_server_script_for_doc_event` **会被派发**（`run_method` 每次都调
  它们，`frappe/model/document.py:1019-1021`），但因为两张表都是 0 行而**不产生外部动作**。

**证伪面**：`sendmail` 或 `evaluate_alert` 非 0。
⚠️ **这条预测的边界照实说**：它只覆盖「本仓这个站点此刻的配置」。
一个装了 Webhook 的客户站点上，同一份代码的答案不同 —— 所以写契约里
`side_effects` 必须**逐个声明**，不能靠这次探测的 0 去推断。

### H4 · A3：提交实际撞了哪几道 `before_submit`

**预测：Stock Entry 的 `before_submit` 链长度 ≤ 1，绝不是 4。**

具体拆成三条独立可证伪的：

1. `doc_events["*"]["before_submit"]` 为**空**；
2. `doc_events["Stock Entry"]["before_submit"]` 为**空**；
3. 控制器 `StockEntry`（含 MRO 上游 `StockController` / `AccountsController`）
   **不定义** `before_submit`。

- 依据：`agenerp/` 里 `before_submit` **零命中**；WBS P3.3 那句「4 道 `before_submit`」
  的出处是 XM 的 `xm_pattern_demo/hooks.py`，已随 D-9 退役 ——
  **本仓说不清那 4 道是哪 4 道。**
- **证伪面**：三条里任意一条不成立，就把实得的链原样登记，并据此重述 P3.3 的验收。
- 无论证伪与否，都要往 `docs/masterplan/STATE.md` §3 追加一条事实行
  （只追加不改写），把「4 道在本仓不可判」连同实得链一起登记，由人裁定 P3.3 怎么改。

### H5 · savepoint 回滚在**进程内**仍成立（❌ 非盲，见 §0）

**预测：`rollback(save_point=…)` 之后，`counters_before` 与 `counters_after_rollback`
逐项相等**，其中包含 `series:MAT-STE-2026-`（即 Spike 05 说的「不产生单号空洞」）。

- **证伪面**：`counter_drift` 非空。
- 🔴 **这条结论有一个条件依赖，必须连着读**：探针把 `frappe.db.commit` 打了桩**并拦截**
  （`payload.py` 纪律 2）。因此 H5 只在 **H1 为 0** 时才是无条件的；
  H1 一旦非 0，H5 的「成立」就是打桩造出来的，不是站点的性质。

### H6 · 前提 0：我们的通道**够不着**这套语义（❌ 非盲，见 §0）

**预测：一条连接开的 savepoint，另一条连接 `ROLLBACK TO SAVEPOINT` 会报错。**

- 这是「够不着」的**直接**证据。工具层是跨 HTTP 调用的：`doc.submit` 一次请求、
  后置断言求值另一次请求，两次请求两条连接。
- `frappe/app.py::sync_database` 的 per-request commit 是**第二层**理由：
  即便同一条连接，POST 在响应返回之前就 commit 了，savepoint 也已经没了。
- **证伪面**：`cross_connection_savepoint_visible == true`。
- 若如预测成立 ⇒ 阶段 D 走 `abort_before_side_effect` 那一支，
  §7.1 的 savepoint 段**不删原文、只加时点限定**。

### H7 · 站点指纹会咬人

**预测：把 `Bin(HRD-PACK-5K, 成品仓 - HRD).actual_qty` 从 1010 改成 1011 之后，
`--verify-site` 退非 0，且报红的那一项逐字点名 `EXPECTED_BACKLOG_QTY`；还原后重新全绿。**

- **证伪面**：变异之后指纹**照样全绿** ⇒ 指纹没牙，**整条探测作废**，
  不许用「大概是指纹太严/太松」解释（plan 坏消息分支表第 3 行）。

---

## 2. 探测**不**回答什么

一条判据有义务先说清自己名字之外的边界。本次探测：

- **不测 REST 面上真提交单据会怎样。** 前提 0 若成立，那样测等于往站点上写脏数据去
  证明一件已经从源码上确定的事。
- **不测别的 DocType 的提交路径。** 只测 Stock Entry 两个场景。
  `before_submit_chain` 那一段**静态**枚举了四个 DocType，但只有 Stock Entry 有实跑轨迹。
- **不测并发。** 单进程、单事务。
- **不测客户站点。** 结论绑定在「本仓这个站点此刻的配置」上，见 H3 的边界句。
