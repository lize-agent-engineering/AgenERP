# 单次解释成本账本的活端点证据（P1.7，2026-08-24）

本目录是 plan
[`2026-08-24-2109-2-explain-cost-accounting.md`](../../plans/p1-insight/2026-08-24-2109-2-explain-cost-accounting.md)
Phase 3 的 **H5**（活端点上账目逐次对得上端点自报的数）的落盘证据。

**只有一跑。** plan Non-Goal 4 与 §7 Phase 3 写死了「**只跑一次**」——
多次跑、算分布是**成本采样实验**，属另一个 plan（D-16 同一条纪律）。

⚠️ **本目录不是 P1.4 那份证据的替代**：
[`docs/evidence/p1-explain/`](../p1-explain/) 记的是 P1.4 的控制循环那一跑，
本目录记的是 P1.7 的**账本**这一跑，两跑是两次不同的解释，数字不可互推。

## `live-run-01.json` 怎么读

| 键 | 内容 |
|---|---|
| `model` / `task_class` | 这一跑的模型与任务类目（由 `route()` 挑出，**不静默降级**） |
| `question` | 与 P1.0 入口关口实验**逐字相同**的那道题（`tools/experiments/p1_entry_gate/question.md`），取它是为了与 P1.4 那一跑可比，**不是为了重跑那个实验** |
| `answer` / `accepted` / `stopped` | ② 作答前门禁放行的答案、判定面、停止原因 |
| `cost_ledger` | **H5 的判定面**：`agenerp/explain/ledger.py` 产出的产品制品。`entries[]` 每条 = 一次模型调用 |
| `usage_total_session` | `ConversationSession.usage_total`（P1.4 的既有载体）—— 与 `cost_ledger.total` 并列，用来看两处账有没有漂移 |
| `model_tool_calls` / `runaway_events` | 失控闸的计量与留痕（本跑**没有触发**） |
| `execute_calls` / `trace` | 结构化轨迹，与 P1.4 那份同形制 |

## H5 逐条对照（plan §6 写死的原文 → 实测）

| §6 的预测 | 实测 | 吻合 |
|---|---|---|
| 账本每条与端点自报的 `raw["usage"]` **逐次相等** | **8 次调用逐次成立**：`total_matches_endpoint` **8/8**、`reasoning_matches_endpoint` **8/8** | 吻合 |
| 三项均 > 0（D-11：推理模型 reasoning 必 > 0） | **8 条全部三项 > 0**，逐条 reasoning：142 / 255 / 288 / 41 / 1,008 / 922 / 181 / 261 | 吻合 |
| **不预测总量落在哪个区间**（roadmap 的 9.7 万–12.8 万与 P1.4 的 45,195 相差一倍以上，本 plan 两个都不当预期） | 实测 **prompt 53,041 · completion 5,538 · reasoning 3,098 · total 58,579**，**8 次模型调用** | 照实记，**不作优劣比较** |

⚠️ **`prompt + completion == total` 那种写法是恒真的**（`Usage.total` 就是这个计算属性），
证不了任何事。上表判的是**端点自报的 `total_tokens` 与
`completion_tokens_details.reasoning_tokens`**，不是 `Usage.total`。

⚠️ **不与任何数字作优劣比较**（plan §8 风险 ⑦）：本跑的 58,579 与 P1.4 的 45,195、
与 roadmap 记的 9.7 万–12.8 万，是**三次不同的解释**，本 plan 没做任何成本优化，
把它们并排读成「变便宜了/变贵了」是错的。实测多少记多少（D-16）。

## 这一跑**证明了什么、没证明什么**（不许含糊）

**证明了**：

- **账本是产品制品，不是一次性脚本的产物**：`cost_ledger` 由 `agenerp/explain/ledger.py`
  在任何一次解释上产出，不需要外挂脚本。P1.4 那次的 `per_call_ledger[]` 只活在证据文件里。
- **账目与端点自报的数在活端点上逐次对得上**（8/8 × 两项）。这一条是**独立核对** ——
  数字来自真实回包，不是重放夹具（重放那一份在
  `tests/unit/test_explain_cost_ledger.py` 的 H2a，那里的期望值与夹具同源，
  **不算独立核对**）。
- **三项分开记这件事在活端点上有意义**：本跑 reasoning 3,098 占 completion 5,538 的
  **56%**，单条最高那次（#5）1,008 / 1,066 = **95%**。折掉这一位，账就按「输出 1,066」去算。
- **两处账在这条路径上没有漂移**：`cost_ledger.total == usage_total_session`
  （本跑没有走异常出口，所以两者应当相等 —— 相等正是预期）。

**没证明**（照实写，不粉饰）：

- **异常出口的记账这一跑没有被走到**：本跑 `stopped == "answered"`，没有 `model-error`、
  没有熔断。那三条由 `tests/unit/test_explain_cost_ledger.py` 的 H1 与计数探针证明，
  **不由这一跑证明**。
- **失控闸这一跑没有被触发**：`model_tool_calls == 9`，远在默认上限 32 之下，
  `runaway_events` 为空。失控闸由 `tests/unit/test_explain_runaway_guard.py` 的 H4 证明，
  **不由这一跑证明**。⚠️ 反过来说，本跑也**顺带证实了默认上限没有误伤正常解释**：
  一次真实的、取证充分的解释只用了 9 次工具调用。
- **答案对不对不在本跑的判定面上**（plan Non-Goal 9）。
- **一跑不是成本分布**：单次采样说不出长尾，定阈值仍然需要采样计划（D-18 的翻案条件）。

## 与 P1.4 那一跑不同的两处，照实记

1. **② 作答前门禁这次被走到了拒绝路径**：`forced_continues` 有 **1** 条、`gate_checks`
   有 **2** 条（第一条 `failed` 非空：L3 要求的入库凭证还差 1 张没查）。
   P1.4 那一跑 `forced_continues` 为空。→ 本跑因此比那一跑多了一轮，
   `execute_calls` 从 8 变成 **9**，模型调用从 7 次变成 **8** 次。
   ⚠️ 这**不是**本 plan 改出来的行为差异 —— 本 plan 一个字没动 `gate.py`
   （Non-Goal 6），是模型这次第一遍没查全。
2. **`opening_request_count` 是 8，不是 P1.4 那次的 10**：本跑给的 `doctypes` 清单是 8 个。

## 复跑口径

一次性脚本**不进仓**（照 P1.4 的先例）。复跑需要：活站点（本地 compose，
`AGENERP_SITE=frontend` / `AGENERP_SITE_URL=http://127.0.0.1:18080`）+
`AGENERP_LLM_BASE_URL` / `AGENERP_LLM_API_KEY` / `AGENERP_LLM_MODEL`。
⚠️ 凭据在 `~/.config/agenerp/secrets.env`（0600，仓库目录之外），
**绝不进 git、绝不打印进日志或轨迹** —— 本目录的 JSON 已复核无任何凭据字样。

⚠️ **第一次尝试没跑完，照实记**：第一次调用在 10 分钟的执行超时上被掐断，没有产物；
原样复跑一次即成功（`elapsed_seconds = 102.0`）。**原因未定位，不猜根因**
（裁判规则 3：复跑不出来才记「不可复现」，这次复跑出来了，但两次的差异本目录不作解释）。
