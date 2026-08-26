"""🔴 门禁 · 断言里不许有「失败也算过」的逃逸出口

判据来源：人 2026-08-26 裁定（P1 复盘 B②）。

## 它防的是什么 —— 一次真实的误放行

`tests/unit/test_explain_service_body.py` 那条答案面判据原本逐字：

    assert payload["answer"] or payload["accepted"] is False

**一个 `or`。** 模型拒绝时 `accepted` 恰好就是 `False` ⇒ **空答案照过**。
实际后果：CI 的路由器走到一个没有免费额度的模型、每一次解释都 403、
每一次都回空答案，而这条判据**一路绿着好几天** —— 那阵子报的「54 项全绿」，
在「Agent 到底能不能答」这一维上**是空的**。

它不是被门禁发现的，是人手动跑了一次真解释才撞出来的。

## 与既有口径同族

本仓已经写死过一条：「**一条会 skip 的门禁等于一条不存在的门禁**」。
本条是它的同族形态：「**一条带失败逃逸的断言等于半条判据**」。
两条防的是同一件事 —— **判据绿着，但它什么都没验**。

## 判据形状

扫 `tests/` 下所有 `assert`，标出「`or` 的某一侧是**失败态**」的写法：

    assert X or Y is False          # 失败也算过
    assert X or Y is None
    assert X or not Y
    assert X or Y == []             # 空也算过

⚠️ **不禁止所有 `or`。** `assert a or b` 里两侧都是**正常态**是合法的
（例如 `assert status in (200, 503)` 那种「两种都对」的语义）。
本条只拦「**其中一侧等价于『它失败了』**」的形状。

⚠️ **允许显式豁免**：确有正当理由的，在该行上一行写
`# assert-escape-ok: <理由>`。**豁免必须写理由** —— 空豁免本身就是逃逸。
"""
from __future__ import annotations

import ast
import pathlib

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TESTS = _REPO_ROOT / "tests"
_EXEMPT = "assert-escape-ok:"

# 「这一侧等价于『它失败了』」的形状。
_FAILURE_SHAPES = ("is False", "is None", "== []", "== {}", '== ""')


def _py_files() -> list[pathlib.Path]:
    return sorted(p for p in _TESTS.rglob("*.py") if "__pycache__" not in p.parts)


def _is_failure_side(node: ast.AST, src: str) -> bool:
    """这一侧是不是『它失败了』的写法。

    ⚠️ **只认把某个字段比作失败值的显式写法**（`is False` / `is None` / 空容器）。

    **裸 `not X` 不算** —— 第一版把它也算进去，当场误报了
    `tests/unit/test_pack_export.py:263`：

        assert not scope_dir.exists() or not list(scope_dir.glob("*.json"))

    那一条两侧都是「**没有残留文件**」，都是正常态，`not` 在那里表示
    「不存在是对的」，不是「它失败了」。**判据宁可窄一点也不要误报** ——
    一条会误报的门禁，最后会被人加豁免加到失效。
    """
    text = ast.get_source_segment(src, node) or ""
    return any(shape in text for shape in _FAILURE_SHAPES)


def test_no_assertion_passes_on_its_own_failure_case() -> None:
    """`assert 成功 or 失败` —— 这种断言恒真，等于没写。"""
    offenders: list[str] = []
    for path in _py_files():
        src = path.read_text(encoding="utf-8")
        lines = src.splitlines()
        tree = ast.parse(src, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assert):
                continue
            test = node.test
            if not (isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or)):
                continue
            if not any(_is_failure_side(v, src) for v in test.values):
                continue
            # 上一行写了带理由的豁免 ⇒ 放行
            prev = lines[node.lineno - 2].strip() if node.lineno >= 2 else ""
            if _EXEMPT in prev and prev.split(_EXEMPT, 1)[1].strip():
                continue
            rel = path.relative_to(_REPO_ROOT).as_posix()
            offenders.append(f"{rel}:{node.lineno}  {(ast.get_source_segment(src, node) or '')[:88]}")

    assert not offenders, (
        "断言里有「失败也算过」的逃逸出口，这种断言恒真、等于没写：\n  "
        + "\n  ".join(offenders)
        + "\n\n改法：拆成两条独立断言，各测一件事，谁坏了都指得出来。\n"
        "确有正当理由的，在该行上一行写 `# assert-escape-ok: <理由>` —— **必须写理由**。"
    )
