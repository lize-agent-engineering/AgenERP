"""`agenerp/context/**` 的源码/AST 扫描器 —— Phase 2 的权限红线与 Phase 3 的零站点写**共用这一套**。

两条红线都属于「靠 code review 不算数」的那一类，所以判据必须是机械的：

- **权限/风险红线**（`context-and-memory.md` §8.4，与 `module-boundaries.md` §7.5 红线行同源）：
  本层的任何字段都不得参与权限判定或风险档计算。
- **零站点写**（plan §5.2 的可逆性声明）：本层一处也不写活站点。

⚠️ **黑名单必须是具体的那几样东西，不能写成「禁止 import `agenerp.tools.runtime`」**：
`agenerp/context/immediate.py` 正要 import 它的 `wrap_free_text`，一条过宽的模块级禁令
会当场把 ① 层打红，而那与红线毫无关系。

⚠️ **残余，照实记**：AST 扫描挡得住直写，挡不住 `getattr(client, "create_" + "doc")`
这类拼名调用。v0 接受这条残余，**不得把本扫描说成「已证明不可能写站点」**。
"""

from __future__ import annotations

import ast
from pathlib import Path

CONTEXT_PACKAGE = Path(__file__).resolve().parents[2] / "agenerp" / "context"

# ① 契约求值面：出现其中任一个名字，就说明本层伸手去碰权限判定了。
EVALUATION_NAMES: frozenset[str] = frozenset(
    {
        "ReadOnlyContext",
        "Condition",
        "Evaluation",
        "evaluate",
        "evaluate_all",
        "unsatisfied",
        "check_preconditions",
        "check_postconditions",
    }
)

# ② 站点写入面。`SiteClient` 的只读传输本身不在黑名单里——本层不用它，但禁的是**写**。
SITE_WRITE_NAMES: frozenset[str] = frozenset({"create_doc", "ensure_doc", "delete_custom_field"})

FORBIDDEN_MODULE_PREFIX = "agenerp.contracts"


def source_files() -> tuple[Path, ...]:
    files = tuple(sorted(CONTEXT_PACKAGE.rglob("*.py")))
    assert files, f"{CONTEXT_PACKAGE} 下一个 .py 都没有——扫描器在空转"
    return files


def _trees() -> list[tuple[Path, ast.AST]]:
    return [(path, ast.parse(path.read_text(encoding="utf-8"), str(path))) for path in source_files()]


def _names_used(tree: ast.AST) -> set[str]:
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            used.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            used.update(alias.name.split(".")[-1] for alias in node.names)
    return used


def contracts_imports() -> list[str]:
    """本层对 `agenerp.contracts` 的任何 import —— 一条都不该有。"""
    hits: list[str] = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                FORBIDDEN_MODULE_PREFIX
            ):
                hits.append(f"{path.name}:{node.lineno} from {node.module} import ...")
            elif isinstance(node, ast.Import):
                hits += [
                    f"{path.name}:{node.lineno} import {alias.name}"
                    for alias in node.names
                    if alias.name.startswith(FORBIDDEN_MODULE_PREFIX)
                ]
    return hits


def evaluation_surface_hits() -> list[str]:
    return [
        f"{path.name}: {sorted(_names_used(tree) & EVALUATION_NAMES)}"
        for path, tree in _trees()
        if _names_used(tree) & EVALUATION_NAMES
    ]


def facts_hits() -> list[str]:
    """构造 `facts` 字典、或把它当关键字参数递出去 —— 两种形态都算。"""
    hits: list[str] = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.keyword) and node.arg == "facts":
                hits.append(f"{path.name}:{node.lineno} facts=...")
            elif isinstance(node, ast.Assign):
                hits += [
                    f"{path.name}:{node.lineno} facts = ..."
                    for target in node.targets
                    if isinstance(target, ast.Name) and target.id == "facts"
                ]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == "facts":
                    hits.append(f"{path.name}:{node.lineno} facts: ... = ...")
    return hits


def execute_call_hits() -> list[str]:
    """调 `agenerp.tools.runtime.execute` —— 本层不执行工具，那是控制循环（P1.4）的事。"""
    hits: list[str] = []
    for path, tree in _trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if called == "execute":
                hits.append(f"{path.name}:{node.lineno} execute(...)")
    return hits


def site_write_hits() -> list[str]:
    return [
        f"{path.name}: {sorted(_names_used(tree) & SITE_WRITE_NAMES)}"
        for path, tree in _trees()
        if _names_used(tree) & SITE_WRITE_NAMES
    ]
