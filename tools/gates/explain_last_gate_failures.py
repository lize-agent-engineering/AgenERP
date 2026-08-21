#!/usr/bin/env python3
"""把上一轮门禁判定的红因原样打出来。**只读** .pytest-gates.xml，不写、不删。

用法：python3 tools/gates/explain_last_gate_failures.py [junit 报告路径]

为什么需要它：判定器以 `-q --tb=no` + `capture_output=True` 起 pytest，
终端上一个字的断言原文都没有；红因**只**存在于 junit 报告里。
判定器此刻把报告留在盘上（见 check_expected_red.py 的 run_pytest），本工具是它的读出口。

退出码：
  0  报告在，已把每条红的原文打出来（报告全绿时也退 0，并逐字说明「本轮没有红」）
  2  报告不存在 —— 取不到证就明说取不到，绝不打印「没有失败」：
     那会让「取不到证」长得像「没红」，正是本工具要消灭的那类失效。

**陈旧可见**：报告长期驻盘，「文件在不在」区分不了「刚才那轮的证」和「三天前那轮的证」。
所以第一行永远先打这份报告的出处、junit 的 timestamp 与文件 mtime，把陈旧摆在肉眼第一行。
"""
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_expected_red import JUNIT, failure_details  # noqa: E402

NO_TIMESTAMP = "<该报告没有 timestamp 属性>"


def report_timestamp(junit_xml: str) -> str:
    """junit 的 timestamp。pytest 写在 <testsuite> 上，别的写法可能写在根节点，两处都认。"""
    for element in ET.fromstring(junit_xml).iter():
        stamp = element.get("timestamp")
        if stamp:
            return stamp
    return NO_TIMESTAMP


def provenance_line(junit_path: Path, junit_xml: str) -> str:
    mtime = datetime.fromtimestamp(junit_path.stat().st_mtime).isoformat(timespec="seconds")
    return (f"报告：{junit_path}｜junit timestamp={report_timestamp(junit_xml)}"
            f"｜文件 mtime={mtime}")


def report_lines(junit_path: Path) -> list[str]:
    """读一份报告，产出要打印的全部行。首行恒为出处行。不写不删。"""
    junit_xml = junit_path.read_text()
    lines = [provenance_line(junit_path, junit_xml)]
    details = failure_details(junit_xml)
    if not details:
        lines.append("本轮没有红：这份报告里没有任何 <failure>/<error>。")
        return lines
    lines.append(f"红 {len(details)} 条，逐条原文如下：")
    for node, detail in sorted(details.items()):
        lines.append("")
        lines.append(f"=== {node}")
        lines.append(detail)
    return lines


def main(argv: list[str]) -> int:
    junit_path = Path(argv[0]) if argv else JUNIT
    if not junit_path.exists():
        print(f"FATAL: 取不到证 —— junit 报告不存在：{junit_path}", file=sys.stderr)
        print("       先跑一次 python3 tools/gates/check_expected_red.py 生成它。"
              "（报告不在 ≠ 没有红）", file=sys.stderr)
        return 2
    for line in report_lines(junit_path):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
