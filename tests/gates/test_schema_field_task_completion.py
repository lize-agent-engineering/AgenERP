# 🔴 **本文件是裁判本体（红线 1）。改它一个字都要人批准，提交带
#    `Gates-Change-Approved-By:`。** 落地经过：人 2026-08-28 明确指派
#    （「你来帮我执行命令吧」），源草稿仍留在
#    `tools/experiments/p2_schema_retrieval/GATE-DRAFT-test_schema_retrieval_recall.py.txt`。
#
# 落地时的实测状态（**不是「应该能过」，是真跑过的**）：
#   · 五条 **5 passed**，**8 秒，零 token**
#   · D-26 变异五轮，主判据每一轮都咬得动 ——
#     (M1) 完成率改成 94.9% · (M2) 标成没跑完 · (M3) 靠 infrastructure 排除做数字 ·
#     (M4) 把题换成 loop 自己出的那份 · (M5) 结果文件整个挪走
#     五轮全红，之后 `sha256` 原状恢复。⇒ **它不是空转的绿。**
#   · `check_expected_red.py` 全绿，**不入预期红名单**
#
# ============================================================================
# 🔴 2026-08-27 **整份重写**。上一版判的是 Top-5 命中率 ≥90%，那一版**作废**。
# ============================================================================
#
# 为什么作废 —— 两条，都是实测出来的，不是口味问题：
#
# ① **Top-5 奖励撒网。** 按 `verifier-design` 的「Test the decision boundary」造 fixture：
#      Job Card.a / Job Card.b / Job Card.total_completed_qty / Job Card.c / Job Card.d
#    旧口径判 **Pass** —— 塞满五个候选就能过。而生产要的是 agent **敢承诺一个答案**。
#    人给的生产标准逐字是「**任务完成率 ≥95%**」，不是 Top-5。
#
# ② **上一版判的东西在仓里不存在。** 它要一个 `_build_retriever()`，
#    而现役 `schema_search` 只做名字子串匹配、根本不回字段。
#    改成任务完成率之后，**被判的是 `agenerp/explain/loop.py` + 只读工具面** ——
#    那是真的产品代码，本来就在仓里。⇒ 这一版不再需要任何「尚不存在的东西」。
#
# ============================================================================
# 落之前请先读这五条
# ============================================================================
#
# ① 🔴 **门槛几、n 多少，这两个数只能由人定，我不给。**
#    - WBS 上那个 90% **在仓里找不到任何推导记录**（Spike 07 的原始线是 80%，早已越过）。
#    - 人口述的生产标准是 **≥95%**。
#    - 而 **n=20 判不了 95%**：20/20 的 95% 置信下界只有 **86.1%**，
#      19/20 只有 **78.4%**。要让下界真的压过 95%，需 **n≥60 且零失败**。
#    - 评测集现在只有 **40 条**。
#    ⇒ 门槛与样本量是**同一个决定的两半**，分开定必然自相矛盾。
#
# ② 🔴 **本门禁已改成「不现跑」——理由是实测。**
#    真跑一轮 60 条实测 **634,442 token**（deepseek-v4-pro-0813，无闸）。
#    而 `gates.yml` 的「L2 全量 live 判定」**每次 push 到 main 都跑全部门禁**，
#    判定器**不接受 skip**，本仓也只有 `live` 一个 marker，摘不出去
#    ⇒ **每次 push 烧 63 万，那条路本来就不成立。**
#    ⇒ 主判据改成**核对已落盘的那次测量**（零 token）。
#    ⚠️ **这是一处让步：核记录不等于核现场。** 写在判据文档串里，不藏。
#
# ③ 🔴 **评测集不该长期是我出的那 40 条。** 我在同一份上跑了六轮，
#    每一轮的 miss 都看过。**在自己出的题上拿 100%，恰恰是这个数最不可信的时候。**
#    这条比上面两条都重要，而且**我自己解不了**。
#
# ④ ⚠️ **验证器本体今天住在 `tools/experiments/` 下。**
#    门禁去 import 实验目录是脆的（实验目录本来就该能随便改）。
#    要长期留着这条门禁，得先把验证器搬进 `agenerp/`（或 `tests/support/`）。
#    **这一步我没做** —— 搬家会改产品包的边界，该由人定落点。
#
# ⑤ ⚠️ **判官与被判是同一个模型族**（都 `glm-5.2`），独立性打折。
#    上一轮 20 条里判官只出场 1 次（其余在「可接受集合」层就判完了），
#    影响有限，但**这条限制要一直写在这儿**，不许因为影响小就抹掉。
#
# ============================================================================

"""🔴 门禁 · schema 字段问答的**任务完成率**

判据来源：人口述的生产标准「Agent 的任务完成率要达到 95% 以上才能具备生产的标准」。
✅ **冲突已解**：WBS `02-WBS.md` §5 的 P2.0R 验收格已由人裁定改判
（`DECISIONS.md` D-28，2026-08-27），与本文件一致。旧口径原文以删除线保留在那一格里。

## 它判什么

拿**真实产品路径**（`agenerp/explain/loop.py` + 只读工具面 + 活站点）跑一组中文业务问句，
每条要求 agent **承诺一个字段**，然后验证那个字段。

⚠️ **本门禁不现跑那一轮**（实测一轮 634,442 token，而 L2 job 每次 push 都跑全部门禁）。
它核的是**已落盘的那次测量**是否干净且达标 —— 详见
`test_a_recorded_measurement_backs_the_claim_that_the_bar_was_met` 的文档串。
真要重新量，那里有现成命令。

验证器的三层（重新量时走的就是它）：

| 层 | 判什么 | 依据 |
|---|---|---|
| 1 规则 | 承诺了吗？字段在站点上**真实存在**吗？ | 硬约束 ④ |
| 2 可接受集合 | 命中事先列好的等价答案 ⇒ 过，**不惊动判官** | reference-based |
| 3 判官 | 只判「这个字段是否同样能回答该问题」 | reference-free |

**最后一行给多个字段 ⇒ 判「未承诺」**，不替它挑 —— 那正是 Top-5 放过的那一格。

## 它**不**判什么

- **不判 Top-5、不判召回率。** 见文件头 ①。
- **不判 oracle 上界**（给定 DocType 时的命中率）—— 那不是可交付的东西。
- **不判成本。** 成本是选型偏好，不是判据（同 `capabilities.py` 的摆放规矩）。
  ⚠️ 但成本要**打印出来**：一条 144,949 token 的通过，是通过，也是警报。
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

pytestmark = pytest.mark.live

def _repo_root() -> pathlib.Path:
    """向上找 `pyproject.toml`，**不数目录层数**。

    ⚠️ 数层数（`parents[2]`）只在「文件恰好落在 tests/gates/ 下」时才对。
    草稿阶段在别处跑一遍就会指到仓外，而失败长得像「验证器坏了」——
    实测踩过（2026-08-27）。
    """
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError(f"从 {here} 向上找不到 pyproject.toml —— 不猜仓根")


REPO_ROOT = _repo_root()
EXPERIMENT_DIR = REPO_ROOT / "tools/experiments/p2_schema_retrieval"
# 🔴 **指向独立评测集，不指向 loop 自己出的那份。**
# `eval-set.json`（40 条）是 loop 出的题，且它看过每一轮的 miss ——
# 拿它当裁判量的是「他挑的题他会不会」。人 2026-08-27 给了这一份 60 条。
EVAL_SET = EXPERIMENT_DIR / "eval-set-independent.jsonl"
LOOP_AUTHORED_SET = EXPERIMENT_DIR / "eval-set.json"


def _items(path: pathlib.Path) -> list[dict]:
    """读评测集。`.jsonl` 逐行、`.json` 读 `{"items": [...]}`。"""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)["items"]

# ── 裁判的两个数：出处写死在这里 ──────────────────────────────────────────
#
# 🔴 **一个没有出处的数不该当裁判。** WBS 上那个 90% 在仓里找不到任何推导记录，
#    却被当验收线用了六轮。这里两个数各自的出处逐条写清楚：
#
# `REQUIRED_COMPLETION_RATE = 95.0`
#   出处：**`DECISIONS.md` D-28（人 2026-08-27 正式裁定）** ——
#   「正式的 agent 的任务完成率 ≥95%」。WBS §5 的 P2.0R 验收格已同步改判，
#   原判据 `test_schema_retrieval_recall.py`（Top-5 ≥90%）**作废**。
#   **不是我推的，是被裁定的**；改这个数就是翻 D-28。
#
# `REQUIRED_SAMPLE_SIZE = 60`
#   出处：二项分布算出来的，不是拍的。要让「零失败」的 95% 置信下界压过 95%：
#     n=20 零失败 → 下界 86.1%   ✗
#     n=40 零失败 → 下界 92.8%   ✗   ← 评测集现在恰好就是 40 条
#     n=60 零失败 → 下界 95.1%   ✓   ← 最小的够用值
#     n=100 零失败 → 下界 97.0%
#   算法：Clopper-Pearson 下界，即最大的 p 使 P(X≥n | p) ≥ 0.05。
#
# ⚠️ **这条门禁落下去当天就是红的**，而且红在**评测集只有 40 条**上
#    （第一条判据会说「先补题，别改线」）。**这是对的** ——
#    `tools/gates/expected-red.txt` 存在的意义就是「故意的红」，请同时加进那份名单。
#    🔴 **不许为了让它绿而把 60 改小。** 改小就等于把置信度让掉，
#       而那正是「90% 无出处」那件事的翻版。
REQUIRED_COMPLETION_RATE: float | None = 95.0
REQUIRED_SAMPLE_SIZE: int | None = 60


def _verifier():
    """把验证器请进来。**见文件头 ④：它今天住在实验目录，这是临时的。**"""
    if str(EXPERIMENT_DIR) not in sys.path:
        sys.path.insert(0, str(EXPERIMENT_DIR))
    import task_completion_eval as tce  # noqa: PLC0415

    return tce


def test_the_sample_is_big_enough_for_the_bar_it_claims_to_check():
    """🔴 **先判「这个样本量撑不撑得起这条线」，再判「过没过」。**

    ⚠️ 这不是形式主义。上一版门禁的 90% 在仓里**没有任何推导记录**，
    而它被当验收线用了六轮 —— 一条**量不出自己声称的东西**的门禁，
    比没有门禁更坏：它给人「已经验过了」的错觉。

    n=40 零失败的 95% 置信下界只有 **92.8%**，压不过 95%。
    ⇒ 评测集不到 60 条时，这条门禁**没资格宣布达标**，所以它先红在这里。

    ⚠️ **fail 不是 skip** —— 一条会 skip 的门禁等于一条不存在的门禁。
    """
    assert REQUIRED_COMPLETION_RATE is not None, "门槛没填 —— 见上方出处段"
    assert REQUIRED_SAMPLE_SIZE is not None, "样本量没填 —— 见上方出处段"

    items = _items(EVAL_SET)
    assert len(items) >= REQUIRED_SAMPLE_SIZE, (
        f"评测集只有 {len(items)} 条，撑不起 {REQUIRED_COMPLETION_RATE}% 这条线"
        f"（需 {REQUIRED_SAMPLE_SIZE} 条零失败，下界才压得过）。"
        "⇒ **先补题，别改线。**"
    )


def test_the_verifier_holds_its_own_decision_boundary_before_it_judges_anything():
    """🔴 **验证器自己先过边界测试，再去判别人。**

    两份 fixture 缺一不可，且**必须跑在评测之前**：
      - `test_verifier_boundary.py`：规则层八格（其中一格专测 reward hack ——
        旧的 Top-5 评分器在那一格是**放行**的）
      - `test_judge_boundary.py`：判官层六格，**误放行与假拒两侧都测**

    ⚠️ 这不是走过场：判官层第一次跑，错的那一格是**出题的人**——
    把 `Job Card.for_quantity`（「Qty To Manufacture」= **计划**数量）
    标成了可接受，而问句问的是**完成**了多少。判官判对了。
    """
    import subprocess  # noqa: PLC0415

    for name in ("test_verifier_boundary.py", "test_judge_boundary.py"):
        done = subprocess.run(  # noqa: S603
            [sys.executable, str(EXPERIMENT_DIR / name)],
            capture_output=True, text=True, timeout=900,
        )
        assert done.returncode == 0, (
            f"{name} 没全过 —— **验证器自己就不可信，别拿它去判 agent**。\n"
            f"{done.stdout[-2000:]}\n{done.stderr[-1000:]}"
        )


RESULTS_GLOB = "results-final-*.json"


def _recorded_runs() -> list[tuple[pathlib.Path, dict]]:
    out = []
    for path in sorted(EXPERIMENT_DIR.glob(RESULTS_GLOB)):
        try:
            out.append((path, json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError):
            continue
    return out


def test_a_recorded_measurement_backs_the_claim_that_the_bar_was_met():
    """🔴 **核对「那次测量」确实发生过、而且是干净的。**

    ⚠️ **本条核的是记录，不是现场 —— 这是一处让步，理由写在这儿。**
    原设计是每次都真跑一轮 60 条。实测一轮 **634,442 token**，
    而 `gates.yml` 的「L2 全量 live 判定」**每次 push 到 main 都跑全部门禁**，
    且判定器**不接受 skip**（skip 被当成「有人放松裁判」），本仓也只有 `live`
    一个 marker，没法把它单独摘出去。⇒ **每次 push 烧 63 万，那条路本来就不成立。**
    **弱一点但一直在跑，比强但没人敢开要好。**

    那么它到底还守得住什么？守住**会悄悄烂掉的那几样**：
      · 有人把完成率的说法改了，却**没有任何一次测量**支撑
      · 有人把评测集换成更容易的一份（本条逐题比对，必须是**独立那份**）
      · 有人靠 `infrastructure` 排除把数字做上去（本条要求**排除 0 条**）
      · 有人拿**没跑完**的一轮当全集结论（本条要求 `halted_at` 为空且 n≥60）

    要重新量（改了检索、换了模型、或想复核）：

        python3 tools/experiments/p2_schema_retrieval/task_completion_eval.py \
          --eval tools/experiments/p2_schema_retrieval/eval-set-independent.jsonl \
          --out  tools/experiments/p2_schema_retrieval/results-final-<模型>.json \
          --max-turns 40 --max-tool-calls 0 \
          --per-question-budget 0 --budget 0 --judge-model <模型>

    ⚠️ **一道 token 闸都不设**（上面三个 0）—— 实测教训：设了闸，
    42% 的题会被闸砍掉，而那些失败会**伪装成 agent 能力不足**。
    """
    runs = _recorded_runs()
    assert runs, (
        f"{EXPERIMENT_DIR} 下找不到任何 {RESULTS_GLOB} —— "
        "**没有一次测量支撑那条线**。跑法见本判据的文档串。"
    )

    theirs = {i["q"] for i in _items(EVAL_SET)}
    problems: list[str] = []
    good: list[str] = []

    for path, run in runs:
        detail = run.get("detail") or []
        why: list[str] = []
        if run.get("halted_at"):
            why.append(f"没跑完（停在第 {run['halted_at']} 条）")
        if len(detail) < REQUIRED_SAMPLE_SIZE:
            why.append(f"只跑了 {len(detail)} 条 < {REQUIRED_SAMPLE_SIZE}")
        if run.get("n_infrastructure"):
            why.append(
                f"排除了 {run['n_infrastructure']} 条 infrastructure"
                " —— 靠归类做数字的那条路，这里堵死"
            )
        asked = {d.get("q") for d in detail}
        if not asked <= theirs:
            why.append(
                f"题目不全来自独立评测集（{len(asked - theirs)} 条是别处的）"
                " —— 换成更容易的一份，这里当场红"
            )
        rate = run.get("task_completion_pct")
        if not isinstance(rate, (int, float)) or rate < REQUIRED_COMPLETION_RATE:
            why.append(f"完成率 {rate} < {REQUIRED_COMPLETION_RATE}")
        if why:
            problems.append(f"  · {path.name}：" + "；".join(why))
        else:
            good.append(f"{path.name}（{rate}% · {len(detail)} 条）")

    assert good, (
        f"没有任何一次留档的测量能支撑 ≥{REQUIRED_COMPLETION_RATE}% 这条线：\n"
        + "\n".join(problems)
        + "\n⇒ 要么重新量（跑法见文档串），要么改判据 —— **别改说法**。"
    )
    print(f"\n支撑这条线的测量：{'、'.join(good)}")  # noqa: T201


def test_every_ground_truth_field_really_exists_on_the_site(live_site):
    """硬约束 ④ 用在**评测集自己**身上：ground truth 必须指回**活站点上**真实存在的字段。

    🔴 **为什么这条必须在跑之前**：`expected` 若指向一个站点上不存在的字段，
    验证器第 1 层会把**任何**回答判错 —— 那是一条注定的假拒，
    而且它会**伪装成「agent 能力不足」**。这种错一旦混进分子分母，整轮数就废了。

    ⚠️ **问活站点，不读快照。** 原先这里调 `tce.field_exists()`，
    而那个函数读的是 `/tmp/schema.json` —— 一个**临时文件**。
    门禁依赖 `/tmp` 下的东西，等于依赖「上一次谁跑过什么」。
    出题方也说他们对着自己的快照核过；快照是他们的，**本条独立对活站点再验一遍**。
    做法与 `verify_eval_set.py` 同源（那份是同一件事的命令行形态）。
    """
    from agenerp.site import SiteClient, SiteError

    client = SiteClient(
        os.environ["AGENERP_SITE"], admin_password=os.environ["AGENERP_ADMIN_PASSWORD"]
    )
    cache: dict[str, dict] = {}

    def fields_of(doctype: str) -> dict:
        """DocType 的字段表；DocType 本身不存在时回空 —— 与「字段不存在」区分开报。"""
        if doctype not in cache:
            try:
                meta = client.get(f"/api/resource/DocType/{doctype}").get("data", {})
            except SiteError:
                cache[doctype] = {}
            else:
                cache[doctype] = {
                    f["fieldname"]: f for f in meta.get("fields", []) if f.get("fieldname")
                }
        return cache[doctype]

    missing_doctype, missing_field = [], []
    for item in _items(EVAL_SET):
        # `acceptable` 也要验 —— 它同样会被第 2 层当成「过」的依据，
        # 一个指不回真实字段的可接受答案是一条**误放行**，比假拒更坏。
        for ref in [*item["expected"], *item.get("acceptable", [])]:
            doctype, _, fieldname = ref.partition(".")
            table = fields_of(doctype)
            if not table:
                missing_doctype.append(ref)
            elif fieldname not in table:
                missing_field.append(ref)

    assert not missing_doctype and not missing_field, (
        f"评测集的 ground truth 在活站点上对不上：\n"
        f"  DocType 不存在：{sorted(set(missing_doctype))}\n"
        f"  字段不存在　　：{sorted(set(missing_field))}\n"
        "⇒ **先修题，别跑**：这些条目会变成注定的假拒，并伪装成 agent 能力不足。"
    )


def test_the_eval_set_is_not_recycled_from_the_one_the_judged_wrote():
    """🔴 独立性 —— **能机械判的那一半**。

    ⚠️ 先说清它**判不到**什么：「题不是被判者出的」终究是一条**过程事实**，
    数据面看不出来。本条只抓那个**最会发生的失败形态**：
    换个说法把 loop 自己那 40 条回收一遍，然后声称「独立」。

    过程那一半的出处（**不在断言里，在这儿写着供人复核**）：
    `eval-set-independent.jsonl` 由人 2026-08-27 提供，loop 未参与出题；
    入场核对见 `verify_eval_set.py`（零 token、不调模型，69 个字段引用全部存在）。

    2026-08-27 实测的对照数，写在这儿当基线：
      问句完全相同 **0** 条 · 目标字段重合 **5/60**（55 个是 loop 那份没有的）
      覆盖了 loop 那份完全没碰的域：`hr` / `Employee.*` / `Bank Account` /
      `Batch` / `Customer Credit Limit`
    """
    assert EVAL_SET.name != LOOP_AUTHORED_SET.name, (
        "门禁读的还是 loop 自己出的那份题 —— 那量的是「他挑的题他会不会」"
    )

    theirs = _items(EVAL_SET)
    mine = _items(LOOP_AUTHORED_SET) if LOOP_AUTHORED_SET.exists() else []

    same_q = {i["q"] for i in theirs} & {i["q"] for i in mine}
    assert not same_q, f"独立集里有 {len(same_q)} 条问句与 loop 自己那份逐字相同：{sorted(same_q)[:5]}"

    their_fields = {e for i in theirs for e in i["expected"]}
    my_fields = {e for i in mine for e in i["expected"]}
    fresh = their_fields - my_fields
    # 阈值取一半：**回收一份旧题最省事的做法就是换问法、留答案**，
    # 目标字段几乎全重合正是那个形态。2026-08-27 实测是 55/60，离这条线很远。
    assert len(fresh) >= len(their_fields) / 2, (
        f"独立集的目标字段只有 {len(fresh)}/{len(their_fields)} 是新的 —— "
        "换了问法、留着 loop 那份的答案，那不算独立"
    )
