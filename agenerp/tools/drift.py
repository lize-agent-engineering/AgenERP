"""`schema.drift` 的执行体 —— 孤儿列巡检的工具面。

**口径不在这里。** 「哪些列算孤儿」由 `agenerp.snapshot.schema_drift()` 答，
它直接复用 Frappe 自己的 `trim_table(dry_run=True)`（§11.8）。本模块只做三件事：
**定范围 · 逐表问 · 把答案摆成行**。

自己再算一遍口径会产生**第二套字段口径**，Frappe 一次升级就能让两边错开，
而错开的表现是「孤儿列漏报」——最难发现的那种假绿（§11.5）。

## 两个入口，二选一

- `doctype=<名>` —— 查一张表
- `pack=<包路径>` —— 扫这个定制包**管辖**的那一组（`pack_doctypes`）

**都不给或都给一律拒。** 都不给时悄悄退化成「扫全站 1000+ 表」，是既慢又没人负责的口径；
都给时哪个范围说了算，调用方自己都没想清楚。

⚠️ **巡检只报不删。** 清除面是 `agenerp.apply.drop_orphan_columns`，且它**刻意收窄**到
「本次 apply 真删掉的 fieldname ∩ Frappe 判定的孤儿列」——历轮残留的**故意不碰**
（2026-08-21 实测 `Item` 上 6 条孤儿列，5 条不是本次造成的）。报出来与动手是两件事。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agenerp.oob import TRIM_TABLE
from agenerp.tools.runtime import Outcome, Session, ToolError


def schema_drift_scan(session: Session, params: Mapping[str, Any]) -> Outcome:
    doctypes = _scope(params)
    from agenerp.snapshot import schema_drift

    # 站点名从 **session 的客户端**取 —— 那是「这次调用在跟哪个站点说话」的唯一来源。
    # ⚠️ 不回落到 `AGENERP_SITE`：回落会让「调用方指的站点」与「环境里配的站点」
    # 在不一致时静默按后者跑，而巡检报的是**哪个站点**的孤儿列。
    site = getattr(getattr(session, "client", None), "site", None)
    if not site:
        raise ToolError(
            "schema.drift 要知道查哪个站点，而这次调用没有带站点客户端。"
            "带外命令按站点执行，站点名不许靠环境变量猜。"
        )

    # 🔴 **后置事实从行为推出来，不是自报**，而记录点在 `Session` 里、不在这里。
    # 2026-08-28 审计的变异 B：记录点原来是本函数的一个局部包装器 ⇒
    # 执行体拿没被包装的 runner 去发命令，记录里看不见（实测真发了 DROP COLUMN 还全绿）。
    # 现在 `session.runner` 本身就是记录器，**这里拿不到未被记录的通道**。
    rows: list[dict[str, str]] = []
    for doctype in doctypes:
        for column in schema_drift(doctype, site=site, runner=session.runner):
            rows.append({"doctype": doctype, "column": column})

    # 排序确定：同一个站点复跑两次的输出可以逐行比对。
    rows.sort(key=lambda row: (row["doctype"], row["column"]))
    return Outcome(
        # 🔴 `scanned` 不是装饰：**「零行」没有分母就说明不了任何事**。
        # 一次扫了 0 张表和一次扫了 15 张表都干净，在结果上长得一样。
        data={"rows": rows, "scanned": list(doctypes)},
        facts={
            "orphan_columns_found": len(rows),
            "doctypes_scanned": len(doctypes),
            **derive_facts(session.oob_calls, session.request_count),
        },
        rows_key="rows",
    )


def derive_facts(sent: list, request_count: int) -> dict[str, bool]:
    """两条后置事实**从观测到的行为算出来**，不是自报。

    🔴 **抽成纯函数是 2026-08-28 独立收口审计逼出来的。**
    原来这段内联在 `schema_drift_scan` 里，判据只断言了「它们是 True」——
    而**把它们改成写死的 `True`，13 条判据一条都不红**。
    一条名叫「不是自报的」、实际分辨不出自报的判据，正是本仓最忌讳的那种绿。
    抽出来之后可以喂**该为假**的输入，「能为假」才证明它在算。

    - `uses_frappe_trim_table_dry_run` —— 发出去的每一条都必须是 `trim_table`
      那个白名单调用，**且 argv 里带着 `dry_run` 那个钉死的开关**。
      ⚠️ 只查函数名不查 `dry_run` 时，事实名承诺了它没验的那一半
      （同一轮审计的 C4）。钉子本身在 `agenerp/oob.py:ALLOWED_CALLS`，
      判据在 `tests/unit/test_schema_drift_oob.py::test_caller_cannot_smuggle_dry_run_false`；
      这里查的是「那颗钉子确实出现在这次真发出去的命令里」。
    - `reports_without_dropping` —— 「只报不删」在传输面的可观测形态：
      **一个 REST 请求都没发**（删 Custom Field 走 REST），且命令里没有 drop。
    """
    joined = [" ".join(c.argv) for c in sent]
    return {
        "uses_frappe_trim_table_dry_run": bool(joined)
        and all(TRIM_TABLE in text and "dry_run" in text for text in joined),
        "reports_without_dropping": request_count == 0
        and all("drop" not in text.lower() for text in joined),
    }


def _scope(params: Mapping[str, Any]) -> tuple[str, ...]:
    """定范围。**二选一**，且空包按错而不是按干净处理。"""
    doctype = str(params.get("doctype") or "").strip()
    pack = str(params.get("pack") or "").strip()

    if bool(doctype) == bool(pack):
        raise ToolError(
            "schema.drift 要**二选一**：给 `doctype`（查一张表）或 `pack`（扫这个包管辖的那组）。"
            f"收到 doctype={doctype!r}、pack={pack!r}。"
            "都不给时悄悄退化成「扫全站」是既慢又没人负责的口径；都给时哪个范围说了算说不清。"
        )

    if doctype:
        return (doctype,)

    from agenerp.apply import pack_doctypes

    covered = tuple(sorted(pack_doctypes(pack)))
    if not covered:
        # 🔴 空包扫出零行，与「这个包一张表都不管」**不是一回事**。
        # 合并成「干净」会让一个打错的路径看起来像体检通过。
        raise ToolError(
            f"定制包 {pack!r} **一张表都不管**（`<包>/doctypes/` 下没有文件）——"
            "这与「扫过了、很干净」不是一回事，多半是路径给错了。"
        )
    return covered
