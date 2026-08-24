"""判定题面：**一段答案文本 → 三个标签之一**。落点节 `docs/architecture/module-boundaries.md` §7.15。

## 题面的出处（不是本模块现编的）

三条判据逐字取自 `docs/evidence/p1-entry-gate/verdicts.md`「三条判据（逐字取自 plan §2，未改写）」
—— 那张表是 P1.0 **跑之前就冻结**的判定协议，人按它读了 24 份答案原文才有了那份标注集。
本模块把同一份协议写成模型能读的题面，**没有新增任何判准**。

## 三条硬规矩

1. **标签集合恰好三个**（`correct` / `incomplete` / `truncated`），逐字来自标注集。
   **不设第四类**（例如 `unjudgeable`）—— 那会让「判不动」变成一个合法出口，
   而那正是 always-correct 之外的第二种偷懒形态（plan D3）。
2. **模型回三者之外 → 指名报错**（`JudgingError`），**不静默归一**。
   静默归成 `correct` 会让一次解析失败长得像一次判定成功。
3. **题面里出现的三个标签词是「输出空间的定义」**，它不随被判的那一行变。
   `build_messages()` **只吃一段答案文本**，行对象上的 `label` / `reason` 一个字节都进不来
   —— 判据是「真行 vs 噪声替换后的同一行 ⇒ `messages` 逐字节相同」（plan §6 H7 ②）。
"""

from __future__ import annotations

import json
import re


class JudgingError(RuntimeError):
    """题面/回包解析这一层的失败：空输入、未知标签、回包不成形。

    **刻意不复用 `RoutingError`**：「模型没选对」与「模型回了个判不动的东西」是两件事，
    混成一个异常，调用方就只能靠读消息文本去分辨。
    **也刻意不单开一个 `errors.py`** —— `agenerp/judging/` 的产品模块只有三个
    （`__init__` / `rubric` / `judge`，plan D7b），异常类型跟着定义它的那一层走。
    """


LABELS = ("correct", "incomplete", "truncated")

# P1.0 那道题的原文（`tools/experiments/p1_entry_gate/question.md` 逐字）。
# 判定器的**已验证适用范围只有这一道题**，跨题族使用按 D-16 只能写「待复验」（plan §1.4）。
QUESTION = (
    "销售订单 SAL-ORD-2026-00001 在系统里显示已经完成了，但车间反映成品仓还压着不少货。\n"
    "这是怎么回事？请说明成品仓现在的实际情况，以及造成这个情况的原因。"
)

# 逐字取自 `docs/evidence/p1-entry-gate/verdicts.md` 的三条判据表。
CRITERIA = (
    "① 报出 1,010 台这个数",
    "② 指出入库 2,000 与发货 990 的差额构成",
    "③ 点名两批生产中的至少一批是多余的（即触及根因，而非只描述现象）",
)

SYSTEM_PROMPT = """你是一名 ERP 答案判定员。你要做的事只有一件：读一段答案文本，给它一个标签。

被判的那段文本，是另一个 Agent 对下面这道题给出的最终答案：

<问题>
{question}
</问题>

这道题的判定判据在提问之前就冻结了，逐字如下（不许增补、不许放宽）：

{criteria}

标签集合恰好三个，**没有第四个**：

- `truncated`：答案在中途断掉 —— 话说到一半就结束、只剩下"下面我来回答"这类过渡句、
  或者归因部分根本没写出来。**先判这一条**：只要文本是断的，无论前面命中几条判据，都记 `truncated`。
- `correct`：文本完整，且 ① ② ③ **三条全中**。
- `incomplete`：文本完整，但 ① ② ③ **没有全中**（少中一条也算）。

判定时的三条纪律：

1. **只看这段文本本身。** 不要猜它是哪个模型写的，不要考虑它写得好不好读。
2. **判据只认实质，不认字面。** 例如 ② 允许写成"1000 + 1000 - 990"或"两笔各 1000 台入库、发货 990 台"；
   ③ 允许写成"外协那 1000 台没有任何销售订单消化""重复记录了一批"等等 —— 意思到了就算命中。
3. **判不动也要给三个标签之一。** 没有"无法判定"这个出口。

输出格式：**只输出一个 JSON 对象**，形如 {{"label": "correct"}}。
`label` 的取值只能是 `correct` / `incomplete` / `truncated` 三者之一。不要输出别的字段，不要加解释。"""


def system_prompt() -> str:
    return SYSTEM_PROMPT.format(question=QUESTION, criteria="\n".join(CRITERIA))


def build_messages(answer: str) -> list[dict]:
    """把一段答案文本包成一次 chat 的 `messages`。

    **参数只有 `answer` 一个** —— 这是 plan §6 H7 ② 那条「标签无关」判据的落地面：
    行对象上的 `label` / `reason` 没有任何形参可以承载，因此它们进不了 `messages`。
    """
    if not isinstance(answer, str):
        raise JudgingError(f"待判的答案必须是一段文本，拿到 {type(answer).__name__}")
    if not answer.strip():
        raise JudgingError("待判的答案是空文本 —— 空答案不是一次判定的合法输入")
    return [
        {"role": "system", "content": system_prompt()},
        {
            "role": "user",
            "content": "下面是待判定的答案文本，判完只输出那个 JSON 对象：\n\n"
            f"<答案>\n{answer}\n</答案>",
        },
    ]


_JSON_OBJECT = re.compile(r"\{[^{}]*\}")


def parse_label(text: str) -> str:
    """从模型回包文本里取出标签。**取不出来就指名报错，绝不静默归一。**

    两种形态都收：整段就是一个 JSON 对象，或者一段话里裹着一个 JSON 对象
    （推理模型常在前面写几句）。**只认 `label` 键**，不去猜"文本里出现了 correct 这个词"
    —— 那种猜法会把"这不是 correct"读成 `correct`。
    """
    if not isinstance(text, str) or not text.strip():
        raise JudgingError("模型回包是空文本，判不出标签（**不降级成任何默认标签**）")
    for match in reversed(_JSON_OBJECT.findall(text)):
        try:
            obj = json.loads(match)
        except ValueError:
            continue
        if isinstance(obj, dict) and "label" in obj:
            label = obj["label"]
            if label in LABELS:
                return label
            raise JudgingError(
                f"模型回了未知标签 {label!r}；标签集合恰好是 {list(LABELS)}，"
                "**不新增第四类、不静默归一**"
            )
    stripped = text.strip().strip("`").strip()
    if stripped in LABELS:
        return stripped
    raise JudgingError(
        f"模型回包里没有可解析的 {{\"label\": …}}，原文前 200 字：{text.strip()[:200]!r}"
    )
