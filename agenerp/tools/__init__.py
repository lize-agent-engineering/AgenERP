"""工具执行层：十个只读契约的执行体，以及它们唯一的执行入口。

`agenerp.tools_readonly` 是**声明面**（契约），本包是**执行面**。
调用方只该用 `execute`——绕过它直接调执行体，等于绕过前置门禁、裁剪与后置断言。
"""

from agenerp.tools.registry import EXECUTORS
from agenerp.tools.runtime import Outcome, Session, ToolError, ToolResult, execute

__all__ = ["EXECUTORS", "Outcome", "Session", "ToolError", "ToolResult", "execute"]
