# 门禁提案 · P3.2 `tests/gates/test_no_commit_in_submit_path.py`

> Status: `proposed`（**提案文本，不是测试代码**）
> Created: 2026-08-29
> 由 plan `~/.claude/plans/p3-swirling-wombat.md` 阶段 B 产出
> 采纳者：**人**。loop 不得据此在 `tests/gates/` 下创建任何文件（`AGENTS.md` 红线 1）

## 为什么需要它

WBS `docs/masterplan/02-WBS.md` 第 143 行把 P3.2 的验收逐字写成
🔴 `tests/gates/test_no_commit_in_submit_path.py`，而 `docs/architecture/module-boundaries.md`
§7.1 要求那三个前提「**必须纳入 CI 回归**」。断言体已经落在红线外：

- `tests/tools/test_rollback_premises_body.py` —— **18 条**（17 离线 + 1 活体），
  2026-08-29 实跑 `18 passed`（活体族命令见下）。

**只有断言体是不够的**，理由与 `tests/gates/test_tool_execution_live.py` 文件头逐字那一条相同：

    无站点时   tests/tools/ → skip（开发期便利）
               tests/gates/ → **fail**（判定器不接受 skip，未跑就是红）

一条会 skip 的判据在没有站点的环境里是绿的 ——「我检查了，全过」与「我根本没看」
又一次在退出码上长得一样，那正是 CP9 继承项①要挡的形状。

## 建议的落地形态

**照抄 `tests/gates/test_tool_execution_live.py` 的两件事，不要重写断言**：
① 按路径加载断言体；② 把「跑不了」的出口收严成 `fail`。

断言体已经为此准备好了一个**单一出口**：模块级函数 `_unavailable(reason)`
（默认 `pytest.skip`）。所有跑不了的分支都只调它，因此加载器**只需重绑这一个名字**。

⚠️ **重绑的是断言体模块自己的属性，不是 `pytest` 模块的属性。**
`_BODY.pytest.skip = pytest.fail` 那种写法改的是**全局 `pytest` 模块**，属进程级污染
（出处：`docs/analysis/2026-08-25-1743-desk-sidebar-probe.md:298`）。

### 建议全文

```python
"""🔴 P3.2 门禁 · 回滚前提：§7.1 那三个前提在活站点上仍然成立。

判据来源（WBS `02-WBS.md` §6 第 P3.2 行，逐字）：

    🔴 `tests/gates/test_no_commit_in_submit_path.py`

**本文件与 `tests/tools/test_rollback_premises_body.py` 的关系**：后者是同一套断言的
开发期形态，由 P3.2 的实现者写在红线外，并在文件里指名「提升进 gates 需要人操作」。
本文件就是人做的那一半 —— **断言逻辑复用，语义只改一处**：无站点时那边 skip，这边 fail。

⚠️ 断言强度不因为换了路径而改变。本文件不重写断言，直接按路径加载开发期那份；
若那边被改弱，这边同步变弱 —— 这是有意的：判据只有一份，不许出现
「门禁版」与「开发版」两套标准。
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_BODY_PATH = "tests/tools/test_rollback_premises_body.py"


def _load_sibling_module(relative_path: str, module_name: str):
    """按路径加载仓内另一个测试模块。找不到就**抛**，不静默降级。"""
    target = _REPO_ROOT / relative_path
    if not target.is_file():
        raise FileNotFoundError(
            f"回滚前提门禁依赖 {relative_path}，但它不存在。"
            "判据的断言逻辑只有一份，源文件没了就是红，不是少跑几条。"
        )
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BODY = _load_sibling_module(_BODY_PATH, "_p3_2_rollback_premises")

# 🔴 **唯一的语义改动**：把断言体的「跑不了」出口收严成 fail。
# 重绑的是 `_BODY` 自己的属性，不是 `pytest.skip` —— 后者是进程级污染。
_BODY._unavailable = pytest.fail

pytestmark = pytest.mark.live


def _premises():
    return _BODY._load(_BODY.PREMISES_JSON)["measurement"]


def test_the_instrument_can_count():
    """阳性对照先跑：前提 1/2 的真值都是 0，仪器瞎了的话那两个 0 不含信息。"""
    _BODY.test_the_instrument_can_count(_premises())


def test_our_channel_cannot_reach_a_savepoint():
    """前提 0 · 两条腿：跨连接够不着 + POST 在响应返回前就 commit。"""
    premises = _premises()
    _BODY.test_premise_0_a_savepoint_does_not_survive_across_connections(premises)
    _BODY.test_premise_0_b_a_post_is_committed_before_the_response_returns(premises)


@pytest.mark.parametrize("scenario", _BODY.SCENARIOS)
def test_the_submit_path_neither_commits_nor_enqueues(scenario):
    premises = _premises()
    _BODY.test_premise_1_the_submit_path_does_not_commit(premises, scenario)
    _BODY.test_premise_2_the_submit_path_does_not_enqueue(premises, scenario)
    _BODY.test_premise_3_no_irreversible_side_effect_escapes_the_transaction(premises, scenario)
    _BODY.test_savepoint_rollback_restores_every_counter(premises, scenario)


def test_backdating_creates_a_work_item_for_an_async_consumer():
    _BODY.test_backdating_creates_a_work_item_for_an_async_consumer(_premises())


def test_the_four_before_submit_hooks_the_wbs_names_do_not_exist_here():
    _BODY.test_no_doctype_has_the_four_before_submit_hooks_the_wbs_names(_premises())


def test_the_defences_that_make_the_measurement_trustworthy_held():
    """三层防线里可判的两层：指纹会咬人 · 探测没污染站点。"""
    _BODY.test_the_site_fingerprint_has_teeth(_BODY._load(_BODY.MUTATION_JSON))
    _BODY.test_the_probe_left_the_site_identical(_premises())


def test_hypotheses_were_frozen_before_the_result_landed():
    _BODY.test_hypotheses_were_frozen_before_the_result_landed()
    _BODY.test_the_hypotheses_say_which_predictions_were_not_blind()


def test_live_the_three_premises_still_hold_today():
    """**当场重跑探测**，不只钉住 2026-08-29 那份 JSON。

    三个前提是 ERPNext 的实现细节、不是承诺（§7.1 原话）——
    只钉历史的话，升一次镜像它照样绿而站点上的语义已经变了。
    """
    _BODY.test_live_the_three_premises_still_hold_today()
```

### 上面那段**已经实跑过**，是逐字可用的

loop 不能把它放进 `tests/gates/`（红线 1），但可以证明它不是纸上谈兵：
2026-08-29 把它从本文件里抽出来、临时落在 `tests/tools/test_zzz_gate_shell_smoke.py`
（**同样的目录深度**，`parents[2]` 因此解析到同一个仓根），跑完即删。

| 场景 | 命令 | 实得 |
|---|---|---|
| 有站点 | `AGENERP_LIVE=1 AGENERP_SITE=frontend … pytest <壳> -q` | **9 passed** |
| **无站点** | `env -u AGENERP_SITE -u AGENERP_LIVE pytest <壳> -q` | **1 failed, 8 passed** —— `E Failed: 没有活站点：…` |
| 无站点 · **断言体那边** | `env -u AGENERP_SITE -u AGENERP_LIVE pytest tests/tools/test_rollback_premises_body.py -q -rs` | **17 passed, 1 skipped** |

⇒ 后两行就是这份提案存在的**全部理由**：同一套断言，同一个无站点环境，
`tests/tools/` 那边 **skip**、门禁那边 **fail**。`_BODY._unavailable = pytest.fail`
那一行是唯一的语义改动，且它**确实起作用**。

## 落地时人要做的三件

1. 把上面那段存成 `tests/gates/test_no_commit_in_submit_path.py`，
   提交带 **`Gates-Change-Approved-By:`** trailer。
2. 决定它进不进 `tools/gates/expected-red.txt`。
   **建议：不进。** 本机实测它是**绿**的（下面有命令与退出码），
   而名单只能变短 —— 加一条本来就绿的进去，等于给账本添一条假红。
   ⚠️ 但它是 `live` 标记：**默认判定环境没有 `AGENERP_LIVE`，那里它会被 deselect**。
   `check_expected_red.py` 默认注入 `-m "not live"`，所以它在默认判定面上一条都不跑 ——
   这与 `tests/render` / `tests/ui` 的处境同形，接进哪个 job 归人。
3. 若把它接进 CI，`.github/workflows/gates.yml` 归人（红线 2）。
   它要活站点 **+ 种子数据已装载**，形态最接近既有的 **`gates-l2-seed`** job。

## 🔴 §7.26 的 ci-coverage 表：本提案**不撞**它

`tests/tools` 与 `tests/gates` 两个目录**都已经在那张表里**，本提案不新增测试目录。
（会撞的是 P3.4 的 `tests/approval/` 与 P3.6 的 `tests/memory/`，那是后话。）

## 变异验证已做，实得值在这里

plan 原定的变异是「把打桩计数改成恒 0 → 判据必须红」。**那条变异本身咬不动**，
因为前提 1/2 的真值就是 0，被致盲的仪器与真值同形。2026-08-29 实跑对照：

| | `selftest_commit` | `premise_1` | `premise_2` | `counter_drift` |
|---|---|---|---|---|
| 诚实 | **1** | `[0, 0]` | `[0, 0]` | `[{}, {}]` |
| 致盲 | **0** | `[0, 0]` | `[0, 0]` | `[{}, {}]` |

⇒ 前提 1/2/drift 三个面上**两者完全同形**。因此探针补了阳性对照
（`tools/experiments/p3_rollback/payload.py::_instrument_selftest`），
判据断它必须为 1。致盲后复跑当场红：

    AssertionError: 阳性对照没记到 —— 仪器是瞎的，下面的 0 不含信息
    assert 0 == 1

还原后 `18 passed`。**采纳本提案时请连这一条一起读** ——
`test_the_instrument_can_count` 不是装饰，它是这套判据唯一的牙齿来源。

## 复跑命令与实得退出码（2026-08-29）

离线族：

```bash
python3 -m pytest tests/tools/test_rollback_premises_body.py -q -m "not live"
```

→ `17 passed, 1 deselected`，exit 0。

活体族（需活站点 + 已装载种子数据）：

```bash
AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/tools/test_rollback_premises_body.py -q
```

→ `18 passed`，exit 0。
