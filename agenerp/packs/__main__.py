"""`python3 -m agenerp.packs` 的入口。

WBS §4 P1.6 的验收原文写的是 `python -m agenerp.packs validate --pack discrete`；
本机没有 `python` 这个可执行名，实际形态是 `python3 -m …`。这处替换是声明过的，
不藏着（同 `agenerp/seed/__main__.py`，定稿证据行在 `docs/masterplan/STATE.md` §2）。

**四种输入四种可区分的处置**（plan §6 H6，口径取 (i) 不同退出码 **并且** 消息指名到具体对象）：

| 输入 | 退出码 | 消息指名到 |
|---|---|---|
| 健康包 | `0` | 包 id、规则条数 |
| `--pack` 拼错 / 包目录不存在 | `3` | 那个 `--pack` 取值、查过的目录、现有的包 |
| 某规则缺 `test_case`（或形状不合） | `4` | 那条 `rule_id` |
| 某规则的 `test_case` 跑不过 | `5` | 那条 `rule_id`、测例名、期望与实测 |

⚠️ **`3` / `4` / `5` 分开不是洁癖**：三者合成同一个「非零」时，「查无此包」会被读成
「这个包有问题」，而 `--pack` 打错一个字母的人拿不到任何线索。
（`2` 留给 argparse 的用法错误，不复用。）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agenerp.packs.loader import (
    DISCRETE,
    Pack,
    PackLoadError,
    PackNotFound,
    describe_failure,
    load_pack,
    packs_root,
    validate_pack,
)

EXIT_OK = 0
EXIT_PACK_NOT_FOUND = 3
EXIT_PACK_INVALID = 4
EXIT_TEST_CASE_FAILED = 5

_DESCRIPTION = "校验一个行业包：装载它，并把它每一条规则自带的 test_case 真跑一遍。"
_PACK_HELP = f"包 id（= `industry-packs/` 下的目录名），默认 {DISCRETE}。"
_PACKS_DIR_HELP = (
    "行业包目录，默认是仓库根的 `industry-packs/`。"
    "**它是真参数**：坏包夹具不放进产品制品目录，判据用它指到别处。"
)


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python3 -m agenerp.packs", description=_DESCRIPTION)
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", description=_DESCRIPTION)
    validate.add_argument("--pack", default=DISCRETE, help=_PACK_HELP)
    validate.add_argument("--packs-dir", type=Path, default=None, help=_PACKS_DIR_HELP)
    return parser.parse_args(argv)


def _report_ok(pack: Pack) -> int:
    print(
        f"✅ 行业包 {pack.pack_id!r}（v{pack.version}，{pack.path}）："
        f"{len(pack.rules)} 条规则全部装载成功，每条自带的 test_case 都真跑过且通过"
    )
    for rule in pack.rules:
        print(f"  - {rule.rule_id} · 测例 {rule.test_case.name!r}")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    root = args.packs_dir if args.packs_dir is not None else packs_root()
    try:
        pack = load_pack(args.pack, root)
    except PackNotFound as error:
        print(f"❌ {error}", file=sys.stderr)
        return EXIT_PACK_NOT_FOUND
    except PackLoadError as error:
        print(f"❌ {error}", file=sys.stderr)
        return EXIT_PACK_INVALID

    failures = validate_pack(pack)
    if failures:
        print(
            f"❌ 行业包 {pack.pack_id!r}：{len(failures)} 条规则的 test_case 不通过"
            f"（共 {len(pack.rules)} 条规则）",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  - {describe_failure(pack, failure)}", file=sys.stderr)
        return EXIT_TEST_CASE_FAILED
    return _report_ok(pack)


if __name__ == "__main__":
    raise SystemExit(main())
