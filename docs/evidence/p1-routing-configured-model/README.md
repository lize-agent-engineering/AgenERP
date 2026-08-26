# `route()` 尊重配置里的模型名 —— 收口证据（P1.1-fix · 工作项 3b 第 1 个 plan）

> 来源 plan：`docs/plans/p1-insight/2026-08-26-1728-1-routing-honors-configured-model.md`
> 执行基线（`BASE`）：`433d2ca780e3e32caf31ebb5759e32c10cfb8f36`
> 落点节：`docs/architecture/module-boundaries.md` §7.25 · `docs/architecture/model-management.md` §12.5
> 全部命令**零网络、零站点、零 docker、零 LLM 凭据**。

---

## 0 · 基线复跑（执行者自己重跑，不采信 plan 自述）

plan 的 `## Current Baseline` B0 给了三个评审期实测数。执行期在 `433d2ca` 干净树上**原样重跑**：

| 命令 | plan B0 写的 | 执行期实测 | 是否吻合 |
|---|---|---|---|
| `python3 tools/gates/check_expected_red.py` | `门禁 29 项：预期红 0，绿 29，跳过 0` | `门禁 29 项：预期红 0，绿 29，跳过 0`（exit 0） | ✅ 逐字 |
| `python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"` | `1299 passed, 23 skipped, 7 deselected` | `1299 passed, 23 skipped, 7 deselected` | ✅ 逐字 |
| `python3 -m pytest tests/routing -q` | `170 passed, 1 skipped` | `170 passed, 1 skipped` | ✅ 逐字 |
| `python3 -m pytest tests/unit/test_configured_model_is_the_one_used.py -q` | `6 passed` | `6 passed` | ✅ 逐字 |

⇒ **基线未漂移**，B0 的数字全部可用。

---

## 1 · B1 复现脚本 —— 改动前后两次输出

脚本逐字（`plan` B1 原文，未改一字）：

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

| 时点 | 输出 |
|---|---|
| **改动前**（`433d2ca` 干净树） | `config.model = qwen3:14b | adapter.model = qwen3.8-max` ⇒ **配了 A 调了 B** |
| **改动后** | `config.model = qwen3:14b | adapter.model = qwen3:14b`（exit 0）⇒ **两边相等** |

---

## 2 · 改动代价实测（Phase 1 只改 `route()`，尚未改夹具时）

```
python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"
→ 15 failed, 1284 passed, 23 skipped, 7 deselected
```

**15 条全部在 `tests/routing/test_router.py`**（`grep -E "^FAILED" | cut -d: -f1 | sort | uniq -c` → `15 FAILED`，
全部前缀 `tests/routing/test_router.py`），其余五个目录 **0 条红** ⇒ **与 plan B5 的「代价形状」结论逐字吻合。**

唯一成因是该文件第 25 行的夹具字面量 `model="unused"` —— 它编码的正是「`config.model` 反正会被忽略」这个缺陷本身。
改成 `model=""` 后 `tests/routing` 回到 `170 passed, 1 skipped`。

**「一条断言都没动」的自证**：

```
git diff -- tests/routing/test_router.py | grep -c '^-[^-]'   →   1
```

（那 1 行就是夹具本身；⑤ 节的 9 条新判据与那 3 行注释全部是**新增**。）

> ⚠️ **更正（2026-08-26 独立收口审计复跑）—— 上面这个 `1` 是执行期的过期数，实测是 `2`。**
> 执行期量这个数时，P7 需要的 `from_env` 还没加进 import 行。两行删除逐字为：
>
> ```
> -from agenerp.routing.config import LlmConfig
> -CONFIG = LlmConfig(base_url="https://endpoint.invalid/v1", model="unused", api_key="sk-test")
> ```
>
> 第 1 行是 import 行、第 2 行是夹具行，**两行都不是断言** ⇒ 本节要证的
> 「一条既有断言未删、未改、未放松」**结论不变**，只是数字从 `1` 改准为 `2`。
> 上面的执行期原文**照实保留不改写**，以本更正为准。**不修饰成「本来就是 2」。**

---

## 3 · 新判据的「先红后绿」逐条取证

命令形态：`python3 -m pytest <node-id> -q --no-header -p no:cacheprovider`，
**改动前** = 用 `git show HEAD:agenerp/routing/router.py` 覆盖回原实现（跑完按 `sha256` 复原，见 §5）。

| 判据 | 文件 | 改动前 | 改动后 |
|---|---|---|---|
| P2 `..._not_the_first_satisfying_candidate` | `test_router.py` | **exit 1** | exit 0 |
| P2 `..._candidates_come_as_the_known_profile_mapping` | `test_router.py` | **exit 1** | exit 0 |
| P3 `test_a_configured_model_outside_the_candidates_fails_by_name` | `test_router.py` | **exit 1** | exit 0 |
| P4 `..._does_not_fall_back_to_a_stronger_one` | `test_router.py` | **exit 1** | exit 0 |
| P5 `test_an_explicit_request_wins_over_the_configured_model` | `test_router.py` | ⚠️ **exit 0（改动前就绿）** | exit 0 |
| P6 `..._keeps_the_first_satisfying_candidate_path` | `test_router.py` | ⚠️ **exit 0** | exit 0 |
| P6b `test_a_blank_configured_model_is_also_treated_as_not_named` | `test_router.py` | ⚠️ **exit 0** | exit 0 |
| P6 后半 `test_the_empty_model_branch_is_unreachable_from_env_config` | `test_router.py` | ⚠️ **exit 0** | exit 0 |
| P7 `test_env_built_config_always_names_a_model` | `test_router.py` | ⚠️ **exit 0** | exit 0 |
| **P8** `test_the_configured_model_is_used_without_anyone_passing_requested` | **`tests/unit/test_configured_model_is_the_one_used.py`** | **exit 1**（`4 failed, 1 passed`） | exit 0（`5 passed`） |
| **P9** `test_an_unknown_configured_model_still_fails_loudly_without_requested` | **同上** | **exit 1**（`DID NOT RAISE RoutingError`） | exit 0 |

P8 改动前的栈顶逐字：

```
E       AssertionError: 配的是 'qwen3.7-plus-2026-05-26'，实际却用了 'qwen3.8-max' —— 没人点名时配置仍然没生效。
E       assert 'qwen3.8-max' == 'qwen3.7-plus-2026-05-26'
```

⇒ **plan 的硬要求「P8 / P9 在改动前必须是红的」成立。**

### ⚠️ 照实说：五条改动前就绿的判据

P5 / P6 / P6b / P6 后半 / P7 **改动前就是绿的**，plan 的 Exit Criteria 对 P2–P5 写的是「逐条对着改动前的实现打红」。
**没有为了凑这条去改它们**，理由如下：

- P5 钉的是「`requested` 压过 `config.model`」。旧实现**从不读 `config.model`** ⇒ 它恰好也满足，
  这不是「判据没测到东西」，而是「这条语义在旧实现里是**真空成立**的」。
  它真正被证明有效是在**变异 M2**（守卫改成 `if True:`）下 **exit 1**。
- P6 / P6b / P6 后半 / P7 钉的是空值 / 空白值语义与 `from_env()` 的恒非空性质，
  **旧实现里根本没有「读 config.model」这条路** ⇒ 同理真空成立。
  它们的有效性由**变异 M3 / M6b** 坐实。

plan 只把**必须打红**写死在 P8 / P9 上（「⚠️ P8 / P9 在改动前必须是红的」），那两条实测都红。
**不修饰成「全部先红后绿」。**

---

## 4 · 变异自查 M1–M10 逐格结果

见 `docs/architecture/module-boundaries.md` §7.25.7 的完整表（含栈顶原文）。摘要：

| # | 结果 |
|---|---|
| M1 | **exit 1**（`2 failed`） |
| M2 | **exit 1**（`1 failed`） |
| M3 | **exit 1**（`1 failed`） |
| M4 | **exit 1**（`DID NOT RAISE`） |
| M5 | **exit 1**（`DID NOT RAISE`） |
| M6 | ⚠️ **exit 0 —— 没打红**（plan 起草期已预判此形） |
| M6b（补） | **exit 1**（`assert '' == 'qwen3:14b'`）；整个 `tests/routing` `32 failed, 147 passed` |
| M7 | **exit 1**（`15 failed, 42 passed`）—— 与 §2 的那 15 条同一批 |
| M8 | ⚠️ **exit 2，红在收集期**（`KeyError: 'qwen3:14b'`）；**对 WBS 验收文件 exit 0（`10 passed`）** |
| M9 | **exit 1**（`4 failed, 1 passed`）⇒ WBS 验收那条确实钉在缺口上 |
| M10 | **exit 1**（`DID NOT RAISE`） |

**8/10 按 plan 预期的形态打红；M6 与 M8 未按预期形态打红，两条都照实登记在 §7.25.7，未修饰。**

---

## 5 · 变异复原的 `sha256` 核对

施加前：

```
f8658cd3ff224f1b5fd295d590187cb84caebaaeefadcc5bb1656d269ee9c1d2  agenerp/routing/router.py
65f79bce189631ec6e3d172439c5b4c5a357658e496dc766084200562aba8f83  tests/routing/test_router.py
3572c24277dc57d298d90de8449f3f50c84368945f6b44e867cf5cf4ea8ab77b  agenerp/routing/capabilities.py
```

M1–M10 全部施加并复原之后 `shasum -a 256` 与上表 `diff` → **无差异**（`SHA256 逐字相同 ✅`）。

---

## 6 · D1（502 vs 503）的本轮亲自实测

plan 的 `Deferred But Adjudicated` D1 引的是起草期的数。**执行期没有采信，自己跑了一次**
（临时探针 `tests/unit/test_b7_probe_tmp.py`，跑完即删，`git status --porcelain` 无残留）：

```
STATUS = 502
TEXT   = 点名的模型 'typo-model' 不在候选档案里；候选是 ['fake-explainer']
```

⇒ 与 plan 所写的形态吻合。**修法面在 `agenerp/serve/**` = 工作项 10（P1.8a，plan 预算 `2/2` 已满）⇒ 本 plan 不动，
已追加登记到 `docs/masterplan/STATE.md` §3。**

---

## 7 · 收口三条命令（原文 + 退出码）

```
python3 tools/gates/check_expected_red.py
→ exit 0 ·「门禁 29 项：预期红 0，绿 29，跳过 0」·「✅ 与预期红名单完全一致」

python3 -m pytest tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments -q -m "not live"
→ exit 0 ·「1314 passed, 23 skipped, 7 deselected」（基线 1299 ⇒ +15，只增不减）

ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui
→ exit 0 ·「All checks passed!」
```

新增 15 条的构成：`tests/routing/test_router.py` **+9**（⑤ 节，`170 → 179`）·
`tests/unit/test_configured_model_is_the_one_used.py` **+6**（P8 参数化 5 条 + P9 一条，`6 → 12`）。

### ⚠️ verification scope limited

- **未跑整仓 `python3 -m pytest tests -q -m "not live"`** —— **已知基线即红**：`gates` × `tools`
  的环境泄漏已单列立案于 `docs/backlog/gates-and-tools-leak-env-across-directories.md`。
  跑的是 plan 与 `gates.yml` 指定的**六目录**口径。
- **未跑 `-m live`** —— `tests/routing/test_live_endpoint.py` 需要真端点与凭据；
  plan 的 `## Infrastructure And Config Prereqs` 逐字**不要求**跑它。
- **未经 CI 服务端复跑。**

---

## 8 · 红线自证

⚠️ **执行期 HEAD 移动了，先把这件事说清楚。** 起跑基线是 `433d2ca`；执行过程中人侧落了两个 commit
（`42fa183` CP9 复盘 · `9be3007` P2 规划落地），HEAD 变成 **`9be3007`**。
那两个 commit 动的是 `docs/masterplan/02-WBS.md` / `STATE.md` / `missions/p2-views.json` /
`docs/backlog/p2-views-roadmap.md` / `docs/audits/` —— **本 loop 一个字节都没写过它们中的前三个**。

⚠️ **一件必须照实说的事**：本 loop 按 plan Phase 3 往 `docs/masterplan/STATE.md` §3 **追加**的那条
needs-human（`2026-08-26T10:15Z` · 502/503），在人侧 `9be3007` 提交时**working tree 里就有它**，
于是**被一并带进了那个 commit**。⇒ 那 8 行现在署在人的 commit 名下，而内容是 loop 写的。
**它仍然满足红线 5**（`git show 9be3007 -- docs/masterplan/STATE.md | grep -c '^-[^-]'` → **0**，零删除、纯追加），
**但署名不准这件事不修饰、不掩盖**，在此登记。

### 本 loop 未提交改动的自证（`vs HEAD = 9be3007`）

```
git diff --name-only HEAD -- tests/gates/ .github/workflows/ missions/ docker-compose.yml \
    industry-packs/ docs/masterplan/
→ 无输出                                                （红线 1 / 2 / 3 / 5）

git show 9be3007 -- docs/masterplan/STATE.md | grep -c '^-[^-]'   →   0        （红线 5：只追加）

git -C /Users/lize/Documents/ChatGPT/XM status --porcelain   →   无输出        （红线 6）
git -C /Users/lize/Documents/ChatGPT/XM rev-parse HEAD
→ 1c622c8119755b36992c54ba98fbf6840cd22ed4  ==  evidence-repo.env 的 XM_SHA   逐字相同
```

**本 loop 改动的全部文件（`git diff --name-only HEAD` 逐字）**：

```
agenerp/routing/router.py
docs/architecture/model-management.md
docs/architecture/module-boundaries.md
docs/logs/2026/08-26.md
docs/plans/p1-insight/2026-08-26-1728-1-routing-honors-configured-model.md
tests/routing/test_router.py
tests/unit/test_configured_model_is_the_one_used.py
?? docs/evidence/p1-routing-configured-model/        （本文件所在目录，新增）
```

- **未生成任何运行时 Server Script**（红线 7）。
- **未改项目名 / 包名 / 命名空间**（红线 4）；`agenerp/routing/__init__.py` 的 `__all__` **逐字未变**
  （`git diff -- agenerp/routing/__init__.py` 无输出）⇒ `tests/routing/test_adapter.py:526` 那条六元组断言未被触动。
- **`docs/masterplan/DECISIONS.md` 未触碰**（红线 3）；**未新增任何 `R-x` 重开记录**。
- **`docs/architecture/model-management.md` 的三张 `machine-read` 表一格未动** ——
  `git diff` 对该文件只有 **1 行删除**（`AGENERP_LLM_MODEL` 那一行的原文，就地改准），
  且 `python3 -m pytest tests/routing/test_capabilities.py -q` → **exit 0（`19 passed`）**（同构判据未红）。
- **`docs/architecture/module-boundaries.md` 是纯追加** ——
  `git diff -- docs/architecture/module-boundaries.md | grep -c '^-[^-]'` → **0**
  ⇒ **§7.13–§7.24 一行未改**。
- **`missions/p2-views.json`**：人侧 `9be3007` 的产物，本 loop 未写、未提交。
