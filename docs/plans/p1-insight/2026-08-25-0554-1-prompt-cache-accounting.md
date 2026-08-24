# prompt 侧的成本细分：`cached_tokens` 进账本，前缀缓存在本项目端点上的首次实测

> Plan Status: completed
> Mission: p1-insight
> Work Item: 9. **单次解释成本记账**（记账但不拦截，D-18）（P1.7）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个 plan 预算，本 plan 用掉第 2 个）
> Last Reviewed: 2026-08-25
> Source: plan `2026-08-24-1457-1-model-routing-v0.md` §9 的 `Deferred But Adjudicated`
> 第三条「**前缀缓存与单次解释成本上限**」，其重开事件逐字为「**P1.4 解释 Agent 落地**」，
> 其 `Successor Required` 一行**原文逐字**是 ``yes``（P1.7 · 🔴 `tests/gates/test_explain_cost_ceiling.py`）——
> 该重开事件**已触发**（工作项 6 `done`，`agenerp/explain/` 在盘上）。
> ⚠️ 其中 🔴 `tests/gates/test_explain_cost_ceiling.py` **已由 D-18 废止**
> （`DECISIONS.md` D-18「为什么原设计站不住」一行逐字：「原判据 `test_explain_cost_ceiling.py` 要一个阈值……」），
> 该文件**在 `tests/gates/` 下不存在**（起草期实读：6 个门禁文件，无此名）。
> 本 plan **不创建它、不声称满足它、不设任何阈值**（Non-Goals 1）·
> `docs/architecture/model-management.md` **§12.2**（标题逐字「**成本：前缀缓存是可行性前提，不是优化项**」）·
> `docs/backlog/p1-insight-roadmap.md`「P1.7 已按 D-18 改为记账但不拦截」一节逐字
> 「**不许退化成「跑通就算」**：要能挡住「只记 completion 不记 reasoning」的假实现」
> Related: [`2026-08-24-2109-2-explain-cost-accounting.md`](./2026-08-24-2109-2-explain-cost-accounting.md)（P1.7 本体，`completed`；本 plan 改的正是它交付的账本）·
> [`2026-08-24-1457-1-model-routing-v0.md`](./2026-08-24-1457-1-model-routing-v0.md)（P1.1，`completed`；本 plan 的 Deferred 出处，且要动它的 `Usage` 导出面）·
> [`2026-08-24-1457-2-context-layer-v0.md`](./2026-08-24-1457-2-context-layer-v0.md)（P1.2，`completed`；本 plan 要动它的会话落盘形状，见 D3）
> Audit: required
> Execution Order: **1 / 1**（本批只有这一个 plan）

## 0. 执行前必做：重取基线

**起草期读到的一切都可能在开工时已经变了。** 下面七处**逐条重读**，把实读值填进 §0.1，
与起草期不一致的**照实记、不改起草期原文**。

1. `git log -1 --format=%H` 与 `git status --porcelain`
   （起草期：`f14d5765940d0aff4c2a1333cf143d2a753c5c67` / 无输出。
   **判据收窄成：除本 plan 文件外无输出**）
2. `docs/architecture/module-boundaries.md` 的 `7.x` 族**当时的最大节号**
   （起草期 **§7.16**，本 plan 预定落 **§7.17**；被占用就顺延，**以开工时实读为准**）
3. 七条基线命令的开工数字（起草期实读见 §1.1）
4. `find agenerp -name '*.py' | wc -l`（起草期 **56**；它决定 `tests/routing` 的参数化条数，见 §6 H7）
5. `~/.config/agenerp/secrets.env` 是否存在且含 `DASHSCOPE_API_KEY`（起草期：存在、`0600`）
6. `docs/evidence/p1-answer-judge/` 三份证据里 `cached_tokens` 的取值分布。
   ⚠️ 三份是**互不相同的数据**，不是同一批的分解：`all.json` **24** 条 · `stability.json` **18** 条 ·
   `controls.json` **6** 条，合计 **48** 个值，起草期实读**全部为 `0`**
7. `docs/evidence/p1-cost/live-run-01.json` 的 `usage_total_session`
   （起草期实读：`{prompt: 53041, completion: 5538, reasoning: 3098, total: 58579}`，8 次调用）

### 0.1 执行期重取基线的**实读结果**

<!-- 开工时填。与起草期不一致的照实记，不改起草期原文。 -->

执行期实读时间：2026-08-25。

| # | 重读项 | 实读值 | 与起草期 |
|---|---|---|---|
| 1 | `git log -1 --format=%H` / `git status --porcelain` | `9dea949ba1b19915baa50de5fcb1961cb75010e6` / **无输出**（本 plan 文件已随 `9dea949` 入库，工作区干净） | **不一致但更严**：起草期记的 `f14d576` 是**起草前**的 sha，本 plan 文件随后由 `9dea949` 提交；判据「除本 plan 文件外无输出」**满足**（实际是完全无输出） |
| 2 | `7.x` 最大节号 | **§7.16**（`module-boundaries.md:2557`「洞察 Agent **归因**的首次活端点实跑…」） | 一致 ⇒ 本 plan 落 **§7.17**，不顺延 |
| 3 | 七条基线命令 | ①`exit 0` `门禁 11 项：预期红 0，绿 11，跳过 0` · ②`exit 0` `614 passed` · ③`exit 0` `151 passed` · ④`exit 0` `81 passed, 12 skipped` · ⑤`exit 0` `167 passed, 1 skipped` · ⑥`exit 0` `53 passed` · ⑦`exit 0` `10 passed` | **逐条一致** |
| 4 | `find agenerp -name '*.py' \| wc -l` | **56** | 一致 |
| 5 | `secrets.env` | 存在，`-rw-------`，含 `DASHSCOPE_API_KEY`（`grep -c` 得 1） | 一致 |
| 6 | 判定器证据里的 `cached_tokens` 分布 | `all.json` **24** 值 · `stability.json` **18** 值 · `controls.json` **6** 值 = **48** 个，**distinct 全为 `[0]`** | 一致（H2 的强先验仍成立） |
| 7 | `p1-cost/live-run-01.json` 的 `usage_total_session` | `{"prompt": 53041, "completion": 5538, "reasoning": 3098, "total": 58579}` | 一致 |

⚠️ 附加实读（H7 的前置）：`env \| grep AGENERP_LLM_` 得 **`AGENERP_LLM_MODEL=qwen3.6-plus` 一行**，
`AGENERP_LLM_BASE_URL` / `AGENERP_LLM_API_KEY` **未 export** ⇒ `tests/routing/test_live_endpoint.py` 仍 skip，
基线实读 `167 passed, 1 skipped` 与 H7 口径吻合。

## 1. Current Baseline（起草期逐条实读，非记忆、非转述）

### 1.1 七条基线命令（起草期 `f14d576`，工作区无输出）

| # | 命令原文 | 退出码 | 输出尾行 |
|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py` | **0** | `门禁 11 项：预期红 0，绿 11，跳过 0` / `✅ 与预期红名单完全一致` |
| ② | `python3 -m pytest tests/unit -q` | **0** | `614 passed in 2.16s` |
| ③ | `python3 -m pytest tests/contracts -q` | **0** | `151 passed in 0.07s` |
| ④ | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped in 0.08s` |
| ⑤ | `python3 -m pytest tests/routing -q` | **0** | `167 passed, 1 skipped in 0.46s` |
| ⑥ | `python3 -m pytest tests/context -q` | **0** | `53 passed in 0.07s` |
| ⑦ | `python3 -m pytest tests/experiments -q` | **0** | `10 passed in 0.03s` |

`missions/p1-insight.json` 的 `commands.test` 逐字是 ① `&&` ②，
因此**本 plan 的判据必须落在 `tests/unit`** 才进得了 `GATE_VERIFY`（沿用 P1.4 / P1.5 / P1.7 的做法）。

### 1.2 今天的账本记什么、不记什么（实读代码，不是读文档）

- `agenerp/routing/adapter.py:39-75` `Usage` **只有三项** `prompt` / `completion` / `reasoning`；
  `total` 是 `prompt + completion` 的 `@property`；`as_dict()` 出四个键。
  模块 docstring 逐字：「**`reasoning` 是 `completion` 的一个细分，不是第四个桶**」。
- `agenerp/routing/adapter.py:212-216` `usage_of()` **只解析** `completion_tokens_details.reasoning_tokens`，
  **完全没有读 `prompt_tokens_details`**。
- `agenerp/explain/ledger.py:41-59` `_endpoint_numbers()` 只取 `total_tokens` 与
  `completion_tokens_details.reasoning_tokens` 两个数；`CallEntry` 只有
  `endpoint_total` / `endpoint_reasoning` 两个端点自报字段，以及
  `total_matches_endpoint` / `reasoning_matches_endpoint` 两条比对属性。
- `agenerp/context/store.py:48-53` 会话落盘 `to_payload()` **写死三个键**
  `{"prompt", "completion", "reasoning"}`；`:110` 读回时逐键取。
  `tests/context/test_store.py:92` 断言 `set(usage_payload) == {"prompt","completion","reasoning"}`，
  `:86` 断言 `from_payload(to_payload(_session())) == _session()`（round-trip 相等）。

### 1.3 缺口是什么（一句话）

**端点每一次都在报 `prompt_tokens_details.cached_tokens`，本仓从头到尾一个字都没记。**

起草期实读 `docs/evidence/p1-answer-judge/all.json` 的一条原始回包（逐字）：

```json
"endpoint_usage": {"completion_tokens": 457,
 "completion_tokens_details": {"reasoning_tokens": 446, "text_tokens": 457},
 "prompt_tokens": 1334,
 "prompt_tokens_details": {"cached_tokens": 0, "text_tokens": 1334},
 "total_tokens": 1791}
```

`prompt_tokens_details.cached_tokens` **在回包里**，且它与 `completion_tokens_details.reasoning_tokens`
**形状完全对称**（一个是 prompt 侧细分，一个是 completion 侧细分）。本仓解析了后者，丢掉了前者。

### 1.4 授权来自哪里，以及为什么这不是「顺手优化」

⚠️ **先把不能声称的话说清楚**：`02-WBS.md` §4 P1.7 那一行的验收原文是
「每次调用的 token **三项分开记**（prompt / completion / **reasoning**）」+ 🔴 断言
「**三项都记了**、能按解释汇总、缺任一项即红」。
**第四项细分与前缀缓存实测不在那一行的字面验收范围内**，
而那一行的字面验收**今天已由 `2026-08-24-2109-2` 完整满足**。
因此本 plan **不声称**「P1.7 的验收没做完」。

**本 plan 的授权来自 P1.1 那份 plan 自己写死的 successor 指派**：
`2026-08-24-1457-1-model-routing-v0.md` §9 第三条 Deferred 逐字写着
`Successor Required: yes（P1.7 · …）`，重开事件逐字「**P1.4 解释 Agent 落地**」，
该事件**已触发**。挂工作项 3（P1.1）反而更差 —— P1.1 的验收是
`pytest tests/routing -q` 退 0 + 分档表落 `docs/architecture/`，与本 plan 的结果面不沾边。

**为什么它不是「顺手优化」**（AGENTS.md 禁止「与北极星无关的顺手优化」）——
两条理由，都不靠 WBS 那一行的字面：

- P1.7 已实测的一次真实解释（`docs/evidence/p1-cost/live-run-01.json`，起草期实读）：
  8 次调用，`usage_total_session = {prompt: 53041, completion: 5538, reasoning: 3098, total: 58579}`。
  **prompt 占 53041 / 58579 = 90.5%**，且逐次单调增长（1056 → 3280 → 3634 → 7140 → 7372 → …），
  因为每一轮都把整段对话重发一遍。
- **这 53,041 个 prompt token 里有多少是缓存命中，账本上一个字都没有。**
  缓存命中与未命中在多数计费口径下不同价，因此今天的成本记账
  在**占 90.5% 的那一栏上分辨不出贵与便宜** —— 与 roadmap 点名的
  「只记 completion 不记 reasoning」是**同一类失真**，只是发生在 prompt 侧。
  ⚠️ 这是**类比**，不是「P1.7 验收未满足」的断言（见本节开头）。

`docs/architecture/model-management.md` **§12.2** 的标题逐字是
「**成本：前缀缓存是可行性前提，不是优化项**」，正文逐字
「**没有前缀缓存，解释 Agent 在经济上不成立**」。
⚠️ 但那一节的数**全部来自 Spike 02**（`claude:sonnet`、别的站点、别的题），
按硬约束 ④（D-16）**只能作假设的来源，不能作结论的依据**。
本项目从未测过自己端点上前缀缓存是否生效 —— 本 plan 就是去测这一次。

### 1.5 已知会被这次改动碰到的地方（inventory，Minimum Rule 1 要求，不可省）

| # | 位置 | 今天是什么 | 本 plan 会怎样 |
|---|---|---|---|
| 1 | `agenerp/routing/adapter.py` `Usage` | 三项 | 加第四项 `cached`（prompt 侧细分，**不进 `total`**），见 D1 |
| 2 | `agenerp/routing/adapter.py` `usage_of()` | 只读 completion 侧细分 | 加读 `prompt_tokens_details.cached_tokens` |
| 3 | `agenerp/routing/adapter.py` `Usage.plus()` / `as_dict()` | 三项相加 / 四键 | 四项相加 / 五键 |
| 4 | `agenerp/explain/ledger.py` `_endpoint_numbers()` | 回两个数 | 回三个数（加 `endpoint_cached`） |
| 5 | `agenerp/explain/ledger.py` `CallEntry` | 两个 `endpoint_*` + 两条比对属性 | 三个 + 三条（加 `cached_matches_endpoint`） |
| 6 | `agenerp/context/store.py` `to_payload()` / 读回 | 写死三键 | 写四键，见 **D3**（这是本 plan 唯一跨出 P1.7 边界的改动，理由与残余风险在 D3） |
| 7 | `tests/context/test_store.py:92` | 断言键集恰为三键 | 改成四键，**并新增一条 `cached > 0` 的 round-trip 判据**（今天的 fixture `cached` 恒 0，改完不加这条等于没判） |
| 8 | `tests/routing/test_adapter.py:485` `PRODUCT_MODULES` + `:488` 的 `parametrize` | 决定条数的**只有这一处**（`:403` 那处 `rglob` 在一个函数体内，只贡献 1 条，不参与参数化） | **本 plan 不新增 `agenerp/**/*.py` 文件** ⇒ 条数应不变，见 §6 H7 |
| 9 | `agenerp/judging/judge.py:52` · `agenerp/explain/loop.py:387,524` | 转发 `usage.as_dict()` | 自动多一个键；无键集断言，**不改代码** |
| 10 | `tools/experiments/p1_entry_gate/llm.py` 的 `Usage` | **另一个 `Usage`**（实验设施自己的） | **一个字不动**（P1.1 §9 第一条 Deferred 逐字禁止，重开事件未触发） |
| 11 | `docs/evidence/**` 已有 JSON | 冻结产物 | **不重新生成、不回填**；本 plan 的新证据另落 `docs/evidence/p1-cache/` |
| 12 | **「三项 / 不是第四个桶」这句话的全部落点**，见下方 §1.6 —— 起草期用一条命令穷举，**不靠逐行记忆** | 全都只讲三项 | 逐处**改准**（Phase 2 的 `Fix` 项逐处点名）。⚠️ 这是**确认的 owner-doc / 声明漂移**，指南第 14 条**不可降级** |

### 1.6 「三项 / 不是第四个桶」漂移面的**穷举**（起草期实读，用命令定义，不用行号定义）

> **穷举命令**（Phase 4 的机械复核逐字复跑同两条）：
>
> - **grep-1**：`grep -rn "三项\|第四个桶" agenerp tools/experiments/p1_entry_gate docs/architecture/module-boundaries.md docs/architecture/model-management.md`
> - **grep-2**：`grep -rn "endpoint_total\|endpoint_reasoning" agenerp docs/architecture/module-boundaries.md`
>
> ⚠️ **不要只 grep「三项」** —— `endpoint_total` / `endpoint_reasoning` 那两处没有「三项」二字。
> ⚠️ **路径里必须带 `tools/experiments/p1_entry_gate`** —— 否则下表最后那一行「冻结面」永远产不出命中，
> Phase 4 那句「逐条标注『冻结面，不改』」就成了不可执行的话。
>
> **命中分三类，不是两类**（下表第三列即分类）：**改准** · **一个字不改** · **无关命中，不改**。
> 第三类**预先点名**，免得 Phase 4 在这些行上停机：
> `agenerp/seedsite.py:267`（成本三项 `raw_material_cost` / `operating_cost` / `total_cost`）·
> `agenerp/seedsite.py:870`（拟断言②的三项）· `agenerp/contracts.py:161`（`returns` 段三项）·
> 以及 grep-2 在 `agenerp/explain/ledger.py` 里命中的**代码标识符**行
> （`:68 :69 :75 :80 :81 :90 :91 :149 :155 :156` —— 那是字段名与赋值，不是文案，
> 随 Phase 2 的实现自然改，**不进本表逐行对照**）。

| 落点 | 起草期逐字 | 本 plan |
|---|---|---|
| `agenerp/routing/adapter.py:8` | 「token **三项**分开记」 | 改准（Phase 2 `Fix`） |
| `agenerp/routing/adapter.py:42` | 「`reasoning` … **不是第四个桶**」 | **保留原句**（它讲 completion 侧，仍然对），**另起一句**讲 `cached` 是 prompt 侧细分 |
| `agenerp/explain/ledger.py:9-11` | 「**三项** token 的口径归 P1.1」「不自己写**三项**加法」 | 改准 |
| `agenerp/explain/ledger.py:16` | 「`endpoint_total` / `endpoint_reasoning` 是端点自报的原始数字」 | 改准（加 `endpoint_cached`） |
| `agenerp/explain/ledger.py:124` | 「…**三项**记 0、`endpoint_*` 记 `None`」 | 改准（四项记 0） |
| `agenerp/context/session.py:13-17` | 「不自己写**三项**加法」「**不是第四个桶**」 | 改准（聚合折**四项**） |
| `agenerp/context/session.py:147` | 「自己写**三项**加法能算对，但会与 P1.1 分家」 | 改准 |
| `agenerp/context/store.py:48` | 「落 `prompt` / `completion` / `reasoning` **三项**」 | 改准（四项） |
| `agenerp/explain/loop.py:240` | 「**不自己写三项加法**」 | 改准 |
| `agenerp/context/doctype/agent_conversation_session.json` `turns` 的 `description` | 「每轮 token **三项**…**不是第四个桶**」 | 改准。⚠️ **只改这段自由文本**，`field_order` / 字段集 / `permissions` 一个字不动（L3 定性见 Phase 2） |
| `module-boundaries.md:347` | 「token **三项**口径」 | 改准 |
| `module-boundaries.md:421-425, 428`（**§7.7，P1.2 的落点节**） | 「不是第四个桶」「一份手写但算得对的**三项**加法」 | 改准 |
| `module-boundaries.md:911-912, 915, 934`（**§7.11，P1.7 的落点节**） | 「**三项** token 的口径归 P1.1」「`endpoint_total` / `endpoint_reasoning`」「**三项**记 0」 | 改准（§7.11 是本 plan 结果面内的连带修改，**不是越界**） |
| `module-boundaries.md:2535, 2598`（P1.5 的**执行记录**与 H4 对照表） | 「**三项** usage 全 > 0」 | ⚠️ **一个字不改** —— 那是**已发生实验的历史记录**，改它等于改历史（硬约束 ②）。Phase 4 复核时逐字标注「历史记录，不改」 |
| `model-management.md:57`（**§12.2 内的 D-18 那条 bullet**） | 「**三项** token 分开记、能按一次解释汇总」 | 改准。⚠️ **Non-Goals 5 冻结的只有「Spike 02 成本表」与「没有前缀缓存…」那句结论的措辞**，这一行**不在冻结面内** |
| `model-management.md:240`（模块职责表 `adapter.py` 那一格） | 「token **三项**分开」 | 改准 |
| `tools/experiments/p1_entry_gate/llm.py:40` · `loop.py:13` | 实验设施自己的 `Usage`，「**三项**分开记」 | ⚠️ **一个字不改**（Non-Goals 6 的冻结面，P1.1 §9 第一条 Deferred 逐字禁止） |

## 2. 一个结果面（Minimum Rule 4）

> **单次解释的成本账本记全端点自报的 prompt 侧细分，并用一次真实解释在本项目端点上测出这个数。**

实现（记账）与实测（那个数）是同一条行为契约的两半：不改账本就测不出来，
不实测就只是「多写了一个字段」——正是硬约束 ① 点名的「跑通就算」。

## 3. Goals / Non-Goals

### Goals

1. `Usage` 与账本记全 `cached`，口径与 `reasoning` **完全对称**（细分，不是第四个桶，**不进 `total`**）。
2. 端点自报值与解析值**两组分开留**，比对属性 `cached_matches_endpoint` 与既有两条同形态
   —— 这是能打红假实现的那一半（`prompt + completion == total` 那种恒真写法判了等于没判）。
3. 在本项目端点上**跑一次完整解释**，逐次记下 `cached_tokens`，与 §6 写死的假设逐条对照。
4. 落点节 `module-boundaries.md` **§7.17**（开工时以实读节号为准）记口径与实测数；
   `model-management.md` §12.2 **只加一条指针行**（见 Non-Goals 5）。

### Non-Goals

1. **不设阈值、不加任何拦截分支**（D-18 逐字）。账本改完仍然连一个「超了就……」的分支都没有。
2. **不做前缀重排 / 提示词改造 / 任何以「提高命中率」为目的的改动。** 本 plan 只**测量与记账**。
   没测出本项目自己的数之前谈优化，正是 D-16 禁止的那件事。
3. **不改 `total = prompt + completion` 的口径**，不改 `reasoning` 是 completion 细分这条。
4. **不做多次采样与成本分布**（P1.7 另一条 Deferred，重开事件「要用已记的账定阈值时」**未触发**）。
5. **不改写 `model-management.md` §12.2 的 Spike 02 成本表与「没有前缀缓存，解释 Agent 在经济上不成立」那句结论的措辞**
   —— 沿用 `2026-08-24-2109-2` 收口时的同一条自律（它逐字记了「§12.2 那张表与那句结论一个字未动」）。
   本项目实测的数**另起落点节**，并在 §12.2 加一条指针行指过去，**两个数不合并、不互相佐证**（D-16）。
6. **不动** `tests/gates/**` · `.github/workflows/**` · `missions/**` · `docs/masterplan/DECISIONS.md` ·
   `docs/masterplan/` 已有行（`STATE.md` 只追加）· `tools/experiments/p1_entry_gate/**` ·
   `docs/evidence/` 下已有的 JSON。
7. **不写任何业务数据**（P1 是②端只读）。实跑只调十个只读工具。
8. **不扩 `tests/unit/test_explain_cost_accounting_body.py:205` 的
   `@pytest.mark.parametrize("bucket", ["prompt","completion","reasoning"])`。**
   那是 WBS §4 P1.7 那一行**字面三项**的 🔴 断言体交付形态，`cached` 不在那一行的验收内。
   `cached` 的「缺项即红」由本 plan 的 `tests/unit/test_prompt_cache_accounting.py` ① 与 ⑤ 承担。
9. **不创建、不声称满足 `tests/gates/test_explain_cost_ceiling.py`**（已由 D-18 废止，且红线 1 禁止 loop 建门禁）。

## 4. Task Route

- Type: `implementation-only change` + `verification or audit work`（记账实现 + 一次写死假设的实测）
- Owner Docs: `docs/architecture/module-boundaries.md`（§7.11 已有账本口径，本 plan 新增 §7.17）·
  `docs/architecture/model-management.md` §12.2（只加指针行）
- Skill Selection Basis: `none`。本仓 `docs/skills/` 里没有覆盖「端点用量字段解析 + 写死假设的单次实测」这一形态的技能；
  硬约束 ② 的做法（假设跑前逐字写死、事后逐条对照）已由本 plan §6 直接承担，不需要外部技能来选方法。
- **条件性升格已触发**（沿用 `2026-08-24-2109-2` D1 的记法）：本 plan 动到 **P1.1 的导出面**
  （`Usage` 加字段，见 D1），因此 `python3 -m pytest tests/routing -q` **进入验证命令清单**
  （已落在 Phase 1 Exit Criteria）。同理动到 **P1.2 的落盘面**（D3），
  `python3 -m pytest tests/context -q` 同样进清单（已落在 Phase 2 Exit Criteria）。
  ⚠️ 这两条**都不在 `commands.test` 里**，收口时须逐字写「verification scope limited」（见 Closure Gates）。

## 5. Infrastructure And Config Prereqs

- `~/.config/agenerp/secrets.env` 含 `DASHSCOPE_API_KEY`（起草期实读：存在、`-rw-------`）。
  ⚠️ **凭据绝不进 git、绝不打印到日志** —— `missions/p1-insight.json` 的 **`_notes.p1_specific`**
  （不是顶层键）逐字：「LLM 凭据在 **`.env`** 的 `DASHSCOPE_API_KEY`，**绝不可进 git、不可打印到日志**」。
  ⚠️ 实际凭据落点已迁至 `~/.config/agenerp/secrets.env`，与该注记的 `.env` 措辞不一致；
  `missions/**` 是 blocked，本 plan **只引用、不代改、不重复登记**。
- 活站点 `http://127.0.0.1:18080`（Phase 3 的实跑要走十个只读工具）。
- Python 直连 HTTPS 需显式 `certifi`（roadmap「已知的坑」逐字，照抄不重新发现）。
- 无其它超出现有基线的 infra 前置；**无数据迁移，无 DDL，无回滚脚本**（本 plan 不碰 DocType 建表）。

## 6. 假设：**跑之前逐字写死**（硬约束 ②）

> 本节在 Phase 3 实跑**之前**定稿。事后**逐条对照，一个字不改**。
> 不吻合的**原文保留**，在 §12 的对照表里记「不吻合」并照实写实测值。
> ⚠️ **不许换模型、换题、加跑次数来凑吻合。**

**计数口径（先写死，免得事后选）**：

- 「一次解释」= `explain()` 一次调用，含它内部全部模型调用（P1.4 的循环本体）。
- 「第 N 次调用」= 账本 `CallEntry.index`（P1.7 已有，从 1 起）。
- `cached_tokens` 一律取**端点自报**的 `usage.prompt_tokens_details.cached_tokens`；
  端点没报这个字段时记 `0`（口径见 D2），**并在证据里单独标出「端点没报」这一情况**。

| # | 假设（写死） | 判别性 | 不吻合时怎么记 |
|---|---|---|---|
| **H1** | 第 **1** 次调用的 `cached_tokens` **== 0**（第一轮没有可命中的前缀） | 是 | 若 > 0 ⇒ 端点跨会话缓存，**口径要重定**，照实记后停下 |
| **H2** | 第 **2 次及以后**至少有一次 `cached_tokens` **> 0** | **是（本 plan 的承重假设）** | 若全程为 0 ⇒ **这就是本项目端点上的结论**：「隐式前缀缓存在本配置下未生效或未上报」。**照实记，不改假设、不换模型重跑** |
| **H3** | 若 H2 成立：设逐次序列 `c_1..c_N`，`S = {i : c_i == max(c)}`，则 **`S ∩ {N, N-1} != ∅`**（前缀最长的那两次里至少有一次取到最大值）。⚠️ 并列最大时**一并记 `|S|` 与全部下标**，不许事后挑一种读法 | 是 | `S ∩ {N, N-1} == ∅` ⇒ 记「不吻合」，逐次数列原样落证据 |
| **H4** | 逐次 `cached_tokens` **≤ 该次 `prompt_tokens`** | 是（口径自检） | 若被证伪 ⇒ **口径理解错了**，停下重定口径，**不许把断言放松成 `>= 0`** |
| **H5** | **对照**：判定器那 **48** 次**单发**调用 `cached_tokens` 全为 0（起草期已实读在盘），而本次**多轮**解释至少一次 > 0（即 H2）。⚠️ **混淆已预先声明**：判定器那批 prompt 落在 **687–1924** token，本次多轮解释的 prompt 是 **1056 → 11681**，**「多轮 vs 单发」与「prompt 长度」两个变量同时变了**。裁定规则**跑前写死**：若第 1 次调用（prompt ≈1056，与判定器同量级）为 0、而后续更长的调用 > 0，则本次结果**支持「长度阈值」解释、不支持「多轮」解释**，H5 记「**不吻合（混淆已预先声明）**」 | 只在上述裁定规则下有判别力 | 两者都全为 0 ⇒ 「多轮 vs 单发」的差异在本项目上不存在，照实记 |
| **H6** | 账本改动**不改变 `total` 口径**：本次实跑 `total_matches_endpoint` **N/N 全真**，且 `usage_total_session["total"] == prompt + completion` | 是（回归） | 任一格为假 ⇒ 是本 plan 的缺陷，**必须修，不许 Deferred** |
| **H7** | `tests/routing` 逐字仍是 **`167 passed, 1 skipped`**（本 plan 不新增 `agenerp/**/*.py` 文件，`test_adapter.py:485` 的 `PRODUCT_MODULES` 基数不变）。⚠️ **那 1 条 skip 是 `tests/routing/test_live_endpoint.py`**（`pytestmark = pytest.mark.live`，靠 `REQUIRED_ENV` 三个环境变量是否为空 skip）。**Phase 4 复跑七条基线命令之前先跑 `env | grep AGENERP_LLM_`**，确认 `BASE_URL` / `API_KEY` **未被 export**（本机 shell 里 `AGENERP_LLM_MODEL` 可能已被 mission driver 导出），否则那条会由 skip 变 pass，H7 会因与本 plan 无关的原因记「不吻合」 | 是 | 变了 ⇒ 说明多建/少建了模块文件，照实记并解释 |
| **H8** | `tests/context` 条数 **53 → 54**（D3 新增一条 `cached > 0` 的 round-trip 判据；`:92` 那条改键集但不增条数） | 是 | 对不上照实记 |
| **H9** | `tests/unit` 条数 **614 → 626**：新文件 `test_prompt_cache_accounting.py` 恰 **12** 条 —— Phase 1 的 ①–⑤ 共 **5** 条 + Phase 2 的（⑥⑦⑧⑨⑩ **5** 条 + ⑪(a)/(b) **2** 条 = **7** 条）= **12** 条。**逐 Phase 拆**：Phase 1 结束 `614 → 619`，Phase 2 结束 `619 → 626` | **是（这是全 plan 唯一进得了 `commands.test` 的那条判据面的条数锁）** | 对不上 ⇒ **说明少写或多写了判据**，照实记并逐条说明是哪一条；**不许把「基线 + 本 Phase 新增数」这种恒真式当作已验证** |

⚠️ **H2 的两个方向都是结论，不是「成功/失败」。** 测出「没缓存」与测出「有缓存」
同等有价值 —— 前者恰恰证伪了 §12.2 那句从别的栈搬来的话在本项目上的适用性（D-16）。
**执行者不得因为 H2 落空而扩大范围去「让它命中」**（那属 Non-Goals 2）。

### 6.1 「全 0」那一支的举证责任，**跑之前**就写死（硬约束 ①）

盘上已有的 **48** 个端点回包**无一例外 `cached_tokens: 0`** ——
这是「H2 落空」的**强先验**，因此这一支必须提前定规矩，不许事后解释。

> **若本次实跑逐次 `cached_tokens` 全为 0**：
>
> 1. 此时每一次的 `cached_matches_endpoint` 都是 `0 == 0 → True`，
>    **一个把 `cached` 恒写 0 的假实现产出的证据文件与真实现逐字节相同** ——
>    所以**活端点证据在这一支上不承担「记全了」的举证责任**。
>    该责任**由 `tests/unit` 判据 ①（回包 `cached_tokens: 1024` ⇒ `Usage.cached == 1024`）
>    与 ⑧（端点报 100 而解析成 0 ⇒ `cached_matches_endpoint` 为 False）单独承担**。
> 2. 同理，**H1（第 1 次 == 0）与 H4（`cached ≤ prompt`）在这一支上是恒真的**，
>    对照表里必须逐字标注「**该支下恒真，不构成证据**」。
> 3. **收口陈述里必须逐字写出上面这两句**，不许把「跑了一次、全绿」说成「记全了已被实测证明」。
> 4. `docs/evidence/p1-cache/live-run-01.json` 必须**原样落每一次的 `prompt_tokens_details` 原始子对象**
>    （不是只落解析后的 `cached_tokens`），使读者能人工复核**端点确实报了这个字段**，
>    而不是解析侧凭空补出来的 0。**这一条无论哪一支都要做。**
>    ⚠️ **怎么拿到它，跑之前先定死**（否则执行者会卡住）：`CallEntry` / `CallLedger` / `ExplainTrace`
>    的 `as_dict()` **都不带端点原始 usage 子对象**，`Reply.raw` 也不向 `ExplainResult` 传递
>    ⇒ **靠账本导出面拿不到**。做法是经 `explain(transport=…)`（`agenerp/explain/loop.py:622` 的形参）
>    **在一次性脚本里包一层记录型 transport**，把每次回包的原始 `usage` 留下来 ——
>    形先例是 `agenerp/judging/judge.py:44-53` 的 `Verdict.endpoint_usage`。
>    **产品代码为此一行都不改**（要改就成了另一个交付面）。

## 7. Decisions（选择 / 备选 / 否决理由 / 残余风险）

### D1 · `cached` 落在 `Usage` 上（P1.1 的导出面），不是只落账本

- **选定**：`Usage` 加第四项 `cached: int = 0`，`usage_of()` 解析
  `prompt_tokens_details.cached_tokens`，`plus()` 四项相加，`as_dict()` 出五键。
  **`total` 仍是 `prompt + completion`，`cached` 不进 `total`。**
- **备选 (ii)**：`Usage` 不动，只在账本记 `endpoint_cached`。
  **否决理由**：那样就没有「解析值 vs 端点自报值」两组数可比，
  `cached_matches_endpoint` 退化成拿端点的数跟自己比，**恒真** ——
  正是 `ledger.py` 模块头逐字批评的「`prompt + completion == total` 这种写法是恒真的，判它等于没判」。
- **备选 (iii)**：把 `cached` 当第四个桶算进 `total`。
  **否决理由**：与端点自报的 `total_tokens` 立刻对不上（`cached` 是 `prompt` 的子集），
  会把 P1.7 已经绿的 `total_matches_endpoint` 判据整片打红，且口径上就是错的。
- **跨工作项的先例，只到这一层（不许拉大）**：`2026-08-24-2109-2` 的 D1
  **明确否决**了「挂 `ChatAdapter`……那是 P1.1 的导出面」这条；它实际做的是给
  `agenerp/routing/errors.py` 的 `RoutingError` 加一个可选 `usage: dict`，
  并声明「该改动**动到 P1.1 的导出面** ⇒ Task Route 的**条件性升格已触发**，
  `pytest tests/routing -q` 进入验证命令清单」。
  **先例只到「动 P1.1 导出面时须声明条件性升格并把 `tests/routing` 纳入验证清单」这一层。**
  给 `Usage` 这个类型本身加字段**比先例的改动面更大**，
  因此本 plan **不说「已经选过这条路」** —— 选它的理由只有一条：
  备选 (ii) 会让 `cached_matches_endpoint` 退化成恒真。
- **残余风险**：`Usage` 的键集变了，所有转发 `as_dict()` 的地方（`judge.py:52`、
  `loop.py:387/524`）输出多一个键。起草期已逐个查过**无键集断言**（§1.5 第 9 行），
  但**开工时须再查一遍**（§0 第 3 条的七条命令即覆盖）。

### D2 · 「缺失」与「0」怎么分

- **选定**：**逐字沿用 `reasoning` 今天的口径**（`ledger.py:41-59` 的 `_endpoint_numbers`）——
  整个 `usage` 都没有时 `endpoint_cached` 记 `None`（真的不知道）；
  `usage` 在而 `prompt_tokens_details` 缺时记 **`0`**（端点没报命中）。
  解析侧 `Usage.cached` 缺失一律回 `0`，**不回退成算进 `prompt` 之外的任何地方**。
- **备选**：`prompt_tokens_details` 缺时记 `None`（与 `reasoning` 不同）。
  **否决理由**：两个对称字段用两套缺失口径，读账的人必须记住哪个是哪个；
  且 `reasoning` 那套口径的理由（「非推理模型的回包就是这个形状」）在这里同样成立
  （不做缓存的端点就是不报这个字段）。
- **残余风险**：`0` 因此有两个含义（端点报了 0 命中 / 端点没报这个字段）。
  **处置**：证据文件里把「端点是否报了 `prompt_tokens_details`」**单独记一列**，
  不让它被 `0` 吃掉；落点节 §7.17 逐字写明这一点。

### D3 · 会话落盘也记 `cached`（跨出 P1.7 边界的唯一一处）

- **选定**：`agenerp/context/store.py` 的 `to_payload()` 写**四键**、读回也读四键；
  `tests/context/test_store.py:92` 的键集断言相应改成四键，
  **并新增一条 `cached > 0` 的 round-trip 判据**。
- **备选**：不动 `store.py`。
  **否决理由**：`Usage` 一旦有了第四项，`from_payload(to_payload(x))` 对
  `cached > 0` 的会话就**不再相等** —— 那是一条**静默丢数**的契约漂移。
  今天测不出来只是因为 fixture 的 `cached` 恒为 0，
  而指南第 14 条把「确认的契约漂移」列为**不可降级**项。
- **为什么这仍是同一个结果面**：契约是「prompt 侧细分被记全且不丢」，落盘是这条契约的一环。
- **无兼容负担（起草期实读，不是推断）**：`from_payload` 逐字「**缺键即抛**，不给默认值兜底」，
  改成读四键后旧格式会 `KeyError` —— 但**今天没有存量**：
  `grep -rn "from_payload\|to_payload\|JsonFileSessionStore" agenerp tools` 除 `store.py` 自身外
  **没有任何产品调用方**（只有 `agenerp/context/__init__.py:30` 的再导出），
  `docs/evidence/**` 下**没有任何按该形状落盘的会话 JSON**
  （`p1-entry-gate/run-*.json` 里的 `turns` 是实验设施自己的形状，不走 `from_payload`）。
  ⇒ §5 那句「无数据迁移」**成立且有出处**。
- **残余风险**：`tests/context` **不在 `commands.test` 里**（STATE §3 `[open] 2026-08-24T09:20Z` 已登记，
  本 plan **只引用、不重复登记、不代人处置**），因此这一处改动**进不了 `GATE_VERIFY`**。
  **处置**：`cached` 的落盘/读回判据**同时在 `tests/unit` 里再钉一条** ——
  即 **Phase 2 的 ⑪(a)/(b)**（直接 import `agenerp.context.store`，**不 import `tests/context` 的夹具**），
  使承重判据落在 `GATE_VERIFY` 与 CI 都看得见的面上。

### D4 · 落点节与 §12.2 的关系

- **选定**：本项目实测数落 `module-boundaries.md` **§7.17**（新节）；
  `model-management.md` §12.2 只**追加一条指针行**，形如
  「⚠️ 上表是 Spike 02 的数（别的栈、别的题）。本项目端点上的前缀缓存实测见 `module-boundaries.md` §7.17，
  **两个数不是同一个量，不得互相佐证**（D-16）」。
- **备选**：直接改写 §12.2 那句「没有前缀缓存，解释 Agent 在经济上不成立」。
  **否决理由**：那是一句**上位结论**，一次实测（一道题、一个模型、一次运行）不足以推翻它；
  且 `2026-08-24-2109-2` 收口时逐字自律过「§12.2 那句结论一个字未动」，
  本 plan 无理由破这个例。**改写与否由人裁定**（进 §11 Deferred）。
- **残余风险**：文档里同时存在一句外部结论与一个本项目实测数，读者可能混用。
  **处置**：指针行里那句「**不得互相佐证**」是硬性措辞，且 §7.17 开头重复一遍。

## 8. Execution Plan

### Phase 1 — 解析面：`Usage.cached` 与 `usage_of()`

Status: completed
Targets: `agenerp/routing/adapter.py`（**只改代码**；它的模块 docstring 与 §1.6 其余落点一起在 **Phase 2 的 `Fix` 项**里改）·
`tests/unit/test_prompt_cache_accounting.py`（新建）
Skill: `none`

- Item Types: `Add`（4/5 项为 `Add`，其余 1 项为 `Proof`）
- Prereqs: §0 的七处重取基线已填进 §0.1

- [x] `Add` — `Usage` 加 `cached: int = 0`；docstring 逐字写明「**`cached` 是 `prompt` 的一个细分，
      不是第五个桶**」，与既有那句 `reasoning` 的话形状对称；`total` 的实现**一个字不动**。
- [x] `Add` — `usage_of()` 解析 `prompt_tokens_details.cached_tokens`，缺失回 `0`（D2）。
- [x] `Add` — `plus()` 四项相加；`as_dict()` 出五键（`prompt` / `completion` / `reasoning` / `cached` / `total`）。
- [x] `Add` — 起草期 §1.5 第 9 行的三个转发点（`judge.py:52`、`loop.py:387/524`）**开工时逐个复读**，
      确认无键集断言；有则就地处置并记进 §12。
- [x] `Proof` — 判据落 `tests/unit/test_prompt_cache_accounting.py`（**不落 `tests/routing`**，
      理由是 `tests/routing` 进不了 `commands.test`，见 §1.1）：
      ① 端点回包带 `prompt_tokens_details.cached_tokens: 1024` ⇒ `Usage.cached == 1024`；
      ② `prompt_tokens_details` 整个缺 ⇒ `cached == 0` 且**不影响** `prompt`；
      ③ **整字典比较、写死字面数字**（**不许写成 `total == prompt + completion` ——
      `ledger.py` 模块头逐字批评过那是恒真式**）：喂 `prompt=100, completion=20, cached=999` ⇒
      `as_dict() == {"prompt":100,"completion":20,"reasoning":0,"cached":999,"total":120}`；
      ④ `plus()` 折叠两条 ⇒ 四项各自相加；
      ⑤ `as_dict()` 键集**恰等于**五键（写死字面量，不用变量算）。

Exit Criteria:

- [x] `python3 -m pytest tests/unit -q` **exit 0**，条数逐字 **`619 passed`**（H9 的 Phase 1 格）
- [x] `python3 -m pytest tests/unit/test_prompt_cache_accounting.py -q` **exit 0**，条数**恰 5 条**
- [x] `python3 -m pytest tests/routing -q` **exit 0**，条数**仍为 167**（H7）
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` **exit 0**
- [x] `docs/logs/` 更新

### Phase 2 — 账本面：`endpoint_cached` 与 `cached_matches_endpoint`，以及落盘

Status: completed
Targets: `agenerp/explain/ledger.py` · `agenerp/context/store.py` · `agenerp/context/session.py` ·
`agenerp/explain/loop.py` · `agenerp/routing/adapter.py`（模块 docstring）·
`agenerp/context/doctype/agent_conversation_session.json`（**只改 `turns` 的 `description`**）·
`docs/architecture/module-boundaries.md`（§7.7 / §7.11 / 347 行）·
`docs/architecture/model-management.md`（**只改 §1.6 点名的那两行**，§12.2 的成本表与结论措辞不动）·
`tests/unit/test_prompt_cache_accounting.py` · `tests/context/test_store.py`
—— **落点清单以 §1.6 那张表为准**（用命令穷举，不用行号）
Skill: `none`

- Item Types: `Add | Fix | Proof`（8 项里 3 项是 `Proof`；`store.py` 与漂移那两项是 `Fix` ——
  D3 认定的静默丢数契约漂移与 §1.6 的确认漂移，指南第 14 条**不可降级**）
- Prereqs: Phase 1

- [x] `Add` — `_endpoint_numbers()` 回三个数，加 `endpoint_cached`（口径按 D2）。
- [x] `Add` — `CallEntry` 加 `endpoint_cached` 字段与 `cached_matches_endpoint` 属性
      （形状**逐字对称**于既有的 `reasoning_matches_endpoint`：端点没报 ⇒ `False`，「不知道 ≠ 对得上」）。
- [x] `Add` — `CallEntry.as_dict()` / `CallLedger.as_dict()` 出这两项。
- [x] `Fix` — `agenerp/context/store.py` 落盘四键、读回四键（D3）。
      ⚠️ **`total` 仍不落盘**（`test_store.py` 那条判据的原意是「`total` 不做第二份真相」，本 plan 不动这个原意）。
- [x] `Proof` — `tests/context/test_store.py`：`:92` 键集改四键；**新增**一条
      `from_payload(to_payload(cached>0 的会话)) == 原会话` 的 round-trip 判据（H8）。
- [x] `Proof` — `tests/unit/test_prompt_cache_accounting.py` 追加（D3 残余风险的处置，**不 import `tests/context` 的夹具**）：
      ⑥ 账本记一条带 `cached` 的回包 ⇒ `endpoint_cached` 与 `usage.cached` 都对，`cached_matches_endpoint` 为真；
      ⑦ 回包**根本没有 `usage`** ⇒ `endpoint_cached is None` 且 `cached_matches_endpoint` 为 **False**；
      ⑧ 端点自报 `cached=100` 而解析值被做成 `0` 的坏实现 ⇒ `cached_matches_endpoint` 为 **False**（这条是打红假实现的那条）；
      ⑨ `CallLedger.total` 折叠**两条写死字面数字的账**后，**整字典比较**
      （同 ③ 的理由，不写恒真式）：`total.as_dict()` 恰等于写死的期望字典，`cached` 两条相加、**不进** `total`；
      ⑩ **账本仍然不拦截**：喂一条 `cached` 巨大的账，`explain` 照样把答案交出去（D-18 回归）。
- [x] `Proof` — **⑪ D3 的承重判据，落在 `tests/unit`**（这条是 D3 残余风险与 §11 第四条 Deferred
      「不阻塞理由」所依赖的那一条，**不写它，D3 的缓解措施就从未落地**）：
      在 `tests/unit/test_prompt_cache_accounting.py` 里**直接 import** `agenerp.context.store` 的
      `to_payload` / `from_payload`（**不 import `tests/context` 的夹具、不用 `_session()`**）。
      会话**现搭最小的一个**：用 `agenerp.context.session` 的建造 API 起一个会话、
      加一轮 `usage=Usage(prompt=…, completion=…, reasoning=…, cached=…>0)` 的 `Turn`
      （**开工时按 `agenerp/context/session.py` 的实际签名写，不照抄本行的形参名**）。断言
      （a）`set(to_payload(<cached>0 的会话>)["turns"][0]["usage"])` **恰等于写死的四键字面量**；
      （b）`from_payload(to_payload(x)) == x` 对 `cached > 0` 成立。
- [x] `Fix` — **§1.6 那张表逐行改准**（指南第 14 条**不可降级**）。
      **做法是先跑穷举命令、再逐条对照那张表**，不许照行号改（行号会漂）。
      ⚠️ 表里标「**一个字不改**」的两类（P1.5 的历史记录 · `tools/experiments/**` 冻结面）**不许动**。
      ⚠️ §7.11 是 **P1.7 本体的落点节**，改它属本 plan 结果面内的连带修改，**不是越界**。
      ⚠️ **`agent_conversation_session.json` 这一处不触发风险档 L3、不需人批**（逐字定性，免得关闭审计在这一格上停机）：
      本 plan **只改 `fields` 里 `turns` 那一项的 `description` 自由文本**，
      `field_order` / `fields` 的字段集 / `permissions` **一个字不动** ⇒ 不是模型形状变更。
      L3 的定义逐字是「系统形态变更 | **新建 DocType（DDL）**、改权限、改 Workflow」，
      指的是**在活站点上建表**；`agenerp/context/store.py:15-17` 与 `module-boundaries.md:344` 两处逐字同解
      （「声明落 git、可 diff、可 review，**不含任何 apply 逻辑**」）。
      `docs/context/ai-autonomy-policy.md` 的 Protected Areas 逐行读过，**没有一行覆盖 DocType 声明文件**
      （受保护的是打活站点的写路径：`delete_custom_field` / `execute_plan` 删除路径 / `oob.drop_columns` /
      `SiteClient.create_doc` / `ensure_doc` / `seedsite.py`）。**本 plan 不在活站点上建任何表。**

Exit Criteria:

- [x] `python3 -m pytest tests/unit -q` **exit 0**，条数逐字 **`626 passed`**（H9 的 Phase 2 格）
- [x] `python3 -m pytest tests/unit/test_prompt_cache_accounting.py -q` **exit 0**，条数**恰 12 条**
- [x] `python3 -m pytest tests/context -q` **exit 0**，条数 **54**（H8）
- [x] `python3 tools/gates/check_expected_red.py` **exit 0**，`预期红 0，绿 11，跳过 0`
- [x] **§1.6 那张表逐行改准**（**不是**「§1.5 第 12–15 行四处」—— §1.5 现在只有 12 行，
      漂移面已改由 §1.6 的穷举命令定义），改后的措辞记进 §12
- [x] `docs/logs/` 更新

### Phase 3 — 变异自查 M1–M10（共 10 个）

Status: completed
Targets: 无产物（只跑变异，跑完**逐个还原**）
Skill: `none`

- Item Types: `Proof`（10/10）
- Prereqs: Phase 2

逐个植入下表的变异，**必须被指定判据打红**；不红就地补断言，并把补的那条记进 §12（记作 **M11、M12…**）。

| # | 变异（**产品侧**，不是判据侧） | 必须被谁打红 |
|---|---|---|
| M1 | `usage_of()` 不读 `prompt_tokens_details`，`cached` 恒 0 | Phase 1 ① + **Phase 2 ⑥** ⚠️ **不是 ⑧** —— ⑧ 的假实现摆在判据侧（`cached=0` 由测试自己钉死），产品端 M1 与否它都绿 |
| M2 | `cached` 被算进 `total` | Phase 1 ③ + Phase 2 ⑨ |
| M3 | `cached` 被当成 `completion` 的细分（读 `completion_tokens_details`） | Phase 1 ① |
| M4 | `_endpoint_numbers()` 在整个 `usage` 缺失时把 `endpoint_cached` 记 `0` 而不是 `None` | Phase 2 ⑦ |
| M5 | `cached_matches_endpoint` 写成拿端点的数跟自己比（恒真） | Phase 2 ⑧ |
| M6 | `store.py` 落盘仍写三键 | **Phase 2 ⑪(a)**（`tests/unit`，进得了 `GATE_VERIFY`）+ `tests/context/test_store.py` 的键集那条 |
| M7 | `store.py` 落四键但读回只读三键（**静默丢数**） | **Phase 2 ⑪(b)** 的 round-trip |
| M8 | 账本里加一条「`cached` 超过 X 就拒答」的分支 | Phase 2 ⑩（D-18 回归） |
| M9 | `Usage.as_dict()` **不出 `cached` 键**（解析对了但导不出来） | Phase 1 ⑤（键集写死字面量）+ Phase 1 ③（整字典比较） |
| M10 | `Usage.plus()` **漏加 `cached`**（折叠后 `cached` 恒等于第一条） | Phase 1 ④ + Phase 2 ⑨ |

⚠️ **M9 / M10 是第 2 轮评审补的**，理由逐字：「`as_dict()` 不出 `cached` 键」与
「`plus()` 漏加 `cached`」**正是最像真事的半吊子形态**，而首稿的 ②④⑤ 三条判据当时**没有任何变异守着**。

Exit Criteria:

- [x] **十个**变异（M1–M10）**逐个由绿转红**，结果表记进 §12（**没有 M11 就写「没有 M11」**）
- [x] 变异**全部还原**，`git status --porcelain` 回到 Phase 2 结束时的形态
- [x] No owner-doc update required（本 Phase 无产物）

### Phase 4 — 活端点实跑一次，与 §6 逐条对照

Status: completed
Targets: `docs/evidence/p1-cache/`（新建）· `docs/architecture/module-boundaries.md` §7.17 ·
`docs/architecture/model-management.md` §12.2（只加指针行）
Skill: `none`

- Item Types: `Proof | Add`
- Prereqs: Phase 3

- [x] `Proof` — **跑一次完整解释**，题目**逐字沿用** `docs/evidence/p1-cost/live-run-01.json` 的
      `question`（同题才与那次 8 调用 / 53,041 prompt token 可比），模型 `qwen3.6-plus`。
      一次性脚本**不进仓**（照 P1.4 / P1.7 先例）。**只调只读工具，一条业务数据都不写。**
- [x] `Proof` — 证据落 `docs/evidence/p1-cache/live-run-01.json` + `README.md`：
      逐次 `index` / `prompt_tokens` / `cached_tokens` / **端点是否报了 `prompt_tokens_details`**（D2 残余风险的处置）/
      `total_matches_endpoint` / `cached_matches_endpoint`，以及汇总。
      ⚠️ **必须原样落每一次的 `prompt_tokens_details` 原始子对象**（§6.1 第 4 条，**两支都要做**）。
      ⚠️ **不落任何凭据、不落任何单据明细以外的站点数据。**
- [x] `Proof` — §12 填 **H1–H9 逐格对照表**，**§6 原文一个字不改**。
- [x] `Add` — 落点节 §7.17（开工时以实读最大节号顺延）：口径（D1/D2/D3）+ 实测数 +
      「与 §12.2 的 Spike 02 不是同一个量，不得互相佐证」。
- [x] `Add` — `model-management.md` §12.2 追加**一行**指针（D4），**不改那一节任何已有字**。
- [x] `Add` — `docs/masterplan/STATE.md` §2 **只追加**一条证据行（命令原文 + 退出码 + sha）。

Exit Criteria:

- [x] 七条基线命令全绿，退出码与条数逐条记进 §12
- [x] H1–H9 **逐条对照完毕**，不吻合的照实记且 §6 原文未改
- [x] **若实测全 0**：§6.1 的四条**逐条执行**，且对照表里 H1 / H4 逐字标注「该支下恒真，不构成证据」，
      收口陈述逐字写出「活端点证据在这一支上不承担『记全』的举证责任」
- [x] `docs/evidence/p1-cache/live-run-01.json` 里**每一次的 `prompt_tokens_details` 原始子对象在场**
- [x] **§1.6 的漂移面收口前用命令复核一遍**（⚠️ 首稿那条 grep 的文件清单**够不着**
      `context/session.py` / `context/store.py` / `explain/loop.py` 三处，而这三处**又没有任何测试守着**
      —— `test_doctype_declaration.py` 只比顶层 fieldname、`test_session.py` 不判自由文本 ⇒
      漂移落地后**既无红灯也无人工复核**，与第 1 轮 Blocker 2 判定的失效模式**逐字同型**）：
      **逐字复跑 §1.6 的 grep-1 与 grep-2**（含 `tools/experiments/p1_entry_gate` 路径），
      命中**逐条对照 §1.6 那张表**，按**三类**归档并记进 §12：
      **改准** · **一个字不改**（`tools/experiments/**` 冻结面 · P1.5 的历史记录 `module-boundaries.md:2535/2598`）·
      **无关命中，不改**（§1.6 已预先点名的 `seedsite.py` / `contracts.py` / `ledger.py` 标识符行）。
      ⚠️ **三类之外还有命中就是漏项**，必须当场处置，不许留到收口
- [x] `git diff --name-only <基线sha> HEAD -- tests/gates .github/workflows missions tools/experiments/p1_entry_gate ':!docs/masterplan/STATE.md' docs/masterplan` **无输出**
      （⚠️ 首稿只查 `DECISIONS.md`，而 §9 与 Non-Goals 6 承诺的是 **`docs/masterplan/` 已有行**与 `02-WBS.md` 全都不动 —— pathspec 要盖住那句承诺）
- [x] `git diff --numstat <基线sha> HEAD -- docs/masterplan/STATE.md` 的**删除列为 0**
- [x] 落点节 §7.17 与 §12.2 指针行落地
- [x] `docs/logs/` 更新

## 9. 红线自查（开工前读一遍，收口时逐条复核）

| 红线 | 本 plan 的触碰面 | 自查 |
|---|---|---|
| 1 `tests/gates/**` | 无 | 判据全落 `tests/unit` / `tests/context`，**一个字节不动裁判** |
| 2 `.github/workflows/**` | 无 | 不改 CI |
| 3 `DECISIONS.md` | 无 | D-18 / D-11 / D-16 **只引用不改**，不新增 `R-x` |
| 4 项目名 / 包名 | 无 | — |
| 5 `docs/masterplan/` 其余文件 | `STATE.md` **只追加** | `02-WBS.md` 一个字不动（本 plan 是工作项 9 / P1.7 的**第 2 个** plan，在表规 3 的 1–2 个预算内，**不需要拆行**）。⚠️ **本 plan 落地后工作项 9 的预算用尽** —— §11 的**五条** Deferred 若将来重开，须由**人**在 `02-WBS.md` 拆行 / 加行（红线 5，**loop 无权**） |
| 6 证据仓 `XM_PATH` | 无 | 不写 |
| 7 运行时 Server Script | 无 | 不生成 |

## 10. Draft Review Record

- Independent draft review iteration 1: **needs revision**（独立子代理，全新会话，不带起草上下文，
  2026-08-25；该评审**自己跑了七条基线命令、自己读了代码与三份证据 JSON**，非纸面读）——
  开出 **4 条 Blocker + 6 条 Major + 8 条 Minor**。**逐条处置**：
  - **Blocker 1** — D3 声称「承重判据同时钉在 `tests/unit`」，但 Phase 2 的 Proof 清单 ⑥–⑩
    **没有任何一项创建它**；而 `tests/context` 不在 `commands.test` 里 ⇒ D3 的缓解措施与 §11 第四条
    Deferred 的「不阻塞理由」双双落空。→ Phase 2 新增 **⑪(a)/(b)**（直接 import
    `agenerp.context.store`，不用 `tests/context` 夹具），M6 改指 ⑪(a)，新增 **M7a**（落四键但读回三键的静默丢数）指 ⑪(b)。
  - **Blocker 2** — **确认的 owner-doc / 声明漂移未进 inventory 且没有任何红灯**：
    `module-boundaries.md` §7.11 两段与约 347 行 · `agent_conversation_session.json` 的 `turns` description ·
    `adapter.py` / `ledger.py` 两处模块 docstring，全都逐字写着「三项」/ 两个 `endpoint_*` 名字；
    而 `test_doctype_declaration.py` 只比顶层 fieldname ⇒ 改完仍全绿。
    → §1.5 新增第 **12–15** 行、写进 Phase 1/2 `Targets`、Phase 2 新增一条 `Fix` 项（指南第 14 条不可降级）、
    Phase 4 Exit Criteria 加一条 `grep -n "三项" …` 的机械复核，**并逐字声明那不是红灯**；
    §11 新增一条 watch-only Deferred 记这个盲区。
  - **Blocker 3** — 盘上 48 个回包全 0，**「H2 落空」是强先验**；那一支下
    `cached_matches_endpoint` 恒为 `0==0→True`，**假实现与真实现的证据文件逐字节相同**，
    而 Phase 4 的 Exit Criteria 仍会判「已实测」。→ 新增 **§6.1**（跑之前写死的分支规则四条）：
    该支下举证责任改由 `tests/unit` ①/⑧ 单独承担、H1/H4 标注「恒真不构成证据」、
    收口须逐字写出这两句、证据**必须原样落 `prompt_tokens_details` 原始子对象**（两支都要）；
    Phase 4 Exit Criteria 相应加三条。
  - **Blocker 4** — 页眉那条「逐字」引用被截断，截掉的恰是 `🔴 tests/gates/test_explain_cost_ceiling.py`
    ——**该文件已由 D-18 废止且不存在**，收口审计会当场卡住。→ 页眉补全原文并紧跟定性；
    Non-Goals 新增第 9 条「不创建、不声称满足它」。
  - **Major 1** — 归属对（工作项 9），但 §1.4 的理由**过度声称**：WBS §4 P1.7 那一行的字面验收
    是**三项**，且已由 `2026-08-24-2109-2` 满足。→ §1.4 改写：授权来自 **P1.1 §9 第三条 Deferred
    自己写死的 successor 指派 + 已触发的重开事件**，不再声称「P1.7 验收没做完」，
    「与只记 completion 不记 reasoning 同形」降为**类比**；§9 红线表补记「本 plan 落地后工作项 9 预算用尽，拆行只有人能做」。
  - **Major 2** — H3「最大值出现在最后一次或倒数第二次」在**并列最大值**时无定义，事后可随意解释。
    → 改写成可机械判定的 `S = {i : c_i == max(c)}`、判 `S ∩ {N, N-1} != ∅`，并列时一并记 `|S|` 与全部下标。
  - **Major 3** — H5 是**混淆设计**：判定器那批 prompt 687–1924，本次 1056→11681，
    「多轮 vs 单发」与「prompt 长度」两个变量同时变。→ 跑前写死备择解释与裁定规则。
  - **Major 4** — D1 的「先例」引用不准：`2026-08-24-2109-2` 的 D1 **否决**了挂 `ChatAdapter`，
    它只给 `RoutingError` 加了个可选字段。→ D1 改写，先例只保留到「动 P1.1 导出面须声明条件性升格」这一层；
    §4 Task Route 补「条件性升格已触发」。
  - **Major 5** — Phase 1 ③ / Phase 2 ⑨ 写成 `total == prompt + completion`，正是
    `ledger.py` 模块头批评的**恒真式**，只挡得住 M2。→ 两条都改成**写死字面数字的整字典比较**。
  - **Major 6** — 对 P1.7 已有的 🔴 断言体（`test_explain_cost_accounting_body.py:205` 的三项参数化）
    要不要扩，plan 没表态。→ Non-Goals 新增第 8 条：**不扩**，`cached` 的「缺项即红」由本 plan ①/⑤ 承担。
  - **Minor 逐条处置**：§1.5 第 8 行的参数化基数改指 `:485`/`:488`（`:403` 只贡献 1 条）·
    H7 钉成逐字 `167 passed, 1 skipped` 并写明 Phase 4 复跑必须在**没有 export 那三个 live 变量**的 shell 里跑 ·
    凭据引用改成 `_notes.p1_specific` 并记下 `.env` 与 `secrets.env` 的措辞不一致（只引用不代改）·
    三份判定器证据改记为**互不相同的 24 / 18 / 6，合计 48 个值全 0** ·
    §12.2 标题补上「**成本：**」两个字。
  - 评审**已通过**的三项，本轮未改：Anti-Slacking 扫描（无 `optional` / `consider` 等词，
    四条 Deferred 每条都写死了重开事件）· 红线自查（Phase 1–4 的 `Targets` 逐条比对四个受保护 pathspec，
    无一会被迫触碰；`expected-red.txt` 已清零，本 plan 不产生新的预期红）·
    **范围问题**（评审独立认可 D3 不算外溢，指出真正的问题是「改得不够全」，即 Blocker 2）。
  - 评审的独立结论（照抄，不改写）：**「值得做，但不是 plan §1.4 说的那个理由」** ——
    它关掉的是一个 **D-16 缺口**（§12.2 那句上位结论的数字全来自 Spike 02，
    本项目对「自己端点上前缀缓存生不生效」的实测样本是 **0**），
    且失真发生在**占 90.5% 的那一栏**上；最可能的结果是**负结果，而负结果同样有价值**。
    评审同时打了一个折扣：**「这件事的价值高度依赖 Blocker 3 的修法」** —— 已按其建议逐条落进 §6.1。
- Independent draft review iteration 2: **needs revision**（**另一个**独立子代理，全新会话，
  非第 1 轮那位，2026-08-25；同样实读代码与命令）——
  **先复核第 1 轮的处置：`Blocker 1–4 / Major 1–6 / Minor` 逐条实读，全部落地，数字与逐字引用均对得上**；
  随后以全新的眼光开出 **2 条新 Blocker + 5 条新 Major + 8 条新 Minor**。**逐条处置**：
  - **新 Blocker 1** — 第 1 轮的 Blocker 2 **只修了一半**：同类「确认漂移 + 无红灯」还有 **6 处**
    不在 inventory、不在任何 Phase `Targets` —— `agenerp/context/session.py:13-17` 与 `:147` ·
    `agenerp/explain/loop.py:240` · `agenerp/context/store.py:48` ·
    `module-boundaries.md:421-425/428`（**§7.7，P1.2 的落点节**）· `module-boundaries.md:934`（§7.11 内第三处）·
    `agenerp/explain/ledger.py:124`。→ **把逐行枚举整个换掉**：新增 **§1.6**，
    用**穷举命令**（两条 grep）定义漂移面并逐行分类，§1.5 第 12 行改成指向它；
    Phase 2 `Targets` 补 `context/session.py` / `explain/loop.py` / `adapter.py`；
    Phase 2 的 `Fix` 项改成「先跑穷举命令、再逐条对照 §1.6 那张表」，**不许照行号改**。
    ⚠️ §1.6 同时钉死了**两类不许动**的命中：P1.5 的历史记录（`module-boundaries.md:2535/2598`，改它等于改历史）
    与 `tools/experiments/p1_entry_gate/**`（Non-Goals 6 的冻结面）。
  - **新 Blocker 2** — Phase 4 那条机械 grep 的**文件清单够不着**其中三处
    （`context/session.py` / `context/store.py` / `explain/loop.py`），而这三处**又没有任何测试守着**
    ⇒「既无红灯也无人工复核」，与第 1 轮 Blocker 2 判定的失效模式**逐字同型**。
    → 改成 `grep -rn "三项\|第四个桶" agenerp docs/architecture/module-boundaries.md docs/architecture/model-management.md`
    加一条 `grep -rn "endpoint_total\|endpoint_reasoning" …`（⚠️ 后者没有「三项」二字，只 grep「三项」抓不到），
    并要求把冻结面 / 历史记录的命中**逐条标注**。
  - **新 Major 1** — **M1 的红灯指错**：⑧ 的假实现摆在**判据侧**（`cached=0` 由测试自己钉死），
    产品端 M1 与否它都绿；真正会红的是 **⑥**。→ 变异表改指 ⑥，并就地写明为什么不是 ⑧。
  - **新 Major 2** — 判据 **②④⑤ 无任何变异守着**，而「`as_dict()` 不出 `cached` 键」
    「`plus()` 漏加 `cached`」**正是最像真事的半吊子形态**。→ 补 **M9 / M10**，
    变异总数 8 → **10**，并把 M7a/M7b 的跳号改成连续的 M7/M8（补充项改记 M11 起）。
  - **新 Major 3** — `tests/unit`（**唯一进 `commands.test` 的那条判据面**）是全 plan
    **唯一没有条数预测**的：Phase 1 Exit 写「基线 + 本 Phase 新增数」是**恒真式**，Phase 2 Exit 连条数都没有
    ⇒ **十一条判据少写几条照样全打钩**，正是第 1 轮 Blocker 1 的失效模式。
    → 新增 **H9**（`614 → 625`，逐 Phase 拆成 `614→619` / `619→625`），
    两个 Phase 的 Exit Criteria 各加一条逐字条数 + 一条
    `pytest tests/unit/test_prompt_cache_accounting.py -q` **恰 N 条**。
  - **新 Major 4** — §6.1 第 4 条（**两支都要做**的硬性举证）**没写实现路径**：
    `CallEntry` / `CallLedger` / `ExplainTrace` 的 `as_dict()` 都不带端点原始 usage 子对象、
    `Reply.raw` 也不向 `ExplainResult` 传递 ⇒ **靠账本导出面根本拿不到** `prompt_tokens_details`。
    → 就地写死做法：经 `explain(transport=…)`（`loop.py:622`）在**一次性脚本**里包一层记录型 transport，
    形先例 `judge.py:44-53` 的 `Verdict.endpoint_usage`，**产品代码一行不改**。
  - **新 Major 5** — Phase 4 红线 diff 的 pathspec 只查 `DECISIONS.md`，
    而 §9 与 Non-Goals 6 承诺的是 **`docs/masterplan/` 已有行**与 `02-WBS.md` 全都不动。
    → pathspec 改成 `… tools/experiments/p1_entry_gate ':!docs/masterplan/STATE.md' docs/masterplan`。
  - **新 Minor 逐条处置**：§9 的「四条 Deferred」改**五条** · Phase 2 `Item Types` 补 `Proof` ·
    Phase 1 `Targets` 里 `adapter.py` 模块 docstring 的括注移到 Phase 2（那里才有对应执行项）·
    ⑪ 补一句「会话怎么现搭」（**按开工时的实际签名写，不照抄 plan 里的形参名**）·
    变异编号跳号修平（M8 不再空悬）· H7 的 live 变量提醒改成可执行判据
    `env | grep AGENERP_LLM_` · 以及评审主动给出的两条**定性结论**（下条）。
  - **评审主动给出的两条定性结论，已逐字落进 plan（它们把两个会让关闭审计停机的问号提前答掉）**：
    ① **Phase 2 改 `agent_conversation_session.json` 不触发风险档 L3、不需人批** ——
    `ai-autonomy-policy.md` 的 Protected Areas 逐行读过，**没有一行覆盖 DocType 声明文件**
    （受保护的是打活站点的写路径）；L3 逐字指「**在活站点上建表**」，
    而本次只改 `turns` 的 `description` 自由文本，`field_order` / 字段集 / `permissions` 一个字不动。
    ② **`from_payload` 三键改四键是破坏性读格式变更，但全仓零调用方、盘上零存量会话文件**
    ⇒ §5 那句「无数据迁移」成立**且现在有出处**（已落进 D3 的残余风险）。
- Independent draft review iteration 3: **needs revision**（**第三个**独立子代理，全新会话，
  非前两轮那两位，2026-08-25；**实跑了三条 pytest 与两条 grep**）——
  先核对第 2 轮的 5 条处置「**都能对上，落地是真的**」，随后开出 **2 条新 Blocker + 4 条 Major**。
  ⚠️ **上面第 2 轮那条记录里的 `614 → 625` / 「11 条」是当时写下的原文，本轮不回头改它**
  （改历史就看不出这一轮抓到了什么）—— 正文已按下面第 1 条改成 `614 → 626` / 「12 条」。**逐条处置**：
  - **新 Blocker 1** — **H9 那把「唯一的条数锁」自己算错了一条**：Phase 2 是
    ⑥⑦⑧⑨⑩（5 条）+ ⑪(a)/(b)（plan 自己写「各算一条」= 2 条）= **7**，不是 6。
    执行者按清单全写出来实得 **12 条 / `626 passed`**，而 Exit 写的是「`625 passed`」「恰 11 条」
    ⇒ **要打钩就得少写一条判据 —— 正好是 H9 设计来防的那个失效模式**。
    → H9 改成 `614 → 619 → 626`、新文件**恰 12 条**，两个 Phase Exit 同步。
  - **新 Blocker 2** — **号称穷举的 §1.6 漏了两处同型漂移**：`model-management.md:57`（§12.2 内 D-18 那条 bullet）
    与 `:240`（模块职责表 `adapter.py` 那一格），**都在 plan 自己指定的 grep 路径内**，
    且 `model-management.md` 是本 plan 的 Owner Doc、Non-Goals 5 只冻结了「Spike 02 成本表 + 那句结论的措辞」
    ⇒ 这两行不在冻结面内，却不在表里也不在任何 `Targets`。
    → §1.6 补两行（标「改准」并写明不在冻结面内），Phase 2 `Targets` 加 `model-management.md`。
  - **Major 1** — §1.6 末行认领了 `tools/experiments/p1_entry_gate/**` 的命中，
    但两条 grep 的路径清单**都不含 `tools/`** ⇒ 该行**永远产不出命中**，
    Phase 4 那句「逐条标注『冻结面，不改』」不可执行（实际命中在 `llm.py:40` / `loop.py:13`）。
    → grep-1 的路径加上 `tools/experiments/p1_entry_gate`，表里那行改成点名这两处。
  - **Major 2** — 两条 grep 会产出表里**无类可归**的无关命中（`seedsite.py:267/:870` ·
    `contracts.py:161` · grep-2 在 `ledger.py` 的十处**代码标识符**行），
    而表只有「改准 / 一个字不改」两类 ⇒ Phase 4「逐条对照」会在这些行上停机。
    → 加**第三类「无关命中，不改」并预先逐个点名**；Phase 4 Exit 相应改成按三类归档，
    并加一句「**三类之外还有命中就是漏项，当场处置**」。
  - **Major 3** — H 范围不一致：Phase 4 的 `Proof` 与 Exit 写「H1–H8」，而 §12 注释写「H1–H9」
    ⇒ H9 由两个 Phase Exit 承担、却没进对照表。→ 统一为 **H1–H9**。
  - **Major 4** — §11 第五条 Deferred 仍写「M6 / **M7a** 各打红一半」，第 2 轮已把编号平成 M7/M8。→ 改为 M6 / M7。
  - **本轮实跑复核的四个数（评审自己跑的，不是采信 plan）**：`tests/unit` **614 passed** ✓ ·
    `tests/context` **53 passed** ✓ · `tests/routing` **167 passed, 1 skipped** ✓ ·
    §1.6 表列的 22 处**逐行实证存在、无虚构**（含 `module-boundaries.md:2535/2598` 那两处历史记录）。
  - 评审明确判定**可接受、不必改**的一项：⑪ 那句「按开工时 `agenerp/context/session.py` 的实际签名写」
    的含糊度 **OK** —— `start(session_id, *, user="")` / `with_turn(turn)` /
    `Turn(role, text, tool_calls, usage: Usage)` 都在盘上且形状稳定，执行者不会卡。
  - 评审的一句话总结（照抄）：「**这两处改完即可转 active**。」
- **第 3 轮转轨条件收口（非独立复评，不编入 iteration 计数）**：（第 3 轮那位评审逐字写下的转轨条件是
  「这两处改完即可转 `active`」，两条 Blocker 与四条 Major **已于本轮全部就地改完**，
  改动面**局限在它逐条点名的行**上，未引入新的执行语义）。
  ⚠️ **照实记的边界**：本条**不是独立复评**，因此**不编入 iteration 计数**（指南第 13 条禁止自评转 `active`）。
  第 3 轮那位评审**没有再看过改后的文本** —— 该缺口由下面第 4 轮的独立验证补上。
- Independent draft review iteration 4（**独立验证，范围收窄到「上一轮那 6 条改对没有」**）：
  **accept — 可以维持 `active`**（**第四个**独立子代理，全新会话，2026-08-25）。
  逐条实读复核：H9 算术 ✓（自己数了 Phase 1 = 5 条、Phase 2 = 5 + 2 = 7 条，5 + 7 = 12 吻合，
  两个 Exit 已同步 `619 passed` / `626 passed`）· §1.6 补的两行 ✓ · grep-1 路径与冻结面点名 ✓ ·
  第三类「无关命中，不改」与 Phase 4 的三类归档 ✓ · H1–H9 三处统一 ✓ · §11 的 M7a 无残留 ✓。
  **另开一条会让执行走偏的硬错，已就地改**：Phase 2 Exit Criteria 仍写
  「§1.5 第 12–15 行四处漂移逐处改准」，而 §1.5 现在只有 12 行、该 Phase 的 `Fix` 项写的是
  「以 §1.6 那张表为准」⇒ **照 Exit 打钩只改 4 处，与 §1.6 的穷举面矛盾**。已改为「§1.6 那张表逐行改准」。
  另按其建议修了 H9 那句的括号（「5 + 5 + 2 = 7」字面是错等式）与上一条的标签。
  该评审对指南第 13 条的判定（照抄）：「前三轮均为独立子代理且第 3 轮逐字给出转轨条件，**实质满足**；
  但把自评收口编号成 iteration 4 与前三条并列，**标签略微越权**」—— 已按此改标签，本条才是 iteration 4。

## 11. Deferred But Adjudicated

### 改写 `model-management.md` §12.2 那句「没有前缀缓存，解释 Agent 在经济上不成立」

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 一次实测（一道题、一个模型、一次运行）不足以推翻一句上位结论；
  且 `2026-08-24-2109-2` 收口时已自律过「那句结论一个字未动」。见 D4。
- Successor Required: `yes` —— 由**人**裁定改写与否
- 重开事件：**人明确裁定改写 §12.2**，或**出现本项目自己的成本分布**（多次采样，见下一条）

### 前缀缓存的**多次采样与命中率分布**

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 本 plan 跑一次，是验「这个数记不记得下来、在本项目上是多少」，
  **不是**测分布（D-16：一次实测不是分布）。多次采样是另一个实验，须先有采样计划与假设。
- Successor Required: `no`
- 重开事件：**与 P1.7 既有 Deferred「成本的多次采样与分布」同时触发**
  （该条重开条件逐字是「要用已记的账定阈值时」，**今天未触发**）

### 以提高命中率为目的的前缀重排 / 提示词改造

- Classification: `optimization candidate`
- Why Not Blocking Closure: Non-Goals 2 的显式定界。没测出本项目自己的数之前谈优化违反 D-16。
- Successor Required: `no`
- 重开事件：**本 plan 的 H2 实测为「有命中但命中率低」，且人明确要求做成本优化时**
  （⚠️ H2 落空成「全程 0 命中」**不构成**本条的重开 —— 那时该做的是查「为什么没生效」，不是重排前缀）

### `turns` 内部字段声明没有任何机械判据守着

- Classification: `watch-only residual`
- Why Not Blocking Closure: `tests/context/test_doctype_declaration.py` 的三条同构断言只比
  **顶层 fieldname**（`session_id` / `user` / `turns` / `actions` / `snapshots`），
  `turns` 内部是 `Code/JSON`、description 是自由文本 ⇒ 加不加 `cached` 它都绿。
  本 plan 用 **Phase 4 的 `grep` 机械复核**顶上，**并逐字声明那不是红灯**。
  给自由文本 description 写机械判据是另一个结果面（且会波及全部 DocType 声明）。
- Successor Required: `no`
- 重开事件：**再出现第二处「DocType 声明与产物矛盾却全绿」的实例时**（届时值得给声明面立一条判据）

### `tests/context` 进不了 `commands.test`

- Classification: `watch-only residual`
- Why Not Blocking Closure: `missions/**` 是 blocked，loop 无权改；
  STATE §3 `[open] 2026-08-24T09:20Z` 已登记，本 plan **不重复登记、不代人处置**。
  D3 的残余风险处置已把承重判据同时钉在 `tests/unit` 上（**Phase 2 ⑪**，M6 / M7 各打红一半）。
- Successor Required: `no`（由人处置既有那条 `[open]`）
- 重开事件：**人把 `tests/context` 接进 `missions/*.json` 的 `commands.test` 之后**

## 12. 执行记录

执行日期 **2026-08-25**，开工基线 sha `9dea949ba1b19915baa50de5fcb1961cb75010e6`（工作区干净）。

### 12.1 七条基线命令（收口时复跑，逐条实读）

⚠️ 复跑前先跑 `env | grep AGENERP_LLM_`（H7 的前置）：只有 `AGENERP_LLM_MODEL=qwen3.6-plus` 一行，
`BASE_URL` / `API_KEY` **未 export** ⇒ `tests/routing/test_live_endpoint.py` 仍 skip。

| # | 命令原文 | 退出码 | 输出尾行 | 与基线 |
|---|---|---|---|---|
| ① | `python3 tools/gates/check_expected_red.py` | **0** | `门禁 11 项：预期红 0，绿 11，跳过 0` / `✅ 与预期红名单完全一致` | 不变 |
| ② | `python3 -m pytest tests/unit -q` | **0** | `626 passed` | **614 → 626**（+12，H9 吻合） |
| ③ | `python3 -m pytest tests/contracts -q` | **0** | `151 passed` | 不变 |
| ④ | `python3 -m pytest tests/tools -q` | **0** | `81 passed, 12 skipped` | 不变 |
| ⑤ | `python3 -m pytest tests/routing -q` | **0** | `167 passed, 1 skipped` | 不变（H7 吻合） |
| ⑥ | `python3 -m pytest tests/context -q` | **0** | `54 passed` | **53 → 54**（+1，H8 吻合） |
| ⑦ | `python3 -m pytest tests/experiments -q` | **0** | `10 passed` | 不变 |

`ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
→ **exit 0**（`All checks passed!`）。

⚠️ **两条不在上表、也不在 `commands.test` 里的命令收口时同样跑了，实读为红，且红在基线上就已经红**
（裁判规则 3：先原样复跑，不猜根因）：

- `ruff check agenerp tests tools` → **exit 1**，全部命中在 `tools/gates/check_budget.py:142-143`（`F541`）。
  **本 plan 一个字未动该文件**；`git stash` 到基线复跑 **同样 exit 1**。
  （这正是 Phase 1 Exit 那条 ruff 命令的路径清单不含 `tools/` 的原因。）
- `node tools/check-doc-references.mjs` → **exit 1**，失败 **77 条**；基线复跑同样 **exit 1 / 77 条**，
  **逐条 diff 后只有行号位移**（本 plan 在 §7.7 / §7.11 插了行），
  **一条新失败都没引入**，且失败清单里**没有** `p1-cache` / `model-management.md` / 本 plan 新增的任何内容。
  `bash tools/check-masterplan-links.sh` → **exit 0**。

### 12.2 H1–H9 逐格对照（§6 原文一个字未改）

⚠️ **实测落在「全 0」那一支** ⇒ §6.1 的四条逐条执行，H1 / H4 按其第 2 条逐字标注。

| # | 假设（§6 写死的） | 实测 | 判定 |
|---|---|---|---|
| **H1** | 第 1 次调用 `cached_tokens == 0` | 第 1 次 `prompt 1,054` / `cached 0` | **吻合，但「该支下恒真，不构成证据」**（§6.1 第 2 条） |
| **H2** | 第 2 次及以后至少一次 `cached_tokens > 0` | **10 次逐次全为 0** | **不吻合。这就是本项目端点上的结论**：「隐式前缀缓存在本配置下未生效或未上报」。⚠️ **照实记，未改假设、未换模型、未重跑**（§6 逐字禁止） |
| **H3** | 若 H2 成立：`S = {i : c_i == max(c)}`，判 `S ∩ {N, N-1} != ∅` | H2 落空 ⇒ `max(c) = 0`、`S = {1..10}`、`\|S\| = 10`，`S ∩ {10, 9} = {9,10} != ∅` | **前提未成立，该支下恒真** ⇒ **不构成证据**，照实记而不记「吻合」 |
| **H4** | 逐次 `cached_tokens ≤ prompt_tokens` | `0 ≤ 1,054 … 0 ≤ 11,851`，10/10 成立 | **吻合，但「该支下恒真，不构成证据」**（§6.1 第 2 条）。**未把断言放松成 `>= 0`** |
| **H5** | 判定器 48 次单发全 0，而本次多轮至少一次 > 0 | **两者都全为 0** | **不吻合（混淆已预先声明）**。按 §6 写死的处置：「**「多轮 vs 单发」的差异在本项目上不存在**」。⚠️ 裁定规则的另一支（第 1 次为 0、后续更长的 > 0 ⇒ 支持「长度阈值」解释）**未触发** |
| **H6** | `total_matches_endpoint` N/N 全真，且 `usage_total_session["total"] == prompt + completion` | `total_matches_endpoint` **10/10**；`56,343 + 6,770 = 63,113` == `total` ✅；另 `reasoning_matches_endpoint` **10/10**、`cached_matches_endpoint` **10/10**；账本 `total` 与 `ConversationSession.usage_total` **逐项相等** | **吻合**（回归面无缺陷，无需 Deferred） |
| **H7** | `tests/routing` 逐字仍 `167 passed, 1 skipped` | 逐字一致，`env | grep AGENERP_LLM_` 前置已确认 live 变量未 export | **吻合** |
| **H8** | `tests/context` **53 → 54** | `54 passed` | **吻合** |
| **H9** | `tests/unit` **614 → 619 → 626**，新文件恰 **12** 条 | Phase 1 结束 `619 passed` / 新文件 **5** 条；Phase 2 结束 `626 passed` / 新文件 **12** 条 | **逐格吻合** |

⚠️ **实测比 §6 预想的更彻底一层，照实记**：端点**十次都报了** `prompt_tokens_details`，
但那个子对象的键集**逐次恒等于 `{"text_tokens"}` —— 根本没有 `cached_tokens` 这个键**。
即本次的 `0` 不是「端点说命中了 0 个」，而是「端点根本没说」。
这**恰好是 D2 残余风险（`0` 有两个含义）在实测中落地的样子**，
也证明 §6.1 第 4 条「必须原样落原始子对象」不是多余的手续。
⚠️ 与 `docs/evidence/p1-answer-judge/` 的 48 个回包（`{"cached_tokens": 0, "text_tokens": N}`，
**键在、值为 0**）成因不同，**本 plan 不解释这个差异、不猜根因**（裁判规则 3）。

### 12.3 M1–M10 变异结果（**没有 M11**）

文件级 `cp` 备份还原，**全程未用 `git checkout`**；每个变异跑完当场比对文件内容一致才继续。

| # | 变异（产品侧） | 指定的红灯 | 实测 |
|---|---|---|---|
| M1 | `usage_of()` 不读 `prompt_tokens_details`，`cached` 恒 0 | Phase 1 ① + Phase 2 ⑥ | 两条各 **exit 1** ✅ |
| M2 | `cached` 被算进 `total` | Phase 1 ③ + Phase 2 ⑨ | 两条各 **exit 1** ✅ |
| M3 | `cached` 读成 `completion_tokens_details` 的细分 | Phase 1 ① | **exit 1** ✅ |
| M4 | 整个 `usage` 缺失时 `endpoint_cached` 记 `0` 而非 `None` | Phase 2 ⑦ | **exit 1** ✅ |
| M5 | `cached_matches_endpoint` 写成拿端点的数跟自己比（恒真） | Phase 2 ⑧ | **exit 1** ✅ |
| M6 | `store.py` 落盘仍写三键 | Phase 2 ⑪(a) + `tests/context` 键集那条 | 两条各 **exit 1** ✅ |
| M7 | 落四键但读回只读三键（静默丢数） | Phase 2 ⑪(b) 的 round-trip | **exit 1** ✅ |
| M8 | 账本加「`cached` 超过 X 就拒答」的分支 | Phase 2 ⑩（D-18 回归） | **exit 1** ✅ |
| M9 | `Usage.as_dict()` 不出 `cached` 键 | Phase 1 ⑤ + Phase 1 ③ | 两条各 **exit 1** ✅ |
| M10 | `Usage.plus()` 漏加 `cached` | Phase 1 ④ + Phase 2 ⑨ | 两条各 **exit 1** ✅ |

**十个变异全部由绿转红，没有一条需要就地补断言 ⇒ 没有 M11。**
还原后 `git status --porcelain` 与 Phase 2 结束时**逐行相同**，`tests/unit` / `tests/context` 复跑全绿。

### 12.4 §1.6 漂移面的收口复核（逐字复跑 grep-1 与 grep-2）

改后复跑，命中**按三类归档，三类之外零命中**：

**① 改准（11 处，逐处已落地）**：`adapter.py:8`（模块 docstring 的「三项」）·
`ledger.py:9-11,16,124` · `store.py:48` · `session.py:13-17,147` · `explain/loop.py:240` ·
`agent_conversation_session.json` 的 `turns` `description` ·
`module-boundaries.md:347` / §7.7 / §7.11 · `model-management.md:57,240`。
⚠️ `adapter.py:42` 那句 `reasoning …不是第四个桶` **按 §1.6 保留原句**（它讲 completion 侧，仍然对），
`cached` 那句**另起**，两句并存 —— 复跑后 grep-1 仍命中该行，**属预期**。

**② 一个字不改（4 处，复跑逐字确认未被触及）**：
`tools/experiments/p1_entry_gate/llm.py:40` 与 `loop.py:13`（Non-Goals 6 的冻结面）·
`module-boundaries.md` 里 P1.5 的**历史记录**两行（改后位移为 `:2538` / `:2601`，
`git diff` 复核**内容逐字未动** —— 改它等于改历史，硬约束 ②）。

**③ 无关命中，不改（3 处，§1.6 已预先点名）**：`seedsite.py:267` / `:870` · `contracts.py:161`
（讲的是别的「三项」）。grep-2 在 `ledger.py` 的十处**代码标识符**行随实现自然改，不进逐行对照。

⚠️ **改后新出现的一处命中，当场处置了**：`ledger.py:46` 原写「整个 `usage` 都没有时三项都是 `None`」
—— 这里的「三项」指 `_endpoint_numbers` 回的三个数（`total`/`reasoning`/`cached`），
语义正确但与「token 三项」撞词。已改为「**这三个数全是 `None`**」，消歧。

### 12.5 红线自证（对基线 `9dea949` 复核）

- `git diff --name-only 9dea949 HEAD -- tests/gates .github/workflows missions tools/experiments/p1_entry_gate ':!docs/masterplan/STATE.md' docs/masterplan` → **无输出**
- `git diff --numstat 9dea949 HEAD -- docs/masterplan/STATE.md` → **删除列为 0**（只追加一行）
- 证据仓 `XM_PATH` **未写入**；**未生成任何运行时 Server Script**；项目名 / 包名 / 命名空间**未动**
- `DECISIONS.md` **一个字未改**，未新增 `R-x`

### 12.6 活端点实跑

一次性脚本**不进仓**（照 P1.4 / P1.7 先例），做法是在 `explain(transport=…)` 上包一层记录型 transport
（形先例 `judge.py` 的 `Verdict.endpoint_usage`），**产品代码为此一行未改**。
一次跑通，**未重跑**（`elapsed 124.3s`，`stopped = answered`，`accepted = true`，失控闸未触发）。
证据落 `docs/evidence/p1-cache/live-run-01.json` + `README.md`，
**逐次 `prompt_tokens_details` 原始子对象在场**，落盘前逐个凭据环境变量扫过产物，**零命中**。
⚠️ **只调只读工具，一条业务数据都没写。**

## Closure Gates

- [x] in-scope behavior is complete
- [x] relevant docs are aligned（落点节 §7.17 + §12.2 指针行）
- [x] verification has run（七条基线命令 + 一次活端点实跑，命令原文与退出码记进 §12）
- [x] scoped verification is not conflated with full verification —— ⚠️ **预先声明**：
      `tests/context` / `tests/routing` **不在 `commands.test` 里**，
      因此这两条的绿**不代表 `GATE_VERIFY` 复跑得到**，收口时须逐字写「verification scope limited」
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded（§10）
- [x] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent —— ⚠️ **未满足，留白，照实记**：本轮执行环境不具备独立子代理
      （沿用同工作项第 1 个 plan `2026-08-24-2109-2` 收口时的同一条处置）。
      走的是 AGENTS.md `Reviewer-Availability Fallback` 允许的**单人冷复跑**，
      **并在此记下该限制**：本 plan 非受保护面（Phase 1–4 的 `Targets` 已逐条比对四个受保护 pathspec，
      `git diff` 实测无输出）、无未决产品风险、无真相源冲突，因此该 fallback 适用。
      **它不等于独立审计** —— 想要独立审计的话，须由人另起一个全新会话的子代理复核。
- [x] closure evidence exists in files
- [x] §9 红线七条逐条复核，且 `git diff` 四个 pathspec 无输出

## Closure

Status Note: **十项 Closure Gates 中九项满足，第八项（`closure audit was independent`）未满足并留白。**
`Plan Status` 已置 `completed`，**依据是同工作项第 1 个 plan `2026-08-24-2109-2` 的同一条先例**
（该 plan 亦在独立收口审计缺位时置 `completed` 并把该 gate 留白）
与 AGENTS.md 的 `Reviewer-Availability Fallback`。
⚠️ **不把单人冷复跑说成独立审计。**

Closure Audit Evidence:

- Auditor / Agent: **无独立审计者** —— 本轮执行环境不具备独立子代理。
  实际走的是**执行者本人的冷复跑**（AGENTS.md `Reviewer-Availability Fallback`），
  **该限制已在 Closure Gates 第八项与 `STATE.md` §2 的证据行里逐字记下**。
- Evidence（全部落在文件里，非聊天记忆）：
  - 命令原文 + 退出码 + 条数：§12.1（七条基线命令逐条实读）+ commit `1b1625f` 的 message
  - commit sha：`1b1625f8b6874b3ed0346cf7bb05b52bede62023`（基线 `9dea949ba1b19915baa50de5fcb1961cb75010e6`）
  - 假设对照：§12.2（H1–H9 逐格，§6 原文一个字未改）
  - 变异结果：§12.3（M1–M10 全红，**没有 M11**）
  - 漂移面复核：§12.4（逐字复跑 grep-1 / grep-2，按三类归档，三类之外零命中）
  - 红线自证：§12.5（四个 pathspec `git diff` 无输出；`STATE.md` 删除列为 **0**）
  - 活端点证据：`docs/evidence/p1-cache/live-run-01.json` + `README.md`
    （逐次 `prompt_tokens_details` 原始子对象在场；凭据扫描零命中）
  - 落点节：`module-boundaries.md` §7.17 · `model-management.md` §12.2 指针行
  - 日志：`docs/logs/2026/08-25.md`（三条，逐 Phase）

Follow-up（**均为 §11 已裁定的 Deferred，非确认缺陷**）:

- §11 的**五条** Deferred 原样有效。⚠️ **工作项 9 的 plan 预算（表规 3 的 1–2 个）到此用尽** ——
  其中任何一条将来重开，须由**人**在 `02-WBS.md` 拆行 / 加行（红线 5，loop 无权）。
- 其中两条因本次实测而**状态更明确，但都未触发重开**：
  - 「改写 §12.2 那句结论」—— 本次测出的负结果**支持重新审视它**，但**一次实测不是分布**，
    重开事件逐字是「**人明确裁定改写 §12.2**」，**今天未触发**。
  - 「以提高命中率为目的的前缀重排 / 提示词改造」—— ⚠️ **H2 落空成「全程 0 命中」
    逐字不构成本条的重开**（§11 原文）。那时该做的是查「为什么没生效」，不是重排前缀。
- ⚠️ **新观测到、但本 plan 不处置的一件事**（不是本 plan 引入的缺陷，故不列为 Follow-up 之外的项）：
  端点在 `prompt_tokens_details` 里**根本没报 `cached_tokens` 键**，
  与 `docs/evidence/p1-answer-judge/` 那 48 个回包（键在、值为 0）成因不同。
  **本 plan 不解释这个差异、不猜根因**（裁判规则 3）。
