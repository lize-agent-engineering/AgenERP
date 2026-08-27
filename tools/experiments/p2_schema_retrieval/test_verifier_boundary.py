#!/usr/bin/env python3
"""新验证器的**决策边界测试** —— `eval-engineering/verifier-design` 的六个 fixture。

    python3 tools/experiments/p2_schema_retrieval/test_verifier_boundary.py

⚠️ **上一版验证器我从没跑过这一步**，结果是：Top-5 口径把「一次答 5 个同族字段」
判成 Pass（reward hack 放行），还把 `Job Card Time Log.completed_qty` 这种
真实且更贴题的答案判成 Fail（假拒）。**这次先跑边界再跑评测。**

本文件只测**规则层**（`committed_field` 与承诺判定）——
判官那一层要连站点与端点，由评测本身的 infrastructure 归因兜着。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_completion_eval import committed_field  # noqa: E402

CASES = [
    (
        "① 已知正确答案（干净承诺）",
        "我查了 meta.fields。\nJob Card.total_completed_qty",
        "Job Card.total_completed_qty",
    ),
    (
        "② 等价但不同的有效答案 —— 规则层放行，交判官",
        "报工记录在时间日志上。\nJob Card Time Log.completed_qty",
        "Job Card Time Log.completed_qty",
    ),
    (
        "③ 现实的错答案 —— 规则层放行，由集合/判官判错",
        "Sales Order.customer",
        "Sales Order.customer",
    ),
    (
        "🔴 ④ 抄近路 / 刷分：一次答 5 个同族字段",
        "Job Card.a\nJob Card.b\nJob Card.c\nJob Card.d Job Card.total_completed_qty",
        None,  # **必须判「未承诺」** —— 这是上一版放行了的那一格
    ),
    (
        "⑤ 编造的字段 —— 规则层放行，第 1 层查存在性时判错",
        "Job Card.completed_quantity",
        "Job Card.completed_quantity",
    ),
    (
        "⑥ 空/损坏的证据 —— 必须判「未承诺」并归 infrastructure",
        "",
        None,
    ),
    (
        "⑦ 边界：整段只出现一个字段但不在最后一行",
        "根据 meta.fields，应该用 Job Card.total_completed_qty 这个字段。\n以上。",
        "Job Card.total_completed_qty",
    ),
    (
        "⑧ 边界：列了候选又在最后一行承诺 —— 承诺算数",
        "候选有 Job Card.total_completed_qty 和 Job Card Time Log.completed_qty。\n"
        "Job Card.total_completed_qty",
        "Job Card.total_completed_qty",
    ),
]


def main() -> int:
    bad = 0
    for name, answer, want in CASES:
        got, note = committed_field(answer)
        ok = got == want
        if not ok:
            bad += 1
        print(f"{'✅' if ok else '❌'} {name}")
        print(f"     输入 {answer!r}")
        print(f"     承诺 = {got!r}（{note}） · 期望 {want!r}")
    print(f"\n{'=' * 60}")
    if bad:
        print(f"❌ {bad}/{len(CASES)} 个边界不对 —— **评测不能跑**，先修验证器")
        return 1
    print(f"✅ {len(CASES)}/{len(CASES)} 个边界都对 —— 验证器可以用了")
    return 0


if __name__ == "__main__":
    sys.exit(main())
