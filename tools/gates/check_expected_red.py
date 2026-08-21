#!/usr/bin/env python3
"""把「故意的红」和「真的坏了」分开。

用法：python3 tools/gates/check_expected_red.py [pytest 额外参数...]

退出码：
  0  一切符合预期（名单内红、名单外绿）
  1  有偏差（名单外的测试红了，或名单内的测试意外绿了）
  2  跑不起来（pytest 自身出错、名单文件缺失）

这个脚本是 GATE_VERIFY 与 CI 共用的判定器。它只读退出结果，不读 AI 的说法。
"""
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / "tools/gates/expected-red.txt"
JUNIT = ROOT / ".pytest-gates.xml"

# 判定器跑在谁的环境里，不由判定器决定：launchd、CI、人手敲的 shell，PATH 各不相同。
# 已装载的 launchd plist 半路改不了（要 unload/load，等于杀掉正在跑的循环），
# tools/loopx-writeback.sh 的自愈也只覆盖走它那条入口的运行。所以在这里再兜一层：
# 判定器自己起 pytest 之前，把系统标准路径补齐。
#
# 漏 /usr/local/bin 的代价是实打实的：Docker Desktop 的 CLI 软链在那儿
# （/usr/local/bin/docker -> Docker.app），缺了它 test_compose_config_valid_with_empty_env
# 会以 `FileNotFoundError: 'docker'` 假红，而它不在预期红名单里 —— 判定器于是报
# 「名单外的门禁红了（真的坏了）」，把一个环境问题误判成实现回归。
# （2026-08-21 迁 launchd 后第二次踩到；第一次见 0f2c59a。）
#
# 只**追加**、不前置：绝不遮挡环境里已经选定的 python / docker 等工具。
# 这不放松任何判据 —— docker 真没装时，测试照样红。
SYSTEM_PATHS = ("/usr/local/bin", "/usr/local/sbin")


def healed_env() -> dict[str, str]:
    env = dict(os.environ)
    parts = env.get("PATH", "").split(os.pathsep)
    parts += [d for d in SYSTEM_PATHS if d not in parts and Path(d).is_dir()]
    env["PATH"] = os.pathsep.join(p for p in parts if p)
    return env


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
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=healed_env())
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
        print("\n❌ 名单内的门禁却绿了 —— 实现已到位，请在同一个提交里把它从 tools/gates/expected-red.txt 划掉：")
        for n in unexpected_green:
            print(f"   {n}")

    if unexpected_red or unexpected_green or skipped:
        return 1
    print("✅ 与预期红名单完全一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
