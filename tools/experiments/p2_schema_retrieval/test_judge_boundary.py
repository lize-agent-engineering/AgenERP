#!/usr/bin/env python3
"""判官层的**决策边界测试**。

    python3 tools/experiments/p2_schema_retrieval/test_judge_boundary.py

⚠️ `test_verifier_boundary.py` 只测了规则层。**判官那一层我一开始没测** ——
而它刚刚放行了一个我原本判错的答案（`Job Card Time Log.completed_qty`）。
那一次放行**看起来是对的**，但「它会不会一味说 yes」是另一个问题：
`verifier-design` 要求同时测 **false acceptance** 与 **false rejection** 两侧。

本文件喂六个真实字段给判官，其中**四个**不能回答那个问题。
判官若把它们也放行 ⇒ **它是个橡皮图章，整个第 3 层作废。**

⚠️ **第一次跑这六格时，错的那一格是我**：我把 `Job Card.for_quantity`
（标签「Qty To Manufacture」= **计划**数量）标成了可接受，而问句问的是**完成**了多少。
判官判 False 且理由准确。**修的是 fixture，不是放宽判官。**
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_completion_eval import JUDGE_PROMPT, judge  # noqa: E402

Q = "工人报工完成了多少数量？"
ACCEPTABLE = ["Job Card.total_completed_qty"]

# 六个**站点上真实存在**的字段。前三个该放行，后三个该拒。
CASES = [
    ("Job Card Time Log", "completed_qty", "Completed Qty", "Float", "", 12.0, True,
     "报工记录就在时间日志上 —— 这是那次假拒的原型"),
    ("Job Card", "for_quantity", "Qty To Manufacture", "Float", "", 100.0, False,
     "🔴 **这一格我第一版标成了 True，标错了** —— 「Qty To Manufacture」是**计划**生产数量，"
     "而问句问的是**完成**了多少。判官答 False 并给出「该字段表示计划生产数量，"
     "而非实际完成数量」—— **判官比我细**。修的是 fixture，不是放宽判官。"),
    ("Work Order", "produced_qty", "Manufactured Qty", "Float", "", 50.0, True,
     "工单完工数，与「报工完成多少」高度相关"),
    ("Job Card", "employee_name", "Employee Name", "Data", "", "张三", False,
     "🔴 员工姓名 —— 明显答不了「多少数量」"),
    ("Job Card", "workstation", "Workstation", "Link", "Workstation", "组装台1", False,
     "🔴 工作站 —— 明显答不了「多少数量」"),
    ("Sales Order", "grand_total", "Grand Total", "Currency", "", 10100.0, False,
     "🔴 销售订单金额 —— 单据和口径都不对"),
]


def main() -> int:
    key = os.environ.get("AGENERP_LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
    base = os.environ.get("AGENERP_LLM_BASE_URL",
                          "https://dashscope.aliyuncs.com/compatible-mode/v1")
    if not key:
        print("没有 API key —— 不猜凭据")
        return 2

    usage: dict = {}
    wrong = []
    for dt, fn, label, ftype, opts, sample, want, note in CASES:
        v = judge(JUDGE_PROMPT.format(
            question=Q, doctype=dt, fieldname=fn, label=label, fieldtype=ftype,
            options=opts or "(无)", sample=sample, acceptable=ACCEPTABLE),
            "qwen3.6-plus", base, key, usage)
        got = bool(v.get("answers"))
        ok = got == want
        if not ok:
            wrong.append((f"{dt}.{fn}", want, got, v.get("why")))
        print(f"{'✅' if ok else '❌'} {dt}.{fn:<20} 判官说 {str(got):<5} "
              f"（期望 {want}） · {v.get('why')}")
        print(f"     {note}")

    print(f"\n{'=' * 68}")
    print(f"判官用量：{usage.get('judge_calls')} 次 · "
          f"{usage.get('judge_in')} in / {usage.get('judge_out')} out")
    if wrong:
        print(f"\n❌ {len(wrong)} 格不对：")
        for k, want, got, why in wrong:
            side = "**误放行（false acceptance）**" if got else "**假拒（false rejection）**"
            print(f"   {k}：期望 {want}、判官 {got} ⇒ {side} · 理由「{why}」")
        print("\n⇒ 判官层不可信，第 3 层的每一次放行都要人复核。")
        return 1
    print("\n✅ 六格全对 —— 判官在这一题上两侧都判得住（**n=6，不足以推广**）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
