# P3.2 · 回滚前提探测（本仓实测，2026-08-29）

> 站点 `frontend` · **frappe 15.118.0 / erpnext 15.119.3**（容器内实读；
> plan 与既有文档多处把 frappe 也写成 15.119.3，那是 erpnext 的版本号）
> 设施 `tools/experiments/p3_rollback/` · 预测 [`HYPOTHESES.md`](./HYPOTHESES.md)（跑之前单独 commit `b601947`）
> 原始结果 [`premises.json`](./premises.json) · [`mutation-check.json`](./mutation-check.json)

## 0. 一句话结论

**§7.1 那套 savepoint 回滚语义在本仓**进程内**仍然成立、逐项复现（含「不产生单号空洞」）；
而我们的工具层**够不着它** —— 不是三个前提哪一条不成立，是它们之前还有一个前提 0。**

---

## 1. 前提 0 🔴 —— 本次探测最重要的一条，且它**不在**原来那张三前提表里

工具层是**跨 HTTP 调用**的：`doc.submit` 是一次请求，后置断言求值在另一次。
「入口开 savepoint、后置不成立时回滚」要成立，savepoint 得跨得过这两次请求。它跨不过：

| 腿 | 实测 | 出处 |
|---|---|---|
| ① 跨连接不可见 | 一条连接开的 savepoint，另一条连接 `ROLLBACK TO` 报 **`(1305, 'SAVEPOINT p3_cross_connection_probe does not exist')`** | `premises.json` → `measurement.premise_0.cross_connection_error` |
| ② 就算同一条连接也已经晚了 | `POST` ∈ `UNSAFE_HTTP_METHODS`（实得 `['DELETE','PATCH','POST','PUT']`），`sync_database` 在响应返回前 `frappe.db.commit()` | 容器内 `frappe/app.py:414` 起（`inspect.getsourcelines` 实取） |

①是「够不着」的**直接**证据，②说明「而且它还提前 commit 了」。**两条都成立，且互相独立。**

⇒ **写契约的 `on_violation` 在 REST 面上只能是 `abort_before_side_effect`。**
`rollback_and_report` 不是「难实现」，是**在这个通道上没有可回滚的对象**。

## 2. 三个前提逐条实测（两个场景：当日 / 倒填 2026-01-05）

| # | 前提 | 当日 | 倒填 | 判 |
|---|---|---|---|---|
| 1 | 提交路径不自行 `db.commit()` | **0 次** | **0 次** | ✅ 成立 |
| — | 附加：提交路径不发裸 `COMMIT` SQL | **0 条** | **0 条** | ✅ 成立 |
| 2 | 提交路径不 `enqueue` 后台任务 | **0 次** | **0 次** | ✅ 成立，**但见 §3** |
| 3 | 无事务外副作用 | `sendmail` 0 · `evaluate_alert` 0 | 同左 | ✅ 成立（**限本站点此刻配置**） |

**前提 3 只记条数是不够的**，所以事务边界上的回调**逐个点名**了：

| 边界 | 当日 | 倒填 | 是什么 |
|---|---|---|---|
| `before_commit` | 0 | 0 | — |
| `after_commit` | 9 | 17 | `frappe.clear_document_cache.<locals>.clear_in_redis` ×8/×16 + `frappe.realtime.flush_realtime_log` ×1 |
| `after_rollback` | 9 | 17 | `clear_in_redis` ×8/×16 + `frappe.realtime.clear_realtime_log` ×1 |

**两边对称**：每一个挂在 `after_commit` 上的缓存失效，`after_rollback` 上都有对应的一条。
⇒ 本站点此刻**没有任何回滚回不掉的事务外动作**。
⚠️ **边界照实说**：站点上 `Workflow` 0 · `Webhook` 0 · `Server Script` 0 · `Client Script` 0，
`Notification` 2 条分别挂 `Material Request` 与 `Fiscal Year`（**都不是 Stock Entry**）。
装了 Webhook 的客户站点上，同一份代码的答案不同 —— 所以写契约的 `side_effects`
必须**逐个声明**，不能拿这次的 0 去推断。

## 3. 🔴 倒填**真的**触发了 `Repost Item Valuation` —— `open-questions.md:92` 那条缺口这次测到了

| | 当日 | 倒填 |
|---|---|---|
| `Repost Item Valuation` 行数（提交后） | 0 | **1** |
| `enqueue` 次数 | 0 | **0** |

倒填新增的那一行：`status='Queued'` · `based_on='Item and Warehouse'` ·
`posting_date='2026-01-05'` · `item_code='HRD-CELL-280'` · `warehouse='原料仓 - HRD'`。

**这件事的形状与「前提 2 不成立」不同，别混成一件事**：重估值**不是**在提交路径上入队的，
它是提交路径上**插进去的一行单据**，由 scheduler 事后捡走。因此：

- 在**进程内 savepoint** 里，它跟着回滚掉了（1 → 0，见 `counters_after_rollback`）；
- 在 **REST 面**上，POST 提前 commit（§1 ②）⇒ **那一行会被提交下去**，
  而后置断言此刻还没求值。⇒ **一个已提交的、给异步消费者的工作项。**

这是前提 0 之外，`rollback_and_report` 在 REST 面上够不着的**第二个**具体对象。

⚠️ 本站点 `is_scheduler_inactive() == True`、`tabScheduled Job Log` 0 行，所以这次探测里
**没有人去捡那行单据**。「重估值本身有没有事务外副作用」**仍未测到** ——
`open-questions.md` B.1 那条风险只被收窄，**没有排除**。

## 4. A3 · 「4 道 `before_submit`」在本仓**不可判**（WBS P3.3 验收条款）

静态枚举，规则逐字照 `frappe/model/document.py:1367-1377` 的 `composer`
（控制器自己的方法 + `doc_events[doctype]` + `doc_events['*']`）：

| DocType | 控制器定义 `before_submit`？ | `doc_events[doctype]` | `doc_events['*']` | **链长** |
|---|---|---|---|---|
| Stock Entry | ❌ | `[]` | `[]` | **0** |
| Delivery Note | ❌ | `[]` | `[]` | **0** |
| Sales Invoice | ✅ `SalesInvoice.before_submit` | `[]` | `[]` | **1** |
| Purchase Invoice | ✅ `PurchaseInvoice.before_submit` | `[]` | `[]` | **1** |

**没有任何一个 DocType 是 4。** 本仓 `agenerp/` 里 `before_submit` 零命中；
WBS P3.3 那句「不绕过 4 道 `before_submit`」的出处是 XM 的 `xm_pattern_demo/hooks.py`，
已随 D-9 退役 ⇒ **仓里说不清那 4 道是哪 4 道**。已按 plan 往 `STATE.md` §3 追加事实行，
P3.3 验收怎么重述**由人裁**。

## 5. savepoint 语义在**进程内**的复现

两个场景的 `counters_before` 与 `counters_after_rollback` **十项逐项相等**，`counter_drift` 空：
`Stock Entry` 4→5→4 · `Stock Ledger Entry` 10→11→10 · `GL Entry` 18→20→18 ·
`Version` 17→18→17 · `Repost Item Valuation`（倒填）0→1→0 ·
**`tabSeries.current` 4→5→4**（Spike 05 说的「不产生单号空洞」，本仓复现）。

🔴 **这条结论有一个条件依赖，必须连着读**：探针把 `frappe.db.commit` 打了桩**并拦截**
（`payload.py` 纪律 2 —— 前提 1 若不成立，放行就等于在站点上留一张真提交的单据）。
因此 §5 只在**前提 1 实测为 0** 时是无条件的。前提 1 实测确为 0（§2），
即那个桩**从未触发过**，所以这次它是无条件的 —— 但换一个 DocType 要重新走这条推理。

## 6. 三层防线的实得值

| 层 | 实得 |
|---|---|
| ① 备份 | `20260829_085059-frontend-database.sql.gz` 868.9 KiB，exit 0 |
| ② 指纹 | 跑前跑后 **32 项逐行文本相等**，两次都 exit 0 |
| ③ 🔴 变异先行 | `Bin(HRD-PACK-5K, 成品仓 - HRD).actual_qty` 1010 → 1011 ⇒ 指纹**退非 0** 并逐字点名 `❌ … expected = 1010.00（出处：agenerp.seed.checks.EXPECTED_BACKLOG_QTY）`；还原后重新 32/32 全绿 |

③见血了 ⇒ ②的「全绿」含信息。探测结束后独立复跑：`Stock Entry` 4 · `GL Entry` 18 ·
`SLE` 10 · `Repost Item Valuation` 0 · `tabSeries.current` 4 · 指纹 32/32。**站点干净。**

## 7. 预测记分（对照 [`HYPOTHESES.md`](./HYPOTHESES.md)，**含未命中**）

| # | 盲？ | 预测 | 实测 | 判 |
|---|---|---|---|---|
| H1 | ✅ | 前提 1 两格各 0 次 | 0 / 0 | **中** |
| H2 | ✅ | 倒填格 `enqueue ≥ 1` **且** RIV 新增 ≥ 1 行 | `enqueue` **0**；RIV **+1** | 🔴 **半错** —— 见下 |
| H3 | 🟡 | `sendmail` 0 · `evaluate_alert` 0 · webhook/server-script 被派发但无外部动作 | 0 · 0 · 派发 56/66 次、0 行配置 | **中** |
| H4 | ✅ | 链长 ≤ 1，绝不是 4 | 0 / 0 / 1 / 1 | **中** |
| H5 | ❌ 非盲 | 逐项相等含 series | `counter_drift` 空 | 中（**不计证据强度**，见 HYPOTHESES §0） |
| H6 | ❌ 非盲 | 跨连接够不着 | 报 1305 | 中（**不计证据强度**） |
| H7 | ✅ | 指纹会咬人并点名 `EXPECTED_BACKLOG_QTY` | 逐字点名 | **中** |

🔴 **H2 的那一半错得有信息量，照实记**：我预测重估值走 `enqueue`，实测它走**插一行单据**。
两者在前提 2 下的判定结果相同（都是 0 次 enqueue），**但在 REST 面上的后果不同** ——
`enqueue` 的任务会随进程结束而无主，一行 `status='Queued'` 的单据会**留在库里等 scheduler**。
把它们混成一件事，写契约就会漏掉 §3 那个「已提交的异步工作项」。

## 8. 这次探测**不**回答什么

- **不测 REST 面上真提交单据会怎样** —— 前提 0 已从源码 + 跨连接两条腿确定，
  再那样测等于为证明一件已确定的事往站点写脏数据。
- **只测了 Stock Entry 两个场景**；`before_submit_chain` 那段静态覆盖四个 DocType，
  但只有 Stock Entry 有实跑轨迹。
- **不测并发**（单进程单事务）、**不测客户站点**（见 §2 边界句）、
  **不测重估值本身**（scheduler 在本站点 inactive，见 §3 末）。

## 9. 顺带消掉的「已知未核实」（plan 末表六条）

| # | 项 | 实得 |
|---|---|---|
| 1 | `Customer.customer_details` / `Supplier.supplier_details` 的真实 fieldtype | 两者均 **`Text`**，`read_only=0` |
| 2 | `Item.description` 是否为空 | **非空**（如 `HRD-CELL-280` = `磷酸铁锂电芯 280Ah`），且 fieldtype 是 **`Text Editor`**（不是 `Text`）—— 载荷移植要按富文本处理 |
| 3 | `Stock Reposting Settings.item_based_reposting` | **1** |
| 4 | Workflow / Notification / Webhook / Server Script 行数 | **0 / 2 / 0 / 0**（另 `Client Script` 0） |
| 5 | `docker compose exec -T` 是否透传 stdin | **是**（`echo … \| docker compose exec -T backend python3` → `STDIN-OK`） |
| 6 | 两个满额模型是否声明 `tool_calling` | **是** —— `kimi-k3` 与 `glm-5.2` 在 `agenerp/routing/capabilities.py` 均为 `frozenset({"tool_calling"})` |
