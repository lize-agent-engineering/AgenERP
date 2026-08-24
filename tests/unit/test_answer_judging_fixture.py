"""判据的判据：任何「判 Agent 答对没有」的判定器，必须先过这份人工标注集。

## 存在理由（四次实测教训，不是预防性设计）

判定 P1.0 那道题的答案时，我用关键词正则判了四次，**四次都判错**：

| 第几次 | 漏掉的 | 表现 |
|---|---|---|
| 1 | 要求字面 `2000`，认不出 `1000 + 1000 - 990` | 把正确答案判成「仅报数」 |
| 2 | 根因词列了「重复生产」，漏了「重复记录」 | 同上 |
| 3 | 认不出 `10 台尾数 + 1000 台外协` 这第三种拆法 | 第一轮整体从 5/12 误判成 2/12 |
| 4 | 「没有任何销售订单来消化」「无单可发」「额外的外协收货」都不在词表里 | 三份正确答案判成「不完全」 |

**每次都是读原文才发现，而每次修完都以为修干净了。**

→ 结论不是「再补一版词表」，而是：**正则判自由文本这条路走不通**。
判定器要么由人判、要么由模型判，但**无论哪种，都必须能复现这份标注集**。

## 这份集子的性质

- **标签由人读原文定**（`reason` 字段记着判定依据），**不由任何判定器产生** ——
  否则就是让判据给自己判卷，那正是 `tests/gates/test_seed_dataset_absurdity.py`
  开头那段说的同一件事
- 24 条覆盖两轮实验的全部有效运行，含 4 条「不完全」与 1 条「截断」——
  **反例比正例值钱**：只有正例的集子挡不住「一律判正确」的假实现

## 给 P1.4 / P1.5 的话

那两个工作项要判的是「解释 Agent 答得对不对」「洞察 Agent 找没找到」，
比这道题更难判。**动手写判定器之前，先让它跑通这份集子。**
跑不通就别往下写 —— 那说明判定方法本身有问题，不是答案有问题。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/p1_entry_gate_labels.jsonl"
VALID_LABELS = {"correct", "incomplete", "truncated"}


def _rows():
    return [json.loads(line) for line in FIXTURE.read_text().splitlines() if line.strip()]


def test_fixture_exists_and_is_parseable():
    """集子本身得在、得能读。找不到就是红，不是「跳过这层保护」。"""
    assert FIXTURE.is_file(), f"标注集不存在：{FIXTURE}"
    rows = _rows()
    assert len(rows) == 24, f"应有 24 条（两轮的全部有效运行），实为 {len(rows)}"


def test_every_row_carries_a_human_written_reason():
    """**标签必须带判定依据。** 没有 reason 的标签等于「我觉得」，将来无法复核。"""
    for r in _rows():
        assert r["label"] in VALID_LABELS, f"{r['run_id']} 的标签 {r['label']!r} 不在允许集内"
        assert len(r.get("reason", "")) >= 10, f"{r['run_id']} 缺少人写的判定依据"
        assert r["answer"], f"{r['run_id']} 没有答案正文，无法复核"


def test_the_fixture_has_enough_negatives_to_catch_a_lazy_judge():
    """**反例比正例值钱。**

    只有正例的集子挡不住「一律判 correct」的假实现 —— 那种实现在纯正例集上满分。
    """
    labels = [r["label"] for r in _rows()]
    negatives = [x for x in labels if x != "correct"]

    assert len(negatives) >= 4, (
        f"反例只有 {len(negatives)} 条，挡不住「一律判正确」的假实现"
    )


def test_a_judge_that_always_says_correct_fails_this_fixture():
    """**元判据**：证明这份集子确实能挡住最偷懒的那种实现。

    这条不测任何产品代码，它测的是**集子自身的判别力**。集子若挡不住
    always-correct，那它作为「判据的判据」就是摆设。
    """
    rows = _rows()
    always_correct = [("correct" == r["label"]) for r in rows]

    assert not all(always_correct), (
        "一律判 correct 竟然全对 —— 这份集子没有判别力，加反例再来"
    )


@pytest.mark.parametrize("run_id", [r["run_id"] for r in _rows()])
def test_each_labelled_answer_is_traceable_to_its_trace_file(run_id):
    """每条标注都能回溯到原始轨迹。断了就无法复核标签对不对。"""
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / f"docs/evidence/p1-entry-gate/{run_id}.json",
        root / f"docs/evidence/p1-entry-gate-round2/{run_id}.json",
    ]
    hit = [p for p in candidates if p.is_file()]

    assert hit, f"{run_id} 找不到对应的轨迹文件，标注无法复核"

    trace = json.loads(hit[0].read_text())
    row = next(r for r in _rows() if r["run_id"] == run_id)
    assert trace["final_answer"] == row["answer"], (
        f"{run_id} 的标注正文与轨迹里的 final_answer 不一致 —— 集子已过期"
    )
