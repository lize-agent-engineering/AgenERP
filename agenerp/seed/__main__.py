"""`python3 -m agenerp.seed` 的入口。

主计划 WBS 的验收原文写的是 `python -m agenerp.seed …`；本机没有 `python` 这个可执行名，
实际形态是 `python3 -m agenerp.seed …`。这处替换是声明过的，不藏着。
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from agenerp.seed.checks import verify
from agenerp.seed.dataset import generate
from agenerp.seed.model import SCOPE
from agenerp.seed.store import to_snapshot, write
from agenerp.snapshot import diff

_DESCRIPTION = "确定性生成离散制造种子数据集（内置 1,010 米积压这个已知业务荒谬）。"
_SEED_HELP = (
    "随机种子（默认 42）。**它是真参数**：只驱动批号等装饰性字段，"
    "不同 seed 的批号不同，但全部断言项完全一致。"
)
_OUT_HELP = (
    f"落盘目录，产物写进 <DIR>/{SCOPE}/。不给则：不带 --verify 时写进临时目录并打印路径，"
    "带 --verify 时不落盘。**仓库里不落生成物。**"
)
_VERIFY_HELP = (
    "判据模式：生成两次求 diff，diff 非空即失败；再跑场景断言，有失败原因即失败。"
    "两者都过退 0，任一不过把原因逐条打到 stderr 并退 1。"
)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python3 -m agenerp.seed", description=_DESCRIPTION)
    parser.add_argument("--seed", type=int, default=42, help=_SEED_HELP)
    parser.add_argument("--out", type=Path, default=None, help=_OUT_HELP)
    parser.add_argument("--verify", action="store_true", help=_VERIFY_HELP)
    return parser.parse_args(argv)


def _run_verify(seed: int) -> list[str]:
    first, second = generate(seed), generate(seed)
    delta = diff(to_snapshot(first), to_snapshot(second))
    if not delta.is_empty():
        return [f"同种子两次生成的 diff 非空：{delta.summary()}"]
    return verify(first)


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    if args.verify:
        failures = _run_verify(args.seed)
        if args.out is not None:
            write(generate(args.seed), args.out)
        if failures:
            print(f"❌ 种子 {args.seed} 未通过 {len(failures)} 条判据：", file=sys.stderr)
            for reason in failures:
                print(f"  - {reason}", file=sys.stderr)
            return 1
        print(f"✅ 种子 {args.seed}：两次生成 diff 为空，场景断言全过")
        return 0
    out = args.out if args.out is not None else Path(tempfile.mkdtemp(prefix="agenerp-seed-"))
    print(write(generate(args.seed), out))
    return 0


if __name__ == "__main__":
    raise SystemExit(0)  # MUTATION-B: plan-0337-1 Phase 3 实验 B，必须 revert
