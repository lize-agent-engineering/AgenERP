"""视图 Agent（P2.3）· 自然语言 → 视图 DSL。

两个文件各管一件事：

- 线格式在 `agenerp/dsl/wire.py`（**属于 DSL，不属于 agent**，2026-08-28 迁走）
- `loop.py` 控制循环，**校验由循环无条件执行，模型没有绕过它的路**
"""

from agenerp.views.loop import ViewLoop, ViewProposal, propose_view
from agenerp.dsl.wire import WireError, view_from_json, view_from_text

__all__ = [
    "ViewLoop",
    "ViewProposal",
    "WireError",
    "propose_view",
    "view_from_json",
    "view_from_text",
]
