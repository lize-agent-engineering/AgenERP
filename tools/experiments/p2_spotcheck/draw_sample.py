#!/usr/bin/env python3
"""P2 · 门禁抽查制的**抽样**（`04-RUNBOOK.md` §7.2.1）。

    python3 tools/experiments/p2_spotcheck/draw_sample.py

## 这个脚本为什么存在

§7.2.1 要求每阶段从**新增或改动过的绿判据**里**随机抽 3 条**，逐条答
「**它测的，是不是它名字说的那件事？**」——
⚠️ 并且逐字写着：**抽查者不得是这些判据的作者。**

**P2 的判据几乎全是我写的 ⇒ 我不能当抽查者。**
但「抽样公平」这件事可以由代码保证：本脚本用**写死的种子**从**机器算出来的候选池**里抽，
任何人重跑都得到同一组。⇒ **抽了什么不由我挑，也不由我事后改。**

形态沿用 P1：那次人把整项交给 loop，抽样写死可复算（`STATE` §3 同日条目）。

## 候选池怎么算

`git diff --name-only <基线>..HEAD -- tests/` 里所有**当前是绿的** `test_` 函数。
⚠️ **活体判据也算**，但它们要活站点才跑得到；标出来，由抽查者决定怎么核。
"""

import ast
import pathlib
import random
import subprocess
import sys

BASELINE = "012385a"  # P2 开工前的 main
SEED = 20260827  # 写死。**改种子就是重抽，git 上看得见。**
N = 3


def changed_test_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{BASELINE}..HEAD", "--", "tests/"],
        capture_output=True, text=True, check=True,
    ).stdout
    return sorted(p for p in out.split() if p.endswith(".py") and "__pycache__" not in p)


def test_functions(path: str) -> list[str]:
    tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]


def main() -> None:
    files = changed_test_files()
    pool = [(f, name) for f in files for name in test_functions(f)]
    pool.sort()  # 排序后再抽 —— 否则 git 输出次序一变，同一个种子抽出来的就不同了

    print(f"基线 {BASELINE} · 种子 {SEED} · 候选池 {len(pool)} 条，来自 {len(files)} 个文件\n")
    for f in files:
        n = len(test_functions(f))
        live = "（活体）" if "tests/render/" in f or "_body.py" in f else ""
        print(f"  {n:>3}  {f} {live}")

    rng = random.Random(SEED)
    drawn = rng.sample(pool, N)
    print(f"\n🔴 抽中这 {N} 条 —— **抽查者不得是作者，而这些全是我写的**：\n")
    for i, (f, name) in enumerate(drawn, 1):
        print(f"  {i}. {f}::{name}")

    print(
        "\n逐条要回答的问题（§7.2.1 原文）：**「它测的，是不是它名字说的那件事？」**\n"
        "答案落进 P2.8 复盘纪要。抽到一条名不副实的，即为一次误放行，按原规则处置。\n"
        f"\n复算：任何人重跑本脚本都得到同一组（种子 {SEED} 写死在源码里）。"
    )


if __name__ == "__main__":
    sys.exit(main())
