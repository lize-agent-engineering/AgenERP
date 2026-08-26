# 2026-08-26-1728-1 `route()` 必须尊重配置里的模型名 —— 静默换模型的那条路堵死

> Plan Status: completed
> Last Reviewed: 2026-08-26
> Mission: p1-insight
> Work Item: 3b. **`route()` 静默换模型 —— 配置的 `AGENERP_LLM_MODEL` 被忽略**（`docs/masterplan/02-WBS.md:81` 的 `P1.1-fix` 行；人 2026-08-26 在 `433d2ca` 从工作项 3 拆出）—— **本 plan 是它的第 1 个 plan**。
> ⚠️ **plan 预算独立计，不占工作项 3 的额度**（`docs/backlog/p1-insight-roadmap.md` 工作项 3b 逐字如此；同 `P1.8a-fix` / 工作项 10b 先例）。
> ⚠️ **起草期写的「工作项 3 的第 2 个 plan、用掉表规 3 的最后一格」是错记，评审期查实改准** —— 那会凭空吃掉工作项 3 的预算格，并把收口记录落到错误的 WBS 行上。
> Source: 人 2026-08-26 `433d2ca` 的裁定「做」，落成 `02-WBS.md:81` 的 `P1.1-fix` 行（**验收逐字**：`tests/unit/test_configured_model_is_the_one_used.py` **补一条不传 `requested` 的用例并绿**；该 commit 正文逐字「**只让现有用例继续绿不算达标**」）· 起草期实读 + 实跑复现的活缺陷（见 `## Current Baseline` 的复现原文）；缺陷的第一次现场记录在 `agenerp/serve/app.py:246-256` 的注释里（2026-08-26 人侧实测）
> Related: `docs/plans/p1-insight/2026-08-24-1457-1-model-routing-v0.md`（**工作项 3** 的第 1 个 plan —— 本缺陷就是它交付后才发现的，本 plan 不回退它的 `done`）· `docs/plans/p1-insight/2026-08-26-1618-1-doc-links-child-host-guard.md`（同一类失败形态：修法只落在一半的站点调用上）
> Audit: required

## Current Baseline

**以下每一条都是起草期在 `0033c7b` 的干净工作树上实跑/实读得到的，不是从旧 plan 抄的。**
⚠️ **起草期为量代价施加过一次可复原的临时补丁，收尾已复原**：`git status --porcelain` → 无输出。
执行者**不得采信下面的数字**，必须自己重跑一遍（数字对不上就是基线变了，先停下来记，不要改断言去凑）。

### B0 · ⚠️ 起草基线已漂移 —— 评审期（`433d2ca`）重测的数字，以本节为准

起草基线 `0033c7b` 之后人落了三个 commit（`f68ae19` / `4f3b488` / `433d2ca`），**动了本 plan 引用的两组数**。
评审期在 `433d2ca` 的干净工作树上**原样重跑**，逐字记：

| 量 | 起草期（`0033c7b`） | 评审期实测（`433d2ca`） | 成因 |
|---|---|---|---|
| `python3 tools/gates/check_expected_red.py` | `门禁 28 项：预期红 0，绿 28，跳过 0` | **`门禁 29 项：预期红 0，绿 29，跳过 0`** | `f68ae19` 新增门禁 `tests/gates/test_assertions_have_no_escape_hatch.py` |
| 六目录 `pytest -q -m "not live"` | `1293 passed, 23 skipped, 7 deselected` | **`1299 passed, 23 skipped, 7 deselected`** | `f68ae19` 新增 `tests/unit/test_configured_model_is_the_one_used.py`（6 条，见 B8） |
| `python3 -m pytest tests/routing -q` | `170 passed, 1 skipped` | **`170 passed, 1 skipped`（逐字未变）** | `tests/routing/**` 未被那三个 commit 触及 ⇒ **B5 的代价实测仍然有效** |

⇒ **Phase 3 的 Exit Criteria 已按 `29` / `1299` 改准**，起草期那两个数**不再是判据**。
执行者仍须自己重跑；**若再对不上，就是基线又漂了 —— 停下来记，不许改断言去凑**。

### B1 · 缺陷本体：`route()` 把 `config.model` 丢掉了，且丢得无声

`agenerp/routing/router.py:75-80` 逐字：

```python
    for profile in candidates:
        if profile.satisfies(task_class):
            resolved = config if config is not None else config_from_env()
            return ChatAdapter(
                resolved, model=profile.name, profile=profile, transport=transport
            )
```

`resolved` 里带着 `config.model`（= `AGENERP_LLM_MODEL`），但 `model=profile.name` 把它**整个盖掉**。
`agenerp/routing/adapter.py:128` 是 `self.model = model or config.model` —— `model` 恒非空，
所以 `config.model` 那一支**在走 `route()` 的路径上永远不会被取到**。

**复现原文（零网络，`transport` 是假的）**：

```
python3 - <<'PY'
from agenerp.routing.capabilities import KNOWN_MODEL_PROFILES
from agenerp.routing.config import LlmConfig
from agenerp.routing.router import route
cfg = LlmConfig(base_url="https://x/v1", model="qwen3:14b", api_key="k")
a = route("explain", models=KNOWN_MODEL_PROFILES, config=cfg, transport=lambda p: {})
print("config.model =", cfg.model, "| adapter.model =", a.model)
PY
```

**实测输出**：`config.model = qwen3:14b | adapter.model = qwen3.8-max` ⇒ **配了 A，调的是 B，没有任何一处说话。**

### B2 · 这不是理论风险，它已经在活栈上发生过一次

`agenerp/serve/app.py:246-256` 是人在 2026-08-26 写下的现场记录（本 plan 一个字不改它，只引）：

> 2026-08-26 实测：不传 `requested` 时 `route()` 取的是「第一个满足该任务类目的档案」，用的是 `profile.name`
> ——**配置里的模型名被完全忽略**。实测配 `qwen3.7-flash`、实际走 `qwen3.8-max`，而后者没有免费额度
> ⇒ 每一次解释都 403，用户却只看到一个空答案。

处置形态是**在那一个调用点上补 `requested=config.model`**（`app.py:257`）。
⚠️ **这与 `doc.links` 子表守卫那次是同一个失败形态**：修法落在**一个**站点调用上，
契约本身没变 ⇒ 下一个调用方照样会踩。

### B3 · 调用面盘点（`grep -rn "route(" agenerp/ tools/ tests/` 实点，不是估计）

| 调用点 | 传 `requested` 吗 | 今天的后果 |
|---|---|---|
| `agenerp/serve/app.py:257` → `explain()` | **传**（`requested=config.model`，B2 的补丁） | 对 —— 但对得靠调用方记得 |
| `agenerp/explain/loop.py:664` `explain()` → `route()` | 转手调用方给的，默认 `None` | 调用方不给就静默换模型 |
| `agenerp/judging/judge.py:73` `judge_one()` → `route()` | 转手调用方给的，默认 `None` | 同上 |
| `agenerp/insight/attribution.py:139` → `explain()` | 转手调用方给的，默认 `None` | 同上 |
| `tools/experiments/p1_insight_live/run.py:206,386` | 传（写死常量 `JUDGE_MODEL` / `ATTRIBUTION_MODEL`） | 对 —— 但绕开了 `AGENERP_LLM_MODEL` |
| `tools/experiments/p1_answer_judge/run.py:76` | 传（写死 `JUDGE_MODEL`） | 同上 |
| `tests/routing/test_live_endpoint.py:67` | **不传**，但调用方自己先 `KNOWN_MODEL_PROFILES.get(live_config.model)` 把候选集缩成一个，再断言 `adapter.model == live_config.model` | **这就是本 plan 要写进 `route()` 的语义** —— 今天它只存在于一个测试文件的调用方手工步骤里 |

⇒ **正确语义已经被人写出来过（`test_live_endpoint.py:50-67`），只是没有写进 `route()`。**

### B4 · owner doc 漂移（指南第 14 条：确认的 owner-doc 漂移不可降级）

`docs/architecture/model-management.md` §12.5 末尾那张环境变量表逐字：

| 变量 | 用途 |
|---|---|
| `AGENERP_LLM_MODEL` | 默认模型名 |

同节「摆放规矩」第 2 条也逐字写着「端点 / 凭据 / **默认模型名**全部从 `AGENERP_LLM_*` 环境变量来」。
**文档说它是默认模型名，代码在走 `route()` 的路径上从不使用它。** 两者必须对齐一处。

⚠️ **`router.py` 模块头第 13 行另有一句「候选顺序 = 调用方的偏好顺序，第一个满足的胜出」** ——
它与 B4 的 owner doc 说法**在 `config.model` 非空时直接冲突**。本 plan 的 `D-1` 就是裁这一格。

### B5 · 起草期实测的改动代价（执行者必须自己复跑，不许采信）

在**可复原的临时补丁**下实跑（补丁已复原，工作树干净）：

- 只改 `route()`（让 `requested is None` 时取 `config.model`）：
  `python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"`
  → **`15 failed, 1278 passed, 23 skipped, 7 deselected`**。
  **15 条全部在 `tests/routing/test_router.py`，其余五个目录 0 条红。**
- 15 条红的**唯一**成因是该文件第 26 行的夹具 `CONFIG = LlmConfig(base_url=..., model="unused", api_key=...)`
  —— 那个 `"unused"` 字面量**本身就是「`config.model` 反正会被忽略」这个缺陷的编码**。
- 把该字面量改成 `model=""`（空 ⇒ 不点名 ⇒ 「第一个满足的胜出」那条路径原样保留）后：
  `python3 -m pytest tests/routing -q` → **`170 passed, 1 skipped`**，
  **一条既有断言未改、未删、未放松**，只动了一个夹具字面量。
- 同一补丁下 `python3 tools/gates/check_expected_red.py` → **exit 0**（`门禁 28 项：预期红 0，绿 28，跳过 0`）；
  六目录合跑 → **`1293 passed, 23 skipped, 7 deselected`**。
  ⚠️ **这两个数已被 B0 的漂移取代**（今天是 `29` / `1299`）——本条按「起草期原文」保留，**不作为 Exit Criteria**。
  本条仍然成立的那一半是**代价的形状**：红只落在 `tests/routing/test_router.py`，其余目录 0 条红
  （`tests/routing` 评审期实测逐字未变 ⇒ 该结论未被漂移动摇）。

### B6 · 红线面（起草期实读，执行前必须复核）

- `grep -rn "route(\|LlmConfig\|config=" tests/gates/*.py` → **只有 3 行命中，全在 `test_agent_seam_stays_swappable.py` 的注释与失败文案里**，
  没有任何一条门禁构造 `LlmConfig` 或调 `route()` ⇒ 本 plan 的改动**不需要碰 `tests/gates/**`**（红线 1）。
- `tests/gates/test_agent_seam_stays_swappable.py:103` 只禁「在 `agenerp/routing/` 之外直接构造 `ChatAdapter`」，
  本 plan 的改动全在 `route()` 体内 ⇒ 该门禁不受影响。
- `tests/routing/test_adapter.py:526` 断言 `routing.__all__` **逐字等于六元组** ⇒
  本 plan **不得新增任何导出名**（新增就要改那条断言，那会长得像放松判据）。
- ⚠️ **评审期新增的一条约束（起草期不存在）**：`tests/gates/test_assertions_have_no_escape_hatch.py`（`f68ae19`）
  **扫 `tests/` 下每一条 `assert`**，拦「`or` 的某一侧是失败态」的写法
  （`is False` / `is None` / `== []` / `== {}` / `== ""`）。本 plan Phase 2 要新写 7–9 条断言，
  **全部落在它的扫描面内** ⇒ 新断言一律**一条只测一件事**，不许用 `or` 兜底；
  确需豁免的写 `# assert-escape-ok: <理由>`（**空豁免它自己也拦**）。
  ⚠️ 它在 `tests/gates/**` 内 ⇒ **只读，红线 1**；本 plan 是**服从**它，不是碰它。

### B7 · 仍然缺的那一格（本 plan 不补，见 `## Deferred But Adjudicated` D1）

`AGENERP_LLM_MODEL` 配了一个系统不认识的名字时，`handle_explain` 回的是 **502**（「上游坏了」），
不是 **503**（「未配置」）——与 `agenerp/serve/app.py:239-242` 自己写死的结构性分法冲突。
**起草期实测**：伪造 `config_factory` 回 `model="typo-model"` → `ServiceError.status = 502`，
文本是 `点名的模型 'typo-model' 不在候选档案里；候选是 [...]`。
**修法面在 `agenerp/serve/**` = 工作项 10（P1.8a），其 plan 预算 `2/2` 已满** ⇒ 本 plan 不动它。

### B8 · **WBS 那一行的验收判据落在另一个文件上** —— 起草期整份 plan 零处覆盖

`02-WBS.md:81` 的 `P1.1-fix` 行、验收列逐字：

> 🔴 `tests/unit/test_configured_model_is_the_one_used.py` 补一条**不传 `requested`** 的用例并绿
> —— **今天那份判据绿是因为它显式传了 `requested`，那不是缺口所在**

`433d2ca` 的 commit 正文另有一句逐字：「**只让现有用例继续绿不算达标。**」

**评审期实读该文件**（`f68ae19` 新增，71 行，评审期实测 `6 passed`）：

- `test_the_model_actually_used_is_the_one_configured`：`@pytest.mark.parametrize` 遍历
  `KNOWN_MODEL_PROFILES` 里所有 `satisfies("explain")` 的档案，**每一条都显式传 `requested=model`**
  ⇒ **它走的是 `requested` 分支，压根没经过本缺陷所在的那条路**。
- `test_an_unknown_model_fails_loudly_instead_of_silently_swapping`：同样**显式传 `requested`**。

⇒ **这份文件今天全绿，而缺陷全须全尾地活着。** 这正是人写「只让现有用例继续绿不算达标」的原因。
⇒ **本 plan 必须往这份文件里补不传 `requested` 的用例**（Phase 2 的 `P8` / `P9`），
否则 Phase 1 的实现改对了、`tests/routing` 也全绿，**WBS 那一行的验收仍然不成立**。

⚠️ 该文件在 `tests/unit/**`，**不在 `tests/gates/**` 内** ⇒ 往里加用例**不触红线 1**；
但**既有 6 条一条不许改、不许弱化**（`433d2ca` 逐字「点名不认识的模型仍必须明确失败……别改弱它」）。

## Goals

1. **`route()` 在 `requested is None` 时必须使用 `config.model`**（`config` 显式给的或 `from_env()` 读的都算），
   用不了就**按名失败**，绝不换一个跑。
2. **「配了 A 调了 B」这条路在代码上不存在** —— 不是靠每个调用方记得传 `requested`。
3. **owner doc 与代码对齐一处**：`model-management.md` §12.5 的「默认模型名」从今天起是真的。
4. **既有 170 条 `tests/routing` 判据一条不放松**，改动代价局限在一个夹具字面量上，并有独立判据钉住新语义。
4b. **WBS `P1.1-fix` 行的验收逐字成立**：`tests/unit/test_configured_model_is_the_one_used.py`
   **多出至少一条不传 `requested` 的用例并绿**，且既有 6 条一条未改、未弱化（B8）。
5. 落点节 `docs/architecture/module-boundaries.md` **§7.25**（新增），`§7.13`–`§7.24` 一行不改。

## Non-Goals

1. **不改 `tests/gates/**` 任何文件**（红线 1）。
2. **不改 `.github/workflows/**`**（红线 2）、不改 `DECISIONS.md` / `02-WBS.md`（红线 3/5）。
3. **不改 `agenerp/serve/**`** —— 包括不删 `app.py:257` 那句 `requested=config.model`（改完之后它成了冗余但**正确且无害**的显式点名），也**不修 B7 的 502/503**（工作项 10 预算已满）。
4. **不动 `KNOWN_MODEL_PROFILES` 的任何一格能力取值**（§12.5 逐字「改能力声明归工作项 3，不在本格」指的是那张表的内容争议，归人）。
5. **不新增导出名**（B6 第三条）、不新增异常类型。
6. **不做模型可用性探测 / 不做额度检查** —— B2 里那次 403 的直接触发因素是「没有免费额度」，
   本 plan 只堵「换了模型」这一格，**不声称能挡住「配对了模型但没额度」**。

## Task Route

- Type: `implementation-only change`（含一处 `Decision`）
- Owner Docs: `docs/architecture/model-management.md` §12.5 · `docs/architecture/module-boundaries.md`（新增 §7.25）
- Skill Selection Basis: `none` —— 本仓 `docs/skills/` 里没有覆盖「改一个纯函数的选择语义 + 变异自查」的技能；工作方法由本 plan 的 Phase 3 变异表自己写死。

## Infrastructure And Config Prereqs

No infra prereqs beyond existing baseline —— 全部判据零网络、零站点、零 docker、零 LLM 凭据。
`tests/routing/test_live_endpoint.py` 是 `-m live` 的，本 plan **不要求**跑它（见 Phase 3 的 `verification scope limited`）。

## Execution Plan

### Phase 1 — 裁定语义，并把它写进 `route()`

Status: completed
Targets: `agenerp/routing/router.py`
Skill: `none`

- Item Types: `Decision | Fix`
- Prereqs: 无

- [x] **`Decision` D-1：`requested is None` 时 `config.model` 的地位。**
      选定 **(A)**：`config.model` 去掉首尾空白后**非空即等同于 `requested`** ——
      先按名从候选里取档案（取不到 → 沿用既有的「不在候选档案里」按名抛），
      再拿它过**同一条**能力校验（`profile.satisfies(task_class)`）。
      **备选与否决理由（逐条写死，不许事后补）**：
      - **(B) 保留「第一个满足的胜出」，但选中的 `profile.name` 与 `config.model` 不同时抛。**
        **否决** —— 成功面上仍然没有「配了 X 就用 X」这条规则；且候选集
        `[qwen-plus, qwen3.6-plus]` + `config.model=qwen3.6-plus` + `explain` 这种
        **完全合法**的配置会被它判红。那是把「静默替换」换成了「误报」，不是修好。
      - **(C) 不动 `route()`，要求每个调用方自己点名。**
        **否决** —— 它**已经被忘过一次**，后果逐字记在 `agenerp/serve/app.py:246-256`
        （活栈上每次解释 403、用户只看到空答案）。把正确性寄托在「每个调用方都记得」
        上，正是本缺陷的成因；B3 的表里今天还有三个默认 `None` 的转手调用点。
      - **(D) 在 `config.py` 的 `from_env()` 里校验模型名。**
        **否决** —— 会让 `agenerp/routing/config.py` import `capabilities`，
        而 §12.5 的落地形态表逐字给 `config.py` 的职责是「三个 `AGENERP_LLM_*` 从环境读，零默认值」、
        给 `capabilities.py` 的是「不做任何调用，不读环境」。为了顺带修 B7 的 502/503
        去掉换这两层的依赖方向，代价与收益不成比例（且 B7 的处置权不在本工作项）。
      **残余风险（照实登记，不修饰）**：选 (A) 之后，`router.py` 模块头第 13 行那句
      「候选顺序 = 调用方的偏好顺序，第一个满足的胜出」**只在 `config.model` 为空串时还成立**；
      而 `from_env()` 保证它非空 ⇒ **环境驱动的路径上，候选偏好顺序事实上失效**。
      这一句必须同时改准（本 Phase）并写进 §7.25 与 §12.5，**不许留在模块头里当一句已不成立的话**。
- [x] `Fix`：`route()` 体内把 `config` 的解析**上提到挑档案之前**（今天它在 `for` 循环体内，
      `router.py:77`），得到 `resolved_config`；`requested is None` 时用 `(resolved_config.model or "").strip() or None` 顶上。
      ⚠️ **上提会改变一件事，必须自己实测确认而不是推断**：`config is None` 且环境没配时，
      `RoutingError("配置不全…")` 现在**在能力校验之前**抛。既有判据
      `test_route_falls_back_to_env_config_only_when_no_config_is_given`
      （`tests/routing/test_router.py:178-183`）用的是 `models=[STRONG]` + `explain`（本来就满足）
      ⇒ 起草期实测**它不红**；但「不满足能力 + 环境也没配」这种双错情形下**报的错换了一个**，
      属行为变化，写进 §7.25，**不假装没变**。
- [x] `Fix`：`router.py` 模块头第 13 行那句「第一个满足的胜出」改准为带前提的说法
      （逐字前提：`config.model` 为空时才成立），并在 `route()` 的 docstring 里点名 `config.model` 的新地位。

Exit Criteria:

- [x] B1 的复现脚本原样重跑，输出变成 `config.model = qwen3:14b | adapter.model = qwen3:14b`（两边相等）
- [x] `agenerp/routing/__init__.py` 的 `__all__` **逐字未变**（B6 第三条），`git diff` 对该文件无输出
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0（**逐字抄 `gates.yml:682`**）
- [x] 相关 owner doc 更新留到 Phase 2；本 Phase 只改 `router.py` 自己的模块头与 docstring

### Phase 2 — 判据：既有 170 条一条不放松，新语义单独钉，**WBS 验收那条钉在它自己的文件上**

Status: completed
Targets: `tests/routing/test_router.py` · `tests/unit/test_configured_model_is_the_one_used.py`（**WBS 验收面，只增不改**，见 B8）
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 1

- [x] `Proof` P1（夹具）：`tests/routing/test_router.py:26` 的 `CONFIG` 把 `model="unused"` 改成 `model=""`。
      **只改这一个字面量。** 改动理由写在该行上方的注释里，逐字说明：
      `"unused"` 编码的是「`config.model` 反正会被忽略」这个**缺陷本身**，
      改成 `""` 之后「不点名」这条路径的全部既有判据**原样继续有效**。
      ⚠️ **收口时必须能证明「一条断言都没动」**：
      `git diff -- tests/routing/test_router.py | grep -c '^-[^-]'` **实测 `2`**
      （起草期写死的是 `1`「就是那一行夹具」—— **该预期是过期数，按实测改准，原文留痕于此**）。
      两行删除逐字为：夹具行 `CONFIG = LlmConfig(...model="unused"...)` + import 行
      `from agenerp.routing.config import LlmConfig`（P7 需要 `from_env`，起草期没预见到这一行会动）。
      ⇒ **无断言行**，判据要证的实质（既有断言零删改）成立。见本 Phase Exit Criteria 同名那条。
- [x] `Proof` P2（新语义 · 成功面）：`config.model` 点名一个**满足**该类目的候选 ⇒ `adapter.model == config.model`，
      **且它不是候选集里第一个满足的那个**（否则「第一个胜出」的旧实现也能蒙混过去）。
      用例至少两组：`models=[STRONG, WEAK]` + `config.model="qwen-plus"` + `explain`；
      `models=KNOWN_MODEL_PROFILES`（映射形态）+ `config.model="qwen3:14b"` + `explain`。
- [x] `Proof` P3（新语义 · 失败面之一）：`config.model` 点名一个**不在候选里**的名字 ⇒ 抛，
      且**文本里含那个名字**（`match="不在候选档案里"` + `assert name in str(exc)`）。
      只断「抛了」不够 —— 一个「永远抛」的假实现同样全绿（该文件模块头第 3 行逐字如此要求）。
- [x] `Proof` P4（新语义 · 失败面之二）：`config.model` 点名一个**在候选里但能力不够**的模型 ⇒ 抛，
      **且不回落到候选集里那个够格的强模型**（`models=[LOCAL, STRONG]` + `config.model="qwen3:14b"` + `lineage`）。
      这是 §12.1 ③「绝不静默降级」在新路径上的反测。
- [x] `Proof` P5（`requested` 优先级）：`requested` 与 `config.model` **同时给且不同**时，
      **`requested` 胜出**（显式点名压过默认值）。逐字写进 §7.25，不留给读者猜。
- [x] `Proof` P6（空模型名保留旧路径）：`config.model == ""` 时仍走「第一个满足的胜出」，
      并**显式断言**这是一个 `from_env()` 造不出来的对象
      （`from_env` 对空值抛「配置不全」）⇒ 该分支**只在直接构造 `LlmConfig` 的判据里可达**。
      ⚠️ 这条是 P1 那个夹具改法的**残余风险的判据化**，不是装饰。
- [x] `Proof` P7（生产路径必然点名）：断言 `from_env()` 造出的 `LlmConfig.model` 恒非空
      （给全三个变量时），⇒ 环境驱动的调用**必然**走点名分支。用 `monkeypatch.setenv`，零网络。
- [x] `Proof` **P8（WBS `P1.1-fix` 的验收本体 —— 缺它整条 WBS 行不算达标）**：
      往 `tests/unit/test_configured_model_is_the_one_used.py` **新增**一条
      **不传 `requested`** 的用例：沿用该文件既有的 `_cfg(model)` 走 `from_env()` 真实构造路径，
      `route("explain", models=capabilities.KNOWN_MODEL_PROFILES, config=_cfg(model))`
      ⇒ `adapter.model == model`。**参数化遍历所有 `satisfies("explain")` 的档案**
      （与既有那条同一组参数，差别只有「不传 `requested`」这一处 —— 缺口正在这一处）。
      ⚠️ **既有 6 条一条不许改、不许弱化**（`433d2ca` 逐字）；收口时自证：
      `git diff -- tests/unit/test_configured_model_is_the_one_used.py | grep -c '^-[^-]'` → **0**（纯新增）。
- [x] `Proof` **P9（同一文件 · 失败面，`433d2ca` 的「顺带交底」）**：同文件再新增一条
      **不传 `requested`** 的用例：`config.model` 是一个系统不认识的名字 ⇒ **明确抛 `RoutingError`**，
      **且文本里含那个名字**。它钉的是 `433d2ca` 逐字那句「改成默认尊重 `config.model` 之后，
      **点名不认识的模型仍必须明确失败**」—— 今天该文件只在 `requested` 分支上钉住了这件事。
- [x] ⚠️ **P2–P9 的每一条断言都要过 `tests/gates/test_assertions_have_no_escape_hatch.py`**（B6 第四条）：
      **一条 `assert` 只测一件事**，不许 `or` 兜底；确需豁免的写带理由的 `# assert-escape-ok:`。

Exit Criteria:

- [x] `python3 -m pytest tests/routing -q` → exit 0，条数 **≥ 170 + 新增条数**（只增不减；数字在收口时逐字记）
- [x] **`python3 -m pytest tests/unit/test_configured_model_is_the_one_used.py -q` → exit 0，条数 ≥ 6 + 新增**
      （评审期实测基线 **6 passed**）⇒ **WBS `P1.1-fix` 行的验收逐字成立**
- [x] `git diff -- tests/unit/test_configured_model_is_the_one_used.py | grep -c '^-[^-]'` → **0**（纯新增，既有 6 条一字未改）
- [x] P2–P5 **与 P8 / P9** 每条**先在 Phase 1 的实现上打绿、再逐条对着改动前的实现打红**
      （改动前红是本 plan 的先红后绿证据，逐条记退出码与栈顶）。
      ⚠️ **P8 / P9 在改动前必须是红的** —— 若其中哪条在改动前就绿，说明它没测到缺口，**当场改到能打红为止，不许留**
      ⚠️ **收口实测：P2 / P3 / P4 / P8 / P9 改动前红；P5 / P6 / P6b / P7 改动前就绿**（旧实现从不读
      `config.model` ⇒ 这几条真空成立）。**未为凑判据改它们**，其有效性改由变异 **M2 / M3 / M6b** 坐实
      —— 逐字见 `## Closure` 的「照实说的三件事」第 1 条。本条按该实测口径勾，不按「P2–P5 全红」勾。
- [x] `git diff -- tests/routing/test_router.py | grep -c '^-[^-]'` → **2**
      ⚠️ **收口审计期复跑得 `2`，不是执行期记的 `1`**：第 2 行是 import 行
      （`from agenerp.routing.config import LlmConfig` → `LlmConfig, from_env`，P7 需要 `from_env`），
      执行期量这个数时该 import 还没加。**本判据要证的「一条既有断言未删未改未放松」仍然成立**
      （两行删除逐字为夹具行 + import 行，`git diff -- tests/routing/test_router.py | grep '^-[^-]'` 可自证）。
      **数字按实测改准，不按执行期原文留。**
- [x] `docs/logs/` 更新

### Phase 3 — 变异自查 + owner doc 对齐 + 收口取证

Status: completed
Targets: `docs/architecture/module-boundaries.md`（新增 §7.25）· `docs/architecture/model-management.md` §12.5 · `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/` · `docs/evidence/p1-routing-configured-model/`
Skill: `none`

- Item Types: `Proof | Add`
- Prereqs: Phase 1, Phase 2

- [x] `Proof` 变异自查 **M1–M10**，逐条施加、记退出码与被打红的判据名、逐条复原并核 `sha256`：

| # | 变异位 | 变异内容 | 必须被哪条判据打红 |
|---|---|---|---|
| M1 | `router.py` | 删掉 `requested = config.model` 那一跳（回到改动前） | P2 两组用例 |
| M2 | `router.py` | `requested is None` 的守卫改成 `if True:`（让 `config.model` 压过显式 `requested`） | P5 |
| M3 | `router.py` | `.strip() or None` 改成 `or None`（空白串当成点名） | 新增一条「`config.model` 是纯空白 ⇒ 视同未点名」的用例（若 P6 未覆盖，**当场补，不放过**） |
| M4 | `router.py` | 点名取不到时改成「忽略、继续按第一个满足的挑」 | P3 |
| M5 | `router.py` | 点名取到之后**跳过** `satisfies` 校验直接回 adapter | P4 |
| M6 | `router.py` | `ChatAdapter(..., model=profile.name)` 改成 `model=None`（让 adapter 走 `or config.model`） | P4（`config.model` 与该类目不匹配时形态会岔开）—— ⚠️ **按构造可能打不红**（点名分支下两者恰好同值），若不红**照实保留在表里并另补 M6b**，不修饰成「全打红」 |
| M7 | `test_router.py` | 夹具 `model=""` 改回 `model="unused"` | 既有 15 条（B5 实测的那 15 条）—— 反测「夹具改法没有掩盖问题」 |
| M8 | `capabilities.py` | `KNOWN_MODEL_PROFILES` 里删掉 `qwen3:14b` 一格 | P2 第二组 + P4（反测「判据真的在读那张表，不是自带一份」） |
| M9 | `router.py` | 同 M1（删掉 `requested = config.model` 那一跳） | **P8**（WBS 验收那条**必须**被打红 —— 它绿着而缺陷活着，正是 B8 记的今天那个形态） |
| M10 | `router.py` | 点名取不到时改成「忽略、继续按第一个满足的挑」（同 M4） | **P9** |

- [x] `Add`：`docs/architecture/module-boundaries.md` 新增 **§7.25**，标题形态照 §7.24 的先例。
      内容必须含：D-1 的选定/被否/残余风险三段 · `requested` 与 `config.model` 的优先级（P5）·
      「候选偏好顺序在环境驱动路径上事实上失效」这条残余风险 ·
      Phase 1 第二项那处**行为变化**（双错情形下报的错换了一个）· 变异表结果（含未打红的那条，若有）·
      **判据分工一句话写清**：`tests/routing/test_router.py` 钉的是 `route()` 的选择语义，
      `tests/unit/test_configured_model_is_the_one_used.py` 钉的是「**从环境配到实际调用**这条端到端路径」（WBS 验收面，B8），
      **两者不互相冒充**。
      ⚠️ **`§7.13`–`§7.24` 一行不改**（`git diff` 对这些区段应无输出，收口时逐字自证）。
- [x] `Add`：`docs/architecture/model-management.md` §12.5 的**环境变量表 `AGENERP_LLM_MODEL` 一行**与
      「摆放规矩」第 2 条各加一句限定，把「默认模型名」改准成可判定的说法
      （「走 `route()` 时它就是被点名的那个模型；点不动就明确失败」），并加一行指向 §7.25 的指针。
      ⚠️ **三张 `machine-read` 表一格不动**（动了 `tests/routing/test_capabilities.py` 会红，那是同构判据）。
- [x] `Add`：`docs/masterplan/STATE.md` §3 **追加**一行（红线 5 只允许追加），记 B7 那一格（502/503）交人。
      **不得改写本节任何已有行。**
- [x] `Proof`：证据落 `docs/evidence/p1-routing-configured-model/README.md` —— 全部命令原文、退出码、
      变异表 M1–M10 逐格结果、`sha256` 复原核对、B1 复现脚本改动前后的两次输出。
      ⚠️ **不写入证据仓 `XM_PATH`**（红线 6）。

Exit Criteria:

- [x] `python3 tools/gates/check_expected_red.py` → exit 0，且计数行逐字为 `门禁 29 项：预期红 0，绿 29，跳过 0`（**29 这个数不得下降**；`29` 是**评审期**在 `433d2ca` 上实测的，见 B0 —— 起草期那个 `28` 已作废）
- [x] `python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"` → exit 0，passed 条数 **≥ 1299 + Phase 2 新增条数**（`1299` 是评审期实测基线，见 B0；只增不减）
- [x] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0
- [x] M1–M10 全部复原，`sha256` 与施加前逐字相同
- [x] owner doc 已更新（§7.25 新增 + §12.5 两处限定），且 `§7.13`–`§7.24`、三张 `machine-read` 表零改动
- [x] `docs/logs/` 更新

## 红线自证清单（执行者收口时必须逐条跑，不许只声称）

- [x] `git diff --name-only <BASE> -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md missions/ docker-compose.yml industry-packs/` → **无输出**（红线 1/2/3/4）
- [x] `git diff <BASE> -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**（红线 5：只追加）
- [x] `git -C "$XM_PATH" status --porcelain` → 无输出，且 `HEAD` 与 `evidence-repo.env` 的 `XM_SHA` 逐字相同（红线 6）
- [x] 未生成任何 Server Script（红线 7）；未改项目名 / 包名 / 命名空间（红线 4）

## Draft Review Record

- Independent draft review iteration 1: **needs revision → 已就地改完，转 `active`**（任务 `2026-08-26-175237-mission-driver` 的草案评审步，评审基线 `433d2ca`）。
  评审期**未采信 plan 自述的任何数字**，四组命令自己重跑/实读过。逐条记：

  | # | 级别 | 问题（评审期实读证据） | 处置 |
  |---|---|---|---|
  | 1 | **Blocker** | **工作项归属错记。** 起草期写「工作项 3 的第 2 个 plan，用掉表规 3 的最后一格」。实读 `433d2ca`（人，2026-08-26 17:53）：人**已把它拆成独立行** `02-WBS.md:81` `P1.1-fix` / roadmap **工作项 3b**，且逐字「**plan 预算独立计，不占工作项 3 的额度**」（同 `P1.8a-fix` / 工作项 10b 先例）。按错记执行会凭空吃掉工作项 3 的预算格、并把收口记录落到错误的 WBS 行上 | 前言 `Work Item` **整段改准**为「工作项 3b · `P1.1-fix` · 本 plan 是它的**第 1 个** plan · 预算独立计」，并把错记原文留痕；`Source` 补人侧裁定与 commit；`Related` 那句「本工作项第 1 个 plan」的归属改准 |
  | 2 | **Blocker** | **WBS 那一行的验收判据，整份 plan 零处覆盖。** 验收列逐字要求 `tests/unit/test_configured_model_is_the_one_used.py` **补一条不传 `requested` 的用例并绿**，commit 正文另有逐字「**只让现有用例继续绿不算达标**」。而起草稿 Phase 2 的 Targets 只有 `tests/routing/test_router.py`，全文未出现过那个文件名。**评审期实读该文件**（`f68ae19` 新增，71 行，实跑 `6 passed`）：两条用例**全部显式传 `requested=model`** ⇒ **它今天全绿，缺陷全须全尾地活着**。⇒ 照起草稿执行完，`route()` 改对了、`tests/routing` 全绿，**WBS 那一行仍不算达标** | 新增 **B8** 一整节（实读证据）· **Goals 4b** · Phase 2 **Targets 补该文件** · 新增 **`Proof` P8**（不传 `requested` 的成功面，参数化遍历）与 **`Proof` P9**（不传 `requested` 的未知模型失败面，钉 `433d2ca` 的「顺带交底」）· Phase 2 **Exit Criteria 加两条**（该文件单跑 exit 0 且条数 ≥ 6 + 新增；`grep -c '^-[^-]'` → **0** 纯新增）· **Closure Gates 加一条** · 变异表补 **M9 / M10** 专钉 P8 / P9 |
  | 3 | **Major** | **两个 Exit Criteria 的数字已经过期，按原文写死会永远判不过。** 起草基线 `0033c7b` 之后人落了 `f68ae19` / `4f3b488` / `433d2ca`。评审期在 `433d2ca` 干净树上原样重跑：`check_expected_red.py` → **`门禁 29 项：预期红 0，绿 29，跳过 0`**（起草稿写死「计数行**逐字**为 `门禁 28 项…`」且「28 不得下降」——**29 逐字对不上 28**）；六目录合跑 → **`1299 passed, 23 skipped, 7 deselected`**（起草稿写 `≥ 1293`）。成因是 `f68ae19` 新增了一条门禁 + 6 条 `tests/unit` | 新增 **B0** 漂移对照表（三组量，逐字记起草期 / 评审期两栏与成因）· Phase 3 两条 Exit Criteria 改准为 **29** / **≥ 1299 + Phase 2 新增条数**· B5 的旧数**照实保留但标注已被取代、不再是判据** |
  | 4 | **Major** | **一条评审期才存在的新门禁会直接扫到本 plan 要写的所有新断言。** `f68ae19` 新增 `tests/gates/test_assertions_have_no_escape_hatch.py`（102 行），扫 `tests/` 下每一条 `assert`，拦「`or` 的某一侧是失败态」（`is False` / `is None` / `== []` / `== {}` / `== ""`），只放行带理由的 `# assert-escape-ok:`。起草稿的 B6 红线面测于 `0033c7b`，**不含它**；而 Phase 2 要新写 7–9 条断言，全部落在它的扫描面内 | **B6 补第四条**（含豁免写法与「它在 `tests/gates/**` 内 ⇒ 只读、本 plan 是服从不是碰它」）· Phase 2 末尾加一条硬约束：**一条 `assert` 只测一件事，不许 `or` 兜底** |

  ⚠️ **未改动的部分照实说**：`D-1` 四选一的裁定与三段理由、Phase 1 的三项、P1–P7、`## Deferred But Adjudicated` D1–D4、
  红线自证清单 —— **一个字未改**。评审期抽验过 P2/P4 的用例可构造性
  （`qwen3:14b` `explain=True`/`lineage=False`、`qwen-plus` `explain=True`/`lineage=False`、`qwen3.6-plus` 两项均 `True`，实跑档案表得到）
  与 B1/B2/B3/B6 的四处逐字引用（`router.py:75-80` · `app.py:246-257` · `test_adapter.py:526` 的六元组），**均与 plan 所写吻合**。
  `tests/routing` 评审期实测 `170 passed, 1 skipped`，**与起草期逐字相同** ⇒ **B5 的代价形状结论未被漂移动摇**。

## Closure Gates

- [x] in-scope behavior is complete
- [x] **WBS `P1.1-fix` 行的验收逐字成立**：`tests/unit/test_configured_model_is_the_one_used.py`
      多出至少一条**不传 `requested`** 的用例且绿，既有 6 条一字未改（B8 · Goals 4b · Phase 2 P8/P9）
- [x] relevant docs are aligned（§7.25 新增 · §12.5 两处限定 · STATE §3 追加一行）
- [x] verification has run（`check_expected_red.py` · 六目录 `pytest -m "not live"` · `ruff`，三条命令原文与退出码逐字记在 `## Closure`）
- [x] scoped verification is not conflated with full verification —— 若整仓 `pytest tests -q -m "not live"` 未跑或基线即红，逐字写「verification scope limited」并说明
- [x] no in-scope item downgraded to deferred/follow-up
- [x] independent draft review completed and recorded
- [x] text consistency verified: status, phases, gates, and log all agree
- [x] closure audit was independent —— ⚠️ **执行期留 `[ ]` 是对的（当时确实没有审计者）；本条由
      2026-08-26 的独立收口审计补勾，不是执行者自己勾**。审计者：任务
      `2026-08-26-175237-mission-driver` 的收口审计步（独立于执行步，未采信 plan / 证据 README 的任何自述数字）。
      审计实跑与实读见 `## Closure` 的 `Closure Audit Evidence`，**并已改准一处过期数**
      （`test_router.py` 的 `grep -c '^-[^-]'`：执行期记 `1`，实测 `2`）。
- [x] closure evidence exists in files（`docs/evidence/p1-routing-configured-model/`）
- [x] 红线自证清单四条全部跑过且贴了原文

## Deferred But Adjudicated

### D1 · `AGENERP_LLM_MODEL` 配错名字时服务回 502 而不是 503

- Classification: `out-of-scope defect`
- Why Not Blocking Closure: 修法面在 `agenerp/serve/app.py`（工作项 10 / P1.8a），
  该工作项的 plan 预算 **`2/2` 已满**，本 plan 的 Non-Goal 3 逐字排除它。
  起草期已实测复现：伪造 `config_factory` 回 `model="typo-model"` → `ServiceError.status = 502`，
  文本 `点名的模型 'typo-model' 不在候选档案里；候选是 [...]`，
  与 `app.py:239-242` 自己写死的「配置拿到之后才叫上游坏了」冲突。
- Successor Required: `yes`（人）
- 重开事件：**人给工作项 10 开新的预算格**，或人直接在 `02-WBS.md` 为 P1.8a 拆行 / 加行（红线 5，loop 无权）。

### D2 · 「配对了模型但该模型没有额度」这一格

- Classification: `watch-only residual`
- Why Not Blocking Closure: B2 那次 403 有**两个**成因（换了模型 + 那个模型没免费额度）。
  本 plan 只堵前者；后者要么做端点探测（网络，判据不可离线）、要么读厂商额度接口（把厂商写进产品，违 §12.1 ①）。
- Successor Required: `no`
- 重开事件：**本仓再出现一次「模型名配对了、仍然全程 403」的可复现观测**（有轨迹为证）。

### D3 · 候选偏好顺序在环境驱动路径上事实上失效

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是 D-1 选 (A) 的**已知代价**，不是遗漏；已逐字写进 §7.25 与 `router.py` 模块头。
  今天没有任何调用方依赖「给一串候选、让 router 按偏好挑」这个行为
  （B3 的表：六个调用点要么点名、要么把候选集缩成一个）。
- Successor Required: `no`
- 重开事件：**出现第一个真正依赖候选偏好顺序的调用方**（例如「主模型不可用时按顺序回落」这类需求落地时）——
  那时 `route()` 需要一个显式的「允许回落」开关，而那是一次新的 `Decision`，须由人开预算格。

### D4 · `KNOWN_MODEL_PROFILES` 仍是 Python 常量，增删它就是改产品源码

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: §12.5「摆放规矩」第 2 条已逐字登记过这条残余风险，
  本 plan 一个字不改它的结论，也不把档案表外置成配置文件（那是 §12.5 逐字「将来的事，本期没做」）。
- Successor Required: `no`
- 重开事件：**人要求把模型档案外置成配置文件**，或 P2 阶段的定制包需要按企业增删模型档案。

## Closure

Status Note: **completed（2026-08-26）** —— 三个 Phase 全部执行完毕，Exit Criteria 逐条实跑取证。
起跑基线 `433d2ca`；⚠️ **执行期人侧落了 `42fa183` / `9be3007`，HEAD 变成 `9be3007`**（详见下方「照实说的三件事」）。

⚠️ **裁判规则 2 未满足的那一格，照实说**：本轮的代码与文档改动**尚未提交**
（`git status --porcelain` 有 8 个 `M` + 1 个 `??`）⇒ **拿不出本次交付的 commit sha**。
AGENTS.md 裁判规则 2 逐字「宣称完成时必须出现：命令原文 + 退出码 + commit sha，三者缺一，
就把『完成』改写成『我认为完成，待验证』」⇒ **本 plan 的状态按该规则读作「我认为完成，待验证」**，
三条命令原文与退出码已逐字在下方，**缺的就是 sha 这一项**。提交由人或 loop 的提交步执行。

### 三条收口命令（原文 + 退出码，逐字）

```
python3 tools/gates/check_expected_red.py
→ exit 0 ·「门禁 29 项：预期红 0，绿 29，跳过 0」·「✅ 与预期红名单完全一致」

python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"
→ exit 0 ·「1314 passed, 23 skipped, 7 deselected」   （评审期基线 1299 ⇒ +15，只增不减）

ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui
→ exit 0 ·「All checks passed!」
```

### WBS `P1.1-fix` 行的验收（Goals 4b · Closure Gates 第 2 条）

```
python3 -m pytest tests/unit/test_configured_model_is_the_one_used.py -q
→ exit 0 ·「12 passed」                              （评审期基线 6 passed ⇒ +6）

git diff -- tests/unit/test_configured_model_is_the_one_used.py | grep -c '^-[^-]'
→ 0                                                  （纯新增，既有 6 条一字未改）
```

新增两条**均不传 `requested`**：`test_the_configured_model_is_used_without_anyone_passing_requested`
（参数化遍历 5 个 `satisfies("explain")` 的档案）· `test_an_unknown_configured_model_still_fails_loudly_without_requested`。
**两条在改动前都是红的**（exit 1 · `4 failed, 1 passed` / `DID NOT RAISE`）⇒ 它们确实钉在缺口上，
不是「让现有用例继续绿」。

### 其余判据面

```
python3 -m pytest tests/routing -q
→ exit 0 ·「179 passed, 1 skipped」                   （基线 170 ⇒ +9）

git diff -- tests/routing/test_router.py | grep -c '^-[^-]'
→ 2                                                  （⚠️ 执行期这里记的是 `1`，是过期数；见下方更正）
```

⚠️ **审计更正（2026-08-26 独立收口审计复跑）**：上面这条**今天跑出的是 `2`，不是 `1`**。
两行删除逐字是：

```
-from agenerp.routing.config import LlmConfig
-CONFIG = LlmConfig(base_url="https://endpoint.invalid/v1", model="unused", api_key="sk-test")
```

第 2 行是夹具（P1 本体），第 1 行是 import 行（P7 需要 `from_env`，执行期量这个数时它还没加）。
⇒ **「一条既有断言未删、未改、未放松」这个实质结论成立**，但**执行期与证据 README §2 记的 `1` 是过期数**，
按实测改准为 `2` 并写明第 2 行的成因。**不修饰成「本来就是 2」。**

### ⚠️ 照实说的三件事（不修饰）

1. **P5 / P6 / P6b / P6 后半 / P7 在改动前就是绿的。** plan 对 P2–P5 写的是「逐条打红」，
   实测这五条真空成立（旧实现从不读 `config.model`）。**没有为凑判据去改它们**；
   它们的有效性由变异 **M2 / M3 / M6b** 坐实。plan 写死「必须打红」的只有 **P8 / P9**，那两条都红。
2. **变异表 11 格里有 2 格没按预期形态打红。** **M6** 对 P4 exit 0（点名分支下两值恰好相同），
   补的 **M6b** 打红；**M8** 红在收集期而非目标断言，且对 WBS 验收文件 **exit 0** ——
   **「遍历一张表」的参数化判据对「表本身变短」是盲的**。两格都原样留在 §7.25.7，未修饰成「全打红」。
3. **本 loop 追加进 `STATE.md` §3 的那条 needs-human，被人侧 `9be3007` 一并提交了。**
   提交那一刻它正在 working tree 里 ⇒ **8 行署在人的 commit 名下，内容是 loop 写的**。
   仍满足红线 5（`git show 9be3007 -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**），
   **但署名不准这件事登记在案**。

### verification scope limited

- **未跑整仓 `python3 -m pytest tests -q -m "not live"`** —— **已知基线即红**：`gates` × `tools`
  的环境泄漏已单列立案于 `docs/backlog/gates-and-tools-leak-env-across-directories.md`。
  跑的是 plan 与 `gates.yml` 指定的**六目录**口径。
- **未跑 `-m live`** —— plan 的 `## Infrastructure And Config Prereqs` 逐字不要求。
- **未经 CI 服务端复跑。**

Closure Audit Evidence:

- Auditor / Agent: **独立收口审计** —— 任务 `2026-08-26-175237-mission-driver` 的收口审计步，
  **独立于执行步**，与执行者不共享上下文；人未在场。
  ⚠️ **执行期确实没有审计者，那时留 `[ ]` 是对的**；本节记的是**其后补做的那一次独立复核**。
  审计口径：**不采信 plan 与证据 README 的任何自述数字**，全部对着 `9be3007` + 未提交工作树自己重跑/实读。

  **审计复跑（命令原文 + 退出码，逐字）**：

  ```
  python3 tools/gates/check_expected_red.py
  → exit 0 ·「门禁 29 项：预期红 0，绿 29，跳过 0」·「✅ 与预期红名单完全一致」

  python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"
  → exit 0 ·「1314 passed, 23 skipped, 7 deselected」

  ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui
  → exit 0 ·「All checks passed!」

  python3 -m pytest tests/routing -q                                   → exit 0 ·「179 passed, 1 skipped」
  python3 -m pytest tests/unit/test_configured_model_is_the_one_used.py -q → exit 0 ·「12 passed」
  ```

  **审计实读（逐条与活仓核对，不看 plan 自述）**：

  - **缺陷已死**：B1 复现脚本原样重跑 → `config.model = qwen3:14b | adapter.model = qwen3:14b`（exit 0）。
  - **不是空壳**：`agenerp/routing/router.py` 实读 —— config 解析已上提到挑档案之前，
    `requested = (resolved_config.model or "").strip() or None` 在 `requested is None` 分支内，
    点名后走**同一条** `satisfies()` 校验。`route()` 是生产调用面
    （`agenerp/explain/loop.py:664` · `agenerp/judging/judge.py:73` · `agenerp/serve/app.py` 经 `explain()`）⇒ 改动**在运行时可达**，非注册未用。
  - **既有判据零放松**：`git diff -- tests/unit/test_configured_model_is_the_one_used.py | grep -c '^-[^-]'` → **0**（纯新增）；
    `tests/routing/test_router.py` 的两行删除逐字核过（夹具行 + import 行，**无断言行**）。
  - **owner doc 已同步**：`module-boundaries.md` §7.25 实读存在（7 小节，`git diff` 对该文件 **0 删除** ⇒ §7.13–§7.24 一行未改）；
    `model-management.md` §12.5 两处限定实读存在（该文件 1 行删除，逐字就是 `AGENERP_LLM_MODEL` 那一行的改写，三张 `machine-read` 表未动）；
    `docs/logs/2026/08-26.md` 两条实读存在。
  - **红线复核（vs HEAD `9be3007`）**：
    `git diff --name-only HEAD -- tests/gates/ .github/workflows/ docs/masterplan/ missions/ docker-compose.yml industry-packs/` → **无输出**；
    `git diff 433d2ca -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**（只追加）。
  - **一处更正**：`test_router.py` 的 `grep -c '^-[^-]'` 执行期记 `1`、审计实测 **`2`**，
    已在本节上方与 Phase 2 Exit Criteria 改准并写明成因（多出的是 import 行，不是断言）。
    ⚠️ **`docs/evidence/p1-routing-configured-model/README.md` §2 的 `1` 是执行期原文** ——
    **执行期那行原样保留不改写**，其下**追加了一段同措辞的更正注**（贴两行删除的逐字与「都不是断言」的结论），
    使证据文件与本节不再互相矛盾；**以本节的更正为准**。
  - **未复核的面（照实说）**：整仓 `pytest tests -q -m "not live"`（已知基线即红，已立案）·
    `-m live` · CI 服务端复跑 · 变异表 M1–M10 **未重做**（审计只核了它记的结论与 §7.25.7 的落盘，
    未再施加一次变异）—— 这三项与执行期的 `verification scope limited` 同口径。
- Evidence: `docs/evidence/p1-routing-configured-model/README.md`（八节：基线复跑 · B1 前后两输出 ·
  改动代价 · 先红后绿逐条 · 变异表 · `sha256` 复原 · D1 实测 · 红线自证）·
  `docs/logs/2026/08-26.md`（Phase 1–2 与 Phase 3 两条）· 任务 `2026-08-26-175237-mission-driver`

Follow-up:

- **D1（`AGENERP_LLM_MODEL` 配错名字回 502 而非 503）交人** —— 已追加进 `docs/masterplan/STATE.md` §3
  （`2026-08-26T10:15Z` 那条）。⚠️ **本次改动把它的暴露面放大了**：改之前配错名字根本不触发这条路
  （静默换模型），现在它是点名分支的正常失败态。**后者远好于前者，但状态码仍是错的。**
- **M8 暴露的普遍形态交人**：`KNOWN_MODEL_PROFILES` 少一格时，按表参数化的判据用例数跟着缩、全绿通过。
  已登记在 §7.25.7，重开事件写在那里。
- ⚠️ **确认的缺陷没有进本节**：D1 与 M8 两条都是**已裁定的 out-of-scope / 已登记残余**，
  处置权在人（工作项 10 预算已满 · 表规改动属红线 5）。
