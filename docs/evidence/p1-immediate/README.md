# ① 即时上下文接进解释循环的活端点证据（P1.8 前置，2026-08-25）

本目录是 plan
[`2026-08-24-2311-1-immediate-context-into-explain-loop.md`](../../plans/p1-insight/2026-08-24-2311-1-immediate-context-into-explain-loop.md)
Phase 3 的 **活端点两跑** 落盘证据：**同一道题，唯一变量是带不带 ① 即时上下文**。

**每侧只有一跑。** plan §7 Phase 3 逐字「**一跑不是分布**」——
结论只覆盖这一道题、这一次。多次采样是成本实验，属另一个 plan（D-16）。

⚠️ **不与任何数字作优劣比较**：本目录的数与
[`p1-explain/`](../p1-explain/) 的 45,195、[`p1-cost/`](../p1-cost/) 的 58,579
是**三次不同的解释**，本 plan 没做任何成本工作。并排读成「变便宜了 / 变贵了」是错的。

## 文件

| 文件 | 内容 |
|---|---|
| `live-run-without-immediate.json` | A 跑：`immediate=None` |
| `live-run-with-immediate.json` | B 跑：`immediate=<活站点取回的销售订单字段表>` |
| `immediate-source-doc.json` | ① 档的**来源**：`GET /api/resource/Sales Order/SAL-ORD-2026-00001` 的 `data`，**70 个字段，一个字没手写** |
| `summary.json` | H4 / H5 的两项计量 + 死端同一性的活端点复核 |

两个 run JSON 同形制（键的读法见 [`p1-cost/README.md`](../p1-cost/README.md)），
另加两个本目录特有的键：`immediate_attached` 与
`opening_immediate_is_the_caller_object`（**活端点上的 J10** ——
`result.opening.immediate is <调用方传进去的那个对象>`，实测 `true`）。

## 两跑的口径（照实写，不含糊）

- 题目：`tools/experiments/p1_entry_gate/question.md` **逐字**（与 P1.4 / P1.7 两跑同题，取它是为了可比）。
- 模型：`qwen3.6-plus`（`requested=`，由 `route()` 挑出，不静默降级）。
- 开场候选集：**10 个 DocType**（`Sales Order` / `Delivery Note` / `Work Order` / `Stock Entry` /
  `Stock Ledger Entry` / `Bin` / `Subcontracting Receipt` / `Item` / `Warehouse` / `Customer`）。
  两跑相同，`opening_request_count` 两侧都是 **10**。
  ⚠️ 这是**本跑的选择**，不声称与 P1.4 那一跑的 10 个逐字相同（那一跑没把清单记下来）。
- ① 档：`assemble(doctype="Sales Order", name="SAL-ORD-2026-00001", fields=<站点取回的 70 个字段>,
  role="Administrator（本地 compose 身份）", view="销售订单详情")`，
  序列化后 **5,478 字符**。⚠️ `role` / `view` 是**调用方给的标签**，
  ① 层不打站点、不查权限（`immediate.py` 模块头规矩 1）—— 这一跑的身份就是 Administrator，
  没有任何权限过滤发生。P1.8 让浏览器发起解释时这条必须由承载面回答（plan §8 R1）。
- 走的是**导出面 `explain(...)`**（不是自建的 `ExplainLoop`）—— 本 plan 动的正是它的签名。

## H4 / H5 逐条对照（plan §6 写死的预测 → 实测）

| §6 的预测 | 实测 | 吻合 |
|---|---|---|
| **H4** 带 ① 时，整跑中对**同一个 `name`**（`SAL-ORD-2026-00001`）的 `doc.get` 次数为 **0** | **0**（不带的那跑是 **1**，是它的第一个动作） | **吻合** |
| **H5** 带 ① 的 prompt token **高于**同题不带的一跑（方向性预测，**不作优劣比较**） | **看在哪一层：第 1 次模型调用上 3,775 vs 1,066（高于，+2,709）；整跑合计 75,159 vs 101,282（低于）** | **部分吻合，前提有错** |

**H4 照实说明**：plan 起草期写着「H4 很可能不吻合 —— 模型完全可能出于『核对』再取一次」。
实测**吻合**：带 ① 的那跑第一个动作直接是 `doc.links`，没有回头再取那张单。
但这**只是一跑**，不能读成「注入总能省掉那次取数」。

**H5 的前提哪里错了**（不改预测列，照实记）：
H5 隐含假设「两跑除了注入那一段以外**一样**」，于是整跑合计可以直接比。
实测两跑的**轮数不同**：不带 **12 次**模型调用且撞上 `max-turns`（`stopped: "max-turns"`，
`accepted: false`，12 轮用完仍未作答）；带 ① **9 次**且 `stopped: "answered"`、`accepted: true`。
轮数不是常量，整跑 prompt 合计因此**主要反映轮数差**，不反映注入量。
**注入量本身可直接归因的是第 1 次调用**：那一次两跑的消息序列除了注入那一条外完全相同，
实测 **+2,709 prompt token**（① 档 5,478 字符）—— **在这一层 H5 的方向吻合**。

⚠️ **「不带的那跑没答出来」不是本 plan 的结论**：那是一跑的观察，不是分布，
也没做过任何控制（同一道题的路径每跑都可能不同）。**不据此声称注入让解释更容易成功。**
两跑的工具路径逐条记在各自的 `trace.tool_calls` 里，任何人可自行复核。

## 怎么复跑

一次性运行器写在 `_tmp/`（**gitignored，不进仓** —— 它不是产品件，也不是判据）。复跑需要：

```bash
set -a; . ~/.config/agenerp/secrets.env; . ./.env; set +a   # DASHSCOPE_API_KEY
export PYTHONPATH="$PWD"
export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin
export AGENERP_LLM_BASE_URL="$DASHSCOPE_BASE_URL" \
       AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY" \
       AGENERP_LLM_MODEL=qwen3.6-plus
```

运行器做的事就四步：`client_from_env("frontend")` →
`client.get("/api/resource/Sales Order/SAL-ORD-2026-00001")["data"]` → `assemble(...)` →
`explain(..., immediate=None)` 与 `explain(..., immediate=<那份>)` 各一次。

⚠️ **`.env` 里已经没有 `DASHSCOPE_API_KEY` 了**（plan §5 写的是它的旧位置）：
用户 2026-08-24 明示敏感凭据一律放 `~/.config/agenerp/secrets.env`（0600，仓库目录之外）。
上面的加载命令按**实际位置**写。

## 凭据

**这份产物里没有任何凭据。** key 只从环境变量读，不打印、不写进 JSON
（`docs/masterplan/04-RUNBOOK.md` §5.6）。落盘前对四个 JSON 逐个扫过
`sk-` / `api_key` / `password` / `secret` / `Bearer` / `token=`，**命中 0**。
