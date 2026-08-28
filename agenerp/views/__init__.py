"""视图 Agent（P2.3）· 自然语言 → 视图 DSL。

两个文件各管一件事：

- `wire.py` 线格式（模型交出来的 JSON ↔ `View`），**只解析形状不判对错**
- `loop.py` 控制循环，**校验由循环无条件执行，模型没有绕过它的路**
"""

from agenerp.views.wire import WireError, view_from_json, view_from_text

__all__ = ["WireError", "view_from_json", "view_from_text"]
