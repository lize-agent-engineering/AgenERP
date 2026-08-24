"""② 会话的**存储端口** + 零依赖内置实现。

`context-and-memory.md` §8.5 逐字：「**内置实现必须存在且零外部依赖**」。
`JsonFileSessionStore` 就是它 —— 只用标准库，不连站点、不连数据库、不装任何包。
MyContext / Harness / 社区 adapter 将来实现同一个 `SessionStore` 协议接进来，
**内置这一份不会因此变成可选项**。

**落盘必须是确定性的**，两条一起才算数：

1. **键序恒等于 `sorted(keys)`**（`sort_keys=True`）—— 只做 round-trip 是验不出来的：
   一个按插入序写的实现 round-trip 完美、同进程内两次落盘也字节相等，
   只有键序断言能把它打红。承载这条判据的是每轮工具调用的 `params`（自由键字典）。
2. **同一会话连续序列化两次字节完全相等** —— 不取时钟、不取进程内地址、不遍历 `set`。

⚠️ 本模块**不写站点**：`agenerp/context/**` 里没有任何一处 `SiteClient.create_doc` /
`ensure_doc` / `delete_custom_field`。这条有机械判据（`tests/context/test_doctype_declaration.py`），
不是靠 code review。会话在**活站点**上还没有落处 —— 那是风险档 L3 的建表，是人的动作。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

from agenerp.context.session import (
    ConversationSession,
    ExecutedAction,
    SnapshotRef,
    ToolCall,
    Turn,
)
from agenerp.routing.adapter import Usage

SUFFIX = ".json"


class SessionStore(Protocol):
    """会话存储端口。实现只需要这两个动作 —— 端口开小一点，adapter 才换得动。"""

    def save(self, session: ConversationSession) -> None: ...

    def load(self, session_id: str) -> ConversationSession: ...


def _usage_payload(usage: Usage) -> dict[str, int]:
    """落 `prompt` / `completion` / `reasoning` 三项。

    **`total` 不落盘**：它是 `prompt + completion` 的派生量（`Usage.total`），
    落进去就成了第二份真相，两边一旦对不上，谁对谁错没人说得清。
    """
    return {"prompt": usage.prompt, "completion": usage.completion, "reasoning": usage.reasoning}


def to_payload(session: ConversationSession) -> dict[str, Any]:
    """会话 → 纯 JSON 结构。字段名与 `ConversationSession` 逐字段同名（DocType 声明据此同构）。"""
    return {
        "session_id": session.session_id,
        "user": session.user,
        "turns": [
            {
                "role": turn.role,
                "text": turn.text,
                "tool_calls": [
                    {"tool": call.tool, "params": dict(call.params), "ok": call.ok}
                    for call in turn.tool_calls
                ],
                "usage": _usage_payload(turn.usage),
            }
            for turn in session.turns
        ],
        "actions": [
            {
                "tool": action.tool,
                "params": dict(action.params),
                "request_count": action.request_count,
                "before": action.before,
                "after": action.after,
                "diff_summary": action.diff_summary,
            }
            for action in session.actions
        ],
        "snapshots": [
            {"label": ref.label, "scope": ref.scope, "entry_count": ref.entry_count}
            for ref in session.snapshots
        ],
    }


def from_payload(payload: Mapping[str, Any]) -> ConversationSession:
    """纯 JSON 结构 → 会话。**缺键即抛**，不给默认值兜底。

    兜底会让「落盘时漏了一个字段」和「那个字段本来就是空的」长得一模一样。
    """
    return ConversationSession(
        session_id=payload["session_id"],
        user=payload["user"],
        turns=tuple(
            Turn(
                role=turn["role"],
                text=turn["text"],
                tool_calls=tuple(
                    ToolCall(tool=call["tool"], params=dict(call["params"]), ok=call["ok"])
                    for call in turn["tool_calls"]
                ),
                usage=Usage(
                    prompt=turn["usage"]["prompt"],
                    completion=turn["usage"]["completion"],
                    reasoning=turn["usage"]["reasoning"],
                ),
            )
            for turn in payload["turns"]
        ),
        actions=tuple(
            ExecutedAction(
                tool=action["tool"],
                params=dict(action["params"]),
                request_count=action["request_count"],
                before=action["before"],
                after=action["after"],
                diff_summary=action["diff_summary"],
            )
            for action in payload["actions"]
        ),
        snapshots=tuple(
            SnapshotRef(label=ref["label"], scope=ref["scope"], entry_count=ref["entry_count"])
            for ref in payload["snapshots"]
        ),
    )


def serialize(session: ConversationSession) -> str:
    """确定性序列化。`sort_keys=True` 是判据钉住的那一项，**不许顺手删**。"""
    return json.dumps(to_payload(session), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def deserialize(text: str) -> ConversationSession:
    return from_payload(json.loads(text))


class JsonFileSessionStore:
    """零依赖内置实现：一个会话一个 JSON 文件，文件名是 `session_id`。

    刻意不做的三件事：不加索引、不做并发锁、不做增量追加。
    v0 的会话是**一次对话**的量级，加上这些会引入一层今天没有任何判据的复杂度。
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def path_of(self, session_id: str) -> Path:
        if "/" in session_id or session_id in {"", ".", ".."}:
            raise ValueError(f"session_id 不能当文件名用：{session_id!r}")
        return self._root / f"{session_id}{SUFFIX}"

    def save(self, session: ConversationSession) -> None:
        path = self.path_of(session.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialize(session), encoding="utf-8")

    def load(self, session_id: str) -> ConversationSession:
        return deserialize(self.path_of(session_id).read_text(encoding="utf-8"))
