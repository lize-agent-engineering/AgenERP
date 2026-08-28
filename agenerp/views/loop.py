"""视图 Agent 的控制循环 —— 自然语言 → 视图 DSL。

🔴 **校验由循环无条件执行，模型没有绕过它的路。**

这是本模块与 `docs/design/agents-and-roles.md` §5.1 字面的一处偏离，人 2026-08-28 裁定：
owner doc 把 `dsl.validate` / `dsl.preview` 列为视图 Agent 的**模型可见工具**，
本模块**不那样做**。理由是 D-15「规则能覆盖的流程不 Agent 化」——
「这个视图合不合法」「哪一块画不了、为什么」`validate()` 与 `plan_render()`
纯规则零模型就能答。把它做成工具，模型就有了「不调它就交」这条路，
而那正是本项要挡住的失败形态。

同形先例在 `agenerp/explain/loop.py`：`permission.scope` **刻意不进模型工具面**，
因为开场注入已经把那一步确定性化了。

## 与解释 Agent 为什么不是同一个循环

停止条件不同：解释 Agent 停在「证据够不够」，视图 Agent 停在「DSL 合不合法」。
塞进 `ExplainLoop` 只有一条实现路径 —— 在证据充分性门禁上开一个
`if task_class == "view": skip`。**那就是给 P1.4 那道门禁开后门**，
而它正是 P1.0 入口关口实验证明「门禁能补偿模型能力」的那个东西。
⇒ 复用零件（`routing` / `tools.runtime` / `context.session`），**不复用循环本体**。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import json

from agenerp.dsl.blocks import (
    AGGREGATES,
    BLOCK_TYPES,
    CHART_KINDS,
    FILTER_OPERATORS,
    SORT_DIRECTIONS,
    View,
)
from agenerp.dsl.fallback import RenderPlan, plan_render
from agenerp.dsl.schema import SchemaView
from agenerp.dsl.validate import SchemaUnavailable, ValidationResult, validate
from agenerp.routing import route
from agenerp.routing.adapter import ChatAdapter
from agenerp.site import SiteClient
from agenerp.tools.runtime import Executor, execute
from agenerp.tools_readonly import READONLY_CONTRACTS
from agenerp.views.wire import WireError, view_from_text

# ⚠️ **借用 `explain` 的两份常量，不复制。** 两者都是**实测换来的**：
#   · `TOOL_PARAMS["meta.fields"]` 的 `keywords` —— 大单据整表 38,000 字符会被截断
#   · `RESULT_CHARS = 20000` —— 6000 时**7 条题的正解被切在返回前面**
# 复制一份等于给它们各留一个会悄悄过期的副本。
# ⚠️ **它们该住在 `agenerp/tools/`，两个循环都引** —— 今天不搬：搬要动
# `agenerp/explain/`，而本项的 Non-Goal 是那里一行不动。P3 出现第三个循环时一起搬。
from agenerp.explain.loop import RESULT_CHARS, TOOL_PARAMS  # noqa: E402

# 每次调用允许模型写多少 token。与 `explain` 那一份同源同值。
PER_CALL_OUTPUT_TOKENS = 4096

STOP_PROPOSED = "proposed"
STOP_MAX_TURNS = "max-turns"
STOP_REPAIR_EXHAUSTED = "repair-exhausted"

# 交出坏 DSL 之后，最多再被顶回去几次。⇒ 最多 `1 + REPAIR_ROUNDS` 次提交。
#
# 🔴 **这个数今天没有实测依据，它是待测量不是结论。**
# 本仓的每个上限都要有出处：`MAX_TURNS` 由 25→40 是实测换来的，
# `RESULT_CHARS` 由 6000→20000 也是。这个不是 —— 它只是「先取一个最小可观测值」。
# 量化评测（plan Phase 4）跑完必须回答：有没有题卡在这个上限上？
# ⚠️ **不许在跑之前把它调大** —— 先把闸放到看不见，同样量不出真实形状。
REPAIR_ROUNDS = 3

# 防跑飞，不是修复轮上限 —— 两者各管一维：`REPAIR_ROUNDS` 数的是「交了几次坏 DSL」，
# 本闸数的是「模型总共说了几轮话」（一轮可以只调工具、不交 DSL）。值同 `explain`。
MAX_TURNS = 40

# 🔴 视图 Agent 的工具面。**封闭，且刻意只有三个。**
#
# 它要的是 schema 不是数据行 —— 给 `query.read` / `doc.get` 只会让它去查数据、
# 烧 token，而答案不在那儿。P2.0R 实测的主力就是前两个
# （`schema.search` 找 DocType → `meta.fields` 找字段）。
#
# 🔴 **`dsl.validate` / `dsl.preview` 不在这里**（D2，人 2026-08-28 裁定）：
# 它们由循环无条件执行。工具面里有它们，模型就有了「不调就交」这条路。
VIEW_TOOLS = ("system.overview", "schema.search", "meta.fields")

# 视图 Agent 的任务类目。`agenerp/routing/capabilities.py` 与 owner doc
# `model-management.md` §12.5 那张 machine-read 表同步声明（两边不同步就红）。
VIEW_TASK_CLASS = "view"

# 连查几轮工具之后开始催它交。
# 🔴 **这个数同样没有实测依据**（同 `REPAIR_ROUNDS`，见那里的注释）。
# 实测只给出了「8 轮不催就查不完」这一个观察，没给出「几轮是对的」。
# 量化评测跑完要回答：被催之后还需要几轮才交？
TOOL_TURN_NUDGE = 4

def _build_system_prompt() -> str:
    """提示词**由 `blocks.py` 的封闭取值生成，不手抄。**

    🔴 2026-08-28 活体实测抓出来的：原来的提示词只说「输出 `{name, title, blocks}`」，
    **一个字都没说块长什么样**。真模型（`qwen3.7-flash-2026-07-15`）因此连查 8 轮
    `meta.fields`（每轮关键词都不同 —— 按 §3① 的口径是**探索不是打转**），
    始终没进入组装；放到 40 轮时端点直接回 400「同名同参的工具调用连续重复」。

    归因照 §3②：**先问是不是我们自己的 harness**。是。
    模型不是不会做，是**没人告诉它要交的东西长什么样**。

    生成而不是手抄，是为了让「封闭表变了、提示词没跟上」这件事不可能发生 ——
    判据在 `tests/agents/test_view_agent.py` 逐条比对。
    """
    return (
        "你是 ERP 的视图 Agent。用户用一句话说他想看什么，你要交出一份视图 DSL。\n"
        "\n"
        "## 怎么找字段\n"
        f"先 `schema.search` 找到 DocType，再 `meta.fields` 看它有哪些字段。\n"
        "`meta.fields` 每行都带 `ref`（形如 `Work Order.status`）—— **照抄它**，不要自己拼。\n"
        "⚠️ 字段名必须来自工具返回，凭记忆写的字段会被校验器拒掉并要求你重做。\n"
        "⚠️ **查够了就交**。同一张表反复用不同关键词查，既拿不到新东西也会把轮次用光。\n"
        "\n"
        "## 要交什么\n"
        "最终**只输出一个 JSON 对象**，不要任何解释文字：\n"
        '{"name": "英文短名", "title": "中文标题", "blocks": [ … ]}\n'
        "\n"
        f"块类型只有这五种：{', '.join(BLOCK_TYPES)}。每种的 `fields` 含义不同：\n"
        "- `list`：要展示的列，顺序即展示顺序。可带 `filters` / `sort` / `limit`\n"
        "- `detail`：单据详情要展示的字段\n"
        "- `metric`：**恰好一个**字段，配 `agg`\n"
        "- `chart`：**恰好两个**字段 `[x 轴, y 轴]`，配 `chart_kind`\n"
        "- `explain`：解释性文本块，**必须没有 fields**，用 `question` 写那个问题\n"
        "\n"
        f"`agg` 只能是：{', '.join(AGGREGATES)}\n"
        f"`chart_kind` 只能是：{', '.join(CHART_KINDS)}\n"
        f"`sort` 写成 `[字段, 方向]`，方向只能是：{', '.join(SORT_DIRECTIONS)}\n"
        "`filters` 写成 `[[字段, 算子, 值], …]` —— **是数组不是对象**，算子只能是："
        f"{', '.join(repr(op) for op in FILTER_OPERATORS)}\n"
        "\n"
        "一个块的例子：\n"
        '{"type": "list", "title": "工单", "doctype": "Work Order", '
        '"fields": ["production_item", "qty", "status"], '
        '"filters": [["status", "=", "In Process"]], "sort": ["planned_start_date", "asc"], '
        '"limit": 50}'
    )


SYSTEM_PROMPT = _build_system_prompt()


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
        if contract.tool in VIEW_TOOLS
    ]


def _signature(tool_calls) -> tuple:
    """一轮工具调用的指纹 = **名字 + 参数**，不是名字。

    🔴 handoff §3①：同一批轨迹按工具名重复 17/16/37/12 次，
    按名字+参数只有 2/0/1/0 次 —— **同一个工具、不同参数是探索，不是打转。**
    按名字判会把正常探索掐死。
    """
    return tuple(
        (
            str((call.get("function") or {}).get("name") or ""),
            str((call.get("function") or {}).get("arguments") or ""),
        )
        for call in tool_calls
    )


def _tool_name(wire_name: str) -> str:
    return wire_name.replace("_", ".", 1) if "_" in wire_name else wire_name


def _clip(text: str) -> str:
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS] + "…（已截断）"


@dataclass
class ViewTrace:
    request: str
    model: str = ""
    turns: list[dict] = field(default_factory=list)


@dataclass
class ViewProposal:
    """一次视图生成的产出。**校验结论与落回计划跟着走** —— 不是「循环内部验过了，相信我」。"""

    view: View | None
    validation: ValidationResult | None
    render_plan: RenderPlan | None
    stop_reason: str
    trace: ViewTrace


class ViewLoop:
    """控制循环本体。`adapter` / `client` / `schema` 都是**注入位**。

    ⚠️ **`schema` 由调用方给，循环自己不去造。** 与 `validate(view, None)` 抛异常同源：
    「拿不到 schema 就没有结论」是校验器的纪律，谁负责提供那份 schema 是调用方的事
    （服务端给静态快照、评测给活站点导出）。循环只保证**没有它就不往下走**。
    """

    def __init__(
        self,
        *,
        adapter: ChatAdapter,
        client: SiteClient,
        schema: SchemaView | None,
        doctypes: Sequence[str] | None = None,
        executors: Mapping[str, Executor] | None = None,
        per_call_output_tokens: int = PER_CALL_OUTPUT_TOKENS,
        repair_rounds: int = REPAIR_ROUNDS,
        max_turns: int = MAX_TURNS,
        tool_turn_nudge: int = TOOL_TURN_NUDGE,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.adapter = adapter
        self.client = client
        self.schema = schema
        self.doctypes = doctypes
        self.executors = executors
        self.per_call_output_tokens = per_call_output_tokens
        self.repair_rounds = repair_rounds
        self.max_turns = max_turns
        self.tool_turn_nudge = tool_turn_nudge
        self.system_prompt = system_prompt

    def run(self, request: str, *, session_id: str = "view", user: str = "") -> ViewProposal:
        """跑一次视图生成。**任何情况下都返回结果对象** —— 交不出来也要留痕。

        唯一的例外是没有 schema：那时**在任何模型调用之前就抛**（见下）。
        """
        if self.schema is None:
            # 🔴 **没有 schema 就没有结论**，与 `validate(view, None)` 抛异常同源。
            # 先跑一遍再抛等于白烧一次 token —— 而它抛不抛跟模型答什么无关。
            raise SchemaUnavailable(
                "视图请求 " + repr(request) + " 无法处理：没有 schema 视图，"
                "字段存在性验不了。验不了的东西不许算过。"
            )

        trace = ViewTrace(request=request, model=self.adapter.model)
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": request},
        ]
        schemas = tool_schemas()
        repairs = 0
        # 🔴 判重复的口径**只有一个**：名字 + 参数（`trajectory_full`）。
        # 按工具名数会把「同一工具不同参数」的探索误判成打转 ——
        # 那个信号在 P2.0R 骗过四次（handoff §3①）。
        last_signature: tuple | None = None
        tool_turns = 0

        for turn in range(1, self.max_turns + 1):
            reply = self.adapter.chat(messages, schemas, self.per_call_output_tokens)

            if reply.tool_calls:
                signature = _signature(reply.tool_calls)
                if signature == last_signature:
                    # 端点自己会因为「同名同参连续重复」回 400，**由它来杀我们什么都留不下**。
                    # 自己判、自己回注，并且**不把这次的 tool_calls 写进 history** ——
                    # 写进去，重复就留在了发给端点的消息里。
                    messages.append(
                        {
                            "role": "user",
                            "content": "你刚刚调过一模一样的工具（同名同参），结果不会变。"
                            "换个参数，或者**现在就交**出那个 JSON 对象。",
                        }
                    )
                    trace.turns.append({"index": turn, "kind": "repeat-blocked",
                                        "usage": reply.usage.as_dict()})
                    continue
                last_signature = signature
                tool_turns += 1
                self._run_tools(reply, messages, trace, turn)
                if tool_turns >= self.tool_turn_nudge:
                    # 轮次是有限的，而模型**看不见还剩几轮**。实测：连查 8 轮不组装。
                    messages.append(
                        {
                            "role": "user",
                            "content": "查到的字段够用了。**现在就交**出那个 JSON 对象，"
                            "不要再调工具。缺的字段就不要放进视图。",
                        }
                    )
                continue

            view, problem = self._read(reply.text)
            if view is not None:
                result = validate(view, self.schema)
                if result.ok:
                    trace.turns.append(
                        {"index": turn, "kind": "proposed", "usage": reply.usage.as_dict()}
                    )
                    return ViewProposal(
                        view=view,
                        validation=result,
                        render_plan=plan_render(view, self.schema),
                        stop_reason=STOP_PROPOSED,
                        trace=trace,
                    )
                problem = _validation_message(result)

            trace.turns.append(
                {"index": turn, "kind": "rejected", "detail": problem,
                 "usage": reply.usage.as_dict()}
            )
            repairs += 1
            if repairs > self.repair_rounds:
                return self._give_up(STOP_REPAIR_EXHAUSTED, trace)
            messages.append({"role": "assistant", "content": reply.text})
            messages.append({"role": "user", "content": problem})

        return self._give_up(STOP_MAX_TURNS, trace)

    def _give_up(self, stop_reason: str, trace: ViewTrace) -> ViewProposal:
        """🔴 **交不出来就是交不出来。**

        **不许把过不了的块删掉再交** —— 那正是 `agenerp/dsl/fallback.py` 模块头
        点名的坏选择：静默丢弃，用户以为那块内容本来就不存在。
        `validation` / `render_plan` 一并留空：有它们就等于说「这个视图校验过了」。
        """
        return ViewProposal(
            view=None,
            validation=None,
            render_plan=None,
            stop_reason=stop_reason,
            trace=trace,
        )

    def _run_tools(self, reply, messages: list[dict], trace: ViewTrace, turn: int) -> None:
        messages.append(
            {
                "role": "assistant",
                "content": reply.text or None,
                "tool_calls": list(reply.tool_calls),
            }
        )
        executed: list[dict] = []
        for call in reply.tool_calls:
            function = call.get("function") or {}
            tool = _tool_name(str(function.get("name") or ""))
            try:
                params = json.loads(function.get("arguments") or "{}")
            except ValueError:
                params = {}
            if not isinstance(params, dict):
                params = {}
            record = self._execute_one(tool, params)
            executed.append({"tool": tool, "params": params, "ok": record["ok"]})
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id"),
                    "content": _clip(record["result"]),
                }
            )
        trace.turns.append(
            {"index": turn, "kind": "tools", "calls": executed,
             "usage": reply.usage.as_dict()}
        )

    def _execute_one(self, tool: str, params: dict) -> dict:
        """⚠️ 工具面之外的名字**明说没有**，不静默忽略：

        模型编了一个工具名却什么反馈都收不到时，它会一直编下去。
        """
        if tool not in VIEW_TOOLS:
            return {"ok": False, "result": f"没有这个工具：{tool}"}
        result = execute(tool, params, client=self.client, executors=self.executors)
        if result.ok:
            return {"ok": True, "result": json.dumps(result.data, ensure_ascii=False)}
        return {"ok": False, "result": "工具未执行：" + "；".join(result.reasons)}

    def _read(self, text: str) -> tuple[View | None, str]:
        """读模型交的那段文本。回 `(视图, "")` 或 `(None, 回注消息)`。

        ⚠️ `WireError` 的回注说的是**输出格式**，`DslError` 那条说的是**内容**。
        合成一句，模型分不清是格式没说清还是字段找错了，只能重猜 ——
        而重猜要花掉一整轮修复预算。
        """
        try:
            return view_from_text(text), ""
        except WireError as exc:
            return None, (
                f"你交的不是一个视图 DSL：{exc} "
                "请只输出一个 JSON 对象，不要带解释文字。"
            )


def _validation_message(result: ValidationResult) -> str:
    """把校验器逐条的原文**原样带给模型**。

    🔴 不许收敛成一句「校验没过」：模型要靠这些原文知道是哪个 DocType 的哪个字段
    找错了。这条回注就是修复循环全部的信息量。
    """
    lines = "\n".join(f"- {error}" for error in result.errors)
    return (
        "这份视图没通过校验，逐条如下：\n"
        f"{lines}\n"
        "字段必须来自工具查到的真实字段。改正后**只输出**那个 JSON 对象。"
    )


def propose_view(
    request: str,
    *,
    client: SiteClient,
    schema: SchemaView | None,
    models,
    requested: str | None = None,
    config=None,
    transport=None,
    doctypes: Sequence[str] | None = None,
    session_id: str = "view",
    user: str = "",
    max_turns: int = MAX_TURNS,
    per_call_output_tokens: int = PER_CALL_OUTPUT_TOKENS,
    executors: Mapping[str, Executor] | None = None,
) -> ViewProposal:
    """产品入口：跑一次视图生成。**校验在这条路径上永远是开的**（无参数可关）。

    任务类目写死 `"view"` —— 调用方不选类目。理由与 `explain()` 不同：那里
    `explain` / `lineage` 都是合法取值（同一个 Agent 按题目难度分档），
    而视图生成只有一档。**能力不满足就明确失败**（`RoutingError`），不静默降级（§12.1 ③）。

    ⚠️ **`repair_rounds` 刻意不在这里暴露** —— 形态照 `explain()` 那条
    「失控闸不许从产品入口被调」：一个能从产品入口调的闸，等于一个可以被调用方
    一行关掉的闸。评测那类要拆闸的场合自己构造 `ViewLoop`。
    判据在 `tests/agents/test_view_agent.py`。

    ⚠️ **`schema` 仍是必传参数，且允许是 `None`** —— `None` 时在任何模型调用之前抛
    `SchemaUnavailable`。给它一个「拿不到就自己去取」的默认值，等于让产品路径在
    最需要结论的时候自己造一份来源不明的 schema。
    """
    adapter = route(
        VIEW_TASK_CLASS, models=models, requested=requested, config=config, transport=transport
    )
    loop = ViewLoop(
        adapter=adapter,
        client=client,
        schema=schema,
        doctypes=doctypes,
        executors=executors,
        max_turns=max_turns,
        per_call_output_tokens=per_call_output_tokens,
    )
    return loop.run(request, session_id=session_id, user=user)
