"""洞察 Agent **归因**的活端点实跑 —— 判结构化事实，不判文本质量。

    python3 -m tools.experiments.p1_insight_live.run --inspect-only
    python3 -m tools.experiments.p1_insight_live.run

plan 是 `docs/plans/p1-insight/2026-08-25-0225-2-insight-attribution-live-run.md`。
**它是实验设施，不是产品代码**（先例 `tools/experiments/p1_answer_judge/run.py`）。
`agenerp/insight/**` 与 `agenerp/inspection/**` 一行不改 —— 本文件只调用它们。

四条摆放上的规矩：

1. **只读按端点语义定义，不按 HTTP 动词定义。** `explain()` 开场无条件注入
   `permission.scope`，它逐个 DocType `POST /api/method/frappe.client.has_permission`
   （`agenerp/tools/site_scope.py` → `agenerp/site.py` 的 `call_method`），
   所以"全程零 POST"是错的。白名单写死在 `ALLOWED_METHOD_PATHS`，
   白名单外的请求**指名报错并让本脚本非零退出**。
2. **判定器（`agenerp/judging/`）的标签取值不进退出码路径。** 判定结果由 `judge`
   形参注入（可替身），落进证据只作观测；`decide()` 读的五项事实里没有它。
   已验证适用范围只有 P1.0 那一道题，喂归因文本属外推（D-16）。
3. **一次 `chat()` 一条账**（P1.7 的 `CallLedger`）。账本条数与**独立计数探针**对账 ——
   从账本自己数账本是同义反复。**本文件没有任何成本阈值、没有拦截分支**（D-18）。
4. **凭据一个字节不进证据文件。** 落盘前扫一遍，扫到就非零退出且**不写文件**。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agenerp.explain.gate import documents_named_in
from agenerp.explain.ledger import CallLedger
from agenerp.insight import attribute_all, hits_unchanged
from agenerp.inspection import inspect_site
from agenerp.judging import JudgingError, judge_one
from agenerp.packs import PackLoadError, load_pack
from agenerp.routing.adapter import ChatAdapter
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES
from agenerp.routing.config import from_env as config_from_env
from agenerp.routing.errors import RoutingError
from agenerp.site import SiteError, SiteRequest, SiteResponse, UrllibTransport, client_from_env

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE = REPO_ROOT / "docs/evidence/p1-insight-live"

PACK_ID = "discrete"

# 起草期点名：与本项目仅有的两个归因成本观测（P1.4 的 7 次、P1.7 的 8 次）同一个模型，
# 否则 H4 那两个数就不可比。**执行期不换。**
ATTRIBUTION_MODEL = "qwen3.6-plus"

# §6.1 O1 那一次判定用的模型 —— 与 `…-0225-1` 的 `JUDGE_MODEL` 同一个常量值。
JUDGE_MODEL = "qwen3.7-plus-2026-05-26"

O1_NOTE = (
    "据判定器，判为 {label}，待复验；本 plan 不据此对归因质量下任何结论"
    "（判定器的已验证适用范围只有 P1.0 那一道题，喂归因文本属外推，D-16）。"
)

# ── 只读白名单（plan §3 Non-Goals 5，起草期写死）────────────────────────────
# 任意 `GET` 放行；`POST` 只放行下面三条方法路径。其余动词与方法名一律拦。
ALLOWED_METHOD_PATHS = (
    "/api/method/login",
    "/api/method/frappe.client.has_permission",
    "/api/method/frappe.client.get_count",
)

# 会被扫的凭据环境变量。**短值不扫**：`AGENERP_ADMIN_PASSWORD=admin` 这种
# 五字符口令在任何一份含 `Administrator` 的证据里都会误报，扫了等于扫不动。
# 跳过了哪几个**照实记进证据**，不假装扫全了。
CREDENTIAL_ENV = (
    "AGENERP_LLM_API_KEY",
    "DASHSCOPE_API_KEY",
    "AGENERP_API_SECRET",
    "AGENERP_API_KEY",
    "AGENERP_ADMIN_PASSWORD",
    "AGENERP_WORKER_PASSWORD",
    "AGENERP_SID",
)
MIN_SCANNED_SECRET_LEN = 8


class RequestNotAllowed(RuntimeError):
    """白名单外的站点请求 —— **指名报错**，不静默放过、不降级成一行日志。"""


class LiveRunFailed(RuntimeError):
    """本次实跑不成立。**空集不是成功**，账对不上不是成功，凭据落盘不是成功。"""


@dataclass
class RecordingTransport:
    """站点传输层的记录器：**逐条记 method + path，按端点语义白名单判**。

    判的是路径而不是动词 —— 一个完全只读的会话也会发出大量 `POST`
    （`frappe.client.has_permission` / `frappe.client.get_count`）。
    白名单外的请求**当场抛**，且在 `denied` 上留一条，让"抛被谁吞了"这件事也可判。
    """

    inner: Any
    records: list[dict] = field(default_factory=list)

    def __call__(self, request: SiteRequest) -> SiteResponse:
        path = urllib.parse.unquote(urllib.parse.urlsplit(request.url).path)
        allowed = request.method == "GET" or (
            request.method == "POST" and path in ALLOWED_METHOD_PATHS
        )
        self.records.append({"method": request.method, "path": path, "allowed": allowed})
        if not allowed:
            raise RequestNotAllowed(
                f"白名单外的站点请求：{request.method} {path} —— 本次实跑是只读的，"
                f"放行的只有任意 GET 与 POST {list(ALLOWED_METHOD_PATHS)}"
            )
        return self.inner(request)

    @property
    def denied(self) -> list[dict]:
        return [item for item in self.records if not item["allowed"]]

    def summary(self) -> dict:
        by_endpoint: dict[str, int] = {}
        for item in self.records:
            key = f"{item['method']} {item['path']}"
            by_endpoint[key] = by_endpoint.get(key, 0) + 1
        return {
            "total": len(self.records),
            "get": sum(1 for r in self.records if r["method"] == "GET"),
            "post": sum(1 for r in self.records if r["method"] == "POST"),
            "other_verbs": sorted(
                {r["method"] for r in self.records if r["method"] not in ("GET", "POST")}
            ),
            "denied": self.denied,
            "allowlist": list(ALLOWED_METHOD_PATHS),
            "by_endpoint": dict(sorted(by_endpoint.items(), key=lambda kv: (-kv[1], kv[0]))),
        }


class CountingModel:
    """`chat()` 计数探针（先例 `tests/unit/test_explain_cost_ledger.py` 的构造面替身）。

    它数的是**可观测量**：`ChatAdapter.chat()` 实际把载荷送出去了几次。
    与账本条数对账时两边必须来自不同的采集面，否则是同义反复。

    `inner` 为空时打真端点：**借 `ChatAdapter` 自己的 `_post`，不另写一份 HTTP** ——
    另写一份就会与 P1.1 的超时、SSL 根证书、鉴权头三件事分家。
    """

    def __init__(self, inner: Callable[[dict], dict] | None = None, *, config=None) -> None:
        if inner is None and config is None:
            raise ValueError("计数探针要么给 inner 替身，要么给端点配置")
        self._inner = inner
        self._poster = None if inner is not None else ChatAdapter(config)
        self.calls = 0

    def __call__(self, payload: dict) -> dict:
        self.calls += 1
        if self._inner is not None:
            return self._inner(payload)
        return self._poster._post(payload)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def credential_hits(text: str, env: dict[str, str] | None = None) -> dict:
    """证据文本里有没有凭据字面量。**跳过的短值照实记**，不假装扫全了。"""
    values = os.environ if env is None else env
    found: list[str] = []
    skipped: list[str] = []
    for name in CREDENTIAL_ENV:
        value = (values.get(name) or "").strip()
        if not value:
            continue
        if len(value) < MIN_SCANNED_SECRET_LEN:
            skipped.append(name)
            continue
        if value in text:
            found.append(name)
    return {
        "found": sorted(found),
        "skipped_too_short": sorted(skipped),
        "min_scanned_len": MIN_SCANNED_SECRET_LEN,
        "scanned": list(CREDENTIAL_ENV),
    }


def live_judge(answer: str) -> dict:
    """§6.1 **O1**：把归因答案喂判定器一次。**观测，不是判据。**

    这次调用**不走归因那条计数探针**，因此不进 H4 的「≤ 12」口径 ——
    那个口径逐字是「本次归因的 `cost_ledger` 条数」。
    """
    ledger = CallLedger()
    try:
        verdict = judge_one(
            answer,
            models=KNOWN_MODEL_PROFILES,
            requested=JUDGE_MODEL,
            ledger=ledger,
            index=0,
        )
    except (RoutingError, JudgingError) as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "label": "",
            "note": "判定器这次没给出标签 —— 照实记；本 plan 的通过与否不依赖它（§2 Goal 3）。",
            "ledger": ledger.as_dict(),
        }
    return {
        "ok": True,
        "error": "",
        "label": verdict.label,
        "note": O1_NOTE.format(label=verdict.label),
        "verdict": verdict.as_dict(),
        "ledger": ledger.as_dict(),
    }


ATTRIBUTION_KEYS = (
    "rule_id",
    "pack_id",
    "hit",
    "question",
    "answer",
    "accepted",
    "gate_l1",
    "tool_calls",
    "cost_ledger",
    "usage_total",
    "trace",
    "judge",
)


def attribution_record(attribution, *, judge: Callable[[str], dict]) -> dict:
    """一条归因的全部可复核事实。**答案全文进证据，凭据一个字节不进。**"""
    trace = attribution.trace
    gate_checks = trace.get("gate_checks") or []
    return {
        "rule_id": attribution.hit.rule_id,
        "pack_id": attribution.hit.pack_id,
        "hit": attribution.hit.as_dict(),
        "question": attribution.question,
        "answer": attribution.answer,
        "accepted": attribution.accepted,
        # H3 判在门禁自己的记录上：`documents_named_in()` 对本次题面返回了什么，
        # 以及 L1 在哪几轮因此发红。**不判在工具调用上**（循环无论如何都会调工具）。
        "gate_l1": {
            "documents_named_in_question": documents_named_in(attribution.question),
            "failed_turns": [
                {
                    "turn": check.get("turn"),
                    "failed": [item.get("fact") for item in check.get("failed") or []],
                    "texts": [item.get("text") for item in check.get("failed") or []],
                }
                for check in gate_checks
                if check.get("failed")
            ],
            "gate_check_count": len(gate_checks),
        },
        "tool_calls": trace.get("tool_calls") or [],
        "cost_ledger": attribution.result.cost_ledger.as_dict(),
        "usage_total": attribution.result.usage.as_dict(),
        "trace": trace,
        "judge": judge(attribution.answer),
    }


EVIDENCE_KEYS = (
    "run",
    "at",
    "pack",
    "site",
    "model",
    "inspection",
    "attributions",
    "checks",
    "requests",
    "credential_scan",
    "elapsed_seconds",
    "notes",
)

CHECK_KEYS = (
    "hits_not_empty",
    "hits_unchanged",
    "ledger_matches_chat_calls",
    "evidence_trace_enumerable",
    "no_denied_requests",
    "no_credentials_in_evidence",
)

NOTES = {
    "readonly": (
        "只读按**端点语义**定义，不按 HTTP 动词：一个完全只读的会话也会 POST "
        "`frappe.client.has_permission` / `frappe.client.get_count`。白名单见 `requests.allowlist`。"
    ),
    "judge": (
        "`attributions[].judge` 是**观测**（plan §6.1 O1）：它测的是判定器在跨题族输入上不崩，"
        "**不是归因质量合格**。标签取值不构成本次实跑的任何通过条件。"
    ),
    "one_run": (
        "一跑不是分布：本文件证明的是这条链在真环境里走得通，**不是**归因稳定或正确。"
    ),
    "cost": "本文件没有任何成本阈值、没有拦截分支（D-18：记账不拦截）。",
}


def decide(payload: dict) -> tuple[dict, list[str]]:
    """结构化事实 → 退出码。**判定器的标签取值不在这几项里**（plan §2 Goal 3 / M6 的靶子）。

    六项逐条：命中非空（**空集不是成功**）· 命中逐字未被改写 · 账本条数 == `chat()` 计数 ·
    取证轨迹非空且工具调用可枚举 · 零白名单外请求 · 证据里没有凭据字面量。
    """
    records = payload["attributions"]
    ledger_calls = sum(item["cost_ledger"]["calls"] for item in records)
    checks = {
        "hits_not_empty": bool(payload["inspection"]["hits"]),
        "hits_unchanged": bool(payload["inspection"]["hits_unchanged"]),
        "ledger_matches_chat_calls": ledger_calls == payload["model"]["chat_calls"],
        "evidence_trace_enumerable": bool(records)
        and all(
            isinstance(item["tool_calls"], list)
            and item["tool_calls"]
            and all(isinstance(call, dict) and call.get("tool") for call in item["tool_calls"])
            for item in records
        ),
        "no_denied_requests": not payload["requests"]["denied"],
        "no_credentials_in_evidence": not payload["credential_scan"]["found"],
    }
    if sorted(checks) != sorted(CHECK_KEYS):
        raise LiveRunFailed(f"判据项集合与 CHECK_KEYS 不一致：{sorted(checks)}")
    failures = [name for name in CHECK_KEYS if not checks[name]]
    return checks, failures


def inspect_once(client, *, pack_id: str = PACK_ID) -> tuple[Any, Any, dict]:
    """装包 → 巡检。**零 LLM**，`--inspect-only` 走的就是这一段。"""
    pack = load_pack(pack_id)
    started = time.monotonic()
    report = inspect_site(pack.rules, client, pack.pack_id)
    elapsed = time.monotonic() - started
    return pack, report, {
        "pack_id": pack.pack_id,
        "version": pack.version,
        "rule_ids": list(pack.rule_ids()),
        "requires_doctypes": list(pack.requires_doctypes),
        "elapsed_seconds": round(elapsed, 3),
    }


def run_attribution(
    *,
    client,
    recorder: RecordingTransport,
    probe: CountingModel,
    judge: Callable[[str], dict],
    models=KNOWN_MODEL_PROFILES,
    requested: str | None = ATTRIBUTION_MODEL,
    config=None,
    pack_id: str = PACK_ID,
    env: dict[str, str] | None = None,
) -> dict:
    """跑一次：巡检 → 逐条归因 → 把全部可复核事实压成一份证据。

    **不判、不拦、不重试** —— 判在 `decide()`，那里没有任何判定器标签。
    `doctypes` 走默认的**发现路径**（`attribute()` 的默认 `None`）：本 plan 是一次
    验证，不替 `agenerp/insight/**` 改任何默认值。
    """
    started = time.monotonic()
    pack, report, pack_meta = inspect_once(client, pack_id=pack_id)

    attributions = attribute_all(
        report,
        client=client,
        models=models,
        requested=requested,
        config=config,
        transport=probe,
    )
    unchanged = hits_unchanged(report, attributions)
    records = [attribution_record(item, judge=judge) for item in attributions]
    elapsed = time.monotonic() - started

    inspection = report.as_dict()
    inspection["hits_unchanged"] = unchanged

    payload: dict[str, Any] = {
        "run": "p1-insight-live-01",
        "at": _now(),
        "pack": pack_meta,
        "site": {"site": client.site, "base_url": client.base_url},
        "model": {
            "attribution_model_requested": requested,
            "judge_model_requested": JUDGE_MODEL,
            "chat_calls": probe.calls,
            "ledger_calls": sum(item["cost_ledger"]["calls"] for item in records),
        },
        "inspection": inspection,
        "attributions": records,
        "requests": recorder.summary(),
        "elapsed_seconds": round(elapsed, 3),
        "notes": dict(NOTES),
    }
    # 凭据扫描要扫**将要落盘的那份文本**，所以先占位再回填。
    payload["credential_scan"] = credential_hits(
        json.dumps(payload, ensure_ascii=False), env
    )
    payload["checks"] = {}
    return payload


def live_wiring(args) -> dict:
    """活跑接线：真站点 + 真端点 + 真判定器。**判据侧不走这条路**（零网络零站点）。"""
    config = config_from_env()
    recorder = RecordingTransport(UrllibTransport())
    client = client_from_env(args.site, transport=recorder)
    return {
        "client": client,
        "recorder": recorder,
        "probe": CountingModel(config=config),
        "judge": live_judge,
        "config": config,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.experiments.p1_insight_live.run",
        description="洞察 Agent 归因的活端点实跑（只读；判结构化事实，不判文本质量）",
    )
    parser.add_argument("--site", default=os.environ.get("AGENERP_SITE", "").strip() or "frontend")
    parser.add_argument("--pack", default=PACK_ID)
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="只跑巡检（零 LLM、零 token），把命中打出来 —— plan §6 H1 那一格用它",
    )
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--out", default="live-run-01.json")
    return parser


def _write(payload: dict, args) -> Path:
    """落盘。**键集合先对一遍** —— 证据的形状是判据的地基，悄悄多一键少一键就没人发现。"""
    if sorted(payload) != sorted(EVIDENCE_KEYS):
        raise LiveRunFailed(f"证据顶层键集合与 EVIDENCE_KEYS 不一致：{sorted(payload)}")
    for record in payload["attributions"]:
        if sorted(record) != sorted(ATTRIBUTION_KEYS):
            raise LiveRunFailed(f"归因记录键集合与 ATTRIBUTION_KEYS 不一致：{sorted(record)}")
    out_dir = Path(args.evidence_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.out
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def main(argv: list[str] | None = None, *, wiring: Callable[[Any], dict] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pieces = (wiring or live_wiring)(args)
    except (RoutingError, SiteError) as exc:
        print(f"起不来，已停在接线这一步：{exc}", file=sys.stderr)
        return 2

    if args.inspect_only:
        try:
            _, report, meta = inspect_once(pieces["client"], pack_id=args.pack)
        except (PackLoadError, SiteError, RequestNotAllowed) as exc:
            print(f"巡检没跑成：{type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({"pack": meta, "inspection": report.as_dict()},
                         ensure_ascii=False, indent=2))
        print(f"命中 {len(report.hits)} 条；站点请求 {len(pieces['recorder'].records)} 条")
        # **空集不是成功**：`--inspect-only` 也照这条口径退码。
        return 0 if report.hits else 1

    try:
        payload = run_attribution(
            client=pieces["client"],
            recorder=pieces["recorder"],
            probe=pieces["probe"],
            judge=pieces["judge"],
            models=pieces.get("models", KNOWN_MODEL_PROFILES),
            requested=pieces.get("requested", ATTRIBUTION_MODEL),
            config=pieces.get("config"),
            pack_id=args.pack,
            env=pieces.get("env"),
        )
    except (PackLoadError, SiteError, RoutingError, RequestNotAllowed) as exc:
        print(f"实跑没跑成：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    checks, failures = decide(payload)
    payload["checks"] = checks

    if payload["credential_scan"]["found"]:
        # **不落盘**：一份带凭据的证据文件写出去就收不回来了。
        print(
            "证据里出现了凭据字面量，已拒绝落盘："
            f"{payload['credential_scan']['found']}",
            file=sys.stderr,
        )
        return 1

    out_path = _write(payload, args)
    print(json.dumps({"checks": checks, "model": payload["model"],
                      "requests": {k: v for k, v in payload["requests"].items()
                                   if k != "by_endpoint"}},
                     ensure_ascii=False, indent=2))
    print(f"证据落盘：{out_path}")
    if failures:
        print(f"本次实跑不成立，未通过的判据：{failures}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
