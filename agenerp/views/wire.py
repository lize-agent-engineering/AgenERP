"""线格式：模型交出来的那段 JSON ↔ `View`。

🔴 **只解析形状，不判对错。** 纪律逐字来自 `agenerp/dsl/blocks.py` 的模块头：
解析器要能造出**非法**的实例，否则校验器的拒绝路径根本没法测。
一个在解析时就把错误挡掉的实现，会让「校验器拒绝了它」和「它压根构造不出来」
这两件事分不清 —— 而 P2.3 的判据里，**拒绝路径就是主角**。

## `WireError` 为什么不复用 `DslError`

两者回注给模型的话术不同：

- `WireError` —— 「你交的不是一个视图」。模型要改的是**输出格式**。
- `DslError`  —— 「你交的是视图，但写错了」。模型要改的是**内容**（块类型、字段名）。

合成一个，模型分不清是格式没说清还是字段找错了，就只能重猜。
**重猜要花一整轮**，而修复轮是有上限的（`loop.py` 的 `REPAIR_ROUNDS`）。

## 边界：接受哪几种文本

`view_from_text()` 只接受两种形状 —— **整段就是 JSON**，或者**一个 ```json 围栏**。
围栏是实测常态（模型十有八九会套一个），**其余一律拒**：
「从一段散文里把 JSON 捞出来」这种宽容会让「模型没按格式答」变成静默通过，
而那正是本项要挡住的失败形态。
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from agenerp.dsl.blocks import Block, View


class WireError(ValueError):
    """模型交的东西**不是一个视图**。消息里必须能看出是哪一块出的问题。"""


_FENCE = re.compile(r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL)


def view_from_text(text: str) -> View:
    """从模型的最终文本里取出视图。整段 JSON 或**一个** ```json 围栏，二者之一。"""
    candidate = text.strip()
    fenced = _FENCE.search(text)
    if fenced:
        candidate = fenced.group(1).strip()
    if not candidate:
        raise WireError("模型没有交出任何内容 —— 视图 DSL 要求一段 JSON 对象。")
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise WireError(
            f"交出来的不是可解析的 JSON（{exc.msg}，第 {exc.lineno} 行第 {exc.colno} 列）。"
            "只接受两种形状：整段就是一个 JSON 对象，或者一个 ```json 围栏。"
        ) from exc
    return view_from_json(payload)


def view_from_json(payload: Any) -> View:
    """把一份**已解析**的 JSON 变成 `View`。取值一律不判对错。"""
    if not isinstance(payload, Mapping):
        raise WireError(f"视图要是一个 JSON 对象，收到 {type(payload).__name__}。")

    raw_blocks = payload.get("blocks", [])
    if isinstance(raw_blocks, (str, bytes)) or not isinstance(raw_blocks, Sequence):
        raise WireError(f"blocks 要是一个数组，收到 {type(raw_blocks).__name__}。")

    blocks = tuple(
        _block_from_json(entry, f"blocks[{index}]") for index, entry in enumerate(raw_blocks)
    )
    return View(
        name=_text(payload.get("name")),
        title=_text(payload.get("title")),
        blocks=blocks,
    )


def _block_from_json(entry: Any, where: str) -> Block:
    if not isinstance(entry, Mapping):
        raise WireError(f"{where} 要是一个 JSON 对象，收到 {type(entry).__name__}。")

    return Block(
        type=_text(entry.get("type")),
        doctype=_text(entry.get("doctype")) or None,
        fields=_str_tuple(entry.get("fields")),
        filters=tuple(_seq(entry.get("filters"), f"{where}.filters", "[字段, 算子, 值]")),
        sort=_sort(entry.get("sort")),
        limit=entry.get("limit") if isinstance(entry.get("limit"), int) else None,
        child_fields=_child_fields(entry.get("child_fields"), f"{where}.child_fields"),
        agg=_text(entry.get("agg")) or None,
        baseline=_text(entry.get("baseline")) or None,
        chart_kind=_text(entry.get("chart_kind")) or None,
        question=_text(entry.get("question")),
        subject=_text(entry.get("subject")) or None,
        title=_text(entry.get("title")),
    )


def _text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _seq(value: Any, where: str, item_shape: str) -> list:
    """一个数组段。**长度不对的原样保留**（判它的是校验器），
    但**每一项必须是数组** —— 这一条是线格式的事，理由见下。

    🔴 2026-08-28 活体实测抓到的：`qwen3.7-flash-2026-07-15` 把 `filters` 交成了
    `[{"field": …, "operator": …, "value": …}]` —— 对象数组，不是三元组数组。
    当时这里原样放行，于是 `validate()` 的 `len(entry) != 3` 对一个**三键的 dict**
    成立（`len` 是 3），走到 `entry[1]` ⇒ **KeyError 崩在循环里**。
    一个本该被干净拒绝、回注给模型的格式错，变成了整轮跑飞。

    ⇒ **线格式必须保证交给校验器的每一段都是校验器求得了值的形状。**
    这不违反「只解析形状不判对错」—— 判的正是形状本身。
    界线是：**能不能被求值**归线格式，**取值对不对**归校验器。
    """
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WireError(f"{where} 要是一个数组，收到 {type(value).__name__}。")
    out = []
    for index, item in enumerate(value):
        if isinstance(item, (str, bytes)) or not isinstance(item, Sequence):
            raise WireError(
                f"{where}[{index}] 要写成数组 {item_shape}，"
                f"收到 {type(item).__name__}。"
            )
        out.append(tuple(item))
    return out


def _str_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WireError(f"fields 要是一个字符串数组，收到 {type(value).__name__}。")
    return tuple(item for item in value if isinstance(item, str))


def _sort(value: Any) -> tuple[str, str] | None:
    """长度不对也原样带过去 —— `validate()` 那条「sort 要形如 (字段, asc|desc)」在等它。"""
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise WireError(f"sort 要是一个数组，收到 {type(value).__name__}。")
    return tuple(value)  # type: ignore[return-value]


def _child_fields(value: Any, where: str) -> tuple:
    entries = _seq(value, where, "[Table 字段, 子表 DocType, [字段…]]")
    out = []
    for entry in entries:
        if isinstance(entry, tuple) and len(entry) == 3 and isinstance(entry[2], (list, tuple)):
            out.append((entry[0], entry[1], tuple(entry[2])))
        else:
            out.append(entry)
    return tuple(out)
