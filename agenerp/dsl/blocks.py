"""视图 DSL 的声明格式。**只声明形状，不判对错** —— 判对错在 `validate.py`。

分开的理由和 `agenerp/contracts.py` 一样：声明格式要能被构造出**非法的实例**，
否则校验器的拒绝路径根本没法测。一个在 `__init__` 里就把错误挡掉的 dataclass，
会让「校验器拒绝了它」和「它压根构造不出来」这两件事分不清。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# §10.2 的那张表就是这五行。**封闭**——多一种少一种都是 DSL 与 owner doc 打架。
BLOCK_TYPES = ("list", "detail", "metric", "chart", "explain")

# `metric` 的聚合口径。封闭，且刻意很小：v0 只做只读呈现，不是嵌一门查询语言进来。
AGGREGATES = ("count", "sum", "avg", "min", "max")

# `chart` 的图种。同样封闭。
CHART_KINDS = ("bar", "line", "pie")

# `list` 的筛选算子。与 Frappe 的 filter 语法对齐的最小子集。
FILTER_OPERATORS = ("=", "!=", ">", ">=", "<", "<=", "in", "not in", "like")

SORT_DIRECTIONS = ("asc", "desc")


@dataclass(frozen=True)
class Block:
    """一个块。

    ⚠️ **`fields` 的语义按块类型不同**，这是刻意的，因为五种块投影字段的方式本来就不同：

    - `list` / `detail`：要展示的列，**顺序即展示顺序**
    - `metric`：恰好一个——被聚合的那个字段（`agg="count"` 时也要给，计的是它非空的行）
    - `chart`：恰好两个——`(x 轴, y 轴)`
    - `explain`：**必须为空**。它是解释性文本块，不投影字段

    把五种语义压进一个字段名，是为了让「这个视图用到了哪些字段」有**唯一**答案
    （`View.field_refs()`）——P2.5 的 `schema.drift` 巡检要靠它知道该盯哪些列。
    """

    type: str
    doctype: str | None = None
    fields: tuple[str, ...] = ()
    # `list` 专用
    filters: tuple[tuple[str, str, object], ...] = ()
    sort: tuple[str, str] | None = None
    limit: int | None = None
    # `metric` 专用
    agg: str | None = None
    # `metric` 的基准与对比（§10.2「必须支持基准与对比」）。
    # ⚠️ v0 **只落声明位，不求值** —— 求值要连站点，属 P2.2 渲染器。
    baseline: str | None = None
    # `chart` 专用
    chart_kind: str | None = None
    # `explain` 专用
    question: str = ""
    subject: str | None = None

    title: str = ""


@dataclass(frozen=True)
class View:
    """一个视图 = 一串块。"""

    name: str
    title: str
    blocks: tuple[Block, ...] = field(default_factory=tuple)

    def field_refs(self) -> tuple[tuple[str, str], ...]:
        """这个视图用到的全部 `(DocType, fieldname)`，去重后按字典序。

        **唯一答案**是它存在的意义：校验器要拿它逐条问 schema，
        P2.5 的 `schema.drift` 要拿它知道该盯哪些列。两处用同一个来源，
        才不会出现「校验时看的是一份、巡检时看的是另一份」。
        """
        refs: set[tuple[str, str]] = set()
        for block in self.blocks:
            if not block.doctype:
                continue
            for fieldname in block.fields:
                refs.add((block.doctype, fieldname))
            for entry in block.filters:
                if len(entry) >= 1 and isinstance(entry[0], str):
                    refs.add((block.doctype, entry[0]))
            if block.sort and isinstance(block.sort[0], str):
                refs.add((block.doctype, block.sort[0]))
        return tuple(sorted(refs))
