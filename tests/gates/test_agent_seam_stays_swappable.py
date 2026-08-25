"""🔴 门禁 · agent 接缝保持可换（循环只许一处 + ChatAdapter 只许在 routing 内构造）

判据来源：人 2026-08-25 的两条裁定。

## 本门禁在防什么

不是防「用错框架」，是防**接缝烂掉**。

人问过一个真问题：等后面 Agent、工具、skills 越来越多，再定 agent harness
就晚了。核查后的结论是 —— **切换成本不随 Agent 数量增长，它随「抽象有多像
某个框架」增长**。今天工具是 `ToolContract` 数据、模型调用全走 `route()`、
agent 循环只有一处，所以换 harness 只需写一个适配器，成本 O(1)。

**真正会让成本失控的只有一件事：多出第二处手写 agent 循环。**
到那时每加一个 Agent 就多一份要迁移的循环，成本才真的变成 O(N)。

本门禁把那件事钉死。它不阻止将来上 harness —— 恰恰相反，它保证到那天
还换得动（`docs/masterplan/DECISIONS.md` D-22）。

## 两条判据

**① agent 循环只许一处。** 判据是「`.chat(...)` 出现在 `for` / `while` 体内」
—— 那是「反复问模型直到收敛」的形状，也就是 agent 循环本身。一次性调用
（如 `agenerp/judging/judge.py` 的裁判）不在此列，**因为它不迭代**。

**② `ChatAdapter` 只许在 `agenerp/routing/` 内构造。** 独立收口审计 F8：
`ChatAdapter(config, model="…").chat(...)` 会绕过全部能力校验，发出一次本该
按 `lineage` 分档的调用。§12.1 ③「绝不静默降级」因此**只对走 `route()` 的
调用方成立**。人 2026-08-25 裁定「加静态判据，不收窄导出面」—— 收窄会破坏
plan 写死的交付形状，静态判据能堵住真正的风险口。

⚠️ **这两条都是静态判据，不打站点、不调模型**，因此在任何模式下都该绿。
它红了只意味着一件事：**有人在接缝上开了新口子**。
"""
from __future__ import annotations

import ast
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PKG = _REPO_ROOT / "agenerp"

# 唯一允许承载 agent 循环的模块。要加第二处，先改这里 —— 而改这里会逼人
# 在 review 里正面回答「为什么需要第二处循环」，那正是本门禁的目的。
_ALLOWED_LOOP = {"agenerp/explain/loop.py"}
# `ChatAdapter` 的合法构造域。
_ALLOWED_ADAPTER_PREFIX = "agenerp/routing/"


def _py_files() -> list[pathlib.Path]:
    return sorted(p for p in _PKG.rglob("*.py") if "__pycache__" not in p.parts)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def test_agent_loop_lives_in_exactly_one_module() -> None:
    """`.chat(...)` 在迭代体内 —— 即 agent 循环 —— 只许出现在一处。"""
    found: dict[str, list[int]] = {}
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "chat"
                ):
                    found.setdefault(_rel(path), []).append(inner.lineno)

    assert found, (
        "一处 agent 循环都没找到 —— 判据本身可能已失效（比如 `.chat` 被改名）。"
        "这不是好消息：门禁静默地什么都不再检查。请核对判据而不是删掉本条。"
    )
    extra = {k: v for k, v in found.items() if k not in _ALLOWED_LOOP}
    assert not extra, (
        f"出现了第二处 agent 循环：{extra}\n"
        "切换 harness 的成本随手写循环的份数增长 —— 一份是 O(1)，N 份是 O(N)。\n"
        "若确实需要第二处，请先在 DECISIONS.md 回答「为什么不能复用 explain/loop.py」，"
        "再把它加进本文件的 _ALLOWED_LOOP。"
    )


def test_chat_adapter_is_only_constructed_inside_routing() -> None:
    """`ChatAdapter(...)` 绕过能力校验 —— 只许在 `agenerp/routing/` 内构造。"""
    offenders: dict[str, list[int]] = {}
    for path in _py_files():
        rel = _rel(path)
        if rel.startswith(_ALLOWED_ADAPTER_PREFIX):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "ChatAdapter":
                    offenders.setdefault(rel, []).append(node.lineno)

    assert not offenders, (
        f"`ChatAdapter` 在 routing 之外被构造：{offenders}\n"
        "这条路绕过全部能力校验（独立收口审计 F8），会发出一次本该按 lineage 分档的调用。\n"
        "请改走 `agenerp.routing.route()` —— 它在能力不满足时明确失败，不静默降级。"
    )
