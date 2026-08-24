"""入口关口实验的 CLI。

    python3 -m tools.experiments.p1_entry_gate.run \\
        --question-file tools/experiments/p1_entry_gate/question.md \\
        --model qwen-plus --gate on --max-tokens 60000 --seed-run-id run-01

**问题从文件读，不从命令行拼**：四格必须逐字相同，命令行里手打一遍迟早打歪。
凭据全部从环境读（站点四个 `AGENERP_*` + `DASHSCOPE_API_KEY` / `DASHSCOPE_BASE_URL`），
**实验设施同样不内置任何 key 或口令默认值**。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agenerp.site import SiteError, client_from_env
from tools.experiments.p1_entry_gate.llm import DashScopeClient, LlmError
from tools.experiments.p1_entry_gate.loop import MAX_TURNS, run, write_trace

DEFAULT_QUESTION = Path(__file__).with_name("question.md")
DEFAULT_EVIDENCE = Path("docs/evidence/p1-entry-gate")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m tools.experiments.p1_entry_gate.run",
        description="入口关口实验：门禁开/关 × 弱/强模型，跑一次并落轨迹",
    )
    parser.add_argument("--question-file", default=str(DEFAULT_QUESTION),
                        help="问题文本文件（四格逐字相同）")
    parser.add_argument("--model", required=True, help="模型名，例如 qwen-plus / qwen3.6-plus")
    parser.add_argument("--gate", choices=("on", "off"), required=True, help="门禁开关")
    parser.add_argument("--max-tokens", type=int, required=True, help="单次运行的 token 上限")
    parser.add_argument("--seed-run-id", required=True, help="轨迹文件名（如 run-01）")
    parser.add_argument("--site", default="frontend", help="活站点名")
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE), help="轨迹落盘目录")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS, help="最大轮数")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    question = Path(args.question_file).read_text(encoding="utf-8").strip()
    try:
        client = client_from_env(args.site)
        llm = DashScopeClient(args.model)
    except (SiteError, LlmError) as exc:
        print(f"起不来，已停在配置这一步：{exc}", file=sys.stderr)
        return 2

    trace = run(
        question=question,
        llm=llm,
        client=client,
        gate_on=args.gate == "on",
        max_tokens=args.max_tokens,
        run_id=args.seed_run_id,
        max_turns=args.max_turns,
    )
    path = write_trace(trace, Path(args.evidence_dir))
    print(f"轨迹：{path}")
    print(
        f"工具调用 {trace.tool_calls_total} 次 · token "
        f"prompt {trace.usage.get('prompt', 0)} / completion {trace.usage.get('completion', 0)} "
        f"/ reasoning {trace.usage.get('reasoning', 0)}"
    )
    for check in trace.gate_checks:
        verdict = "红" if check["failed"] else "绿"
        enforced = "已回注" if check["enforced"] and check["failed"] else "仅记录"
        print(f"门禁判定（第 {check['turn']} 轮）：{verdict}，{enforced}")
        for item in check["failed"]:
            print(f"  · {item['text']}（缺 {item['missing_count']} 项）")
    if trace.invalid:
        print(f"⚠️ 无效运行：{trace.invalid['reason']}", file=sys.stderr)
        return 1
    print("--- 最终答案 ---")
    print(trace.final_answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
