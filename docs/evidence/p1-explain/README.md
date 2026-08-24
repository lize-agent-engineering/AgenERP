# 解释 Agent 控制循环的活端点轨迹（P1.4，2026-08-24）

本目录是 plan
[`2026-08-24-1755-1-explain-agent-and-evidence-gate.md`](../../plans/p1-insight/2026-08-24-1755-1-explain-agent-and-evidence-gate.md)
Phase 4 的 **H4**（活端点上跑得起来且账目对得上）的落盘证据。

**只有一跑。** 单次解释的成本量级已知，plan §8 风险 ⑤ 写死了「只跑一次；跑不了就照实记
『未验证』，不补跑、不采样」——多次采样是实验，属另一个 plan（D-16）。

## `live-run-01.json` 怎么读

| 键 | 内容 |
|---|---|
| `model` / `task_class` | 这一跑的模型与任务类目（由 `route()` 挑出，**不静默降级**） |
| `question` | 与 P1.0 入口关口实验**逐字相同**的那道题（`tools/experiments/p1_entry_gate/question.md`），取它是为了可比，不是为了重跑那个实验 |
| `answer` / `accepted` | ② 作答前门禁放行的那个答案。`accepted` 是判定面 |
| `usage_total` | 三项分开记（`prompt` / `completion` / `reasoning`），走 `ConversationSession.usage_total` |
| `per_call_ledger[]` | **H4 的账目核对面**：每次调用的 `usage` 对上端点自报的 `raw["usage"]` |
| `trace` | 结构化轨迹：`tool_calls[]` / `gate_checks[]` / `forced_continues[]` / `breaker_events[]` / `execute_calls` |
| `session_actions[]` | 落进 `ConversationSession` 的已执行动作（本跑只有开场注入那一条） |

## H4 逐条对照（plan §6 写死的原文 → 实测）

| §6 的预测 | 实测 | 吻合 |
|---|---|---|
| `usage.prompt > 0` | 40,885 | 吻合 |
| `usage.completion > 0` | 4,310 | 吻合 |
| `usage.reasoning > 0` | 2,784 | 吻合 |
| `usage.prompt + usage.completion == raw["usage"]["total_tokens"]` | **七次调用逐次成立** | 吻合 |
| `usage.reasoning == raw["usage"]["completion_tokens_details"]["reasoning_tokens"]` | **七次调用逐次成立** | 吻合 |

⚠️ **`prompt + completion == total` 那种写法是恒真的**（`Usage.total` 就是这个计算属性），
证不了任何事。上表判的是**端点自报的 `raw["usage"]`**，不是 `Usage.total`。

## 这一跑**证明了什么、没证明什么**（不许含糊）

**证明了**：

- 循环在活站点 + 活端点上跑得通：开场注入 10 次 `has_permission` → 模型七轮 →
  **8 次 `execute`**（`doc.get` ×5、`doc.links` ×1、`query.read` ×2）→ 作答 → ② 门禁放行。
- **① 工具前置那一面在活站点上真的起作用**：两次 `query.read`（`ANSWERING_TOOLS` 之一）
  都发生在 L1/L2 已满足之后，`ok=True`。
- **L3 在真实数据上抓到了它被设计来抓的那件事**：答案报了成品仓的 1,010 台，门禁据此
  从库存流水反查出两张入库凭证 `MAT-SCR-2026-00001`（外协入库）与 `MAT-STE-2026-00003`
  （自制入库），模型对两张都调过 `doc.get`，因此放行。**那张外协单正是 P1.0 记录的
  「沿订单查得再深也看不见」的那一张。**
- 账目对得上端点自报的数（上表）。

**没证明**（照实写，不粉饰）：

- **② 门禁的拒绝路径这一跑没有被走到**：`forced_continues` 为空，模型第一次作答就已取证充分，
  `gate_checks` 只有一条且 `failed` 为空。「拦得住单跳」这件事由
  `tests/unit/test_evidence_gate_single_hop_body.py` 的判据证明，**不由这一跑证明**。
- **熔断这一跑没有被触发**：`breaker_events` 为空（Administrator 身份不会撞 403）。
  H3 由 `tests/unit/test_explain_loop.py` 的判据证明。
- **答案对不对不在本跑的判定面上**。H4 逐字「不预测答案对错」；这道题的正确率归 P1.0，
  本 plan 不重跑那个实验、不引用它的数字作结论。

## 一处与 plan 预期不同的数字，照实记

plan §8 风险 ⑤ 引 roadmap P1.7 节写着「P1.0 实测单次解释 **9.7 万–12.8 万 token**」，
本跑是 **45,195 token**，**低于那个区间**。不修饰成「优化了」——本 plan 没做任何成本工作
（Non-Goals 1），差异的成因（提示词形状、轮数、模型这一次的取证路径）**没有被测量**，
成本记账归 P1.7。这里只记下这个数与它和预期的差。

## 怎么复跑

一次性运行器写在会话 scratchpad，**不进仓**（它不是产品件，也不是判据）。复跑需要：

```bash
set -a; . ~/.config/agenerp/secrets.env; set +a      # DASHSCOPE_API_KEY
export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080
export AGENERP_ADMIN_PASSWORD=<本地 compose 的 Administrator 口令>
export AGENERP_LLM_BASE_URL="$DASHSCOPE_BASE_URL" \
       AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY" \
       AGENERP_LLM_MODEL=qwen3.6-plus
```

运行器做的事就三步：`client_from_env("frontend")` → `route("explain", models=KNOWN_MODEL_PROFILES,
requested="qwen3.6-plus")` → `ExplainLoop(adapter=..., client=..., doctypes=<10 个候选>,
max_turns=12).run(question)`。

⚠️ **两处照实说明**：

1. 走的是 `ExplainLoop`，不是导出面的 `explain()`。两者的装配**完全相同**
   （`explain()` 内部就是 `route()` + `ExplainLoop(...).run(...)`），分开只为一件事：
   在 `adapter.chat` 外面包一层把每个 `Reply` 留下来 —— **`Reply.raw` 不进 `ExplainResult`**，
   而 H4 的账目核对要的正是它。产品行为一个字没改（② 门禁走默认值 `True`）。
2. 开场注入给了 **10 个候选 DocType**（`doctypes=[...]`）而不是走发现式路径。
   理由与 `permission_scope` 的文档一致：给了候选集就只探候选集，一个元数据枚举请求都不发；
   这也把注入代价框在 10 次请求。**这是调用方的选择，不是循环的默认。**

## 凭据

**这份产物里没有任何凭据。** key 只从环境变量读，不打印、不写进 JSON
（`docs/masterplan/04-RUNBOOK.md` §5.6：真凭据一律放仓库目录之外）。
