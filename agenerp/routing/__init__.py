"""模型路由 v0（P1.1）—— `docs/architecture/model-management.md` §12.5 是它的落点节。

**导出面刻意很小**：调用方需要的只有"挑一个模型"（`route`）、"拿它调一次"（`ChatAdapter`）、
"出事了接住"（`RoutingError`），以及三份声明。其余（配置对象、usage 解析、校验器、本仓实测过的模型档案表、
transport 细节）是内部件，从子模块 import 即可，但不进这一层 —— 导出面一旦泄开就收不回来。
"""

from __future__ import annotations

from agenerp.routing.adapter import ChatAdapter
from agenerp.routing.capabilities import (
    CAPABILITIES,
    TASK_MINIMUM_CAPABILITIES,
    ModelProfile,
)
from agenerp.routing.errors import RoutingError
from agenerp.routing.router import route

__all__ = (
    "route",
    "ChatAdapter",
    "RoutingError",
    "CAPABILITIES",
    "TASK_MINIMUM_CAPABILITIES",
    "ModelProfile",
)
