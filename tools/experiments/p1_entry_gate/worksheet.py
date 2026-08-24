"""把 12 份轨迹压成一张**只有答案文本**的判定工作单。

判定协议要求「只看最终答案文本，不看轨迹、不看模型名」（plan §2）。
本脚本因此**只取 `final_answer` 与 `run_id`**，其余一律不输出 ——
把模型名和门禁开关摆在判定者眼前，事后挪标准就成了无成本的事。

    python3 -m tools.experiments.p1_entry_gate.worksheet docs/evidence/p1-entry-gate
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    root = Path(args[0]) if args else Path("docs/evidence/p1-entry-gate")
    lines = ["# 判定工作单（只有答案文本，配置一律不显示）", ""]
    for path in sorted(root.glob("run-*.json")):
        trace = json.loads(path.read_text(encoding="utf-8"))
        lines.append(f"## {trace['run_id']}")
        lines.append("")
        if trace.get("invalid"):
            lines.append(f"**无效运行**：{trace['invalid']['reason']}")
        else:
            lines.append(trace["final_answer"] or "（空答案）")
        lines.append("")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
