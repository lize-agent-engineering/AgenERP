"""站点状态快照与结构化 diff。

与 agenerp.pack 同一约定：此刻只有签名，没有行为。
"""

from typing import Any

_TODO = "尚未实现 —— 见 docs/backlog/p0-foundation-roadmap.md 的工作项对照表"


def capture(scope: str) -> Any:
    """对当前站点在 `scope` 范围内打一次状态快照。"""
    raise NotImplementedError(f"capture {_TODO}（工作项 2 · 状态快照与结构化 diff）")


def diff(before: Any, after: Any) -> Any:
    """比较两次快照，给出结构化的 added / removed / changed。"""
    raise NotImplementedError(f"diff {_TODO}（工作项 2 · 状态快照与结构化 diff）")


def schema_drift(doctype: str) -> Any:
    """列出 `doctype` 在物理表上残留、但已不在定制包里的孤儿列。"""
    raise NotImplementedError(f"schema_drift {_TODO}（工作项 5 · 差集 apply 引擎）")
