"""两份 `InspectionReport.as_dict()` 的**纯比对器** —— dict 进、结构化差异出。

plan 是 `docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md`。
落点节 `docs/architecture/module-boundaries.md` §7.19。
**它是实验设施，不是产品代码**（先例 `tools/experiments/p1_insight_live/run.py`）。

⚠️ **本文件 `import` 本仓任何模块都是一次回归。** 只用标准库。
这不是洁癖，是 plan §6 H7 ① 那条判据的被测对象：
判据在**全新解释器**里 `import` 本文件之后断言 `agenerp.routing` 不在 `sys.modules`。
起草期实测过：同目录的 `run.py` **担不起这个主张**（它按路径加载
`tests/unit/inspection_fakes.py`，那条链 `:39` → `explain_fakes` → `agenerp.routing`），
所以主张的主语**只能是比对器**。**照实分开，不假装 `run.py` 也干净。**

比对器的四条契约（plan Phase 3 起草期写死，执行期不许现编）：

1. **比对面是两份报告的全部三个键**（`rule_ids` / `request_count` / `hits`），
   其中 `hits` 逐条比 `Hit.as_dict()` 的**全部七个键**。
   键集合**在本文件里逐字写死并强制校验** —— 报告多一键少一键当场抛，
   不静默按已知键比（那样新增的键会永远不被比）。
2. **`request_count` 只记录、不参与一致性判定。** 这是一条**取舍**，不是最佳实践。
   实测依据：离线侧 `request_count = 10`，而活站点侧是 **9**（`module-boundaries.md` §7.10
   逐字记的 H4 实测）—— **两侧本来就不同**；把它算进判定会让比对**永远不一致**，
   而恒红与恒绿一样没有判别力。正反两面见 plan Phase 3 的 `Decision D1`。
3. **比对前先断言两侧命中集合非空。** 两侧都空 ⇒ `incomparable`（「比不了」），
   **不是** `identical` —— 否则「两个空集相等」也叫「逐字一致」。
   ⚠️ 恰好一侧空是**另一件事**：那时两侧显然不同，判 `different` 更强，且不许崩。
4. **输出是结构化差异，不是布尔。** 哪条 `rule_id`、哪个 `subject`、两侧各是什么，
   都要从输出里读得出来。

**顺序不是判别面**：`hits` 按内容做多重集比对（同一条命中出现两次算两次），
一侧列表倒序仍判一致 —— 否则比对器在测排序，不是在测内容。
`rule_ids` 相反，按 plan §6 H3 逐字比**含顺序**的列表（同一份包、同一个顺序）。
"""

from __future__ import annotations

import json
from typing import Any

REPORT_KEYS = ("rule_ids", "request_count", "hits")
HIT_KEYS = (
    "pack_id",
    "rule_id",
    "statement",
    "subject",
    "quantity_name",
    "quantity",
    "measures",
)

IDENTICAL = "identical"
DIFFERENT = "different"
INCOMPARABLE = "incomparable"

SIDES = ("offline", "live")


class ParityInputError(ValueError):
    """喂进来的东西不是一份 `InspectionReport.as_dict()`。

    **不降级成「判不一致」** —— 那会把「形状变了」和「数据不同」混成一件事，
    而前者意味着比对面本身失效了。
    """


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _check_report(report: Any, side: str) -> None:
    if not isinstance(report, dict):
        raise ParityInputError(f"{side} 侧不是 dict：{type(report).__name__}")
    if sorted(report) != sorted(REPORT_KEYS):
        raise ParityInputError(
            f"{side} 侧的报告键集合不是 {sorted(REPORT_KEYS)}，实为 {sorted(report)} —— "
            "比对面是 `InspectionReport.as_dict()` 的全部键，多一键少一键都不许静默放过"
        )
    if not isinstance(report["rule_ids"], list):
        raise ParityInputError(f"{side} 侧的 rule_ids 不是 list")
    if not isinstance(report["hits"], list):
        raise ParityInputError(f"{side} 侧的 hits 不是 list")
    for index, hit in enumerate(report["hits"]):
        if not isinstance(hit, dict):
            raise ParityInputError(f"{side} 侧第 {index} 条命中不是 dict")
        if sorted(hit) != sorted(HIT_KEYS):
            raise ParityInputError(
                f"{side} 侧第 {index} 条命中的键集合不是 {sorted(HIT_KEYS)}，实为 {sorted(hit)}"
            )


def _identity(hit: dict) -> str:
    """一条命中的**身份**：出处 + 规则 + 分组键取值。差异要指名到这一层。"""
    return _canonical(
        {"pack_id": hit["pack_id"], "rule_id": hit["rule_id"], "subject": hit["subject"]}
    )


def _fingerprint(hit: dict) -> str:
    """一条命中的**全部七个键**。内容比对判在它上面。"""
    return _canonical({key: hit[key] for key in HIT_KEYS})


def _multiset(hits: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for hit in hits:
        out.setdefault(_fingerprint(hit), []).append(hit)
    return out


def _named(hit: dict) -> dict:
    """差异报告里指名一条命中用的最小事实（**指名到 `rule_id` 与 `subject`**）。"""
    return {
        "pack_id": hit["pack_id"],
        "rule_id": hit["rule_id"],
        "subject": hit["subject"],
        "quantity_name": hit["quantity_name"],
        "quantity": hit["quantity"],
    }


def _hit_diff(offline: list[dict], live: list[dict]) -> dict:
    left, right = _multiset(offline), _multiset(live)
    only_offline: list[dict] = []
    only_live: list[dict] = []
    matched = 0
    for fingerprint in sorted(set(left) | set(right)):
        mine, theirs = left.get(fingerprint, []), right.get(fingerprint, [])
        matched += min(len(mine), len(theirs))
        only_offline.extend(mine[len(theirs):])
        only_live.extend(theirs[len(mine):])

    # 同一个身份两侧都在、但七个键的内容对不上 —— 这是最要读得出来的一类差异，
    # 单看 `only_*` 只能看到「一边多一条、一边少一条」，看不出差在哪个键上。
    differing: list[dict] = []
    by_identity_left: dict[str, list[dict]] = {}
    for hit in only_offline:
        by_identity_left.setdefault(_identity(hit), []).append(hit)
    by_identity_right: dict[str, list[dict]] = {}
    for hit in only_live:
        by_identity_right.setdefault(_identity(hit), []).append(hit)
    for identity in sorted(set(by_identity_left) & set(by_identity_right)):
        for mine, theirs in zip(by_identity_left[identity], by_identity_right[identity]):
            differing.append(
                {
                    "identity": json.loads(identity),
                    "differing_keys": sorted(
                        key for key in HIT_KEYS if mine[key] != theirs[key]
                    ),
                    "offline": mine,
                    "live": theirs,
                }
            )

    return {
        "equal": not only_offline and not only_live,
        "matched": matched,
        "count": {"offline": len(offline), "live": len(live)},
        "only_offline": sorted(( _named(hit) for hit in only_offline), key=_canonical),
        "only_live": sorted((_named(hit) for hit in only_live), key=_canonical),
        "differing": sorted(differing, key=_canonical),
    }


def compare(offline: Any, live: Any) -> dict:
    """两份 `InspectionReport.as_dict()` → 一份结构化差异。**不是布尔。**

    `verdict` 三取一：`identical` / `different` / `incomparable`。
    **`incomparable` 只在两侧命中集合都空时出现**（契约 ③），它不是一种「一致」。
    """
    _check_report(offline, "offline")
    _check_report(live, "live")

    # 契约 ③：**非空断言写在任何比对之前**。先比后判的实现在两侧都空时会返回
    # 「一致」，而那正是本条要挡的假实现。
    empty = [side for side, report in zip(SIDES, (offline, live)) if not report["hits"]]
    request_count = {
        "offline": offline["request_count"],
        "live": live["request_count"],
        "judged": False,
        "note": (
            "契约 ②：只记录、不参与一致性判定。两侧本来就不同"
            "（离线侧走假站点行源、活站点侧走 REST），"
            "算进判定会让比对恒红 —— 恒红与恒绿一样没有判别力。"
        ),
    }
    if len(empty) == len(SIDES):
        return {
            "verdict": INCOMPARABLE,
            "reason": (
                "两侧命中集合都空 —— **比不了**，不是「一致」。"
                "空集相等在这里没有判别力（plan §6 H4 / 契约 ③）。"
            ),
            "empty_sides": list(empty),
            "rule_ids": {
                "offline": list(offline["rule_ids"]),
                "live": list(live["rule_ids"]),
                "equal": list(offline["rule_ids"]) == list(live["rule_ids"]),
            },
            "hits": _hit_diff(offline["hits"], live["hits"]),
            "request_count": request_count,
        }

    rule_ids = {
        "offline": list(offline["rule_ids"]),
        "live": list(live["rule_ids"]),
        "equal": list(offline["rule_ids"]) == list(live["rule_ids"]),
    }
    hits = _hit_diff(offline["hits"], live["hits"])
    return {
        "verdict": IDENTICAL if (rule_ids["equal"] and hits["equal"]) else DIFFERENT,
        "reason": "",
        "empty_sides": list(empty),
        "rule_ids": rule_ids,
        "hits": hits,
        "request_count": request_count,
    }
