"""schema 视图 —— 校验器问「这个字段存在吗」的那个对象。

**它是一个注入进来的只读快照，本模块不连任何站点。** 这和
`agenerp/contracts.py` 的 `Condition.evaluate` 是同一条纪律：校验器要能在
`pip install pytest` 的环境里独立跑，而「连站点才能校验」等于校验器只能在
有站点的地方跑，`tests/dsl` 就成了 live 层。

活站点的那一份由调用方构造（`from_meta_rows`），来源是 `meta.fields` 工具或
`tools/experiments/p2_schema_retrieval/dump_schema.py` 导出的 JSON。
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping


class SchemaView:
    """`{DocType: {fieldname: fieldtype}}` 的只读包装。

    ⚠️ **空的 `SchemaView` 是「这个站点什么都没有」，不是「别查了」。**
    这个区别很要紧：把「空」当成「跳过」，就等于给校验器留了一个
    「拿不到数据时一律放行」的后门 —— P1 那次误放行就是这个形状
    （`docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2）。
    「拿不到 schema」这件事由 `validate()` 抛 `SchemaUnavailable` 表达，
    **不由一个空 `SchemaView` 表达。**
    """

    __slots__ = ("_by_doctype",)

    def __init__(self, by_doctype: Mapping[str, Mapping[str, str]]) -> None:
        self._by_doctype = {
            doctype: dict(fields) for doctype, fields in by_doctype.items()
        }

    def has_doctype(self, doctype: str) -> bool:
        return doctype in self._by_doctype

    def has_field(self, doctype: str, fieldname: str) -> bool:
        return fieldname in self._by_doctype.get(doctype, {})

    def fieldtype(self, doctype: str, fieldname: str) -> str | None:
        return self._by_doctype.get(doctype, {}).get(fieldname)

    def doctypes(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_doctype))

    def __len__(self) -> int:
        return len(self._by_doctype)

    @classmethod
    def from_meta_rows(cls, rows: Iterable[Mapping[str, object]]) -> SchemaView:
        """从 `{doctype, fieldname, fieldtype}` 的行集合构造。

        `dump_schema.py` 的输出与 `meta.fields` 工具的返回都是这个形状。
        """
        by_doctype: dict[str, dict[str, str]] = {}
        for row in rows:
            doctype = str(row.get("doctype") or "")
            fieldname = str(row.get("fieldname") or "")
            if not doctype or not fieldname:
                continue
            by_doctype.setdefault(doctype, {})[fieldname] = str(row.get("fieldtype") or "")
        return cls(by_doctype)
