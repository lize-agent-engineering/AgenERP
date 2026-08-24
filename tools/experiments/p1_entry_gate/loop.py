"""最小控制循环 —— 模型选工具 → 执行 → 回注结果 → 作答 → 门禁判定 → 强制续跑。

**这是实验设施，不是产品**（落在 `tools/experiments/`，不进 `agenerp/`）。
它只为回答一个问题而存在：**确定性的循环门禁，能否补偿模型能力的不足？**

四条设计约束，每条都对着一种会让实验失去意义的失败模式：

1. **提示词单一来源**：四格共用 `prompt.md`，循环**不得**按配置改写它。
   改写了的话，测到的就是提示词差异而不是门禁差异。判据 `tests/experiments/` 逐字断言。
2. **门禁关时照样判、只是不回注**：`--gate off` 记录「本应发红的条目」，
   用于事后比对「无门禁下它漏了什么」。不记的话，无门禁那两格只剩一句「答错了」。
3. **事实由循环记，不由模型自报**：门禁的五条事实全部来自轨迹与站点（见 `gate.py`）。
4. **token 三项分开记**：`qwen3.6-plus` 是推理模型，reasoning token 混进 completion
   里的话，P1.7 的成本上限就没法算。

⚠️ **`permission.scope` 不在本实验的工具面里**，理由写在这里而不是靠人记得：
它的后置断言 `injected_at_session_start` 断的是**编排面**的事实（开场自动注入，属 P1.3），
本设施没有实现那件事。把它当 `True` 递进去就是**断言一件不成立的事**；
而本实验以单一身份（Administrator）跑，这道题里根本没有权限维度。
因此**不提供它**，而不是提供一个必然违约或必须靠假事实才能过的工具。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from agenerp.contracts import ReadOnlyContext
from agenerp.site import SiteClient
from agenerp.tools import execute
from agenerp.tools_readonly import READONLY_CONTRACTS
from tools.experiments.p1_entry_gate import gate as gate_rules
from tools.experiments.p1_entry_gate.llm import DashScopeClient, LlmError, Usage

PROMPT_PATH = Path(__file__).with_name("prompt.md")

# 每次调用允许模型写多少 token。**这不是运行预算**——运行预算是 `--max-tokens`，
# 两者分开：前者防一次跑飞，后者是 §8 风险④的成本闸。
PER_CALL_OUTPUT_TOKENS = 4096

MAX_TURNS = 25

# 工具返回值回注给模型时的字符上限。契约的 `max_rows` 已经把行数框住了，
# 这一层框的是**字符数**：一行也可能很长（`doc.get` 一张单据）。
RESULT_CHARS = 6000

EXCLUDED_TOOLS = ("permission.scope",)

# 每个工具的调用参数。**契约不声明参数形状**（它声明的是前置/后置/裁剪），
# 所以这份 schema 属于实验设施；它只描述**怎么调**，不新增任何约束。
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
    "snapshot.read": {
        "type": "object",
        "properties": {"scope": {"type": "string"}},
    },
    "rule.lookup": {
        "type": "object",
        "properties": {"doctype": {"type": "string"}},
    },
}


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


# 门禁关时喂给工具前置的**放行上下文**：五条事实全空 → `covers_fact` 平凡成立。
# 它只关掉**工具前置**那一道；「本应发红」由 `gate.py` 另算一遍并照记（见模块头第 2 条）。
PERMISSIVE = ReadOnlyContext(
    {
        "documents_named_in_question": [],
        "doc_links_called_for": [],
        "doc_get_called_for": [],
        "submitted_downstream_documents": [],
        "inbound_vouchers_of_quantities_in_answer": [],
    }
)


@dataclass
class Trace:
    """一次运行的结构化轨迹。**它是判定的原料**，所以什么都不许省略。"""

    run_id: str
    model: str
    gate: str
    question: str
    max_tokens: int
    prompt_sha256: str
    prompt_bytes: int
    started_at: str
    finished_at: str = ""
    turns: list[dict] = field(default_factory=list)
    gate_checks: list[dict] = field(default_factory=list)
    final_answer: str = ""
    usage: dict = field(default_factory=dict)
    tool_calls_total: int = 0
    invalid: dict | None = None

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "model": self.model,
            "gate": self.gate,
            "question": self.question,
            "max_tokens": self.max_tokens,
            "prompt_sha256": self.prompt_sha256,
            "prompt_bytes": self.prompt_bytes,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "tool_calls_total": self.tool_calls_total,
            "usage": self.usage,
            "turns": self.turns,
            "gate_checks": self.gate_checks,
            "final_answer": self.final_answer,
            "invalid": self.invalid,
        }


def read_prompt() -> tuple[str, str, int]:
    raw = PROMPT_PATH.read_bytes()
    return raw.decode("utf-8"), hashlib.sha256(raw).hexdigest(), len(raw)


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _clip(text: str) -> str:
    return text if len(text) <= RESULT_CHARS else text[:RESULT_CHARS] + "…（已截断）"


def run(
    *,
    question: str,
    llm: DashScopeClient,
    client: SiteClient,
    gate_on: bool,
    max_tokens: int,
    run_id: str,
    max_turns: int = MAX_TURNS,
) -> Trace:
    """跑一次完整对话，返回轨迹。**任何情况下都返回轨迹**——无效运行也要留痕。"""
    prompt, digest, size = read_prompt()
    trace = Trace(
        run_id=run_id,
        model=llm.model,
        gate="on" if gate_on else "off",
        question=question,
        max_tokens=max_tokens,
        prompt_sha256=digest,
        prompt_bytes=size,
        started_at=_now(),
    )
    messages: list[dict] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question},
    ]
    observed = gate_rules.Observations()
    total = Usage()
    schemas = tool_schemas()

    for turn in range(1, max_turns + 1):
        if total.total >= max_tokens:
            return _invalidate(trace, total, f"token 超限：已用 {total.total} ≥ 上限 {max_tokens}")
        try:
            reply = llm.chat(messages, schemas, PER_CALL_OUTPUT_TOKENS)
        except LlmError as exc:
            return _invalidate(trace, total, f"模型侧失败：{exc}")
        total = total.plus(reply.usage)

        if reply.tool_calls:
            records = _run_tools(reply, messages, observed, client, gate_on)
            trace.tool_calls_total += len(records)
            trace.turns.append(
                {"index": turn, "kind": "tools", "usage": reply.usage.as_dict(), "calls": records}
            )
            continue

        trace.turns.append(
            {"index": turn, "kind": "answer", "usage": reply.usage.as_dict(),
             "text": reply.text}
        )
        evaluations, collected = gate_rules.evaluate(question, reply.text, observed, client)
        failed = gate_rules.failures(evaluations)
        trace.gate_checks.append(
            {
                "turn": turn,
                "enforced": gate_on,
                "facts": collected,
                "failed": [
                    {
                        "text": item.condition.text,
                        "fact": item.condition.fact,
                        "reason": item.reason,
                        "missing_count": gate_rules.missing_count(item, collected),
                    }
                    for item in failed
                ],
            }
        )
        if failed and gate_on:
            messages.append({"role": "assistant", "content": reply.text})
            messages.append(
                {"role": "user", "content": gate_rules.forced_continue_message(failed, collected)}
            )
            continue
        trace.final_answer = reply.text
        trace.usage = total.as_dict()
        trace.finished_at = _now()
        return trace

    return _invalidate(trace, total, f"超过最大轮数 {max_turns}，没有产出最终答案")


def _run_tools(reply, messages: list[dict], observed, client, gate_on: bool) -> list[dict]:
    messages.append(
        {
            "role": "assistant",
            "content": reply.text or None,
            "tool_calls": list(reply.tool_calls),
        }
    )
    records: list[dict] = []
    for call in reply.tool_calls:
        function = call.get("function") or {}
        tool = _tool_name(str(function.get("name") or ""))
        try:
            params = json.loads(function.get("arguments") or "{}")
        except ValueError:
            params = {}
        record = _execute_one(tool, params, observed, client, gate_on)
        records.append(record)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.get("id"),
                "content": _clip(record["result"]),
            }
        )
    return records


def _execute_one(tool: str, params: dict, observed, client, gate_on: bool) -> dict:
    if tool not in {c.tool for c in READONLY_CONTRACTS} or tool in EXCLUDED_TOOLS:
        return {"tool": tool, "params": params, "ok": False, "stage": "unknown-tool",
                "reasons": [f"没有这个工具：{tool}"], "request_count": 0,
                "result": f"没有这个工具：{tool}"}
    context = (
        ReadOnlyContext(gate_rules.facts("", "", observed, client)) if gate_on else PERMISSIVE
    )
    result = execute(tool, params, client=client, context=context)
    if result.ok:
        observed.record_call(tool, params, result.data)
        payload = json.dumps(result.data, ensure_ascii=False)
    else:
        payload = "工具未执行：" + "；".join(result.reasons)
    return {
        "tool": tool,
        "params": params,
        "ok": result.ok,
        "stage": result.stage,
        "reasons": list(result.reasons),
        "request_count": result.request_count,
        "result": payload,
    }


def _invalidate(trace: Trace, total: Usage, reason: str) -> Trace:
    """无效运行**照实记录**，不静默丢弃（plan §2 的判定协议）。"""
    trace.invalid = {"reason": reason}
    trace.usage = total.as_dict()
    trace.finished_at = _now()
    return trace


def write_trace(trace: Trace, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{trace.run_id}.json"
    path.write_text(
        json.dumps(trace.as_dict(), ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path
