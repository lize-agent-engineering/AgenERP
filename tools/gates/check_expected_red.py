#!/usr/bin/env python3
"""把「故意的红」和「真的坏了」分开。

用法：python3 tools/gates/check_expected_red.py [pytest 额外参数...]

退出码：
  0  一切符合预期（名单内红、名单外绿）
  1  有偏差（名单外的测试红了，或名单内的测试意外绿了）
  2  跑不起来（pytest 自身出错、名单文件缺失）

这个脚本是 GATE_VERIFY 与 CI 共用的判定器。它只读退出结果，不读 AI 的说法。
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "tests/gates/EXPECTED_RED.txt"
JUNIT = ROOT / ".pytest-gates.xml"


def load_allowlist() -> set[str]:
    if not ALLOWLIST.exists():
        print(f"FATAL: 找不到预期红名单 {ALLOWLIST}", file=sys.stderr)
        sys.exit(2)
    return {
        line.strip()
        for line in ALLOWLIST.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


def run_pytest(extra: list[str]) -> dict[str, str]:
    cmd = [sys.executable, "-m", "pytest", "tests/gates", "-q", "--tb=no",
           f"--junitxml={JUNIT}", *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if not JUNIT.exists():
        print("FATAL: pytest 没产出 junit 报告，它自己就跑挂了：", file=sys.stderr)
        print(proc.stdout[-2000:], proc.stderr[-2000:], file=sys.stderr)
        sys.exit(2)

    outcomes: dict[str, str] = {}
    for tc in ET.parse(JUNIT).getroot().iter("testcase"):
        nodeid = f"{tc.get('classname', '').replace('.', '/')}.py::{tc.get('name')}"
        if tc.find("failure") is not None or tc.find("error") is not None:
            outcomes[nodeid] = "red"
        elif tc.find("skipped") is not None:
            outcomes[nodeid] = "skipped"
        else:
            outcomes[nodeid] = "green"
    JUNIT.unlink(missing_ok=True)
    return outcomes


def main() -> int:
    expected_red = load_allowlist()
    outcomes = run_pytest(sys.argv[1:])

    unexpected_red = sorted(n for n, o in outcomes.items() if o == "red" and n not in expected_red)
    unexpected_green = sorted(n for n, o in outcomes.items() if o == "green" and n in expected_red)
    skipped = sorted(n for n, o in outcomes.items() if o == "skipped")

    print(f"门禁 {len(outcomes)} 项：预期红 {len([o for o in outcomes.values() if o=='red'])}，"
          f"绿 {len([o for o in outcomes.values() if o=='green'])}，跳过 {len(skipped)}")

    if skipped:
        print("\n❌ 有测试被跳过 —— 门禁不允许 skip/xfail：")
        for n in skipped:
            print(f"   {n}")

    if unexpected_red:
        print("\n❌ 名单外的门禁红了（真的坏了）：")
        for n in unexpected_red:
            print(f"   {n}")

    if unexpected_green:
        print("\n❌ 名单内的门禁却绿了 —— 实现已到位，请在同一个提交里把它从 EXPECTED_RED.txt 划掉：")
        for n in unexpected_green:
            print(f"   {n}")

    if unexpected_red or unexpected_green or skipped:
        return 1
    print("✅ 与预期红名单完全一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
