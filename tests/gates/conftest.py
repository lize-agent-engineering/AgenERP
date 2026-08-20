"""门禁测试的 harness 接缝。

这里的 fixture 是**判据的一部分**：它们规定了实现必须提供什么样的测试接缝。
现在全部抛 NotImplementedError —— 门禁应当红在「实现还不存在」，
而不是红在「fixture 名字拼错了」。实现到位时，把 raise 换成真东西即可。

⚠️ 本文件同样在 `tests/gates/**` 红线内：loop 不得修改（含把 raise 改成 skip）。
"""
import pytest

_TODO = "尚未实现 —— 见 docs/backlog/implementation-roadmap.md 的 P0 交付表"


@pytest.fixture
def live_site():
    """一个可写的 ERPNext 活站点（L2 慢门禁用）。由 P0「零依赖启动」+ 契约层提供。"""
    raise NotImplementedError(f"live_site {_TODO}（P0 · 工具契约层 v0 / 零依赖启动）")


@pytest.fixture
def pack_repo():
    """一个 git 管理的定制包工作副本。由 P0「定制包规范化器 + 差集 apply 引擎」提供。"""
    raise NotImplementedError(f"pack_repo {_TODO}（P0 · 定制包规范化器 / 差集 apply 引擎）")


@pytest.fixture
def compose_stack():
    """已 `docker compose up -d` 起来的整栈，用完拆掉。由 P0「零依赖启动 CI」提供。"""
    raise NotImplementedError(f"compose_stack {_TODO}（P0 · 零依赖启动 CI）")
