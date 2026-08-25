"""行业包的**离线↔活站点命中集合逐字比对** —— 跑两侧、比一次、落一次账。

    python3 tools/experiments/p1_pack_parity/run.py --offline-only
    python3 tools/experiments/p1_pack_parity/run.py

plan 是 `docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md`。
落点节 `docs/architecture/module-boundaries.md` §7.19。
**它是实验设施，不是产品代码**（形态照抄 `tools/experiments/p1_insight_live/run.py`）。
`agenerp/**` 与 `industry-packs/**` 一行不改 —— 本文件只调用它们。

⚠️ **本文件担不起「零模型接缝」那个主张，判定逻辑也不在这里。** 两句都照实说：

1. **判定逻辑在 `parity.py`**（同目录的纯比对器，零仓内 import）。本文件只做编排：
   装包 / 建两侧行源 / 调比对器 / 落盘。**不在这里另写一份比对。**
2. 离线那一侧由本文件**按路径加载** `tests/unit/inspection_fakes.py`（不复制夹具、不下沉它），
   而那条链 `:39` → `explain_fakes` → `agenerp.routing` **会把 routing 拉进 `sys.modules`**
   （起草期实测）。所以 plan §6 H7 ① 那条「import 后 routing 不在 `sys.modules`」的判据
   **主语只能是 `parity.py`**。**不靠删依赖去凑它，也不假装本文件干净。**

三条摆放上的规矩：

- **只读按端点语义判，不按方法名听起来只读判。** 站点请求经 `ReadOnlyTransport`
  逐条留痕，放行的只有任意 `GET` 与 `POST /api/method/login`（换会话那一条既有路径）。
  白名单外的请求**指名报错并让本脚本非零退出**（plan §5.1 第 3 条是停机线，不是提醒）。
- **空集不是成功。** `--offline-only` 与整跑都按这条退码。
- **一致与否由 `parity.compare()` 说了算，本文件不修饰它的结论**：
  仍不一致就落盘「仍不一致」，不写成「基本一致」。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agenerp.inspection import inspect_site  # noqa: E402
from agenerp.packs import PackLoadError, load_pack  # noqa: E402
from agenerp.site import SiteError, SiteRequest, SiteResponse, UrllibTransport, client_from_env  # noqa: E402

DEFAULT_EVIDENCE = REPO_ROOT / "docs/evidence/p1-pack-parity"
FIXTURE = "tests/unit/inspection_fakes.py"
PARITY = Path(__file__).resolve().parent / "parity.py"

PACK_ID = "discrete"

OFFLINE_FILE = "offline-hits.json"
LIVE_FILE = "live-hits.json"
PARITY_FILE = "parity.json"

# 任意 `GET` 放行；`POST` 只放行换会话那一条。其余动词与方法路径一律拦。
ALLOWED_METHOD_PATHS = ("/api/method/login",)


class RequestNotAllowed(RuntimeError):
    """白名单外的站点请求 —— **指名报错**，不静默放过、不降级成一行日志。"""


class ParityRunFailed(RuntimeError):
    """本次比对不成立。**空集不是成功**，形状对不上不是成功。"""


def _load_by_path(relative_path: str, module_name: str):
    """按路径加载仓库里的一个模块。**源文件没了就是红**，不是少跑几步。

    先注册再 `exec_module`：模块级 `@dataclass` 会反查 `sys.modules[cls.__module__]`
    （`tests/unit/explain_fakes.py` 头部记的那处实测）。
    """
    target = REPO_ROOT / relative_path
    if not target.is_file():
        raise ParityRunFailed(
            f"离线那一侧的行源是 {relative_path}，但它不在了 —— 比对失去一侧。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_parity():
    """装比对器。**本文件不另写一份比对逻辑**（判据 ⑩ 的同一条纪律）。"""
    if not PARITY.is_file():
        raise ParityRunFailed(f"比对器 {PARITY} 不在了 —— 本脚本没有第二份比对逻辑。")
    spec = importlib.util.spec_from_file_location("_p1_pack_parity_parity", PARITY)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class ReadOnlyTransport:
    """站点传输层的记录器：**逐条记 method + path，按端点语义白名单判**。

    判的是路径而不是动词的**名字**：`SiteClient.call_method` / `post_method` 内部走
    `POST`，光看方法名会以为它们只读。白名单外的请求**当场抛**，
    且在 `denied` 上留一条，让「抛被谁吞了」这件事也可判。
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
                f"白名单外的站点请求：{request.method} {path} —— 本次比对是只读的，"
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


def offline_client():
    """离线那一侧：`tests/unit/inspection_fakes.py` 的 `seed_site()`，**一次网络都不打**。

    ⚠️ 它由 `agenerp.seed.generate()` 派生，**不是从站点读回来的** ——
    否则比对就成了拿站点跟站点比，永远绿（plan §8 R1）。
    """
    fakes = _load_by_path(FIXTURE, "_p1_pack_parity_fixture")
    return fakes.client_for(fakes.seed_site())


def live_client(site: str):
    """活站点那一侧：真 REST，只读传输记录器包在外面。"""
    recorder = ReadOnlyTransport(UrllibTransport())
    return client_from_env(site, transport=recorder), recorder


def inspect_once(client, *, pack_id: str = PACK_ID) -> tuple[Any, dict]:
    """装包 → 巡检 → 整份 `InspectionReport.as_dict()`。**零 LLM、零写操作。**

    ⚠️ 落盘的是**整份报告**（`rule_ids` / `request_count` / `hits` 三个键都在），
    不是只有 `hits` —— 只存 `hits` 会让 H3 与 H5 在复算时取不到数。
    """
    pack = load_pack(pack_id)
    report = inspect_site(pack.rules, client, pack.pack_id)
    return pack, report.as_dict()


def live_wiring(args) -> dict:
    """活跑接线：离线侧假站点 + 活站点侧真 REST。**判据侧不走这条路。**"""
    client, recorder = (None, None) if args.offline_only else live_client(args.site)
    return {"offline_client": offline_client(), "live_client": client, "recorder": recorder}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 tools/experiments/p1_pack_parity/run.py",
        description="行业包的离线↔活站点命中集合逐字比对（只读；零 LLM）",
    )
    parser.add_argument("--site", default=os.environ.get("AGENERP_SITE", "").strip() or "frontend")
    parser.add_argument("--pack", default=PACK_ID)
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="只跑离线那一侧（无站点、无凭据）—— 入口点自己的冒烟支",
    )
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE))
    return parser


def _write(out_dir: Path, name: str, payload: dict) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / name
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: list[str] | None = None, *, wiring: Callable[[Any], dict] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pieces = (wiring or live_wiring)(args)
    except (SiteError, ParityRunFailed) as exc:
        print(f"起不来，已停在接线这一步：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    try:
        _, offline = inspect_once(pieces["offline_client"], pack_id=args.pack)
    except (PackLoadError, SiteError, RequestNotAllowed) as exc:
        print(f"离线那一侧没跑成：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    if args.offline_only:
        print(json.dumps({"offline": offline}, ensure_ascii=False, indent=2))
        print(f"离线命中 {len(offline['hits'])} 条；行源请求 {offline['request_count']} 次")
        # **空集不是成功**：入口点的冒烟支也照这条口径退码。
        return 0 if offline["hits"] else 1

    try:
        _, live = inspect_once(pieces["live_client"], pack_id=args.pack)
    except (PackLoadError, SiteError, RequestNotAllowed) as exc:
        print(f"活站点那一侧没跑成：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    parity = load_parity()
    result = parity.compare(offline, live)

    out_dir = Path(args.evidence_dir)
    # **先落盘再退码**：结论不一致时证据比退出码重要（plan §6 H2 的三种处置都要它）。
    _write(out_dir, OFFLINE_FILE, offline)
    _write(out_dir, LIVE_FILE, live)
    parity_path = _write(out_dir, PARITY_FILE, result)

    recorder = pieces.get("recorder")
    summary = recorder.summary() if recorder is not None else None
    print(json.dumps({"verdict": result["verdict"], "rule_ids_equal": result["rule_ids"]["equal"],
                      "hits": {k: result["hits"][k] for k in ("equal", "matched", "count")},
                      "request_count": {k: result["request_count"][k] for k in ("offline", "live", "judged")},
                      "requests": summary}, ensure_ascii=False, indent=2))
    print(f"证据落盘：{parity_path.parent}")
    if summary is not None and summary["denied"]:
        print(f"出现了白名单外的站点请求：{summary['denied']}", file=sys.stderr)
        return 1
    if result["verdict"] != parity.IDENTICAL:
        print(f"两侧**不是**逐字一致：verdict={result['verdict']} —— 照实记，不修饰",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
