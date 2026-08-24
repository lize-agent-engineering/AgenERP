"""② 会话层：一次对话的轮次、已执行动作、前后快照引用。

**命名消歧，这一条最容易读错**：本模块的 `ConversationSession` 是**对话会话**；
`agenerp.tools.runtime.Session` 是**工具会话** —— 执行体与站点之间的唯一通道，
只记站点请求留痕（`request_count` / `resource_doctypes` / `row_sources` / `methods`）。
**同名不同义**，两者没有继承、没有组合、不可互换。产品类名带 `Conversation` 前缀就是为了这个。

**红线（`context-and-memory.md` §8.4，代码级、不可配置）：本层的任何字段都不得参与
权限判定或风险档计算。** v0 把它表达成三条可机械扫描的禁令：
本包不 import `ReadOnlyContext`、不 import `agenerp.contracts` 的求值面、
不构造 `facts` 字典交给 `execute`。判据在 `tests/context/test_session.py`，**不是靠 code review**。

**用量聚合**：`usage_total` 逐轮调 `agenerp.routing.adapter.Usage.plus()`，
**不自己写三项加法** —— 自己写就会与 P1.1 漂移。折叠形态**定死为「从空 `Usage()` 起折 N 轮」**，
即 N 轮恰好 N 次 `plus()`；判据 monkeypatch `Usage.plus` 数调用次数。
逐项语义沿用 P1.1：`reasoning` 是 `completion` 的细分，**不是第四个桶**，
`total = prompt + completion`，reasoning **不参与求和**。

**快照那一项复用 `agenerp.snapshot`，不另写一套。** 本模块**不调 `capture`**（那是 I/O，
归调用方），只收 `Snapshot` 对象、用 `snapshot.diff` 算差异。
⚠️ v0 的 ② 端**只有只读工具**，没有写动作，因此这里记的是**取证前后的只读快照**，
**不是写操作的回滚点** —— 不要读成「已经在记回滚点了」。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from agenerp.routing.adapter import Usage
from agenerp.snapshot import Snapshot, diff

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_TOOL = "tool"


@dataclass(frozen=True)
class ToolCall:
    """一轮里的一次工具调用。`params` 是**自由键字典**，原样留着。

    留着它不是为了好看：落盘确定性（键序）唯一能验的地方就是一个自由键字典，
    dataclass 的字段序是固定的，拿它验不出插入序问题。
    """

    tool: str
    params: Mapping[str, Any] = field(default_factory=dict)
    ok: bool | None = None


@dataclass(frozen=True)
class Turn:
    """一轮对话。`usage` 是**这一轮**的 token 账，口径见 `agenerp.routing.adapter.Usage`。"""

    role: str
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = field(default_factory=Usage)


@dataclass(frozen=True)
class SnapshotRef:
    """对一次 `agenerp.snapshot.capture` 结果的**引用** —— 不复制快照内容。

    复制内容会让会话记录随站点规模膨胀，而 ② 层要落进一条 DocType 记录里。
    """

    label: str
    scope: str
    entry_count: int


def snapshot_ref(label: str, snapshot: Snapshot) -> SnapshotRef:
    return SnapshotRef(label=label, scope=snapshot.scope, entry_count=len(snapshot))


@dataclass(frozen=True)
class ExecutedAction:
    """一条**已执行动作的审计记录**（§8.2 优先级规则 ②：不可压缩）。

    `before` / `after` 是 `SnapshotRef.label`，指向 `ConversationSession.snapshots` 里的条目。
    """

    tool: str
    params: Mapping[str, Any] = field(default_factory=dict)
    request_count: int = 0
    before: str = ""
    after: str = ""
    diff_summary: str = ""


@dataclass(frozen=True)
class ConversationSession:
    """一次对话会话。**不可变**：每个 `with_*` 回一个新会话，原对象不动。

    不可变是有意的：会话记录是审计面，就地改写会让「第 3 轮时记录长什么样」不可回溯。
    """

    session_id: str
    user: str = ""
    turns: tuple[Turn, ...] = ()
    actions: tuple[ExecutedAction, ...] = ()
    snapshots: tuple[SnapshotRef, ...] = ()

    def with_turn(self, turn: Turn) -> ConversationSession:
        return replace(self, turns=(*self.turns, turn))

    def with_action(self, action: ExecutedAction) -> ConversationSession:
        return replace(self, actions=(*self.actions, action))

    def with_readonly_probe(
        self,
        *,
        tool: str,
        params: Mapping[str, Any],
        before: Snapshot,
        after: Snapshot,
        request_count: int = 0,
    ) -> ConversationSession:
        """记一次取证：前后两张只读快照 + 它们的结构化 diff 摘要。

        差异由 `agenerp.snapshot.diff` 算，**本模块不自己比对** —— 第二套比对口径
        会在 scope 不同、属性变更这类边角上与它错开。
        """
        index = len(self.actions)
        before_ref = snapshot_ref(f"{tool}#{index}·before", before)
        after_ref = snapshot_ref(f"{tool}#{index}·after", after)
        action = ExecutedAction(
            tool=tool,
            params=dict(params),
            request_count=request_count,
            before=before_ref.label,
            after=after_ref.label,
            diff_summary=diff(before, after).summary(),
        )
        return replace(
            self,
            actions=(*self.actions, action),
            snapshots=(*self.snapshots, before_ref, after_ref),
        )

    @property
    def usage_total(self) -> Usage:
        """本会话累计用量。**折叠形态：从空 `Usage()` 起折 N 轮 → 恰好 N 次 `plus()`。**

        必须走 `Usage.plus()`。自己写三项加法能算对，但会与 P1.1 的口径分家 ——
        下一次 `Usage` 改口径时，漂移的是这里，而且不会有任何东西说话。
        """
        total = Usage()
        for turn in self.turns:
            total = total.plus(turn.usage)
        return total

    def audit_records(self) -> tuple[str, ...]:
        """已执行动作的审计记录，喂给 `immediate.assemble(actions=...)` 的那一档。

        §8.2 规则 ② 逐字「已执行动作的审计记录**不可压缩**」：这里逐条摊平，不做摘要合并。
        """
        return tuple(
            f"{a.tool}({_render_params(a.params)}) · 请求 {a.request_count} 次 · {a.diff_summary}"
            for a in self.actions
        )


def _render_params(params: Mapping[str, Any]) -> str:
    return ", ".join(f"{k}={params[k]!r}" for k in sorted(params))


def start(session_id: str, *, user: str = "") -> ConversationSession:
    return ConversationSession(session_id=session_id, user=user)


def turns_of(roles_and_texts: Sequence[tuple[str, str]]) -> tuple[Turn, ...]:
    return tuple(Turn(role=role, text=text) for role, text in roles_and_texts)
