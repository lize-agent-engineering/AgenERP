"""P0 门禁 · 种子数据集：确定性 + 内置的已知业务荒谬。

判据来源（roadmap P0 交付表，逐字）：

    种子数据 | **确定性程序化生成**的离散制造数据集（不含图片，无第三方权利），
    **必须内置一个已知业务荒谬**（如成品积压 1,010 台）作为洞察 Agent 与
    行业包规则的固定测例

以及 P1 验收里那条对它的引用：行业包声明「成品库存无对应订单」规则后，
应报出「成品仓积压 1,010 台、价值 3,110,200 元」。

D-9 起样板公司换成本项目自有的虚构实体（恒锐动力 / 储能电池包），单位由
米改台、价格改为电池包量级；**数量骨架 1,000 / 990 / 1,010 原样保留**——
那是这个测例的身份。历史实测记录（`docs/analysis/`）保持原样不改，那是证据。

**本文件里的数字是判据自带的，绝不从 `agenerp.seed.checks` import。**
那里有一份同名常量（`EXPECTED_BACKLOG_QTY` 等），但它是**被测实现的一部分**：
import 它等于让实现自己给自己判卷 —— 常量被改成 999，实现的自检照样全绿。
判据必须独立持有真值，哪怕看起来像重复。这与 `conftest.py` 里 `pack_repo`
不复用 `agenerp` 解析函数是同一条理由。
"""
from __future__ import annotations

import json

# —— 判据自带的真值（出处：roadmap P0 交付表 + P1 验收）——
BACKLOG_QTY_UNITS = 1010.0       # 成品仓积压（台）
BACKLOG_VALUE_CNY = 3110200.0    # 积压价值
FINISHED_GOODS_HINT = "成品"      # 成品仓的识别线索

# 第三方权利风险词：真实品牌 / 商标 / 受版权保护的作品名。
# 数据集必须是程序化生成的虚构数据，不许夹带这类东西。
THIRD_PARTY_MARKS = (
    "nike", "adidas", "uniqlo", "zara", "h&m", "gucci", "prada", "chanel",
    "louis vuitton", "burberry", "disney", "hello kitty", "marvel",
    "优衣库", "耐克", "阿迪达斯", "迪士尼",
)

# 二进制 / 图片载荷的痕迹：数据集不含图片（roadmap 逐字要求）
BINARY_HINTS = ("data:image", "base64,", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")


def _dataset(seed: int = 42):
    from agenerp.seed import generate
    return generate(seed)


def _as_json(dataset) -> str:
    """把数据集序列化成可比字符串。用于确定性比对与全文扫描。"""
    return json.dumps(
        {k: v for k, v in sorted(dataset.records.items())},
        ensure_ascii=False, sort_keys=True, default=str,
    )


def test_generation_is_deterministic():
    """同一个 seed 两次生成必须逐字节相同 —— 否则它当不了固定测例。"""
    a, b = _dataset(42), _dataset(42)
    assert _as_json(a) == _as_json(b), "同一 seed 两次生成结果不同，数据集不是确定性的"
    assert a.as_of == b.as_of, "两次生成的基准日期不同 —— 大概率用了 today()，会随时间漂移"


def test_different_seed_yields_different_data():
    """seed 参数必须真的起作用，否则「确定性」是假的（写死一份也满足上一条）。"""
    assert _as_json(_dataset(42)) != _as_json(_dataset(7)), (
        "换 seed 结果不变 —— 数据集是写死的，不是程序化生成的"
    )


def test_backlog_absurdity_is_present_and_exact():
    """成品仓积压 1,010 米、价值 6,450 元，必须精确存在。

    这是整个数据集存在的理由：洞察 Agent 与行业包规则的固定测例。
    数字对不上，P1 的验收（「无需指令报出积压」）就失去了判定基准。
    """
    ds = _dataset(42)
    bins = ds.records.get("Bin", ())
    finished = [b for b in bins if FINISHED_GOODS_HINT in str(b.get("warehouse", ""))]
    assert finished, f"找不到成品仓的库存记录，仓库有：{[b.get('warehouse') for b in bins]}"

    qty = sum(float(b.get("actual_qty") or 0) for b in finished)
    value = sum(float(b.get("stock_value") or 0) for b in finished)
    assert qty == BACKLOG_QTY_UNITS, f"成品仓积压应为 {BACKLOG_QTY_UNITS} 台，实际 {qty}"
    assert value == BACKLOG_VALUE_CNY, f"积压价值应为 {BACKLOG_VALUE_CNY} 元，实际 {value}"


def test_backlog_is_discoverable_by_a_rule_not_just_present():
    """积压必须**在规则看得见的地方**：成品库存量 > 未交付订单量。

    只是「有这么多库存」不够——洞察 Agent 是靠「成品库存无对应订单」这条规则
    发现它的。若订单量恰好覆盖库存，规则就不该报警，那这个测例也就废了。
    """
    ds = _dataset(42)
    finished_qty = sum(
        float(b.get("actual_qty") or 0)
        for b in ds.records.get("Bin", ())
        if FINISHED_GOODS_HINT in str(b.get("warehouse", ""))
    )
    open_order_qty = 0.0
    for so in ds.records.get("Sales Order", ()):
        for item in so.get("items", ()) or ():
            open_order_qty += float(item.get("qty") or 0) - float(item.get("delivered_qty") or 0)
    assert finished_qty > open_order_qty, (
        f"成品库存 {finished_qty} 未超过未交付订单量 {open_order_qty}，"
        "「库存无对应订单」这条规则不会报警 —— 这个固定测例失去意义"
    )


def test_no_images_or_binary_payloads():
    """roadmap 逐字要求「不含图片」。图片会带来体积、版权与不可 diff 三重问题。"""
    blob = _as_json(_dataset(42)).lower()
    hits = [h for h in BINARY_HINTS if h in blob]
    assert not hits, f"数据集里出现了图片/二进制载荷痕迹：{hits}"


def test_no_third_party_rights():
    """roadmap 逐字要求「无第三方权利」。程序化生成的虚构数据不许夹带真实品牌。"""
    blob = _as_json(_dataset(42)).lower()
    hits = [m for m in THIRD_PARTY_MARKS if m in blob]
    assert not hits, f"数据集里出现了第三方品牌/权利标识：{hits}"
