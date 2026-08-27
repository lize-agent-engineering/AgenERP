"""🔴 P2.7 · 术语层：给字段一个中文名字，且能证明它没乱起。

WBS §5 第 107 行那条验收命令打的就是本目录：`pytest tests/i18n -q` 退 0。

## 基线是「零」，不是「少」

活站点导出实读（2026-08-27）：**业务 app 全量 6,350 个字段，label 含中文的 = 0**。
`Item Reorder.warehouse` 的 label 逐字是「**Request for**」——
字段名说的是仓库，标签说的是「请求给」。

## ⚠️ 这套判据的上限，写在最前面

**它验的是「有没有离谱地错」，不是「翻译得好不好」。**

后者没有规则面的判法。而本仓硬约束 ③（D-15）不许把规则能覆盖的事交给模型，
**反过来也成立：不许让模型判自己的产物**。
⇒ 术语层的质量上限由 `test_the_fifteen_terms_that_must_not_be_wrong` 那 15 条决定，
**这个上限是低的，不掩饰。**

能守住的是这几条（全是规则面）：
覆盖率 · **逐条指回真实存在的字段**（硬约束 ④）· 含中文 · 不等于英文原文 · 不等于 fieldname。
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from agenerp.i18n import TERMS_PATH, load_terms
from agenerp.dsl.roles import WORKER_DOCTYPES

CJK = re.compile(r"[一-鿿]")

_SCHEMA_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "dsl/fixtures/site-schema-subset.json"
)
_CHILD_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[1] / "dsl/fixtures/child-tables.json"
)

# 🔴 §2.4 的清单。**在生成之前写死并提交**（`a080f15`），事后不许调。
# 可接受关键词只列**客观词**（数量 / 仓库 / 日期这一类），不含风格判断 ——
# 否则这条判据会变成「我喜不喜欢这个译法」。
MUST_NOT_BE_WRONG = {
    "Item.item_code": ("编码", "编号", "代码", "料号"),
    "Item.item_name": ("名称",),
    "Item.stock_uom": ("单位",),
    "Item.description": ("描述", "说明"),
    "Item.brand": ("品牌",),
    "Work Order.qty": ("数量",),
    "Work Order.produced_qty": ("数量", "产量"),
    "Work Order.status": ("状态",),
    "Work Order.company": ("公司",),
    "Work Order.source_warehouse": ("仓库",),
    "Stock Entry.posting_date": ("日期",),
    "Stock Entry.from_warehouse": ("仓库",),
    "Stock Entry.to_warehouse": ("仓库",),
    "Stock Entry Detail.qty": ("数量",),
    "Stock Entry Detail.uom": ("单位",),
}
MUST_NOT_BE_WRONG_THRESHOLD = 13


@pytest.fixture(scope="module")
def terms() -> dict:
    return load_terms()


@pytest.fixture(scope="module")
def scope_fields() -> dict[str, str]:
    """车间工人覆盖面上的 `(DocType.fieldname) → 英文 label`。

    ⚠️ 来自**活站点导出**（`dump_schema.py` 的产物子集），不是手写的 ——
    与 `tests/dsl/` 那一层同源。
    """
    fields = json.loads(_SCHEMA_FIXTURE.read_text(encoding="utf-8"))["fields"]
    children_raw = json.loads(_CHILD_FIXTURE.read_text(encoding="utf-8"))
    scope = set(WORKER_DOCTYPES)
    for key, child in children_raw.items():
        if key.split(".", 1)[0] in WORKER_DOCTYPES:
            scope.add(child)
    return {
        f"{doctype}.{fieldname}": fieldname
        for doctype, table in fields.items()
        if doctype in scope
        for fieldname in table
    }


# ── T1 · 覆盖率与「指回真实字段」 ────────────────────────────────────────────


def test_the_terms_file_exists_and_declares_where_it_came_from(terms):
    """一份没有出处的术语层与手写的没有区别。"""
    for key in ("generated_by", "generated_on", "model", "scope", "site"):
        assert terms["provenance"].get(key), f"术语层的 provenance 缺 {key}"


def test_every_term_points_at_a_field_that_actually_exists(terms, scope_fields):
    """🔴 硬约束 ④ 用在术语层自己身上。

    一条指不回真实字段的术语是纯粹的噪音：它永远不会被用到，
    却会让「覆盖率」这个数变得好看。**指不回的一律不入库，不是「先留着再说」。**
    """
    strays = [key for key in terms["terms"] if key not in scope_fields]
    assert not strays, f"术语层里有 {len(strays)} 条指不回本轮范围内的真实字段：{strays[:8]}"


def test_the_terms_cover_every_field_in_the_worker_scope(terms, scope_fields):
    """T1 · 覆盖率 = 100%。漏掉的字段在界面上仍然是英文。"""
    missing = sorted(set(scope_fields) - set(terms["terms"]))
    assert not missing, (
        f"车间工人覆盖面 {len(scope_fields)} 个字段里，还有 {len(missing)} 个没有中文名："
        f"{missing[:10]}"
    )


# ── T2 · 规则面的质量下限 ────────────────────────────────────────────────────


def test_almost_every_term_actually_contains_chinese(terms):
    """T2 · ≥ 95% 含中文。

    一条不含中文的「中文名」是这一层完全失效的形态，而它在覆盖率上仍然算数。
    """
    total = len(terms["terms"])
    with_cjk = [k for k, v in terms["terms"].items() if CJK.search(v or "")]
    ratio = len(with_cjk) * 100 / total
    assert ratio >= 95.0, (
        f"只有 {ratio:.1f}% 的术语含中文（{len(with_cjk)}/{total}）；"
        f"不含中文的例子：{sorted(set(terms['terms']) - set(with_cjk))[:8]}"
    )


def test_no_term_is_just_the_english_label_copied_over(terms, scope_fields):
    """抄一遍英文 label 也能拿满覆盖率 —— 那是这一层最省事的假装方式。"""
    english = _english_labels()
    copied = [k for k, v in terms["terms"].items() if english.get(k) and v.strip() == english[k]]
    assert not copied, f"这些术语只是把英文 label 抄了一遍：{copied[:8]}"


def test_no_term_is_just_the_fieldname(terms, scope_fields):
    """抄 fieldname 同理。"""
    copied = [
        key for key, value in terms["terms"].items()
        if scope_fields.get(key) and value.strip() == scope_fields[key]
    ]
    assert not copied, f"这些术语只是把 fieldname 抄了一遍：{copied[:8]}"


def test_no_term_is_empty_or_absurdly_long(terms):
    """空的与长篇大论都不是「标签」。列宽有限，一个 40 字的表头等于没有表头。"""
    bad = {k: v for k, v in terms["terms"].items() if not v.strip() or len(v.strip()) > 20}
    assert not bad, f"这些术语为空或过长：{list(bad.items())[:6]}"


# ── T3 · 🔴 那 15 条不该错的 ─────────────────────────────────────────────────


def test_the_fifteen_terms_that_must_not_be_wrong(terms):
    """🔴 T3 · 决定性的一格。清单与关键词在**生成之前**写死（`a080f15`）。

    ⚠️ **它验的是「有没有离谱地错」，不是「翻译得好不好」** —— 见本模块 docstring。
    这条判据是术语层质量的**上限**，而这个上限低。不掩饰。
    """
    hits, misses = [], []
    for key, acceptable in MUST_NOT_BE_WRONG.items():
        value = (terms["terms"].get(key) or "").strip()
        if any(word in value for word in acceptable):
            hits.append(key)
        else:
            misses.append((key, value, acceptable))
    assert len(hits) >= MUST_NOT_BE_WRONG_THRESHOLD, (
        f"15 条「不该错」的只中了 {len(hits)} 条（要求 ≥ {MUST_NOT_BE_WRONG_THRESHOLD}）。\n"
        + "\n".join(f"  · {k} → 「{v}」，期望含以下任一 {list(a)}" for k, v, a in misses)
    )


def test_the_must_not_be_wrong_list_is_not_quietly_shrinkable(terms, scope_fields):
    """清单本身也要守：条目数与阈值都写死，且每一条都必须指向真实字段。

    没有这一条，「把清单删到只剩 13 条」是让 T3 变绿的最省事办法。
    """
    assert len(MUST_NOT_BE_WRONG) == 15
    assert MUST_NOT_BE_WRONG_THRESHOLD == 13
    for key in MUST_NOT_BE_WRONG:
        assert key in scope_fields, f"清单里的 {key} 不是本轮范围内的真实字段"


# ── 术语层不许悄悄改变「哪些字段被用到」 ─────────────────────────────────────


def test_the_terms_file_is_valid_json_and_lives_where_the_loader_says():
    assert TERMS_PATH.exists(), f"术语层产物不在 {TERMS_PATH}"
    raw = json.loads(TERMS_PATH.read_text(encoding="utf-8"))
    assert set(raw) == {"provenance", "terms"}


def _english_labels() -> dict[str, str]:
    """字段的英文 label —— 从活站点导出的 fixture 里拿，不手写。"""
    path = pathlib.Path(__file__).resolve().parents[1] / "i18n" / "fixtures" / "english-labels.json"
    if not path.exists():
        pytest.fail(
            f"缺 {path} —— 英文 label 必须来自活站点导出，不许手写。"
            "生成方式见 tools/experiments/p2_terminology/"
        )
    return json.loads(path.read_text(encoding="utf-8"))


# ── 一条**执行期补的**判据：Check 字段不许被起成名词 ─────────────────────────


def test_a_checkbox_field_reads_as_a_yes_no_question_not_as_a_noun(terms, scope_fields):
    """🔴 **这条是跑完之后补的，起因写在这里，不掩饰。**

    第一版生成后 T3 报 **15/15 全中**，而术语层里躺着实打实的错：

        Item.has_batch_no  →  「批次号」   ← 它是**勾选框**，含义是「是否批次管理」

    「批次号」是个**名词**，读者会以为那一列填的是批次编号。
    而 T3 没抓到它 —— 因为 `has_batch_no` 压根不在那 15 条里。
    ⇒ **判据绿 ≠ 判据在测它名字说的那件事**，这次发生在我自己刚写的判据上。

    `Check` 是**规则能覆盖**的一类（硬约束 ③）：它的值只有是/否，
    列名就该读成一个是非问句。**这条判据抓的是一整类，不是一个个例。**

    ⚠️ 它仍然守不住「翻译得好不好」（见本模块 docstring）——
    `Item.item_code` 被起成「项目代码」（制造业语境该是**物料**）这类误译，
    规则面抓不到。**上限还是低。**
    """
    checks = _check_fields()
    yes_no = ("是否", "有无", "允许", "启用", "禁用", "已", "需", "可")
    bad = []
    for key in checks:
        value = (terms["terms"].get(key) or "").strip()
        if value and not any(word in value for word in yes_no):
            bad.append((key, value))
    # 阈值：Check 字段里 **≥ 80%** 要读成是非。留 20% 的余量是因为
    # 有些 Check 的中文习惯说法确实是名词（例如「默认」），硬卡 100% 会变成挑刺。
    ok = len(checks) - len(bad)
    ratio = ok * 100 / len(checks) if checks else 100.0
    assert ratio >= 80.0, (
        f"{len(checks)} 个 Check 字段里只有 {ok} 个（{ratio:.1f}%）读成了是非问句。"
        f"\n读成名词的：\n"
        + "\n".join(f"  · {k} → 「{v}」" for k, v in bad[:12])
    )


def _check_fields() -> list[str]:
    """`Check` 类型的字段，从活站点导出的 fixture 里拿。"""
    fields = json.loads(_SCHEMA_FIXTURE.read_text(encoding="utf-8"))["fields"]
    children_raw = json.loads(_CHILD_FIXTURE.read_text(encoding="utf-8"))
    scope = set(WORKER_DOCTYPES)
    for key, child in children_raw.items():
        if key.split(".", 1)[0] in WORKER_DOCTYPES:
            scope.add(child)
    return [
        f"{doctype}.{fieldname}"
        for doctype, table in fields.items()
        if doctype in scope
        for fieldname, fieldtype in table.items()
        if fieldtype == "Check"
    ]


def test_no_term_carries_a_doctype_prefix(terms):
    """**执行期补的第二条**：列名里不许出现单据名前缀。

    起因同样是实测：`Work Order Operation.workstation` 被起成
    「**工单工序.工作站**」—— 模型把单据名一起写进了列名。
    20/317 条如此。它不算「错」（意思是对的），但表头里带一个点号前缀，
    在一张已经写明是哪张单的表格里是纯粹的噪音。

    ⚠️ 这条同样只是**格式**判据。它抓不到译得对不对 —— 见本模块 docstring。
    """
    bad = {k: v for k, v in terms["terms"].items() if "." in v or "。" in v}
    assert not bad, (
        f"{len(bad)} 条列名里带了单据名前缀（或句号）：\n"
        + "\n".join(f"  · {k} → 「{v}」" for k, v in list(bad.items())[:10])
    )


# ── 一个协议，两份配置 ───────────────────────────────────────────────────────


def test_the_generator_never_branches_on_provider_name():
    """🔴 人 2026-08-27 逐字：「**不是不支持本地模型，而是要根据相关的协议可以灵活的配置**」。

    ⇒ 本地与托管**不该是代码里的两条分支**。两边都说 OpenAI 兼容协议
    （Ollama 在 `/v1`，百炼在 `/compatible-mode/v1`），差别只在
    `--base-url` / `--model` / 有没有 key。

    ⚠️ 这条判据是**补的**，起因照实记：我第一版写成了
    `if model.startswith("dashscope:"): ...` —— 那是按 provider 名字分流，
    换端点就要改代码，正是这条指示要消除的形状。

    判法：读生成器源码，**不许出现按 provider 名字分流的写法**，
    也不许把任何一家的地址写死在代码里（默认值除外，且默认值只有一个常量）。
    读的是纸面上的字，比「我保证做到了」硬。
    """
    import pathlib

    src = pathlib.Path(
        "tools/experiments/p2_terminology/generate_terms.py"
    ).read_text(encoding="utf-8")

    # 去掉注释与 docstring 再看 —— 注释里点名这些形状是应该的（教训就写在那儿）。
    import ast

    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            node.value = ""
    code = ast.unparse(tree)

    for shape in ("ollama_chat", "dashscope_chat", "startswith('dashscope"):
        assert shape not in code, f"生成器里还留着按 provider 分流的写法：{shape}"

    # 端点常量只允许有一个默认值，且必须能被命令行 / 环境覆盖。
    # ⚠️ **这三条查的是 `src` 不是 `code`** —— 上面那步把字符串常量全清空了，
    # 而 `"--base-url"` / `"AGENERP_LLM_BASE_URL"` 本身就是字符串常量。
    # 第一版写成查 `code`，判据自己红了一次，红在我身上不在代码上。照实记。
    assert "DEFAULT_BASE_URL" in code, "端点默认值不是一个具名常量"
    assert "--base-url" in src, "端点不可由命令行覆盖 —— 那就不叫灵活配置"
    assert "AGENERP_LLM_BASE_URL" in src, "端点不可由环境变量覆盖"
