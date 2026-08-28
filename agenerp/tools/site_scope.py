"""站点全局面的三个执行体：`system.overview` · `permission.scope` · `schema.search`。

三个都不针对某一张单据，而是回答「这个站点/这个身份/这个词，落在哪儿」。
契约的实测硬约束逐条落在下面的代码里，**不在注释里**——注释不可测。

三个都从同一个候选集出发：**属于业务 app 的实体 DocType**（`business_doctypes`）。
按 app 过滤是 §7.3.1 的实测裁剪规则（不过滤时九成是 Token Cache 这类框架管道）。

`system.overview` 与 `schema.search` 在它之上再过一道「表里真有数据」
（`schema.search` 的裁剪规则：本站点 542 → 88，干扰项几乎全来自空表）。
**`permission.scope` 不过这一道**：那道筛子要对每个候选计数，而计数本身需要读权限——
拿它去筛「能读什么」是循环依赖，受限身份会在第一次计数上 403 而不是得到 `can_read: False`。
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from agenerp.site import SiteError
from agenerp.tools.runtime import Outcome, Session

# 站点自己的 app 名。按 app 过滤是三个工具共用的裁剪规则：
# 不过滤时老板 83 个 DocType、工人 61 个，九成是 Token Cache / Desktop Icon 这类管道。
FRAMEWORK_APP = "frappe"

# `frappe.client.has_permission` 是 REST 面上唯一走得通的探测方式（2026-08-24 实测：
# `frappe.permissions.has_permission` 回 403，不在白名单）。**不得从 DocPerm / Custom DocPerm
# 反推**——反推版漏报了 Sales Invoice，而该用户明明读得到；漏报比噪声更危险。
HAS_PERMISSION_METHOD = "frappe.client.has_permission"
COUNT_METHOD = "frappe.client.get_count"

# 记账与库存两条流水的日期字段。「数据时间范围」取它们的并集：缺了它模型会对着空区间提问。
_DATE_SOURCES = (("GL Entry", "posting_date"), ("Stock Ledger Entry", "posting_date"))


def _fields(names: tuple[str, ...]) -> dict[str, str]:
    return {"fields": json.dumps(list(names)), "limit_page_length": "0"}


def business_doctypes(session: Session) -> list[dict]:
    """站点上属于业务 app 的实体 DocType（非框架、非单例、非子表、非虚拟）。

    **虚拟 DocType 必须排掉**：它们没有物理表，`frappe.client.get_count` 对它们回
    `{}`（无 `message`）而不是 0（2026-08-24 实测 `Bulk Transaction Log`，`is_virtual = 1`）。
    不排掉的话，一个纯粹的结构事实会被读成「站点答不上话」。
    """
    rows = session.list_rows(
        "DocType", _fields(("name", "module", "istable", "issingle", "is_virtual"))
    )
    modules = session.list_rows("Module Def", _fields(("name", "app_name")))
    app_of = {m["name"]: m.get("app_name") for m in modules}
    return [
        row
        for row in rows
        if not row.get("istable")
        and not row.get("issingle")
        and not row.get("is_virtual")
        and app_of.get(row.get("module")) not in (None, FRAMEWORK_APP)
    ]


def doctypes_with_data(session: Session) -> tuple[list[dict], list[str]]:
    """业务 DocType 里**表中真有行**的那些（按行数降序），外加**当前身份读不到的**那些。

    代价照实记：一次 `frappe.client.get_count`／候选，本站点 239 次、约 2 秒
    （2026-08-24 实测）。REST 面上没有批量计数端点，这是够得着的唯一口径。

    **只有 HTTP 403 被判成「这个身份读不到」**（2026-08-24 实测：受限用户对
    `Sales Order` 计数回 403，而 `has_permission` 回 `False`）。其余任何失败
    照旧抛出去——把站点宕机读成「什么都没有」正是 `agenerp/site.py` 第 1 条要挡的。
    **读不到的不静默丢**：它们的条数进返回值，让「这个身份看不见 N 个」是可见的。
    """
    counted: list[dict] = []
    unreadable: list[str] = []
    for row in business_doctypes(session):
        try:
            count = session.call_method(COUNT_METHOD, {"doctype": row["name"]})
        except SiteError as exc:
            if "HTTP 403" not in str(exc):
                raise
            unreadable.append(row["name"])
            continue
        if count:
            counted.append({"doctype": row["name"], "module": row.get("module"), "rows": count})
    counted.sort(key=lambda item: (-item["rows"], item["doctype"]))
    return counted, sorted(unreadable)


def _date_range(session: Session) -> dict[str, str]:
    dates: list[str] = []
    for doctype, field in _DATE_SOURCES:
        for row in session.list_rows(doctype, _fields((field,))):
            value = row.get(field)
            if value:
                dates.append(str(value))
    if not dates:
        return {}
    return {"from": min(dates), "to": max(dates)}


def system_overview(session: Session, params: Mapping[str, Any]) -> Outcome:
    """站点全局：公司、有数据的核心 DocType（按记录数降序）、数据时间范围。

    公司名是 Spike 01 实测的硬约束：缺它模型会把公司名当客户名查，白费 2–3 次调用。
    """
    companies = [row["name"] for row in session.list_rows("Company", _fields(("name",)))]
    core, unreadable = doctypes_with_data(session)
    time_range = _date_range(session)
    return Outcome(
        data={
            "companies": companies,
            "core_doctypes": core,
            "data_time_range": time_range,
            "unreadable_doctypes": len(unreadable),
        },
        facts={"company_names": companies, "data_time_range": time_range},
        rows_key="core_doctypes",
    )


def permission_scope(session: Session, params: Mapping[str, Any]) -> Outcome:
    """当前身份对每个业务 DocType 读得到读不到。**逐个调 `frappe.client.has_permission`**。

    **候选集是全部业务 DocType，不先按「有没有数据」筛**：筛数据要计数，计数要读权限
    （2026-08-24 实测：受限用户对 `Sales Order` 计数回 403），拿它筛「能读什么」是循环依赖。

    **候选集可以由调用方给**（`params["doctypes"]`），不给才走发现式默认路径。
    ⚠️ 这不是便利参数，是实测逼出来的：stock Frappe 里 `DocType` 的读权限**只给
    System Manager 与 Administrator**（2026-08-24 实读该 DocType 的 `DocPerm` 只有这两条），
    且对它建 `Custom DocPerm` **不生效**（同日实测：授了 read 之后
    `has_permission("DocType")` 仍为 `False`）。受限身份因此**枚举不出 DocType 清单**——
    发现式路径只对有元数据读权限的身份成立。这条限制照实记在
    `docs/architecture/module-boundaries.md` §7.6，不靠给工人发 System Manager 绕过去
    （那等于把「受限」这件事取消掉，判别力也就没了）。

    `can_read = False` 的行**照样返回**，不只返回可见的那一半：返回值里全是 `True`
    的话，「一个永远回 true 的假实现」与正确实现长得一模一样（STATE §3 那条 `[open]` 的形状）。

    `permission_probe_method` 由**本次实际调过的方法名**推出来（见 `runtime.Session`），
    不是执行体自报的常量：从 DocPerm 反推的实现调不出 `has_permission`，这条后置断言就红。
    """
    given = params.get("doctypes")
    candidates = (
        [str(name) for name in given]
        if given
        else [entry["name"] for entry in business_doctypes(session)]
    )
    rows: list[dict] = []
    for doctype in candidates:
        answer = session.call_method(
            HAS_PERMISSION_METHOD, {"doctype": doctype, "docname": "", "perm_type": "read"}
        )
        can_read = bool(answer.get("has_permission")) if isinstance(answer, dict) else bool(answer)
        rows.append({"doctype": doctype, "can_read": can_read})
    # **可读的排在前面**：契约的 `max_rows` 是 60，而本站点的业务 DocType 有 239 个。
    # 截断只能截掉读不到的那一半——工具的 target 是「当前身份的可见范围」，
    # 把可见项截掉等于答错。读不到的行照样返回（未被截掉的部分），
    # 因为全是 `True` 的返回值与「一个永远回 true 的假实现」长得一模一样。
    rows.sort(key=lambda row: (not row["can_read"], row["doctype"]))
    probed = sorted({method.rsplit(".", 1)[-1] for method in session.methods()})
    return Outcome(
        data=rows,
        # 恰好探过一种方法时才把它作为事实交出去。零种（什么都没探）与多种（混着反推）
        # 都交出原样的清单，让后置断言红在「探测方式不对」上，而不是红在 KeyError 上。
        facts={"permission_probe_method": probed[0] if len(probed) == 1 else probed},
    )


def _keywords(params: Mapping[str, Any]) -> list[str]:
    raw = params.get("keywords") or params.get("query") or ""
    if isinstance(raw, str):
        return [part for part in raw.replace(",", " ").split() if part]
    return [str(part) for part in raw if str(part)]


def schema_search(session: Session, params: Mapping[str, Any]) -> Outcome:
    """按关键词/结构化匹配找候选 DocType。**召回器，不是选择器**。

    命中口径是 DocType 名与模块名的子串匹配，大小写不敏感；无关键词时回全部候选。
    **搜索面是全部业务 DocType**，表里没行的**标记 `has_data: false` 而不剔除** ——
    「哪个字段存这个」与站点上有没有数据无关（2026-08-27 实测：按有数据过滤时，
    `Request for Quotation` / `Production Plan` 搜出 0 个候选，而它们正是正解所在）。
    向量兜底不在本期（P1.0a §9，重开事件写在那里）：owner doc 的现行结论是
    「结构化导航优先，向量检索降级为兜底召回」，在没有实测召回缺口之前不建索引。
    """
    keywords = [word.lower() for word in _keywords(params)]

    # 🔴 2026-08-27：搜索面从「**有数据的**业务 DocType」放宽到「**全部**业务 DocType」，
    # 没数据的**标记 `has_data: false`，不再剔除**。理由是实测：
    #   `schema.search("Request for Quotation")` → **0 个候选**
    #   `schema.search("Production Plan")`       → **0 个候选**
    # 两个单据在演示站点上没有行，于是整个单据**不在索引里** ——
    # agent 搜的是**完全正确的词**，工具回了空，它只好去猜别的单据
    # （实测因此错了 2 条：答成 `Purchase Order Item.schedule_date`
    #  与 `Material Request Item.qty`）。
    # ⚠️ 问的是 **schema 问题**「哪个字段存这个」—— 答案与站点上有没有数据**无关**。
    # 这与 `meta.fields` 那个 hidden 缺陷是同一 species：
    # **工具把本该是答案的东西过滤掉了**，而失败会伪装成 agent 选错。
    # ⇒ 一律按「**标记而不是剔除**」处理，让调用方自己看得见。
    with_data, unreadable = doctypes_with_data(session)
    rows_of = {e["doctype"]: e.get("rows") for e in with_data}
    universe = [
        {
            "doctype": row["name"],
            "module": row.get("module"),
            "rows": rows_of.get(row["name"], 0),
            "has_data": row["name"] in rows_of,
        }
        for row in business_doctypes(session)
        if row["name"] not in set(unreadable)
    ]
    # 有数据的排前面（行数降序），没数据的跟在后面 —— 顺序是提示，不是过滤。
    universe.sort(key=lambda e: (not e["has_data"], -(e["rows"] or 0), e["doctype"]))
    matched = [
        entry
        for entry in universe
        if not keywords
        or any(
            word in f"{entry['doctype']} {entry.get('module') or ''}".lower() for word in keywords
        )
    ]
    # **命中多少就交多少**，收窄只允许发生在 runtime 的 `max_rows` 截断那一步。
    # 事实由「交出去的条数 == 命中的条数」推出来：一个只挑最优解的选择器式实现
    # （`matched[:1]`）在这里必然为假，而不是靠执行体自报一句「我是召回器」。
    candidates = list(matched)
    return Outcome(
        data={"keywords": keywords, "candidates": candidates},
        facts={"returns_candidate_list_not_single_pick": len(candidates) == len(matched)},
        rows_key="candidates",
    )
