#!/usr/bin/env python3
"""把「故意的红」和「真的坏了」分开。

用法：python3 tools/gates/check_expected_red.py [pytest 额外参数...]

两种判定模式，由环境变量 AGENERP_LIVE 选中（与 tests/gates/conftest.py 的
_require_live() 是同一个开关，两者不可能各判各的）：

  default（未设 AGENERP_LIVE）：按 tools/gates/expected-red.txt 判定。
      名单内红 = 正常，名单外红 = 真的坏了，名单内绿 = 名单过期，出现 skip = 有人放松裁判。
  live（AGENERP_LIVE=1）：契约是全部门禁绿、零 red、零 skip，**不读**预期红名单。
      理由与偏离记录见 docs/architecture/system-baseline.md §14.4。

退出码：
  0  一切符合预期
  1  有偏差
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


def run_pytest(extra: list[str]) -> str:
    cmd = [sys.executable, "-m", "pytest", "tests/gates", "-q", "--tb=no",
           f"--junitxml={JUNIT}", *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=healed_env())
    if not JUNIT.exists():
        print("FATAL: pytest 没产出 junit 报告，它自己就跑挂了：", file=sys.stderr)
        print(proc.stdout[-2000:], proc.stderr[-2000:], file=sys.stderr)
        sys.exit(2)
    junit_xml = JUNIT.read_text()
    JUNIT.unlink(missing_ok=True)
    return junit_xml


def classify(junit_xml: str) -> dict[str, str]:
    outcomes: dict[str, str] = {}
    for tc in ET.fromstring(junit_xml).iter("testcase"):
        nodeid = f"{tc.get('classname', '').replace('.', '/')}.py::{tc.get('name')}"
        if tc.find("failure") is not None or tc.find("error") is not None:
            outcomes[nodeid] = "red"
        elif tc.find("skipped") is not None:
            outcomes[nodeid] = "skipped"
        else:
            outcomes[nodeid] = "green"
    return outcomes


def verdict(outcomes: dict[str, str], expected_red: set[str],
            live: bool) -> tuple[int, list[str]]:
    """纯判定：只吃分类结果与名单，不碰进程、不打印。live=True 时不读 expected_red。"""
    reds = sorted(n for n, o in outcomes.items() if o == "red")
    greens = sorted(n for n, o in outcomes.items() if o == "green")
    skipped = sorted(n for n, o in outcomes.items() if o == "skipped")

    if live:
        lines = [f"门禁 {len(outcomes)} 项：红 {len(reds)}，绿 {len(greens)}，跳过 {len(skipped)}"]
    else:
        lines = [f"门禁 {len(outcomes)} 项：预期红 {len(reds)}，"
                 f"绿 {len(greens)}，跳过 {len(skipped)}"]

    if skipped:
        lines.append("")
        lines.append("❌ 有测试被跳过 —— 门禁不允许 skip/xfail：")
        lines += [f"   {n}" for n in skipped]

    if live:
        if reds:
            lines.append("")
            lines.append("❌ live 判定契约是全部门禁绿，下列门禁红了：")
            lines += [f"   {n}" for n in reds]
        if reds or skipped:
            return 1, lines
        lines.append("✅ live 判定：全部门禁绿，零 red、零 skip")
        return 0, lines

    unexpected_red = [n for n in reds if n not in expected_red]
    unexpected_green = [n for n in greens if n in expected_red]

    if unexpected_red:
        lines.append("")
        lines.append("❌ 名单外的门禁红了（真的坏了）：")
        lines += [f"   {n}" for n in unexpected_red]

    if unexpected_green:
        lines.append("")
        lines.append("❌ 名单内的门禁却绿了 —— 实现已到位，"
                     "请在同一个提交里把它从 tools/gates/expected-red.txt 划掉：")
        lines += [f"   {n}" for n in unexpected_green]

    if unexpected_red or unexpected_green or skipped:
        return 1, lines
    lines.append("✅ 与预期红名单完全一致")
    return 0, lines


def main() -> int:
    live = os.environ.get("AGENERP_LIVE") == "1"
    # 两种模式都打印模式行：只在 live 打的话，日志答不出「这条绿是谁判的」。
    if live:
        print("判定模式：live（AGENERP_LIVE=1）—— 契约为全部门禁绿、零 skip，不读预期红名单")
    else:
        print("判定模式：default —— 按 tools/gates/expected-red.txt 判定")

    expected_red: set[str] = set() if live else load_allowlist()
    outcomes = classify(run_pytest(sys.argv[1:]))
    code, lines = verdict(outcomes, expected_red, live)
    for line in lines:
        print(line)
    return code


if __name__ == "__main__":
    sys.exit(main())
