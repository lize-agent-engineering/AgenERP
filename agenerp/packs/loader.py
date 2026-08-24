"""行业包的**装载面与校验器**（P1.6）。落点节是
`docs/architecture/module-boundaries.md` §7.10。

⚠️ **三个「包」不是一回事**，本模块只管第三个：
`agenerp/pack.py` 是**定制包**（Custom Field / Property Setter 的导出与 apply）·
`agenerp/inspection/minimal.py` 是**引擎自带的判据夹具**（一条规则，不是制品）·
本模块是**行业包制品**（`pack_id` + `rule_id` 的来源）。

`Decision` D2：包文件是 **JSON**，不是 D01 建议的 YAML —— CI 的五处
`pip install pytest certifi` 里没有 PyYAML，而 `.github/workflows/**` 在红线内，
本期无权加装依赖（`agenerp/contracts.py:9-11` 已有同一条先例）。
**代价照实记**：JSON 写不了注释，规则的「为什么」只能进 `statement` 字段。

`Decision` D1：判据表达取 `agenerp.inspection.rules.Rule` 的形状，
**不取 D01 建议的 `query`（裸 SQL）+ `assert`（自然语言）** —— 本仓取数走站点 REST
只读端点，根本没有 SQL 面；自然语言 `assert` 不可执行，落地必然退回「让模型理解规则」。

**装载失败一律抛，不降级、不返回半份包**（`RuleLoadError` 的既有纪律）：
半份规则清单跑出来的零命中，读起来与「一切正常」一模一样。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agenerp.inspection.engine import TestCaseFailure, check_test_cases
from agenerp.inspection.rules import Rule, RuleLoadError, load_rules

PACK_FILE = "pack.json"
PACK_KEYS = frozenset({"pack_id", "version", "requires_doctypes", "rules"})
DISCRETE = "discrete"


class PackNotFound(FileNotFoundError):
    """查无此包。**与「包装载失败」分得开**：一个是没找到，一个是找到了但坏的。
    两者混成同一个错误时，`--pack` 拼错会被读成「这个包有问题」而不是「你打错了」。"""


class PackLoadError(RuleLoadError):
    """包装载失败（顶层形状不合，或某条规则不合形状 / 缺 `test_case`）。"""


@dataclass(frozen=True)
class Pack:
    """一份装载好的行业包。`pack_id` 是**命中记录的出处**（`Decision` D5）：
    它由包这一层给出，经 `agenerp.inspection.engine.run()` 的 `pack_id` 形参盖进 `Hit`，
    **不从 `rule_id` 里猜** —— 同一条 `rule_id` 挂在两个包下时出处必须不同。"""

    pack_id: str
    version: str
    requires_doctypes: tuple[str, ...]
    rules: tuple[Rule, ...]
    path: Path

    def rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.rules)


def packs_root() -> Path:
    """默认的行业包目录：仓库根的 `industry-packs/`（`Decision` D4 选 (A)）。

    今天可判的口径只有两条 —— **路径解析方式**（本函数：由本文件位置上溯两级到仓库根）
    与**它自己的判据**（解析不到时 `load_pack` 抛 `PackNotFound`，CLI 退非零）。
    ⚠️ 「随 wheel 打包」不在可判之列：仓里没有 `MANIFEST.in`、`pyproject.toml` 没有
    `[tool.setuptools.package-data]`、CI 也没有任何 wheel 构建步骤。
    因此**「装出来的 wheel 里找不到 `industry-packs/`」只是一个今天不可验证的假设**，
    `--packs-dir` 是它的逃生口。
    """
    return Path(__file__).resolve().parents[2] / "industry-packs"


def available_packs(packs_dir: Path | None = None) -> tuple[str, ...]:
    root = packs_dir or packs_root()
    if not root.is_dir():
        return ()
    return tuple(sorted(item.name for item in root.iterdir() if (item / PACK_FILE).is_file()))


def _text(declaration: Mapping[str, Any], key: str, where: str) -> str:
    value = declaration.get(key)
    if not (isinstance(value, str) and value.strip()):
        raise PackLoadError(f"{where}：`{key}` 缺失或为空")
    return value


def load_pack(pack_id: str, packs_dir: Path | None = None) -> Pack:
    """读一个行业包。**查无此包**抛 `PackNotFound`，**形状不合 / 规则不合**抛 `PackLoadError`。"""
    root = packs_dir or packs_root()
    path = root / pack_id / PACK_FILE
    if not path.is_file():
        raise PackNotFound(
            f"行业包 {pack_id!r} 查无此包：{path} 不存在。"
            f"已查的目录是 {root}（可用 --packs-dir 覆盖）；"
            f"这个目录下现有的包是 {list(available_packs(root))}"
        )
    where = f"行业包 {pack_id!r}（{path}）"
    try:
        declaration = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PackLoadError(f"{where}：不是合法 JSON —— {error}") from error
    if not isinstance(declaration, Mapping):
        raise PackLoadError(f"{where}：顶层必须是对象")
    unknown = sorted(set(declaration) - PACK_KEYS)
    if unknown:
        raise PackLoadError(f"{where}：不认识的顶层键 {unknown}（有限形状，未知键一律拒载）")

    declared_id = _text(declaration, "pack_id", where)
    if declared_id != pack_id:
        raise PackLoadError(
            f"{where}：包里写的 `pack_id` 是 {declared_id!r}，与目录名 {pack_id!r} 对不上。"
            "出处靠它指回来源，对不上就不是同一个包"
        )
    rules = declaration.get("rules")
    if not isinstance(rules, list) or not rules:
        raise PackLoadError(f"{where}：`rules` 缺失或为空 —— 空包与「查过了，没有规则」分不开")
    try:
        loaded = load_rules(rules)
    except RuleLoadError as error:
        raise PackLoadError(f"{where}：{error}") from error
    return Pack(
        pack_id=declared_id,
        version=_text(declaration, "version", where),
        requires_doctypes=tuple(str(name) for name in declaration.get("requires_doctypes", ())),
        rules=loaded,
        path=path,
    )


def validate_pack(pack: Pack) -> tuple[TestCaseFailure, ...]:
    """**逐条真跑 `test_case`**（走 `agenerp.inspection.engine.check_test_cases`），
    返回失败清单，空 = 全过。只检查 `test_case` 这个键存在是不够的：
    那样的校验器在「把 `expect_hit` 翻转」这个变异上照样是绿的。"""
    return check_test_cases(pack.rules)


def describe_failure(pack: Pack, failure: TestCaseFailure) -> str:
    """失败消息**指名到具体对象**：哪个包的哪条规则的哪个测例，期望什么、实测什么。"""
    return (
        f"行业包 {pack.pack_id!r} 的规则 {failure.rule_id!r} 的测例 "
        f"{failure.case!r} 不通过：{failure.reason}"
    )
