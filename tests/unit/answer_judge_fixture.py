"""判定器判据的共用件：**读那 24 条标注 + 那一个验收口径 + 一组假回包**。

## 为什么它在 `tests/unit/` 而不在 `agenerp/`（plan `Decision D7b`）

- 产品包依赖 `tests/fixtures/**` 是**边界倒置**：`agenerp/judging/` 装在别处也得能用，
  而那份标注集只在本仓、只为这一次实验存在。
- 验收口径是**这一次实验的**口径。焊进产品导出面之后，它就再也改不动了 ——
  而它本来就该随集子一起长。
- 备选「落 `tools/experiments/`」也被否决：`tools/` 不在本仓 `ruff` 作用域内
  （`pyproject.toml` 的 `ruff check` 参数列表逐字如此），验收函数会失去静态检查。

⇒ `agenerp/judging/` 只留 `__init__.py` / `rubric.py` / `judge.py` **三个**产品模块。

## 两条纪律

1. **只把 `answer` 送模型。** `judge_row()` 读的行键只有 `answer` 一个；
   `label` 仅用于事后比对，`reason` **一次都不读**。
2. **验收口径只有 `meets_acceptance()` 这一处实现**，不许在判据文件里再写一遍。
   `meets_legacy_acceptance()` 是**旧口径**，它只为 H1c 记账而存在
   （证明"收紧口径挡下了单子串规则"这件事），**不是本 plan 的验收**。
"""

from __future__ import annotations

import hashlib
import json
import pathlib

from agenerp.judging import judge_one
from agenerp.routing.capabilities import ModelProfile
from agenerp.routing.config import LlmConfig

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/fixtures/p1_entry_gate_labels.jsonl"

# 集子的形状（起草期与执行期各实读一次，逐条相符）。写死是为了让"集子被改了"当场变红。
EXPECTED_ROWS = 24
EXPECTED_POSITIVES = 19
EXPECTED_NEGATIVES = 5
POSITIVE_FLOOR = 17

# H7 ③ 钉死用的那条答案：`run-01`，1133 字符，**含「外协」** ——
# 不含该词的答案挡不住 M9b 那种"命中关键词就直接返回 correct、其余才读回包"的混合短路。
KEYWORD_BEARING_RUN_ID = "run-01"
OVERFIT_KEYWORD = "外协"


def rows() -> list[dict]:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def row_by_id(run_id: str) -> dict:
    return next(r for r in rows() if r["run_id"] == run_id)


def fixture_sha256() -> str:
    return hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


# 集子在**本模块导入那一刻**的指纹。判据拿它当参照，而不是"跑之前先算一次" ——
# 后者是顺序依赖的：同一次会话里若有更早的判据已经把文件写过一遍，
# "跑之前"读到的就已经是被写过的内容，前后一比反而相等（2026-08-25 变异自查 M7 实测到这一点）。
# 模块导入发生在任何一条判据之前，所以这个常量是这次会话里唯一可信的原样指纹。
PRISTINE_SHA256 = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def noise_row(row: dict) -> dict:
    """把该行的 `label` 与 `reason` 换成噪声，**其余字节一个不动**。

    plan §6 H7 ② 那条谓词的另一半：真行与本行生成的 `messages` 必须**逐字节相同**。
    """
    noised = dict(row)
    noised["label"] = "NOISE-LABEL-0000"
    noised["reason"] = "NOISE-REASON-0000000000"
    return noised


# -- 假模型端点 --------------------------------------------------------------


def usage_body(prompt: int = 733, completion: int = 41, reasoning: int = 29) -> dict:
    """端点自报的 token 账（D-11 实读的形状：`total = prompt + completion`）。"""
    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "completion_tokens_details": {"reasoning_tokens": reasoning},
    }


def reply_body(text: str, usage: dict | None = None) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": usage if usage is not None else usage_body(),
    }


def label_body(label: str) -> dict:
    return reply_body(json.dumps({"label": label}, ensure_ascii=False))


class RecordingTransport:
    """按剧本回包，**收到的载荷逐条留痕**。剧本用完之后重复最后一条。"""

    def __init__(self, *bodies: dict) -> None:
        self.bodies = list(bodies) or [label_body("correct")]
        self.payloads: list[dict] = []

    @property
    def calls(self) -> int:
        return len(self.payloads)

    def __call__(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return self.bodies[min(len(self.payloads) - 1, len(self.bodies) - 1)]


def models() -> list[ModelProfile]:
    """一个能力齐全的假档案。能力校验本身归 `tests/routing`，本文件不重复覆盖。"""
    return [
        ModelProfile(
            name="fake-judge",
            capabilities=frozenset({"tool_calling", "long_context", "reasoning", "multi_hop"}),
            is_reasoning_model=True,
        )
    ]


def config() -> LlmConfig:
    """假端点配置。**不读环境变量** —— 判据必须在无凭据的机器上全绿。"""
    return LlmConfig("http://fake-endpoint", "fake-judge", "not-a-real-key")


def judge_row(row: dict, **kwargs):
    """判一行。**读的行键只有 `answer`** —— `label` 只用于事后比对，`reason` 一次都不读。"""
    return judge_one(row["answer"], models=models(), config=config(), **kwargs)


# -- 验收口径 ----------------------------------------------------------------


def meets_acceptance(pairs) -> bool:
    """**plan §6 H2 的那一个口径，全仓只此一处实现。**

    ① 5 条负例**逐条三分类精确匹配**（`run-07` -> `truncated`，其余四条 -> `incomplete`）；
    ② 19 条正例里被判成非 `correct` 的**不超过 2 条**（正例 >= 17/19）。**两条合取。**

    ⚠️ **它是必要条件，不是充分条件。** plan §1.3 已实测：一个两行规则
    （`len<300 -> truncated；否则 '外协' in a`）照样通过它。那件事由 H1c(b) 钉在账上。
    """
    pairs = list(pairs)
    negatives = [(h, j) for h, j in pairs if h != "correct"]
    positives = [(h, j) for h, j in pairs if h == "correct"]
    if len(negatives) != EXPECTED_NEGATIVES or len(positives) != EXPECTED_POSITIVES:
        raise ValueError(
            f"验收口径钉在这份 {EXPECTED_ROWS} 条集子上（{EXPECTED_POSITIVES} 正 / "
            f"{EXPECTED_NEGATIVES} 负），拿到 {len(positives)} 正 / {len(negatives)} 负"
        )
    exact = sum(1 for human, judged in negatives if judged == human)
    kept = sum(1 for _, judged in positives if judged == "correct")
    return exact == EXPECTED_NEGATIVES and kept >= POSITIVE_FLOOR


def meets_legacy_acceptance(pairs) -> bool:
    """**旧口径，只为 H1c 记账**：负例判成"非 `correct`"即算（不要求标签对）+ 正例 >= 17/19。

    留着它不是为了用它验收，是为了让「收紧口径确实挡下了单子串规则」这件事**有判据守着**。
    """
    pairs = list(pairs)
    negatives = [(h, j) for h, j in pairs if h != "correct"]
    positives = [(h, j) for h, j in pairs if h == "correct"]
    if len(negatives) != EXPECTED_NEGATIVES or len(positives) != EXPECTED_POSITIVES:
        raise ValueError("旧口径同样钉在这份集子上")
    caught = sum(1 for _, judged in negatives if judged != "correct")
    kept = sum(1 for _, judged in positives if judged == "correct")
    return caught == EXPECTED_NEGATIVES and kept >= POSITIVE_FLOOR


# -- 假实现与预注册的对抗基线 ------------------------------------------------

CONSTANT_JUDGES = {
    "always-correct": lambda answer: "correct",
    "always-incomplete": lambda answer: "incomplete",
    "always-truncated": lambda answer: "truncated",
}


def _substring_only(answer: str) -> str:
    """H1c (a)：起草期实测出来的那个**一行关键词匹配器**。它发不出 `truncated`。"""
    return "correct" if OVERFIT_KEYWORD in answer else "incomplete"


def _length_plus_substring(answer: str) -> str:
    """H1c (b)：**两行规则**。起草期实测它**通过**收紧后的新口径（负例 5/5 精确、正例 18/19）。

    ⚠️ 它必须原样留在账上 —— 它证明的是「H2 是必要条件，不是充分条件」。
    """
    if len(answer) < 300:
        return "truncated"
    return "correct" if OVERFIT_KEYWORD in answer else "incomplete"


ADVERSARIAL_BASELINES = {
    "substring-only": _substring_only,
    "length-plus-substring": _length_plus_substring,
}

# plan §6 H1c 起草期写死的结论：(基线名) -> (旧口径, 新口径)。执行期只复核，不改。
EXPECTED_BASELINE_OUTCOMES = {
    "substring-only": {"legacy": True, "current": False},
    "length-plus-substring": {"legacy": True, "current": True},
}

# plan §6 H1 的四种假实现 = 三个常量判定器 + 那个一行关键词匹配器。
FAKE_JUDGES = {**CONSTANT_JUDGES, "substring-only": _substring_only}


def pairs_from_rule(rule) -> list[tuple[str, str]]:
    """拿一个 `answer -> label` 的规则跑一遍全集，产出 `(人标签, 判定标签)` 对。"""
    return [(row["label"], rule(row["answer"])) for row in rows()]
