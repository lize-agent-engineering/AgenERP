"""答案判定器 v0 的**活端点实验**：判那 24 条人工标注，落证据。

    python3 -m tools.experiments.p1_answer_judge.run --all
    python3 -m tools.experiments.p1_answer_judge.run --stability
    python3 -m tools.experiments.p1_answer_judge.run --controls

**它是实验设施，不是产品代码**（先例 `tools/experiments/p1_entry_gate/`）。
产品面只有 `agenerp/judging/` 三个模块；本文件负责"跑一趟、把每一条都记下来"。

三条摆放上的规矩：

1. **验收口径不在这里实现。** `meets_acceptance()` 只有一处实现，在
   `tests/unit/answer_judge_fixture.py`（plan D7b）；本文件**按路径把它加载进来**，
   不复制、不另写 —— 两份口径会各自漂移，而它正是 H2 的承重面。
2. **凭据一个字节不进证据文件、不进日志。** 端点与 key 从 `AGENERP_LLM_*` 读
   （`agenerp/routing/config.py`），本文件不打印它们，也不把 `config` 塞进证据。
3. **一次 `chat()` 一条账**（P1.7 的 `CallLedger`）。账本条数就是这一趟真花掉的调用次数，
   plan §5.2 的 72 次上限按它对账。**本文件没有任何阈值、没有拦截分支**（D-18）。

⚠️ **判定器的已验证适用范围只有 P1.0 那一道题**（`agenerp.judging.rubric.QUESTION`）。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agenerp.explain.ledger import CallLedger
from agenerp.judging import JudgingError, judge_one
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES
from agenerp.routing.config import from_env as config_from_env
from agenerp.routing.errors import RoutingError

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVIDENCE = REPO_ROOT / "docs/evidence/p1-answer-judge"

# plan `Decision D2`：起草期点名，**执行期不许换**；换了就是一次修订（§5.2）。
JUDGE_MODEL = "qwen3.7-plus-2026-05-26"

# plan §6 H3：5 条负例全收 + `run-01`。
STABILITY_RUN_IDS = ("run-02", "run-05", "run-07", "run-13", "r2-07", "run-01")
STABILITY_REPEATS = 3
CONTROL_REPEATS = 3

# plan §6 H5 / §6.1 O1 的构造对照，两条都基于 `run-01`。
CONTROL_SOURCE_RUN_ID = "run-01"
TRUNCATE_TO = 179  # = `run-07` 的长度
STRIP_MARKERS = ("外协", "1000 台", "1,000 台", "MAT-SCR-2026-00001")


def _load_acceptance():
    """按路径加载 `tests/unit/answer_judge_fixture.py`。**源文件没了就是红**，不是少判一项。"""
    target = REPO_ROOT / "tests/unit/answer_judge_fixture.py"
    if not target.is_file():
        raise FileNotFoundError(
            f"验收口径只有一处实现（{target}），它不在了 —— 本脚本不另写一份口径。"
        )
    spec = importlib.util.spec_from_file_location("_p1_answer_judge_fixture", target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def judge_text(text: str, *, ledger: CallLedger, index: int, transport=None) -> dict:
    """判一段文本，把这一次的全部可复核事实压成一条记录。失败也照实记，不静默跳过。"""
    try:
        verdict = judge_one(
            text,
            models=KNOWN_MODEL_PROFILES,
            requested=JUDGE_MODEL,
            transport=transport,
            ledger=ledger,
            index=index,
        )
    except (RoutingError, JudgingError) as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    return {
        "ok": True,
        "judged_label": verdict.label,
        "judge_model": verdict.model,
        "usage": verdict.usage.as_dict(),
        "endpoint_usage": verdict.endpoint_usage,
        "raw_text": verdict.raw_text,
    }


def run_all(fixture, *, transport=None) -> dict:
    """全量判 24 条 —— **一轮**（plan §5.2 的定义）。"""
    ledger = CallLedger()
    records = []
    for index, row in enumerate(fixture.rows()):
        outcome = judge_text(row["answer"], ledger=ledger, index=index, transport=transport)
        records.append(
            {
                "run_id": row["run_id"],
                "answer_model": row["model"],
                "human_label": row["label"],
                "answer_chars": len(row["answer"]),
                **outcome,
                "agrees": outcome.get("judged_label") == row["label"],
            }
        )

    pairs = [(r["human_label"], r.get("judged_label")) for r in records]
    negatives = [r for r in records if r["human_label"] != "correct"]
    positives = [r for r in records if r["human_label"] == "correct"]
    by_answer_model: dict[str, dict] = {}
    for record in records:
        bucket = by_answer_model.setdefault(
            record["answer_model"], {"total": 0, "agrees": 0, "run_ids": []}
        )
        bucket["total"] += 1
        bucket["agrees"] += int(bool(record["agrees"]))
        bucket["run_ids"].append(record["run_id"])

    return {
        "kind": "all",
        "at": _now(),
        "judge_model": JUDGE_MODEL,
        "fixture_sha256": fixture.fixture_sha256(),
        "records": records,
        "summary": {
            "rows": len(records),
            "failed_calls": sum(1 for r in records if not r["ok"]),
            "negatives_exact": sum(
                1 for r in negatives if r.get("judged_label") == r["human_label"]
            ),
            "negatives_total": len(negatives),
            "positives_kept": sum(1 for r in positives if r.get("judged_label") == "correct"),
            "positives_total": len(positives),
            "overall_agreement": sum(1 for r in records if r["agrees"]),
            "meets_acceptance": fixture.meets_acceptance(pairs),
            "by_answer_model": by_answer_model,
        },
        "ledger": ledger.as_dict(),
    }


def run_stability(fixture, *, transport=None) -> dict:
    """H3：6 条 × 3 次。**不一致就照实记不一致，不许取多数再报成一致。**"""
    ledger = CallLedger()
    index = 0
    records = []
    for run_id in STABILITY_RUN_IDS:
        row = fixture.row_by_id(run_id)
        attempts = []
        for _ in range(STABILITY_REPEATS):
            attempts.append(judge_text(row["answer"], ledger=ledger, index=index, transport=transport))
            index += 1
        labels = [a.get("judged_label") for a in attempts]
        records.append(
            {
                "run_id": run_id,
                "human_label": row["label"],
                "labels": labels,
                "consistent": len(set(labels)) == 1,
                "attempts": attempts,
            }
        )
    return {
        "kind": "stability",
        "at": _now(),
        "judge_model": JUDGE_MODEL,
        "repeats": STABILITY_REPEATS,
        "records": records,
        "summary": {
            "rows": len(records),
            "consistent_rows": sum(1 for r in records if r["consistent"]),
        },
        "ledger": ledger.as_dict(),
    }


def truncated_control(answer: str) -> str:
    """H5：**机械变换**，截到 `run-07` 的长度。不含任何内容判断。"""
    return answer[:TRUNCATE_TO]


def stripped_control(answer: str) -> str:
    """O1：删掉提到那几个记号的**整行**（按 `\n` 切，不做句子切分）。

    ⚠️ **删哪些句子由本脚本自列的关键词表决定** —— roadmap 逐字「标签只能由人读原文定，
    不能由任何判定器产生」，所以 O1 的结果**只记不判**，不得被引用为判别力或泛化的证据。
    """
    sentences = [s for s in answer.replace("\r", "").split("\n") if s.strip()]
    kept = [s for s in sentences if not any(marker in s for marker in STRIP_MARKERS)]
    return "\n".join(kept)


def run_controls(fixture, *, transport=None) -> dict:
    ledger = CallLedger()
    source = fixture.row_by_id(CONTROL_SOURCE_RUN_ID)
    index = 0
    blocks = []
    for name, text, note in (
        (
            "H5-truncated",
            truncated_control(source["answer"]),
            "判据。机械截断，无内容判断。⚠️ 证据强度低：一个长度阈值规则同样能通过它。",
        ),
        (
            "O1-stripped",
            stripped_control(source["answer"]),
            "**观测，不作证据**（plan §6.1）：删哪些句子由脚本自列的关键词表决定。",
        ),
    ):
        attempts = []
        for _ in range(CONTROL_REPEATS):
            attempts.append(judge_text(text, ledger=ledger, index=index, transport=transport))
            index += 1
        blocks.append(
            {
                "control": name,
                "note": note,
                "source_run_id": CONTROL_SOURCE_RUN_ID,
                "source_human_label": source["label"],
                "transformed_input": text,
                "transformed_chars": len(text),
                "labels": [a.get("judged_label") for a in attempts],
                "attempts": attempts,
            }
        )
    return {
        "kind": "controls",
        "at": _now(),
        "judge_model": JUDGE_MODEL,
        "repeats": CONTROL_REPEATS,
        "blocks": blocks,
        "ledger": ledger.as_dict(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.experiments.p1_answer_judge.run",
        description="答案判定器 v0：判那 24 条人工标注（活端点）",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="全量判 24 条（一轮）")
    group.add_argument("--stability", action="store_true", help="H3：6 条 × 3 次")
    group.add_argument("--controls", action="store_true", help="H5 判据 + O1 观测，各 3 次")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--out", default="", help="证据文件名（默认按子命令取）")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config_from_env()  # 端点配置不全就**当场停在这一步**，不要跑出一整份全是错误的证据
    except RoutingError as exc:
        print(f"起不来，已停在配置这一步：{exc}", file=sys.stderr)
        return 2
    fixture = _load_acceptance()
    if args.all:
        result, default_name = run_all(fixture), "all.json"
    elif args.stability:
        result, default_name = run_stability(fixture), "stability.json"
    else:
        result, default_name = run_controls(fixture), "controls.json"

    out_dir = Path(args.evidence_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (args.out or default_name)
    out_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result.get("summary", {"calls": result["ledger"]["calls"]}),
                     ensure_ascii=False, indent=2))
    print(f"调用次数（账本条数）：{result['ledger']['calls']}")
    print(f"证据落盘：{out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
