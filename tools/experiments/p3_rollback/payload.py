"""P3.2 探测的**容器内测量载荷** —— 这个文件永远不在宿主上 import。

它由 `probe.py` 通过 `docker compose exec -T backend … python3 -` 的 **stdin** 投递
（该通道 2026-08-29 实测透传，见 `docs/evidence/p3-rollback/README.md` 的「已知未核实」表），
因此模块级 `import frappe` 在宿主上必然 `ModuleNotFoundError` —— **这不是缺陷，是落点**：
`frappe.db` 在 REST 面上根本够不着（`agenerp/oob.py` 模块头同一条理由），
四个前提里有三个只能在带外的进程内测。

配置一律走**环境变量**，不走 argv：stdin 已经被脚本本身占满了。

    P3_SITE       站点名（必填）
    P3_MODE       premises | bin_read | bin_set
    P3_ITEM       bin_read / bin_set 的目标物料
    P3_WAREHOUSE  bin_read / bin_set 的目标仓库
    P3_VALUE      bin_set 要写进 `actual_qty` 的值

⚠️ 靶子按 **(item_code, warehouse)** 指名，不按 `Bin.name`：后者是站点自己生成的 hash
（本机实测 `03911kfmtj`），换一次站点就变，写死它等于把探测绑在一次装载上。

**三条纪律，每条都对着一种会让这次探测失去意义的失败模式：**

1. **一律 rollback，且在 `finally` 里。** 探测要真提交单据才测得到提交路径，
   所以「收得干净」不能靠流程正确，只能靠 `finally`。
2. **打桩既计数也拦截。** `db.commit()` 的桩**不放行**那次 commit。
   放行的话，一旦前提 1 不成立，站点上就会留下一张真提交的单据 —— 用污染站点
   去换一个「更真实」的观测，代价与收益不成比例。计数为 0 时拦截是空操作，
   而计数非 0 时它同时是观测结果和保护措施。**代价照实记**：这使
   `savepoint_rollback_in_process` 那一段的结论**条件依赖于前提 1 为 0**，
   README 与 HYPOTHESES 里都写死了这句。
3. **不伪装成功。** 任何一步抛错都进 JSON 的 `error` 段并把整段标 `ok=False`，
   不吞、不改写、不降级成空结果（`agenerp/site.py` 模块头第 1 条，这里不开第二套口径）。
"""

from __future__ import annotations

import json
import os
import re

import traceback

SITE = os.environ.get("P3_SITE", "").strip()
MODE = os.environ.get("P3_MODE", "premises").strip()

if not SITE:
    print(json.dumps({"ok": False, "error": "P3_SITE 未设置"}), flush=True)
    raise SystemExit(2)

import frappe  # noqa: E402  —— 只有容器内有；见模块头

frappe.init(site=SITE)
frappe.connect()
frappe.set_user("Administrator")

# 探测用的那张单据：物料接收，1 只电芯进原料仓。
# 选它的三个理由：① 有 SLE 也有 GL（回滚要能连着两张账一起回）；② 走 naming series
# （Spike 05 的「不产生单号空洞」那一条只有它测得到）；③ 倒填日期时它是
# `Repost Item Valuation` 的触发者，`open-questions.md:92` 那条缺口正卡在这里。
PROBE_ITEM = "HRD-CELL-280"
PROBE_WAREHOUSE = "原料仓 - HRD"
PROBE_COMPANY = "恒锐动力科技有限公司"
PROBE_UOM = "只"
PROBE_RATE = 185.0
SERIES_PREFIX = "MAT-STE-2026-"

# 倒填到种子数据集第一张单据（`agenerp.seed.model.BASE_DATE` = 2026-02-02）之前。
BACKDATED_POSTING_DATE = "2026-01-05"

COUNTED_DOCTYPES = (
    "Stock Entry",
    "Stock Ledger Entry",
    "GL Entry",
    "Repost Item Valuation",
    "Email Queue",
    "File",
    "Version",
    "Comment",
    "Serial and Batch Bundle",
)

_TXN_SQL = re.compile(r"^\s*(commit|rollback|begin|start\s+transaction)\b", re.I)


def _series_current(prefix: str):
    row = frappe.db.sql("select current from tabSeries where name = %s", (prefix,), as_dict=True)
    return row[0]["current"] if row else None


def _counters() -> dict:
    out = {name: frappe.db.count(name) for name in COUNTED_DOCTYPES}
    out[f"series:{SERIES_PREFIX}"] = _series_current(SERIES_PREFIX)
    return out


def _stack(depth: int = 12) -> list[str]:
    """调用栈摘要。计数说明「发生了几次」，栈说明「谁干的」——只有后者能定位到 DocType。"""
    frames = traceback.extract_stack()[:-2]
    return [f"{f.filename}:{f.lineno} {f.name}" for f in frames[-depth:]]


class Probe:
    """一次提交的打桩记录。**装桩与拆桩成对，拆桩在 `finally` 里。**"""

    def __init__(self) -> None:
        self.commits: list[dict] = []
        self.txn_sql: list[dict] = []
        self.enqueues: list[dict] = []
        self.sendmails: list[dict] = []
        self.webhooks: list[dict] = []
        self.server_scripts: list[dict] = []
        self.alerts: list[dict] = []
        self.run_methods: list[dict] = []
        self._undo: list = []

    # ── 装桩 ───────────────────────────────────────────────────────────────
    def install(self) -> None:
        import frappe.model.document as document_module
        import frappe.utils.background_jobs as background_jobs
        from frappe.core.doctype.server_script import server_script_utils
        from frappe.email.doctype.notification import notification as notification_module
        from frappe.integrations.doctype import webhook as webhook_module

        db = frappe.db
        real_sql = db.sql

        def counting_commit(*args, **kwargs):
            # ⚠️ **不放行**。理由见模块头纪律 2。
            self.commits.append({"args": repr(args), "kwargs": repr(kwargs), "stack": _stack()})

        def watching_sql(query, *args, **kwargs):
            text = query if isinstance(query, str) else None
            if text is not None and _TXN_SQL.match(text):
                self.txn_sql.append({"query": text.strip()[:200], "stack": _stack()})
            return real_sql(query, *args, **kwargs)

        db.commit = counting_commit
        db.sql = watching_sql
        self._undo.append(lambda: (db.__dict__.pop("commit", None), db.__dict__.pop("sql", None)))

        # `enqueue` 有两条能被引用的名字（`frappe.enqueue` 与源模块里的那个），
        # 两条都堵；只堵一条时，模块级 `from … import enqueue` 的调用方会漏掉。
        def counting_enqueue(kind):
            def stub(*args, **kwargs):
                self.enqueues.append(
                    {"via": kind, "args": [repr(a) for a in args],
                     "kwargs": {k: repr(v) for k, v in kwargs.items()}, "stack": _stack()}
                )
                return None  # 不真入队：入队的任务会对着一个即将被回滚的事务跑
            return stub

        for holder, attr, kind in (
            (frappe, "enqueue", "frappe.enqueue"),
            (frappe, "enqueue_doc", "frappe.enqueue_doc"),
            (background_jobs, "enqueue", "background_jobs.enqueue"),
            (background_jobs, "enqueue_doc", "background_jobs.enqueue_doc"),
        ):
            self._patch(holder, attr, counting_enqueue(kind))

        def counting_sendmail(*args, **kwargs):
            self.sendmails.append({"kwargs": {k: repr(v) for k, v in kwargs.items()},
                                   "stack": _stack()})

        self._patch(frappe, "sendmail", counting_sendmail)

        real_webhooks = document_module.run_webhooks

        def watching_webhooks(doc, method):
            self.webhooks.append({"doctype": doc.doctype, "method": method})
            return real_webhooks(doc, method)

        self._patch(document_module, "run_webhooks", watching_webhooks)
        self._patch(webhook_module, "run_webhooks", watching_webhooks)

        real_server_script = document_module.run_server_script_for_doc_event

        def watching_server_script(doc, method):
            self.server_scripts.append({"doctype": doc.doctype, "method": method})
            return real_server_script(doc, method)

        self._patch(document_module, "run_server_script_for_doc_event", watching_server_script)
        self._patch(server_script_utils, "run_server_script_for_doc_event", watching_server_script)

        real_alert = notification_module.evaluate_alert

        def watching_alert(doc, alert, event):
            self.alerts.append({"doctype": doc.doctype, "alert": str(alert), "event": event})
            return real_alert(doc, alert, event)

        self._patch(notification_module, "evaluate_alert", watching_alert)

        # A3：**提交实际撞了哪几道钩子**。`run_method` 是 `before_submit` 的唯一入口
        # （`frappe/model/document.py:1002`，容器内实读），钩子链由它的 `Document.hook`
        # 装饰器合成 —— 记它就等于记下整条链的调用序。
        real_run_method = document_module.Document.run_method

        def watching_run_method(doc, method, *args, **kwargs):
            self.run_methods.append({"doctype": doc.doctype, "name": doc.name, "method": method})
            return real_run_method(doc, method, *args, **kwargs)

        self._patch(document_module.Document, "run_method", watching_run_method)

    def _patch(self, holder, attr: str, replacement) -> None:
        original = getattr(holder, attr)
        setattr(holder, attr, replacement)
        self._undo.append(lambda h=holder, a=attr, o=original: setattr(h, a, o))

    def remove(self) -> None:
        while self._undo:
            self._undo.pop()()

    # ── 读数 ───────────────────────────────────────────────────────────────
    def summary(self) -> dict:
        return {
            "premise_1_commit_calls": len(self.commits),
            "premise_1_commit_detail": self.commits,
            "premise_1_raw_txn_sql": self.txn_sql,
            "premise_2_enqueue_calls": len(self.enqueues),
            "premise_2_enqueue_detail": self.enqueues,
            "premise_3_sendmail_calls": len(self.sendmails),
            "premise_3_sendmail_detail": self.sendmails,
            "premise_3_webhook_dispatches": self.webhooks,
            "premise_3_server_script_dispatches": self.server_scripts,
            "premise_3_notification_alerts": self.alerts,
            "run_method_trace": self.run_methods,
        }


def _before_submit_chain(doctype: str) -> dict:
    """静态枚举某 DocType 的 `before_submit` 链 —— **不提交任何东西也能得到**。

    合成规则逐字照 `frappe/model/document.py:1367-1377` 的 `composer`：
    控制器自己的方法 + `doc_events[doctype][method]` + `doc_events['*'][method]`。
    """
    from frappe.model.base_document import get_controller

    doc_events = frappe.get_doc_hooks()
    controller = get_controller(doctype)
    own = getattr(controller, "before_submit", None)
    return {
        "controller": f"{controller.__module__}.{controller.__name__}",
        "controller_defines_before_submit": own is not None,
        "controller_before_submit_defined_in": (
            next((f"{k.__module__}.{k.__name__}" for k in controller.__mro__
                  if "before_submit" in k.__dict__), None)
        ),
        "doc_events_for_doctype": list(doc_events.get(doctype, {}).get("before_submit", [])),
        "doc_events_for_all": list(doc_events.get("*", {}).get("before_submit", [])),
    }


def _premise_0() -> dict:
    """前提 0：REST 面上 POST 在响应返回**之前**就 commit 了。

    两条腿，缺一条都不够：
    ① **源码复核** —— `frappe/app.py::sync_database` 在容器内的当期原文；
    ② **跨连接实证** —— 一个连接开的 savepoint，另一个连接够不着。
       我们的工具层是跨 HTTP 调用的，②才是「够不着」这件事的直接证据，
       ①只说明「而且它还提前 commit 了」。
    """
    import inspect

    import frappe.app as frappe_app
    from frappe.auth import SAFE_HTTP_METHODS, UNSAFE_HTTP_METHODS

    lines, first = inspect.getsourcelines(frappe_app.sync_database)
    source = "".join(lines)

    out = {
        "frappe_version": frappe.__version__,
        "source_file": inspect.getsourcefile(frappe_app.sync_database),
        "first_line": first,
        "source": source,
        "unsafe_http_methods": sorted(UNSAFE_HTTP_METHODS),
        "safe_http_methods": sorted(SAFE_HTTP_METHODS),
        "post_is_unsafe": "POST" in UNSAFE_HTTP_METHODS,
        "commits_on_unsafe_method": bool(
            "UNSAFE_HTTP_METHODS" in source and "frappe.db.commit()" in source
        ),
    }

    # ② 跨连接：另开一条连接去 ROLLBACK TO 一个本连接开的 savepoint。
    frappe.db.savepoint("p3_cross_connection_probe")
    other = frappe.database.get_db(
        socket=frappe.conf.db_socket, host=frappe.conf.db_host, port=frappe.conf.db_port,
        user=frappe.conf.db_name, password=frappe.conf.db_password,
        cur_db_name=frappe.conf.db_name,
    )
    try:
        other.connect()
        other.sql("ROLLBACK TO SAVEPOINT p3_cross_connection_probe")
        out["cross_connection_savepoint_visible"] = True
        out["cross_connection_error"] = None
    except Exception as exc:  # 预期落在这里：savepoint 是连接私有的
        out["cross_connection_savepoint_visible"] = False
        out["cross_connection_error"] = f"{exc.__class__.__name__}: {exc}"
    finally:
        try:
            other.close()
        except Exception:
            pass
    frappe.db.sql("RELEASE SAVEPOINT p3_cross_connection_probe")
    return out


def _submit_once(scenario: str, posting_date: str) -> dict:
    """在 savepoint 内真提交一张单据，测完回滚到 savepoint。

    返回的 `counters_before` / `counters_after_rollback` 逐项相等，就是
    「savepoint 语义在本仓这个版本上仍然成立」的**进程内**证据 ——
    注意它只是进程内的，跨 HTTP 调用那一格由 `_premise_0` 的第②条腿否掉。
    """
    savepoint = f"p3_probe_{scenario}"
    probe = Probe()
    result: dict = {"scenario": scenario, "posting_date": posting_date, "ok": False}

    result["counters_before"] = _counters()
    frappe.db.savepoint(savepoint)
    try:
        probe.install()
        try:
            doc = frappe.get_doc({
                "doctype": "Stock Entry",
                "stock_entry_type": "Material Receipt",
                "company": PROBE_COMPANY,
                "posting_date": posting_date,
                "set_posting_time": 1,
                "items": [{
                    "item_code": PROBE_ITEM, "qty": 1, "basic_rate": PROBE_RATE,
                    "t_warehouse": PROBE_WAREHOUSE, "uom": PROBE_UOM,
                    "stock_uom": PROBE_UOM, "conversion_factor": 1,
                }],
            })
            doc.insert()
            result["inserted_name"] = doc.name
            doc.submit()
            result["docstatus"] = int(doc.docstatus)
            result["sle_rows"] = frappe.db.count("Stock Ledger Entry", {"voucher_no": doc.name})
            result["gl_rows"] = frappe.db.count("GL Entry", {"voucher_no": doc.name})
            result["counters_after_submit"] = _counters()
            # 事务边界上挂了什么回调 —— 「回滚回不掉的东西」的另一条线索。
            result["callbacks_registered"] = {
                name: len(getattr(frappe.db, name)._functions)
                for name in ("before_commit", "after_commit", "after_rollback")
                if hasattr(getattr(frappe.db, name, None), "_functions")
            }
            result["ok"] = True
        finally:
            probe.remove()
    except Exception as exc:
        result["error"] = f"{exc.__class__.__name__}: {exc}"
        result["traceback"] = traceback.format_exc()[-4000:]
    finally:
        result.update(probe.summary())
        frappe.db.rollback(save_point=savepoint)
        result["counters_after_rollback"] = _counters()

    before, after = result["counters_before"], result["counters_after_rollback"]
    result["rollback_restored_every_counter"] = before == after
    result["counter_drift"] = {
        k: [before[k], after[k]] for k in before if before[k] != after.get(k)
    }
    return result


def _mode_premises() -> dict:
    out: dict = {"ok": True, "site": SITE}
    out["premise_0"] = _premise_0()
    out["premise_3_static_row_counts"] = {
        name: frappe.db.count(name)
        for name in ("Workflow", "Notification", "Webhook", "Server Script", "Client Script")
    }
    out["notifications"] = frappe.db.sql(
        "select name, document_type, event, enabled, channel from tabNotification", as_dict=True
    )
    out["before_submit_chain"] = {
        dt: _before_submit_chain(dt)
        for dt in ("Stock Entry", "Delivery Note", "Sales Invoice", "Purchase Invoice")
    }
    out["scenarios"] = [
        _submit_once("normal", frappe.utils.today()),
        _submit_once("backdated", BACKDATED_POSTING_DATE),
    ]
    out["ok"] = all(s.get("ok") for s in out["scenarios"])
    return out


def _bin_name() -> str:
    name = frappe.db.get_value(
        "Bin", {"item_code": os.environ["P3_ITEM"], "warehouse": os.environ["P3_WAREHOUSE"]}, "name"
    )
    if not name:
        raise RuntimeError(
            f"站点上没有 Bin({os.environ['P3_ITEM']}, {os.environ['P3_WAREHOUSE']})"
        )
    return name


def _mode_bin_read() -> dict:
    row = frappe.db.sql(
        "select name, item_code, warehouse, actual_qty, stock_value from tabBin where name = %s",
        (_bin_name(),), as_dict=True,
    )
    return {"ok": bool(row), "site": SITE, "bin": row[0] if row else None}


def _mode_bin_set() -> dict:
    """A1 变异先行**唯一**的写动作：把一个 Bin 的 `actual_qty` 改成给定值并 commit。

    选 `Bin.actual_qty` 而不是别的，是因为它同时满足三件事：站点指纹的第 1 项直接盯着它 ·
    它是一个标量，还原是字节级精确的 · 它是冗余表，本仓 scheduler 实测 inactive，
    不会有后台任务把它「顺手改回去」而让还原步骤看起来成功。
    """
    name = _bin_name()
    value = float(os.environ["P3_VALUE"])
    before = frappe.db.get_value("Bin", name, "actual_qty")
    frappe.db.set_value("Bin", name, "actual_qty", value, update_modified=False)
    frappe.db.sql("COMMIT")  # 指纹从另一条连接（REST）读，不 commit 它看不见
    after = frappe.db.get_value("Bin", name, "actual_qty")
    return {"ok": True, "site": SITE, "bin": name,
            "before": float(before), "requested": value, "after": float(after)}


MODES = {"premises": _mode_premises, "bin_read": _mode_bin_read, "bin_set": _mode_bin_set}

try:
    if MODE not in MODES:
        payload = {"ok": False, "error": f"未知 P3_MODE {MODE!r}，可选 {sorted(MODES)}"}
    else:
        payload = MODES[MODE]()
except Exception as exc:  # 不伪装成功：原文进 JSON，退出码非 0
    payload = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}",
               "traceback": traceback.format_exc()[-4000:]}
finally:
    # `bin_set` 已经自己 commit 过；其余模式一律不留任何未提交的东西。
    if MODE != "bin_set":
        try:
            frappe.db.rollback()
        except Exception:
            pass

print("<<<P3JSON>>>" + json.dumps(payload, ensure_ascii=False, default=str), flush=True)
raise SystemExit(0 if payload.get("ok") else 1)
