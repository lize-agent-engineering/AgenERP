"""非门禁测试 · 钉住 `agenerp/seed/model.py` 里**带公司缩写后缀的常量**的形状。

判据的全部内容是一句话：**站点的 `autoname` 必须有可能派生出这个常量**。
ERPNext v15 的 `Account.autoname` / `Warehouse.autoname` 走 `" - ".join([<x>_name, abbr])`
（2026-08-22 用真载荷在活站点上实测），所以常量必须逐字形如 `<name> - {ABBR}`。

⚠️ **本文件不得经由 `seedsite.strip_abbr` / `seedsite.site_name_of` 求值**：
那两个函数的职责就是把后缀摘掉再拼回去，拿它们证明常量合规是自己跟自己比，判据会空转。
一律对字符串本身断言。

⚠️ **清单靠遍历模块属性得到，不手抄**：第 16 个带后缀的常量加进来时，判据要自己长出来。
"""

from agenerp import seedsite
from agenerp.seed import model as M

SUFFIXED_PREFIXES = ("ACC_", "WH_")


def suffixed_constants() -> list[tuple[str, str]]:
    """`model.py` 里全部带公司缩写后缀的字符串常量，`(属性名, 值)`，按属性名排序。"""
    return sorted(
        (name, value)
        for name, value in vars(M).items()
        if name.startswith(SUFFIXED_PREFIXES) and isinstance(value, str)
    )


def test_the_constant_sweep_actually_finds_something():
    """遍历本身不许空转：一个都扫不到时上面那些断言会全部真空通过。"""
    found = suffixed_constants()

    assert len(found) >= 15, found
    names = [name for name, _ in found]
    assert "ACC_OPERATING" in names and "WH_RAW" in names, names


def test_every_suffixed_constant_can_be_derived_by_the_site_autoname():
    """每一个 `ACC_*` / `WH_*` 都必须等于 `" - ".join([<x>_name, ABBR])`。

    不满足的常量在活站点上**永远命不中**：站点建出来的名字带空格，本仓的常量不带，
    幂等键因此每次都落空。历史实例见
    `docs/bugs/01-acc-operating-constant-can-never-match-a-live-account-name.md`。
    """
    suffix = f" - {seedsite.ABBR}"

    for name, value in suffixed_constants():
        assert value.endswith(suffix), (
            f"{name} = {value!r} 不以 {suffix!r} 结尾，"
            f"站点的 autoname（\" - \".join([<x>_name, abbr])）永远派生不出它；"
            f"常量必须形如 `<name>{suffix}`"
        )
        x_name = value[: -len(suffix)]
        assert x_name, f"{name} = {value!r} 摘掉后缀之后没有名字剩下"
        assert x_name == x_name.strip(), (
            f"{name} = {value!r} 的 `<x>_name` 段带首尾空白（{x_name!r}），"
            f"站点会把它 strip 掉后再拼，派生名与常量对不上"
        )
        assert value == " - ".join([x_name, seedsite.ABBR]), (
            f"{name} = {value!r} ≠ {' - '.join([x_name, seedsite.ABBR])!r}"
        )


def test_the_company_abbr_in_the_constants_is_bound_to_seedsite_abbr():
    """`seedsite.ABBR` 与常量里字面的公司缩写必须是同一个东西。

    两处此刻各写各的（`seedsite.py` 一个 `ABBR = "XM"`，`model.py` 里 15 处字面 `XM`）。
    没有这条绑定，改公司缩写时常量会集体失配而无人告知 —— 而 `strip_abbr`
    自 plan `2026-08-22-2325-1` 起是失败即停，那会变成一次装载都起不来。
    """
    for name, value in suffixed_constants():
        assert value.endswith(seedsite.ABBR), (
            f"{name} = {value!r} 不以 seedsite.ABBR（{seedsite.ABBR!r}）结尾："
            f"公司缩写在两处对不上"
        )
