"""上下文层 v0（P1.2）—— `docs/architecture/module-boundaries.md` §7.7 是它的落点节。

只做 `docs/design/context-and-memory.md` §8.2 的 **① 即时**与 **② 会话**两层。
③ 记忆与 ④ 检索**不在本层**（plan `2026-08-24-1457-2` Non-Goals 1/2），
装配面只给它们留了优先级档位，没有实现。

**全是确定性规则，零模型参与**（D-15）：字段取舍、优先级、裁剪顺序、落盘排序
没有一处让模型决定带什么上下文。

导出面只有装配与会话两侧的入口；存储实现从 `agenerp.context.store` 取。
"""

from __future__ import annotations

from agenerp.context.immediate import (
    ContextBudgetExceeded,
    CurrentDocument,
    ImmediateContext,
    assemble,
    trim,
)
from agenerp.context.session import (
    ConversationSession,
    ExecutedAction,
    SnapshotRef,
    ToolCall,
    Turn,
    start,
)
from agenerp.context.store import JsonFileSessionStore, SessionStore

__all__ = (
    "ContextBudgetExceeded",
    "CurrentDocument",
    "ImmediateContext",
    "assemble",
    "trim",
    "ConversationSession",
    "ExecutedAction",
    "SnapshotRef",
    "ToolCall",
    "Turn",
    "start",
    "SessionStore",
    "JsonFileSessionStore",
)
