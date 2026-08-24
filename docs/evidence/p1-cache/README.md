# 前缀缓存在本项目端点上的首次实测（P1.7 第 2 个 plan，2026-08-25）

本目录是 plan
[`2026-08-25-0554-1-prompt-cache-accounting.md`](../../plans/p1-insight/2026-08-25-0554-1-prompt-cache-accounting.md)
Phase 4 的落盘证据：**账本记全端点自报的 prompt 侧细分 `cached_tokens`，并在本项目自己的端点上测出这个数。**

## 一句话结论

> **本项目端点上，`qwen3.6-plus` 的一次 10 轮解释里，
> 前缀缓存命中 token 逐次全为 `0` —— 而且端点在 `prompt_tokens_details` 里
> 根本没有报 `cached_tokens` 这个键。**

**这是一个负结果，而负结果同样有价值。** 它恰恰证伪了
[`model-management.md`](../../architecture/model-management.md) §12.2 那句
从 Spike 02（别的栈、别的站点、别的题）搬来的话在本项目上的直接适用性 ——
在本项目自己的端点上，**前缀缓存今天一个 token 都没省下来**。

⚠️ **不许把它读成「所以解释 Agent 在经济上不成立」**。§12.2 那句是**上位结论**，
一次实测（一道题、一个模型、一次运行）不足以推翻它，也不足以证实它。
两个数**不是同一个量，不得互相佐证**（D-16）。

## 逐次实测（10 次模型调用）

| index | outcome | `prompt_tokens` | `cached_tokens`（解析值） | `endpoint_cached_tokens` | 端点报了 `prompt_tokens_details` | 其中含 `cached_tokens` 键 |
|---|---|---|---|---|---|---|
| 1 | tools | 1,054 | 0 | 0 | ✅ | ❌ |
| 2 | tools | 3,278 | 0 | 0 | ✅ | ❌ |
| 3 | tools | 3,407 | 0 | 0 | ✅ | ❌ |
| 4 | tools | 3,588 | 0 | 0 | ✅ | ❌ |
| 5 | tools | 3,733 | 0 | 0 | ✅ | ❌ |
| 6 | tools | 6,719 | 0 | 0 | ✅ | ❌ |
| 7 | tools | 6,876 | 0 | 0 | ✅ | ❌ |
| 8 | answer | 7,415 | 0 | 0 | ✅ | ❌ |
| 9 | tools | 8,422 | 0 | 0 | ✅ | ❌ |
| 10 | answer | 11,851 | 0 | 0 | ✅ | ❌ |

**汇总**：`prompt 56,343 · completion 6,770 · reasoning 3,806 · cached 0 · total 63,113`，
`stopped = answered`、`accepted = true`、`elapsed = 124.3s`、失控闸未触发（`runaway_events` 为空）。

⚠️ **最后两列是两件事，不许合并成一件**（这正是 D2 的残余风险「`0` 有两个含义」在实测中落地的样子）：

- 端点**报了** `prompt_tokens_details` —— 十次都报了；
- 但那个子对象的键集**逐次恒等于 `{"text_tokens"}`**，**没有 `cached_tokens` 这个键**。

所以本次的 `cached = 0` 不是「端点说命中了 0 个」，而是「**端点根本没说**」。
按 D2 写死的口径，`usage` 在而字段缺 ⇒ 解析值与 `endpoint_cached` 都记 `0`。
**原始子对象已逐次原样落进 `live-run-01.json` 的 `prompt_tokens_details_raw`**，
读者可以人工复核这一点，不必相信本文的转述。

⚠️ **与 `docs/evidence/p1-answer-judge/` 的 48 个回包不同，照实记**：那三份证据里
`prompt_tokens_details` 是 `{"cached_tokens": 0, "text_tokens": N}` ——
**键在、值为 0**。本次是**键都不在**。两者都得出 `cached = 0`，但成因不是一回事。
本目录**不解释这个差异**（模型不同、时间不同、端点侧配置不可见），**不猜根因**。

## 这一跑**证明了什么、没证明什么**（§6.1 的举证责任，跑之前就写死的）

**没证明**（必须逐字写出来，不许含糊）：

> **活端点证据在这一支上不承担「记全了」的举证责任。**
> 逐次 `cached_tokens` 全为 0 时，每一次的 `cached_matches_endpoint` 都是 `0 == 0 → True`，
> **一个把 `cached` 恒写 0 的假实现产出的证据文件与真实现逐字节相同。**

「记全了」这一条由 `tests/unit/test_prompt_cache_accounting.py` 的两条判据**单独承担**：

- ①（回包 `prompt_tokens_details.cached_tokens: 1024` ⇒ `Usage.cached == 1024`）；
- ⑧（端点报 100 而解析成 0 ⇒ `cached_matches_endpoint` 为 `False`）。

同理，**H1（第 1 次 == 0）与 H4（`cached ≤ prompt`）在这一支下恒真，不构成证据。**

**证明了**：

- **链路是通的且账目对得上**：`total_matches_endpoint` **10/10**、
  `reasoning_matches_endpoint` **10/10**、`cached_matches_endpoint` **10/10**，
  `cost_ledger.total` 与 `ConversationSession.usage_total` **逐项相等**
  （两处账无漂移），`total = prompt + completion` 口径未被 `cached` 污染。
- **本项目端点上今天没有前缀缓存可用**（至少：没有被上报）。这是本仓关于这个问题的
  **第一个自己的观测样本** —— 此前是 0 个。

## 与 `p1-cost/live-run-01.json` 的关系

同一道题、同一个模型（`qwen3.6-plus`），但**是两次不同的解释**：那次 8 次调用 / prompt 53,041，
本次 10 次调用 / prompt 56,343。**不作优劣比较**（本 plan 没做任何成本优化，D-16）。
⚠️ 那一跑给的 `doctypes` 清单是 8 个但**具体是哪 8 个没有落进它的证据文件**，
本跑给的 8 个逐字落在 `live-run-01.json` 的 `doctypes` 键里 ——
**两跑的开场注入面因此不保证相同**，这一条照实记，不假装可比到底。

## 复跑口径

一次性脚本**不进仓**（照 P1.4 / P1.7 先例）。它做的事就一件产品代码之外的事：
在 `explain(transport=…)` 上包一层**记录型 transport**，把每次回包的原始 `usage` 子对象留下来
—— `CallEntry` / `CallLedger` / `ExplainTrace` 的 `as_dict()` 都不带端点原始 usage 子对象，
`Reply.raw` 也不向 `ExplainResult` 传递，**靠账本导出面拿不到 `prompt_tokens_details`**。
形先例是 `agenerp/judging/judge.py` 的 `Verdict.endpoint_usage`。**产品代码为此一行都没改。**

```bash
set -a; . ./.env; . ~/.config/agenerp/secrets.env; set +a
export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080
export AGENERP_ADMIN_PASSWORD=<本地 compose 的 Administrator 口令>
export AGENERP_LLM_BASE_URL="$DASHSCOPE_BASE_URL" \
       AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY" \
       AGENERP_LLM_MODEL=qwen3.6-plus
```

⚠️ 凭据在 `~/.config/agenerp/secrets.env`（0600，仓库目录之外），**绝不进 git、绝不打印进日志**。
落盘前脚本逐个环境变量扫过产物，**本目录的 JSON 已复核无任何凭据字样**。

⚠️ **只调只读工具，一条业务数据都没写**（P1 是 ② 端只读）。
