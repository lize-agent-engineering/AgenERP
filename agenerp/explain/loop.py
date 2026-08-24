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

⚠️ **`max_turns` 只为防跑飞，不是失控闸**（plan Non-Goals 2）：「工具调用轮数上限」
那套判据归 P1.7，本模块不声称做过它。`usage` 同理 —— 这里只有**载体**（`ConversationSession`
的 `usage_total`，走 `Usage.plus()`，不自己写加法），成本记账判据归 P1.7。
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from agenerp.context import session as conversation
from agenerp.context.session import ConversationSession, ExecutedAction, ToolCall, Turn
from agenerp.explain import gate as evidence
from agenerp.explain.gate import EvidenceSurface
from agenerp.orchestration import DenialBreaker, OpeningPack, open_session
from agenerp.routing import RoutingError, route
from agenerp.routing.adapter import ChatAdapter, Usage
from agenerp.site import SiteClient
from agenerp.tools.runtime import Executor, execute
from agenerp.tools_readonly import READONLY_CONTRACTS

# 每次调用允许模型写多少 token。防一次跑飞，不是运行预算（预算归 P1.7）。
PER_CALL_OUTPUT_TOKENS = 4096

MAX_TURNS = 25

# 工具返回值回注给模型时的字符上限。契约的 `max_rows` 框的是行数，这一层框的是字符数：
# 一行也可能很长（`doc.get` 一张单据）。
RESULT_CHARS = 6000

EXCLUDED_TOOLS = ("permission.scope",)

STOP_ANSWERED = "answered"
STOP_BREAKER = "permission-breaker"
STOP_MAX_TURNS = "max-turns"
STOP_MODEL_ERROR = "model-error"

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
    opening_request_count: int = 0
    execute_calls: int = 0
    stopped: str = ""

    def as_dict(self) -> dict:
        return {
            "question": self.question,
            "model": self.model,
            "task_class": self.task_class,
            "opening_request_count": self.opening_request_count,
            "execute_calls": self.execute_calls,
            "stopped": self.stopped,
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "gate_checks": self.gate_checks,
            "forced_continues": self.forced_continues,
            "breaker_events": self.breaker_events,
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
        **不自己写三项加法** —— 自己写就会与 P1.1 漂移（§7.7 逐字）。"""
        return self.session.usage_total


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
        per_call_output_tokens: int = PER_CALL_OUTPUT_TOKENS,
        executors: Mapping[str, Executor] | None = None,
        doctypes: Sequence[str] | None = None,
        breaker: DenialBreaker | None = None,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.adapter = adapter
        self.client = client
        self.answer_gate_enabled = answer_gate_enabled
        self.max_turns = max_turns
        self.per_call_output_tokens = per_call_output_tokens
        self.executors = executors
        self.doctypes = doctypes
        self.breaker = breaker if breaker is not None else DenialBreaker()
        self.system_prompt = system_prompt

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
        )

    def _opening_message(self, pack: OpeningPack) -> str:
        rows = [
            f"- {row.get('doctype')}：{'可读' if row.get('can_read') else '不可读'}"
            for row in pack.scope
        ]
        body = "\n".join(rows) if rows else "（开场注入没有取回任何可见范围）"
        return "本次会话的可见范围（由控制循环在开场自动注入，不必也无法自行调用）：\n" + body

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
            {"role": "user", "content": question},
        ]
        session = session.with_turn(Turn(role=conversation.ROLE_USER, text=question))
        schemas = tool_schemas()

        for index in range(1, self.max_turns + 1):
            try:
                reply = self.adapter.chat(messages, schemas, self.per_call_output_tokens)
            except RoutingError as exc:
                trace.stopped = STOP_MODEL_ERROR
                trace.turns.append({"index": index, "kind": "model-error", "detail": str(exc)})
                return self._result("", False, trace, session, surface, pack)

            if reply.tool_calls:
                session, stopped = self._run_tools(
                    reply, messages, surface, trace, session, index
                )
                if stopped:
                    return self._breaker_stop(trace, session, surface, pack)
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
    ) -> tuple[ConversationSession, bool]:
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
            record = self._execute_one(tool, params, surface, trace)
            calls.append(ToolCall(tool=tool, params=params, ok=record["ok"]))
            messages.append(
                {
                    "role": conversation.ROLE_TOOL,
                    "tool_call_id": call.get("id"),
                    "content": _clip(record["result"]),
                }
            )
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
                return self._record_breaker(session), True
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
        return session, False

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
    executors: Mapping[str, Executor] | None = None,
) -> ExplainResult:
    """产品入口：跑一次解释。**② 作答前门禁在这条路径上永远是开的**（无参数可关）。

    `task_class` **由调用方指定**，循环不替调用方选类目 —— `TASK_MINIMUM_CAPABILITIES`
    里已声明的 `explain` / `lineage` 都是合法取值。模型侧一律走 `route()`：
    能力不满足就明确失败（`RoutingError`），**不静默降级**（D1）。

    ⚠️ **残余风险照实登记**：`lineage` 档今天会放行 `qwen3.6-plus`，而它在本项目两跳题上
    是 1/6（STATE §3 `[open] 2026-08-24T07:50Z`）。那条 `[open]` **不因本模块落地而消失**，
    本模块也不代人处置它。
    """
    adapter = route(
        task_class, models=models, requested=requested, config=config, transport=transport
    )
    loop = ExplainLoop(
        adapter=adapter,
        client=client,
        max_turns=max_turns,
        executors=executors,
        doctypes=doctypes,
    )
    result = loop.run(question, session_id=session_id, user=user)
    result.trace.task_class = task_class
    return result
