# 2026-08-26-1728-1 `route()` 必须尊重配置里的模型名 —— 静默换模型的那条路堵死

> Plan Status: draft
> Last Reviewed: 2026-08-26
> Mission: p1-insight
> Work Item: 3. 模型路由 v0：OpenAI 兼容 adapter + 能力声明按任务分档（P1.1）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个预算，本 plan 用掉最后一格）
> Source: 起草期实读 + 实跑复现的活缺陷（见 `## Current Baseline` 的复现原文）；缺陷的第一次现场记录在 `agenerp/serve/app.py:246-256` 的注释里（2026-08-26 人侧实测）
> Related: `docs/plans/p1-insight/2026-08-24-1457-1-model-routing-v0.md`（本工作项第 1 个 plan）· `docs/plans/p1-insight/2026-08-26-1618-1-doc-links-child-host-guard.md`（同一类失败形态：修法只落在一半的站点调用上）
> Audit: required

## Current Baseline

**以下每一条都是起草期在 `0033c7b` 的干净工作树上实跑/实读得到的，不是从旧 plan 抄的。**
⚠️ **起草期为量代价施加过一次可复原的临时补丁，收尾已复原**：`git status --porcelain` → 无输出。
执行者**不得采信下面的数字**，必须自己重跑一遍（数字对不上就是基线变了，先停下来记，不要改断言去凑）。

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

### B6 · 红线面（起草期实读，执行前必须复核）

- `grep -rn "route(\|LlmConfig\|config=" tests/gates/*.py` → **只有 3 行命中，全在 `test_agent_seam_stays_swappable.py` 的注释与失败文案里**，
  没有任何一条门禁构造 `LlmConfig` 或调 `route()` ⇒ 本 plan 的改动**不需要碰 `tests/gates/**`**（红线 1）。
- `tests/gates/test_agent_seam_stays_swappable.py:103` 只禁「在 `agenerp/routing/` 之外直接构造 `ChatAdapter`」，
  本 plan 的改动全在 `route()` 体内 ⇒ 该门禁不受影响。
- `tests/routing/test_adapter.py:526` 断言 `routing.__all__` **逐字等于六元组** ⇒
  本 plan **不得新增任何导出名**（新增就要改那条断言，那会长得像放松判据）。

### B7 · 仍然缺的那一格（本 plan 不补，见 `## Deferred But Adjudicated` D1）

`AGENERP_LLM_MODEL` 配了一个系统不认识的名字时，`handle_explain` 回的是 **502**（「上游坏了」），
不是 **503**（「未配置」）——与 `agenerp/serve/app.py:239-242` 自己写死的结构性分法冲突。
**起草期实测**：伪造 `config_factory` 回 `model="typo-model"` → `ServiceError.status = 502`，
文本是 `点名的模型 'typo-model' 不在候选档案里；候选是 [...]`。
**修法面在 `agenerp/serve/**` = 工作项 10（P1.8a），其 plan 预算 `2/2` 已满** ⇒ 本 plan 不动它。

## Goals

1. **`route()` 在 `requested is None` 时必须使用 `config.model`**（`config` 显式给的或 `from_env()` 读的都算），
   用不了就**按名失败**，绝不换一个跑。
2. **「配了 A 调了 B」这条路在代码上不存在** —— 不是靠每个调用方记得传 `requested`。
3. **owner doc 与代码对齐一处**：`model-management.md` §12.5 的「默认模型名」从今天起是真的。
4. **既有 170 条 `tests/routing` 判据一条不放松**，改动代价局限在一个夹具字面量上，并有独立判据钉住新语义。
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

Status: planned
Targets: `agenerp/routing/router.py`
Skill: `none`

- Item Types: `Decision | Fix`
- Prereqs: 无

- [ ] **`Decision` D-1：`requested is None` 时 `config.model` 的地位。**
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
- [ ] `Fix`：`route()` 体内把 `config` 的解析**上提到挑档案之前**（今天它在 `for` 循环体内，
      `router.py:77`），得到 `resolved_config`；`requested is None` 时用 `(resolved_config.model or "").strip() or None` 顶上。
      ⚠️ **上提会改变一件事，必须自己实测确认而不是推断**：`config is None` 且环境没配时，
      `RoutingError("配置不全…")` 现在**在能力校验之前**抛。既有判据
      `test_route_falls_back_to_env_config_only_when_no_config_is_given`
      （`tests/routing/test_router.py:178-183`）用的是 `models=[STRONG]` + `explain`（本来就满足）
      ⇒ 起草期实测**它不红**；但「不满足能力 + 环境也没配」这种双错情形下**报的错换了一个**，
      属行为变化，写进 §7.25，**不假装没变**。
- [ ] `Fix`：`router.py` 模块头第 13 行那句「第一个满足的胜出」改准为带前提的说法
      （逐字前提：`config.model` 为空时才成立），并在 `route()` 的 docstring 里点名 `config.model` 的新地位。

Exit Criteria:

- [ ] B1 的复现脚本原样重跑，输出变成 `config.model = qwen3:14b | adapter.model = qwen3:14b`（两边相等）
- [ ] `agenerp/routing/__init__.py` 的 `__all__` **逐字未变**（B6 第三条），`git diff` 对该文件无输出
- [ ] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0（**逐字抄 `gates.yml:682`**）
- [ ] 相关 owner doc 更新留到 Phase 2；本 Phase 只改 `router.py` 自己的模块头与 docstring

### Phase 2 — 判据：既有 170 条一条不放松，新语义单独钉

Status: planned
Targets: `tests/routing/test_router.py`
Skill: `none`

- Item Types: `Proof`
- Prereqs: Phase 1

- [ ] `Proof` P1（夹具）：`tests/routing/test_router.py:26` 的 `CONFIG` 把 `model="unused"` 改成 `model=""`。
      **只改这一个字面量。** 改动理由写在该行上方的注释里，逐字说明：
      `"unused"` 编码的是「`config.model` 反正会被忽略」这个**缺陷本身**，
      改成 `""` 之后「不点名」这条路径的全部既有判据**原样继续有效**。
      ⚠️ **收口时必须能证明「一条断言都没动」**：
      `git diff -- tests/routing/test_router.py | grep -c '^-[^-]'` 必须是 **1**（就是那一行夹具）。
- [ ] `Proof` P2（新语义 · 成功面）：`config.model` 点名一个**满足**该类目的候选 ⇒ `adapter.model == config.model`，
      **且它不是候选集里第一个满足的那个**（否则「第一个胜出」的旧实现也能蒙混过去）。
      用例至少两组：`models=[STRONG, WEAK]` + `config.model="qwen-plus"` + `explain`；
      `models=KNOWN_MODEL_PROFILES`（映射形态）+ `config.model="qwen3:14b"` + `explain`。
- [ ] `Proof` P3（新语义 · 失败面之一）：`config.model` 点名一个**不在候选里**的名字 ⇒ 抛，
      且**文本里含那个名字**（`match="不在候选档案里"` + `assert name in str(exc)`）。
      只断「抛了」不够 —— 一个「永远抛」的假实现同样全绿（该文件模块头第 3 行逐字如此要求）。
- [ ] `Proof` P4（新语义 · 失败面之二）：`config.model` 点名一个**在候选里但能力不够**的模型 ⇒ 抛，
      **且不回落到候选集里那个够格的强模型**（`models=[LOCAL, STRONG]` + `config.model="qwen3:14b"` + `lineage`）。
      这是 §12.1 ③「绝不静默降级」在新路径上的反测。
- [ ] `Proof` P5（`requested` 优先级）：`requested` 与 `config.model` **同时给且不同**时，
      **`requested` 胜出**（显式点名压过默认值）。逐字写进 §7.25，不留给读者猜。
- [ ] `Proof` P6（空模型名保留旧路径）：`config.model == ""` 时仍走「第一个满足的胜出」，
      并**显式断言**这是一个 `from_env()` 造不出来的对象
      （`from_env` 对空值抛「配置不全」）⇒ 该分支**只在直接构造 `LlmConfig` 的判据里可达**。
      ⚠️ 这条是 P1 那个夹具改法的**残余风险的判据化**，不是装饰。
- [ ] `Proof` P7（生产路径必然点名）：断言 `from_env()` 造出的 `LlmConfig.model` 恒非空
      （给全三个变量时），⇒ 环境驱动的调用**必然**走点名分支。用 `monkeypatch.setenv`，零网络。

Exit Criteria:

- [ ] `python3 -m pytest tests/routing -q` → exit 0，条数 **≥ 170 + 新增条数**（只增不减；数字在收口时逐字记）
- [ ] P2–P5 每条**先在 Phase 1 的实现上打绿、再逐条对着改动前的实现打红**（改动前红是本 plan 的先红后绿证据，逐条记退出码与栈顶）
- [ ] `git diff -- tests/routing/test_router.py | grep -c '^-[^-]'` → **1**
- [ ] `docs/logs/` 更新

### Phase 3 — 变异自查 + owner doc 对齐 + 收口取证

Status: planned
Targets: `docs/architecture/module-boundaries.md`（新增 §7.25）· `docs/architecture/model-management.md` §12.5 · `docs/masterplan/STATE.md`（**只追加**）· `docs/logs/` · `docs/evidence/p1-routing-configured-model/`
Skill: `none`

- Item Types: `Proof | Add`
- Prereqs: Phase 1, Phase 2

- [ ] `Proof` 变异自查 **M1–M8**，逐条施加、记退出码与被打红的判据名、逐条复原并核 `sha256`：

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

- [ ] `Add`：`docs/architecture/module-boundaries.md` 新增 **§7.25**，标题形态照 §7.24 的先例。
      内容必须含：D-1 的选定/被否/残余风险三段 · `requested` 与 `config.model` 的优先级（P5）·
      「候选偏好顺序在环境驱动路径上事实上失效」这条残余风险 ·
      Phase 1 第二项那处**行为变化**（双错情形下报的错换了一个）· 变异表结果（含未打红的那条，若有）。
      ⚠️ **`§7.13`–`§7.24` 一行不改**（`git diff` 对这些区段应无输出，收口时逐字自证）。
- [ ] `Add`：`docs/architecture/model-management.md` §12.5 的**环境变量表 `AGENERP_LLM_MODEL` 一行**与
      「摆放规矩」第 2 条各加一句限定，把「默认模型名」改准成可判定的说法
      （「走 `route()` 时它就是被点名的那个模型；点不动就明确失败」），并加一行指向 §7.25 的指针。
      ⚠️ **三张 `machine-read` 表一格不动**（动了 `tests/routing/test_capabilities.py` 会红，那是同构判据）。
- [ ] `Add`：`docs/masterplan/STATE.md` §3 **追加**一行（红线 5 只允许追加），记 B7 那一格（502/503）交人。
      **不得改写本节任何已有行。**
- [ ] `Proof`：证据落 `docs/evidence/p1-routing-configured-model/README.md` —— 全部命令原文、退出码、
      变异表 18 格逐格结果、`sha256` 复原核对、B1 复现脚本改动前后的两次输出。
      ⚠️ **不写入证据仓 `XM_PATH`**（红线 6）。

Exit Criteria:

- [ ] `python3 tools/gates/check_expected_red.py` → exit 0，且计数行逐字为 `门禁 28 项：预期红 0，绿 28，跳过 0`（**28 这个数不得下降**）
- [ ] `python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"` → exit 0，passed 条数 **≥ 1293**（B5 实测基线，只增不减）
- [ ] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → exit 0
- [ ] M1–M8 全部复原，`sha256` 与施加前逐字相同
- [ ] owner doc 已更新（§7.25 新增 + §12.5 两处限定），且 `§7.13`–`§7.24`、三张 `machine-read` 表零改动
- [ ] `docs/logs/` 更新

## 红线自证清单（执行者收口时必须逐条跑，不许只声称）

- [ ] `git diff --name-only <BASE> -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md missions/ docker-compose.yml industry-packs/` → **无输出**（红线 1/2/3/4）
- [ ] `git diff <BASE> -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**（红线 5：只追加）
- [ ] `git -C "$XM_PATH" status --porcelain` → 无输出，且 `HEAD` 与 `evidence-repo.env` 的 `XM_SHA` 逐字相同（红线 6）
- [ ] 未生成任何 Server Script（红线 7）；未改项目名 / 包名 / 命名空间（红线 4）

## Draft Review Record

- Independent draft review iteration 1: <pending>

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（§7.25 新增 · §12.5 两处限定 · STATE §3 追加一行）
- [ ] verification has run（`check_expected_red.py` · 六目录 `pytest -m "not live"` · `ruff`，三条命令原文与退出码逐字记在 `## Closure`）
- [ ] scoped verification is not conflated with full verification —— 若整仓 `pytest tests -q -m "not live"` 未跑或基线即红，逐字写「verification scope limited」并说明
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files（`docs/evidence/p1-routing-configured-model/`）
- [ ] 红线自证清单四条全部跑过且贴了原文

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

Status Note: <未开工>

Closure Audit Evidence:

- Auditor / Agent: <独立子代理，收口时填>
- Evidence: <task id / 证据目录 / 命令原文与退出码>

Follow-up:

- <收口时填；确认的缺陷不得进这一节>
