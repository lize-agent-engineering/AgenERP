"""解释 Agent 的**控制循环本体** —— 开场注入 → 模型选工具 → `execute` → 结果回注 →
作答 → 证据充分性门禁判定 → 不满足则强制续跑；满足才把答案交出去。

落点节是 `docs/architecture/module-boundaries.md` §7.8。形状继承
`tools/experiments/p1_entry_gate/loop.py`（P1.0 的实验设施，**一行不动、不复制文件**），
**换掉四个零件**：

| 零件 | 实验设施 | 本模块 |
|---|---|---|
| 模型侧 | 自带的 `llm.py`（模块头逐字「实验设施，不是产品代码」） | `agenerp.routing.route()` → `ChatAdapter`（D1） |
| 开场侧 | 没有（`permission.scope` 因此被排除在工具面外） | `agenerp.orchestration.open_session()`（D3） |
| 会话侧 | 一个 `Trace` dataclass | `agenerp.context.session` 的 `Turn` / `ToolCall` / `ExecutedAction` |
| 熔断侧 | 没有 | `agenerp.orchestration.DenialBreaker`（§7.4 欠账，本模块结清） |

**门禁在两处求值，事实采集面只有一份**（D2）：① 工具前置（`QUERY_READ` /
`SNAPSHOT_READ` 的 `preconditions`，P1.0a 已在）卡「作答类工具能不能调」；
② 作答前（本模块新增）卡「这个 answer 能不能被接受」。只有 ② 拦得住
「模型不调作答类工具、直接凭 `doc.get` 的返回值报数字」——那正是 Spike 02 实测到的失败形态。
两处都走同一个 `EvidenceSurface` 实例，同源性由它自己的 `uses` 留痕承担。

⚠️ **`permission.scope` 不进模型可见的工具面**（D3）。理由与实验设施**不同**：
实验期是「本设施没实现开场注入」，本期是「开场注入**已由 P1.3 实现**，再让模型自己调一次
等于把已经确定性化的一步交回给模型（D-15：规则能覆盖的流程不 Agent 化）」。
残余风险：模型若需在开场包之外更新可见范围（例如换身份），本期没有这条路径 —— watch-only。

⚠️ **`max_turns` 只为防跑飞，不是失控闸** —— 失控闸是**另一个**上限，`MAX_TOOL_CALLS`
（P1.7 / D-18 已在本模块落地）：它数的是**单次解释的工具调用总数**，因为一次回复可以携带
K 个 `tool_call`，轮数根本不设限于此。两者**必须能独立触发**，`STOP_RUNAWAY` 因此是
**专属**停止原因，不复用 `STOP_MAX_TURNS`。判据在 `tests/unit/test_explain_runaway_guard.py`。

⚠️ **成本记账也已在本模块落地**（P1.7 / D-18）：账本本体是 `agenerp/explain/ledger.py`，
采集面是下面 `run()` 里那**唯一一个** `adapter.chat(...)` 调用点的**两条出口**。
**记账，不拦截** —— 这里没有阈值。`ConversationSession.usage_total` 那个载体**仍然保留**
（P1.4 的既有导出面，`ExplainResult.usage` 读它），但两者口径不同：**要算钱就读账本**
（`ExplainResult.cost_ledger`）。分工写死在 `docs/architecture/module-boundaries.md` §7.11。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from agenerp.context import session as conversation
from agenerp.context.immediate import ImmediateContext
from agenerp.context.session import ConversationSession, ExecutedAction, ToolCall, Turn
from agenerp.explain import gate as evidence
from agenerp.explain.gate import EvidenceSurface
from agenerp.explain.ledger import CallLedger
from agenerp.orchestration import DenialBreaker, OpeningPack, open_session
from agenerp.routing import RoutingError, route
from agenerp.routing.adapter import ChatAdapter, Usage
from agenerp.site import SiteClient
from agenerp.tools.runtime import Executor, execute
from agenerp.tools_readonly import READONLY_CONTRACTS

# 每次调用允许模型写多少 token。防一次跑飞，不是运行预算（预算归 P1.7）。
PER_CALL_OUTPUT_TOKENS = 4096

# 2026-08-26 由 25 提到 40，**依据是实测不是拍脑袋**（D-16）。
# 归因类问题（「这些库存是怎么来的」）在修好 `doc.links` 之后仍有 1/3 撞 `max-turns`：
# 实测 `23/32` 工具调用却用满 25 轮 —— **卡的是轮数不是工具数**。
# 收敛的那几次用 **12–13 轮 / 19–25 次调用**；给到 40 轮后同一问题答了出来
# （1,010 台、三笔流水、逐笔指到 Stock Ledger Entry 与业务单据）。
# ⚠️ 轮被吃掉的主因是**证据充分性门禁把答案顶回去重答** —— 那是它该做的事，
# 但每顶一次就是一轮。轮数上限太紧 ⇒ 门禁刚开始起作用就没轮次了。
MAX_TURNS = 40

# 工具返回值回注给模型时的字符上限。契约的 `max_rows` 框的是行数，这一层框的是字符数：
# 一行也可能很长（`doc.get` 一张单据）。
# 每条工具结果进上下文前的字符上限。
#
# 🔴 2026-08-27 由 **6000 提到 20000**，**依据是实测不是拍脑袋**（D-16）。
#
# 人指出：「如果上下文给的正确的话，我给的那些模型都能够给出正确的回答，
# 否则就是 harness 没有做到位。」——**查下去，人是对的。**
#
# 独立评测集 60 条逐条核（零 token，走真工具层 + 本函数的 `_clip`）：
#   🔴 **7 条题的正解字段，agent 根本看不见** —— `meta.fields` 的返回被切在了它前面。
#      其中 **5 条是 hard 档** ⇒ 这直接解释了 hard 档为什么只有 73.3%。
#   例：`Payment Entry` 的字段表 **18,416 字符 / 98 字段**，切到 6000 只剩三成。
#
# ⚠️ **而我此前把其中三条判成了「真能力失败」，判错了**：
#   · `Purchase Receipt Item.rejected_warehouse`（烧 230,024 token）
#   · `Payment Entry.reference_date`
#   · `Sales Order Item.prevdoc_docname` —— 我还拿「两个模型都编出同一个不存在的
#     `Sales Order Item.quotation`、**跨模型复现**」当过「真能力失败」的硬证据。
#   三条全在那 7 条名单上。**「跨模型复现」不是能力弱的证据 ——
#   是两个模型收到的是同一份被切残的字段表，只能猜。**
#
# 20000 这个数是量出来的：评测集涉及 50 个 DocType，那 7 条所在的
# DocType **全部 ≤ 18,416 字符** ⇒ 20000 让它们全部可见（留 ~8% 余量）。
# 实测装得下的比例：6000 → 58% · 12000 → 74% · 16000 → 88% · **20000 → 92%**。
#
# ⚠️ **剩下的 8% 本次没解决，照实记**：`Sales Order` / `Purchase Order` /
# `Purchase Invoice` / `Quotation` 四个各约 **38,000 字符**，而且它们**正好是 200 字段**
# —— 那是契约 `max_rows=200` 的上限，说明它们在 `_clip` 之前**就已经被契约层截过一次**。
# 对这种体量，「把整张字段表倒给模型」本身就是错的形状，该给 `meta.fields` 加**按关键词过滤**。
# 那是契约层改动（`tools_readonly.py` + 门禁），**不在本次范围内，留给人裁定。**
#
# ⚠️ **代价照实记**：20000 字符 ≈ 5–7k token/条结果，上下文更贵了。
# 但对照是：看不见答案时它会盲搜 —— 实测一条题 **42 次工具调用 / 445,431 token**。
# 一次 18k 的完整字段表，比四十轮盲搜便宜一个数量级。
RESULT_CHARS = 20000

EXCLUDED_TOOLS = ("permission.scope",)

STOP_ANSWERED = "answered"
STOP_BREAKER = "permission-breaker"
STOP_MAX_TURNS = "max-turns"
# **专属停止原因，不复用 `STOP_MAX_TURNS`** —— 三道闸必须能各判各的（D-18）。
STOP_TOKEN_BUDGET = "token-budget"
STOP_MODEL_ERROR = "model-error"
# **失控闸专属**，不复用上面任何一个（D-18 逐字「两者的判据分开写，不许合并」）。
STOP_RUNAWAY = "tool-call-runaway"

# 单次解释允许模型发起多少次工具调用 —— **失控闸，不是成本闸**（P1.7 / D-18）。
#
# ⚠️ **它与 `MAX_TURNS` 各管一维，不许合并**：`MAX_TURNS` 限的是主循环**轮数**，
# 而一次回复可以携带 K 个 `tool_call`，`K` 由模型决定 —— 轮数没到上限，
# 工具调用早就可以爆到 `MAX_TURNS × K`。D-18 要挡的「调得通但陷入循环」正是后者。
#
# **取值 32 的两段算术，依据只能是本项目实测**（外部经验值一律不引）：
# ① 对实测留余量：P1.4 那一次活端点解释实测 `trace.execute_calls == 8`
#    （`docs/evidence/p1-explain/live-run-01.json`）—— 这是本项目**唯一**可引用的数字。
#    32 = 8 × 4，给真实解释留四倍余量。
# ② 对 `MAX_TURNS` 留余量，**严格大于**：`loop.py` 的主循环是 `range(1, max_turns + 1)`，
#    「每轮发一次工具调用」的正常形态下第 25 轮恰好是第 25 次调用。默认值取 25 时，
#    失控闸会**赶在 `STOP_MAX_TURNS` 之前**触发，产品默认路径上 `max-turns` 永不可达，
#    失控闸就地退化成一个更严的 `max_turns` —— **那正是 D-18 禁止的合并**。
#    所以下界是 `MAX_TURNS + 1 = 26`（等号处不算数），32 > 26。
# 2026-08-26 由 32 提到 50（人裁定）。实测收敛只要 19–25 次，**50 是余量不是目标**。
# ⚠️ **提上限会同时抬高最坏成本**：D-26 定的 20 万 token/次是按当时实测推的，
# 本次改动之后最坏情况可能越过它。**那条上限不因本改动自动跟着涨** ——
# 若实测出现越界，按 D-26 原来的推导法重算，不要临时放宽。
MAX_TOOL_CALLS = 50

BREAKER_ACTION = "circuit.denial_breaker"

# 每个工具的调用参数。**契约不声明参数形状**（它声明的是前置/后置/裁剪），
# 所以这份 schema 属于循环侧；它只描述**怎么调**，不新增任何约束。
TOOL_PARAMS: dict[str, dict] = {
    "system.overview": {"type": "object", "properties": {}},
    "schema.search": {
        "type": "object",
        "properties": {"keywords": {"type": "string", "description": "空格分隔的关键词"}},
        "required": ["keywords"],
    },
    "meta.fields": {
        "type": "object",
        "properties": {"doctype": {"type": "string"}},
        "required": ["doctype"],
    },
    "doc.get": {
        "type": "object",
        "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}},
        "required": ["doctype", "name"],
    },
    "doc.links": {
        "type": "object",
        "properties": {"doctype": {"type": "string"}, "name": {"type": "string"}},
        "required": ["doctype", "name"],
    },
    "lineage.trace": {
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "name": {"type": "string"},
            "depth": {"type": "integer", "description": "展开几跳，默认 1"},
        },
        "required": ["doctype", "name"],
    },
    "query.read": {
        "type": "object",
        "properties": {
            "doctype": {"type": "string"},
            "fields": {"type": "array", "items": {"type": "string"}},
            "filters": {
                "type": "array",
                "items": {"type": "array", "items": {"type": "string"}},
                "description": '形如 [["item_code","=","X"]]',
            },
            "limit": {"type": "integer"},
        },
        "required": ["doctype"],
    },
    "snapshot.read": {"type": "object", "properties": {"scope": {"type": "string"}}},
    "rule.lookup": {"type": "object", "properties": {"doctype": {"type": "string"}}},
}

SYSTEM_PROMPT = (
    "你是 ERP 的解释 Agent。只能通过给定的只读工具取证，"
    "不许凭常识或记忆报任何数字。取证不足时继续调工具，不要猜。"
)

# ① 即时上下文注入那条消息的抬头。正文是 `blocks()` 里 `key == "document"` 那块的
# `payload` 原样序列化，抬头与正文之间**只有一个换行** —— 判据据此把正文解析回来。
IMMEDIATE_PREFIX = "当前单据（由调用方在发起解释时给定，已在上下文中，不必再取一次）："

# ① 档在 `ImmediateContext.blocks()` 里的块名。**按名取，不按下标取**：
# 下标取会在 `blocks()` 改序时静默串档（§7.12 的 D2 残余风险）。
IMMEDIATE_BLOCK_KEY = "document"


def tool_schemas() -> list[dict]:
    """OpenAI 兼容的工具声明，**由契约生成**：契约表变了这里自动跟着变。"""
    return [
        {
            "type": "function",
            "function": {
                "name": contract.tool.replace(".", "_"),
                "description": f"{contract.tool} —— 目标：{contract.target}",
                "parameters": TOOL_PARAMS[contract.tool],
            },
        }
        for contract in READONLY_CONTRACTS
        if contract.tool not in EXCLUDED_TOOLS
    ]


def _tool_name(wire_name: str) -> str:
    return wire_name.replace("_", ".", 1) if "_" in wire_name else wire_name


def _clip(text: str) -> str:
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS] + "…（已截断）"


@dataclass
class ExplainTrace:
    """一次运行的结构化轨迹。**它是判定的原料**，所以什么都不许省略。

    判据全部落在这里与假站点的请求记录上，**不落在答案文本上** —— 那是「答对」与「蒙对」的分界。
    """

    question: str
    model: str = ""
    task_class: str = ""
    turns: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    gate_checks: list[dict] = field(default_factory=list)
    forced_continues: list[str] = field(default_factory=list)
    breaker_events: list[dict] = field(default_factory=list)
    runaway_events: list[dict] = field(default_factory=list)
    model_tool_calls: int = 0
    opening_request_count: int = 0
    execute_calls: int = 0
    stopped: str = ""
    cost_ledger: CallLedger = field(default_factory=CallLedger)

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "model": self.model,
            "task_class": self.task_class,
            "opening_request_count": self.opening_request_count,
            "execute_calls": self.execute_calls,
            "stopped": self.stopped,
            "model_tool_calls": self.model_tool_calls,
            "cost_ledger": self.cost_ledger.as_dict(),
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "gate_checks": self.gate_checks,
            "forced_continues": self.forced_continues,
            "breaker_events": self.breaker_events,
            "runaway_events": self.runaway_events,
        }


@dataclass(frozen=True)
class ExplainResult:
    """一次解释的产物。`accepted` 是判定面 —— **答案被交出去，当且仅当它为真**。"""

    answer: str
    accepted: bool
    trace: ExplainTrace
    session: ConversationSession
    surface: EvidenceSurface
    breaker: DenialBreaker
    opening: OpeningPack | None = None

    @property
    def usage(self) -> Usage:
        """累计用量。走 `ConversationSession.usage_total`（内部逐轮 `Usage.plus()`），
        **不自己写四项加法** —— 自己写就会与 P1.1 漂移（§7.7 逐字）。

        ⚠️ **它不是成本账本，两者的权威面分工写死在落点节 §7.11**（P1.7 的 `Decision` D2）：
        本属性答的是「**这次会话累计了多少**」（口径：成为了一轮对话的那些调用）；
        `cost_ledger` 答的是「**这次解释一共调了几次模型、各花了多少**」
        （口径：`adapter.chat` 发生过几次）。正常路径上两者逐项相等；
        模型抛错那一次**没有 turn**，所以异常路径上账本 ≥ 本属性 ——
        **要算钱就读账本**。判据钉在 `tests/unit/test_explain_cost_ledger.py`。
        """
        return self.session.usage_total

    @property
    def cost_ledger(self) -> CallLedger:
        """本次解释的成本账本（P1.7 / D-18）：一次模型调用一条记录。

        **记账，不拦截** —— 这里没有阈值，也没有任何「超了就……」的分支。"""
        return self.trace.cost_ledger


class ExplainLoop:
    """控制循环本体。

    **`answer_gate_enabled` 不进产品导出面**（D7）：在一道安全闸上给产品面开关，
    调用方一行就能关掉。判据侧要做消融就直接构造本类，产品入口 `explain()` 永远走默认值
    `True`。⚠️ ① 工具前置那一面**全程开着、无开关**（那是 P1.0a 已收口的契约声明），
    消融**只作用于 ② 作答前那一次求值**。
    """

    def __init__(
        self,
        *,
        adapter: ChatAdapter,
        client: SiteClient,
        answer_gate_enabled: bool = True,
        max_turns: int = MAX_TURNS,
        max_tool_calls: int = MAX_TOOL_CALLS,
        per_call_output_tokens: int = PER_CALL_OUTPUT_TOKENS,
        max_run_tokens: int | None = None,
        executors: Mapping[str, Executor] | None = None,
        doctypes: Sequence[str] | None = None,
        breaker: DenialBreaker | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        immediate: ImmediateContext | None = None,
    ) -> None:
        self.adapter = adapter
        self.client = client
        self.answer_gate_enabled = answer_gate_enabled
        self.max_turns = max_turns
        self.max_tool_calls = max_tool_calls
        self.per_call_output_tokens = per_call_output_tokens
        self.max_run_tokens = max_run_tokens
        self.executors = executors
        self.doctypes = doctypes
        self.breaker = breaker if breaker is not None else DenialBreaker()
        self.system_prompt = system_prompt
        self.immediate = immediate

    # ── 开场 ────────────────────────────────────────────────────────────────
    def _open(self, session: ConversationSession) -> OpeningPack:
        """开场注入：**在任何模型消息之前**跑一次 `permission.scope`。

        注入代价（`InjectionCost.request_count`）照记 —— 不记就是把「自动注入」
        变成一笔隐性成本。
        """
        return open_session(
            client=self.client,
            doctypes=self.doctypes,
            session=session,
            executors=self.executors,
            immediate=self.immediate,
        )

    def _opening_message(self, pack: OpeningPack) -> str:
        rows = [
            f"- {row.get('doctype')}：{'可读' if row.get('can_read') else '不可读'}"
            for row in pack.scope
        ]
        body = "\n".join(rows) if rows else "（开场注入没有取回任何可见范围）"
        return "本次会话的可见范围（由控制循环在开场自动注入，不必也无法自行调用）：\n" + body

    def _immediate_message(self, pack: OpeningPack) -> str | None:
        """① 即时上下文（当前单据）渲染成一条消息体；没给就返回 `None`（**一条都不注入**）。

        内容取自 `ImmediateContext.blocks()` 里 `key == "document"` 那块的 `payload`，
        **原样序列化**：不截断、不省略、不 unwrap §7.5 的边界标记、也不从
        `pack.immediate.document` 另行重拼 —— 重拼会绕过 `blocks()` 这个唯一口径。
        ② 档（`key == "actions"`）**不在这里注入**：同一批事实在 `messages` 里已逐条在场
        （`tool_call` + 工具结果），再注一份就是双写（§7.12 的 D2）。
        """
        immediate = pack.immediate
        if immediate is None:
            return None
        for block in immediate.blocks():
            if block.key == IMMEDIATE_BLOCK_KEY:
                body = json.dumps(block.payload, ensure_ascii=False, sort_keys=True)
                return f"{IMMEDIATE_PREFIX}\n{body}"
        return None

    # ── 主循环 ──────────────────────────────────────────────────────────────
    def run(self, question: str, *, session_id: str = "explain", user: str = "") -> ExplainResult:
        """跑一次完整解释。**任何情况下都返回结果对象** —— 中止也要留痕。"""
        surface = EvidenceSurface(question, self.client)
        session = conversation.start(session_id, user=user)
        trace = ExplainTrace(question=question, model=self.adapter.model)

        pack = self._open(session)
        session = pack.session if pack.session is not None else session
        trace.opening_request_count = pack.cost.request_count

        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": self._opening_message(pack)},
        ]
        # ① 只在装配 `messages` 时插这一次；主循环里**不再 append**，
        # 不然注入的 prompt 成本会随轮数放大（判据 J9）。
        immediate_message = self._immediate_message(pack)
        if immediate_message is not None:
            messages.append({"role": "system", "content": immediate_message})
        messages.append({"role": "user", "content": question})
        session = session.with_turn(Turn(role=conversation.ROLE_USER, text=question))
        schemas = tool_schemas()

        for index in range(1, self.max_turns + 1):
            try:
                reply = self.adapter.chat(messages, schemas, self.per_call_output_tokens)
            except RoutingError as exc:
                # **异常出口照样记账**（P1.7）：账本的采集面就是这一处 `adapter.chat` 的
                # 两条出口，一条都不许绕过去。
                trace.cost_ledger.record_error(index, self.adapter.model, exc)
                trace.stopped = STOP_MODEL_ERROR
                trace.turns.append({"index": index, "kind": "model-error", "detail": str(exc)})
                return self._result("", False, trace, session, surface, pack)
            trace.cost_ledger.record_reply(index, reply)

            # ⚠️ **单次解释的 token 预算**（2026-08-27 加，默认 `None` = 不设限
            # ⇒ 产品行为一个字没变）。它与 `MAX_TURNS` / `MAX_TOOL_CALLS`
            # **各管一维，不许合并**（同 D-18 的道理）：
            #   · `MAX_TURNS` 数轮数 · `MAX_TOOL_CALLS` 数工具调用数
            #   · 本闸数**花掉的 token**
            # 实测撞出来的（`qwen3.8-flash`，独立集第 4 条）：**42 次工具调用**、
            # 按名字+参数只重复 1 次（是游荡不是死循环），
            # `MAX_TOOL_CALLS=50` **没触发**（42 < 50），
            # 最后由 `max_turns=40` 停下 —— 而那时**一条题已经烧掉 445,431 token**，
            # 把一轮 60 条的预算吃掉一半。⇒ 前两道闸数的都不是钱，**挡不住这个形态**。
            if self.max_run_tokens is not None:
                spent = sum(
                    e.usage.prompt + e.usage.completion for e in trace.cost_ledger.entries
                )
                if spent >= self.max_run_tokens:
                    trace.stopped = STOP_TOKEN_BUDGET
                    trace.turns.append(
                        {"index": index, "kind": "token-budget",
                         "spent": spent, "limit": self.max_run_tokens}
                    )
                    return self._result("", False, trace, session, surface, pack)

            if reply.tool_calls:
                session, stopped = self._run_tools(
                    reply, messages, surface, trace, session, index
                )
                if stopped == STOP_BREAKER:
                    return self._breaker_stop(trace, session, surface, pack)
                if stopped == STOP_RUNAWAY:
                    trace.stopped = STOP_RUNAWAY
                    return self._result("", False, trace, session, surface, pack)
                continue

            session = session.with_turn(
                Turn(role=conversation.ROLE_ASSISTANT, text=reply.text, usage=reply.usage)
            )
            trace.turns.append(
                {"index": index, "kind": "answer", "usage": reply.usage.as_dict()}
            )
            accepted, message = self._judge(reply.text, surface, trace, index)
            if accepted:
                trace.stopped = STOP_ANSWERED
                return self._result(reply.text, True, trace, session, surface, pack)
            messages.append({"role": "assistant", "content": reply.text})
            messages.append({"role": "user", "content": message})
            trace.forced_continues.append(message)

        trace.stopped = STOP_MAX_TURNS
        return self._result("", False, trace, session, surface, pack)

    # ── ② 作答前那一次求值 ──────────────────────────────────────────────────
    def _judge(
        self, answer: str, surface: EvidenceSurface, trace: ExplainTrace, index: int
    ) -> tuple[bool, str]:
        """门禁关时**不求值、不留 gate_check** —— 消融那一侧要的就是「这一步不存在」。"""
        if not self.answer_gate_enabled:
            return True, ""
        evaluations, collected = surface.evaluate(answer)
        failed = evidence.failures(evaluations)
        trace.gate_checks.append(
            {
                "turn": index,
                "enforced": True,
                "surface_id": surface.surface_id,
                "facts": collected,
                "failed": [
                    {
                        "text": item.condition.text,
                        "fact": item.condition.fact,
                        "reason": item.reason,
                        "missing_count": evidence.missing_count(item, collected),
                    }
                    for item in failed
                ],
            }
        )
        if not failed:
            return True, ""
        return False, evidence.forced_continue_message(failed, collected)

    # ── 工具执行 + 熔断 ─────────────────────────────────────────────────────
    def _run_tools(
        self,
        reply,
        messages: list[dict],
        surface: EvidenceSurface,
        trace: ExplainTrace,
        session: ConversationSession,
        index: int,
    ) -> tuple[ConversationSession, str]:
        """回第二项是**停止原因**（空串 = 继续）。三态而不是布尔：熔断与失控闸是
        **两个不同的闸**，合成一个布尔就等于把它们的停止原因混成一个（D-18 禁止的合并）。"""
        messages.append(
            {
                "role": "assistant",
                "content": reply.text or None,
                "tool_calls": list(reply.tool_calls),
            }
        )
        calls: list[ToolCall] = []
        for call in reply.tool_calls:
            function = call.get("function") or {}
            tool = _tool_name(str(function.get("name") or ""))
            try:
                params = json.loads(function.get("arguments") or "{}")
            except ValueError:
                params = {}
            if not isinstance(params, dict):
                params = {}
            # **失控闸的计量对象是「模型发起的工具调用数」（D3 的 B1），不是
            # `trace.execute_calls`（B2）**：未知工具 / 被排除工具在 `_execute_one()` 里
            # 计数之前就早返回，选 B2 的话一个不断编造工具名的跑飞模型会让计数恒为 0、
            # 闸门永不触发 —— 那正是这个闸要挡的形态。代价照实记：B1 把「没打到站点的
            # 调用」也算进来，闸门因此比「实际干了多少活」略严。**这是刻意的**，
            # 它管的是「停下来」，不是「花了多少」。
            trace.model_tool_calls += 1
            record = self._execute_one(tool, params, surface, trace)
            calls.append(ToolCall(tool=tool, params=params, ok=record["ok"]))
            messages.append(
                {
                    "role": conversation.ROLE_TOOL,
                    "tool_call_id": call.get("id"),
                    "content": _clip(record["result"]),
                }
            )
            if trace.model_tool_calls >= self.max_tool_calls:
                trace.runaway_events.append(
                    {
                        "turn": index,
                        "tool_calls": trace.model_tool_calls,
                        "limit": self.max_tool_calls,
                    }
                )
                # **停机不清账**：这一轮的 usage 照样进 `ConversationSession`，
                # 账本那一条在 `run()` 里早就记过了（不拦截 ≠ 不记账，也 ≠ 不停失控）。
                session = session.with_turn(
                    Turn(
                        role=conversation.ROLE_ASSISTANT,
                        text=reply.text,
                        tool_calls=tuple(calls),
                        usage=reply.usage,
                    )
                )
                return session, STOP_RUNAWAY
            if self.breaker.tripped:
                # **第 N 次之后不再发起第 N+1 次 `execute`** —— 同一批里剩下的调用也不发。
                trace.breaker_events.append(
                    {
                        "turn": index,
                        "streak": self.breaker.streak,
                        "denied": list(self.breaker.denied),
                    }
                )
                session = session.with_turn(
                    Turn(
                        role=conversation.ROLE_ASSISTANT,
                        text=reply.text,
                        tool_calls=tuple(calls),
                        usage=reply.usage,
                    )
                )
                return self._record_breaker(session), STOP_BREAKER
        session = session.with_turn(
            Turn(
                role=conversation.ROLE_ASSISTANT,
                text=reply.text,
                tool_calls=tuple(calls),
                usage=reply.usage,
            )
        )
        trace.turns.append(
            {
                "index": index,
                "kind": "tools",
                "usage": reply.usage.as_dict(),
                "calls": [c.tool for c in calls],
            }
        )
        return session, ""

    def _execute_one(
        self, tool: str, params: dict, surface: EvidenceSurface, trace: ExplainTrace
    ) -> dict:
        if tool not in {c.tool for c in READONLY_CONTRACTS} or tool in EXCLUDED_TOOLS:
            detail = f"没有这个工具：{tool}"
            trace.tool_calls.append(
                {"tool": tool, "params": params, "ok": False, "stage": "unknown-tool",
                 "reasons": [detail], "request_count": 0, "surface_id": surface.surface_id}
            )
            return {"ok": False, "result": detail}

        # ① 工具前置那一次求值 —— 与 ② 取自**同一个** `EvidenceSurface`（D2）。
        context = surface.tool_context()
        trace.execute_calls += 1
        result = execute(tool, params, client=self.client, context=context,
                         executors=self.executors)
        self.breaker.record(result, doctype=_denial_subject(tool, params))
        if result.ok:
            surface.record_call(tool, params, result.data)
            payload = json.dumps(result.data, ensure_ascii=False)
        else:
            payload = "工具未执行：" + "；".join(result.reasons)
        trace.tool_calls.append(
            {
                "tool": tool,
                "params": params,
                "ok": result.ok,
                "stage": result.stage,
                "reasons": list(result.reasons),
                "request_count": result.request_count,
                "surface_id": surface.surface_id,
            }
        )
        return {"ok": result.ok, "result": payload}

    def _record_breaker(self, session: ConversationSession) -> ConversationSession:
        """D4：熔断事件作为一条结构化记录进 `ConversationSession`。

        ⚠️ **这不是站点侧审计**。会话轨迹今天落在 `JsonFileSessionStore`（P1.2），
        会话 DocType 在活站点上尚未建表 —— 本期「写入审计」的含义是**本地可回放的轨迹**。
        """
        report = self.breaker.report()
        return session.with_action(
            ExecutedAction(
                tool=BREAKER_ACTION,
                params={"streak": self.breaker.streak, "threshold": self.breaker.threshold},
                request_count=0,
                diff_summary="权限探测事件 · " + report.text(),
            )
        )

    def _breaker_stop(
        self,
        trace: ExplainTrace,
        session: ConversationSession,
        surface: EvidenceSurface,
        pack: OpeningPack,
    ) -> ExplainResult:
        trace.stopped = STOP_BREAKER
        return self._result(self.breaker.report().text(), False, trace, session, surface, pack)

    def _result(
        self,
        answer: str,
        accepted: bool,
        trace: ExplainTrace,
        session: ConversationSession,
        surface: EvidenceSurface,
        pack: OpeningPack | None,
    ) -> ExplainResult:
        return ExplainResult(
            answer=answer,
            accepted=accepted,
            trace=trace,
            session=session,
            surface=surface,
            breaker=self.breaker,
            opening=pack,
        )


def _denial_subject(tool: str, params: Mapping[str, Any]) -> str:
    """熔断清单里这次拒绝记在谁头上（D6 的 (C)：有 `doctype` 参数的按参数取，没有的按工具名）。

    ⚠️ **残余风险照实登记**：按工具名记的那一类，`report()` 给出的不是 `read:<DocType>`
    形状（会是 `read:system.overview`），§7.4 表第二行的「指名 DocType」对它只成立一半。
    不粉饰 —— 兜底口径的存在是为了让清单**不为空**，而不是为了假装它总是 DocType。
    """
    doctype = params.get("doctype")
    return str(doctype) if doctype else tool


def explain(
    question: str,
    *,
    task_class: str,
    client: SiteClient,
    models,
    requested: str | None = None,
    config=None,
    transport=None,
    doctypes: Sequence[str] | None = None,
    session_id: str = "explain",
    user: str = "",
    max_turns: int = MAX_TURNS,
    per_call_output_tokens: int = PER_CALL_OUTPUT_TOKENS,
    executors: Mapping[str, Executor] | None = None,
    immediate: ImmediateContext | None = None,
) -> ExplainResult:
    """产品入口：跑一次解释。**② 作答前门禁在这条路径上永远是开的**（无参数可关）。

    `task_class` **由调用方指定**，循环不替调用方选类目 —— `TASK_MINIMUM_CAPABILITIES`
    里已声明的 `explain` / `lineage` 都是合法取值。模型侧一律走 `route()`：
    能力不满足就明确失败（`RoutingError`），**不静默降级**（D1）。

    ⚠️ **残余风险照实登记**：`lineage` 档今天会放行 `qwen3.6-plus`，而它在本项目两跳题上
    的逐格数见 `docs/architecture/model-management.md` §12.3 的四列并置表 —— 四列在那两格上
    并不一致，孰为准归人裁定（STATE §3 `[open] 2026-08-24T07:50Z`）。那条 `[open]`
    **不因本模块落地而消失**，本模块也不代人处置它。

    ⚠️ **`max_tool_calls` 刻意不在这里暴露** —— `tests/unit/test_explain_runaway_guard.py`
    的 H4 ⑤ 逐字断言 `"max_tool_calls" not in explain.__code__.co_varnames`：
    失控闸**不许从产品入口被调**。2026-08-27 试过加透传，被这条判据当场拦下，**撤回了**。
    评测那类要拆闸的场合自己构造 `ExplainLoop`，不从产品入口开这个口子。

    ⚠️ **`per_call_output_tokens` 2026-08-27 在入口暴露出来了**，理由是实测的 —— `ExplainLoop`
    一直有这个参数，`explain()` 却没透传，于是产品路径上它**只能是默认的 4096**。
    暴露它的理由是实测：`glm-5.2`（**思考默认开着**）做难题时把 4096 全烧在 reasoning 上，
    回包 `finish_reason='length'`、`completion=4097 / reasoning=4096`，**一个字都没吐**。
    同一批题上 `kimi-k3` 从未触发（45 条零次，单次 reasoning 最大 **765**）
    ⇒ 这是**模型 × 上限的交互**，不是模型能力差。
    ⚠️ **默认值本次不动**：把它调大会同时抬高最坏成本，而 `PER_CALL_OUTPUT_TOKENS = 4096`
    上方那段推导是既有的。**产品默认要不要跟着改，归人裁定** ——
    今天的实情是：真人拿 `glm-5.2` 问一个难问题，会拿到一片空白。

    `immediate` 是 ① 即时上下文（当前单据），给了就渲染成**一条独立的 `system` 消息**
    插在开场可见范围之后、提问之前。⚠️ **① 层不查权限**（`agenerp/context/immediate.py`
    模块头规矩 1）：字段表是不是当前身份有权看的，**由调用方负责** —— 这一层不判、也判不了。
    """
    adapter = route(
        task_class, models=models, requested=requested, config=config, transport=transport
    )
    loop = ExplainLoop(
        adapter=adapter,
        client=client,
        max_turns=max_turns,
        per_call_output_tokens=per_call_output_tokens,
        executors=executors,
        doctypes=doctypes,
        immediate=immediate,
    )
    result = loop.run(question, session_id=session_id, user=user)
    result.trace.task_class = task_class
    return result
