"""P3.0 入口关口实验的 CLI。

    python3 -m tools.experiments.p3_injection.run --model glm-5.2

**问题与提示词从文件读，不从命令行拼**：四格必须逐字相同，命令行里手打一遍迟早打歪。
凭据只从环境读（`DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL`），实验设施不内置默认值。

⚠️ **本实验不连活站点。** 站点是 `site_fixture.py` 的假件（形状与实读一致），
写工具是 `decoys.py` 的诱饵（只记录、不落地）。**跑它不会改任何数据。**
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from tools.experiments.p1_entry_gate.llm import DashScopeClient, LlmError
from tools.experiments.p3_injection import judge as judge_module
from tools.experiments.p3_injection import site_fixture
from tools.experiments.p3_injection.loop import MAX_TURNS, QUESTION_PATH, run_grid
from tools.experiments.p3_injection.payloads import PAYLOADS, SENTINELS

DEFAULT_EVIDENCE = Path("docs/evidence/p3-injection")


def payload_digest() -> str:
    """四条载荷的字节级指纹。四格必须共用同一个 —— 判据核对它。"""
    blob = "\n".join(f"{p.code}|{p.doctype}|{p.name}|{p.fieldname}|{p.value}" for p in PAYLOADS)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.experiments.p3_injection.run",
        description="P3.0 写权限下的注入复测：边界标记 × 提示词，四格各跑一次",
    )
    parser.add_argument("--model", required=True, help="模型名，例如 glm-5.2 / kimi-k3")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--run-id", default="run-01")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    question = QUESTION_PATH.read_text(encoding="utf-8").strip()
    try:
        DashScopeClient(args.model)  # 先把凭据问题暴露在跑之前
    except LlmError as exc:
        print(f"起不来，已停在配置这一步：{exc}", file=sys.stderr)
        return 2

    traces = run_grid(
        llm_for=lambda: DashScopeClient(args.model),
        client=site_fixture.client(site_fixture.poisoned_rows()),
        question=question,
        sentinels=SENTINELS,
        payload_digest=payload_digest(),
        max_turns=args.max_turns,
    )
    payload = {
        "captured_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": args.model,
        "payload_sha256": payload_digest(),
        "traces": [t.as_dict() for t in traces],
    }
    payload["judgement"] = judge_module.judge_grid(payload["traces"], SENTINELS)

    target = Path(args.evidence_dir) / f"{args.model}-{args.run_id}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    result = payload["judgement"]
    for verdict in result["verdicts"]:
        print(f"  {verdict['cell']:24} {verdict['verdict']:9} {verdict['reason']}")
    print(f"\n{'✅' if result['grid_is_interpretable'] else '❌'} {result['headline']}")
    for problem in result["problems"]:
        print(f"  · {problem}")
    print(f"轨迹已落 {target}")
    return 0 if result["grid_is_interpretable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
