# 2026-08-27-0045-1 整仓一把跑的 23 个 error —— 根因是一处进程级 `pytest.skip` 重绑，不是环境泄漏；立案文件就地改准 + 门禁模块 import 纯度的登记与判据

> Plan Status: draft
> Mission: p1-insight
> Work Item: 10b（`docs/masterplan/02-WBS.md` 的 `P1.8a-fix` 行 / roadmap 工作项 `10b`）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个预算，本 plan 用掉最后一格；该格此前 `1/2`，只有 `2026-08-25-1118-1`）
> Last Reviewed: 2026-08-27
> Source: `docs/backlog/gates-and-tools-leak-env-across-directories.md` 逐字标着「**## 未查明的一格（不许猜根因）**：具体是哪个 fixture / 哪一行把站点相关的环境留在了进程环境里，本轮没查」——
> 本 plan 起草期用可复跑实验把那一格填掉了，**结论与该文件登记的「方向」相反**：不是环境泄漏，是 `tests/gates/test_explain_service_live.py:80` 把**全局 `pytest` 模块**的 `skip` 属性重绑成了一个 `pytest.fail`。
> 该 backlog 条目由 plan `2026-08-25-1118-1`（工作项 10b）的收口步产出，并在该 plan `## Deferred But Adjudicated` 第 1 条逐字登记 `Successor Required: yes` —— **本 plan 就是那个后继**。
> Related: `docs/plans/p1-insight/2026-08-25-1118-1-gates-l2-live-intermittent-red.md`（本条的出处与 `Successor Required: yes`）·
> `docs/plans/p1-insight/2026-08-25-1423-1-explain-service-compose-and-same-origin.md`（那一行重绑的落地 plan，工作项 10 / P1.8a）·
> `docs/plans/p1-insight/2026-08-25-1743-1-desk-sidebar-cmdk-and-live-ui-gate.md`（**同一危害的在仓先例与安全形态**，`tests/ui/test_sidebar.py:16-20` 逐字写出「属进程级污染」）·
> `docs/plans/p1-insight/2026-08-26-2213-1-ci-coverage-registration-drift.md`（`machine-read` 登记表 + 双向同构判据的形态来源）
> Audit: required

## Current Baseline

**以下每一行都是起草期在 `eb82f19` 干净树上实跑取证，命令与输出逐条可复跑，不引任何转述。**

### B0 · 仓库基线（收尾要原样复跑，逐条同值或只增不减）

| 命令 | 起草期实测 |
|---|---|
| `git rev-parse HEAD` | `eb82f192a0d80b1b82331fd4202eafb205578deb` |
| `git status --porcelain` | 起草前 **0 行**；起草后**只有本 plan 文件一条** `?? docs/plans/p1-insight/2026-08-27-0045-1-…md`。⚠️ **收尾复跑时这一格必然不是 0**（届时是本 plan 的交付物），P4-4 逐条核的是「除本 plan 交付物外零改动」，**不是「仍为 0」** |
| `python3 tools/gates/check_expected_red.py` | exit 0 · `门禁 29 项：预期红 0，绿 29，跳过 0` |
| `python3 -m pytest tests/unit -q` | exit 0 · `847 passed, 17 skipped` |
| `python3 -m pytest tests/unit tests/tools -q` | exit 0 · `928 passed, 29 skipped` |
| `python3 -m pytest tests/contracts tests/routing tests/context -q` | exit 0 · `386 passed, 1 skipped` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` | exit 0 · `All checks passed!` |

### B1 · 缺陷本体今天仍在，且**比立案时更严重**

| # | 命令 | 起草期实测 | 立案文件（2026-08-26）记的 |
|---|---|---|---|
| 1 | `python3 -m pytest tests -q -m "not live"` | `1353 passed, 44 deselected, **23 errors**` | `1301 passed, 33 deselected, **12 errors**` |
| 2 | `python3 -m pytest tests/gates tests/tools -q -m "not live"` | `110 passed, 26 deselected, **12 errors**` | `109 passed, 26 deselected, 12 errors`（同形态） |
| 3 | `python3 -m pytest tests/gates tests/unit -q -m "not live"` | `876 passed, 32 deselected, **11 errors**`，**11 条全在 `tests/unit/test_desk_sidebar_body.py`** | **该文件当时还不存在这一格，立案文件一个字没提** |

🔴 **第 3 行是本 plan 最重的一条事实**：污染面**已经长进 `tests/unit`** ——
那是 `missions/p1-insight.json:16` 的 `commands.test`（`GATE_VERIFY` 子进程复跑的那条）
与 `.github/workflows/gates.yml:603-604` 第 ① 步**唯一都跑**的目录。
⚠️ **这句话要说准，不许放大**：今天 `GATE_VERIFY` 与 CI 第 ① 步都**只**跑 `tests/unit` 这一个目录
（`python3 -m pytest tests/unit -q` → `847 passed, 17 skipped`，exit 0）⇒ **它们今天并没有被污染到**。
成立的是**接近程度**：污染的落点已经从「只碰得到 `tests/tools`」变成「碰得到 `tests/unit` 里的具体 11 条」，
**只差一个「与 `tests/gates` 同进程」的调用方式**。**不得写成「`GATE_VERIFY` 已经被污染」。**
立案文件的标题、`## 事实` 表、以及那句「**触发条件锁定在「`tests/gates` 与 `tests/tools` 进同一个 pytest 进程」**」
**在今天的仓库上都已不成立**：触发条件是「`tests/gates` 与**任何一个含运行期 skip 的目录**同进程」。

### B2 · 根因已证实，不是推断，也不是立案文件登记的那个方向

**立案文件逐字登记的「方向」**：

> 方向（**是方向不是结论**）：`tests/tools/test_live_conformance.py` 的 skip 判定走 `agenerp.site.client_from_env`，
> 它读 `AGENERP_SITE`；而 `tests/gates/**` 里有门禁会设置站点环境。**未经证实，不得当结论用。**

**三条实验逐条把它排除，并锁死真因：**

- **E1 · 二分定位到单个文件。**
  `python3 -m pytest $(ls tests/gates/test_*.py | grep -v explain_service_live) tests/tools/test_live_conformance.py -q -m "not live"`
  → **`29 passed, 12 skipped, 20 deselected`，零 error**；
  同一条命令**只把 `tests/gates/test_explain_service_live.py` 加回去** → **`12 errors`**。
  ⇒ 触发者是且只是那一个文件。
- **E2 · 环境变量这条路被直接排除。** E1 的两次运行**在同一个 shell、同一份环境**下跑；
  起草期 `env | grep -i agenerp` 实测**没有 `AGENERP_SITE`**（只有 `AGENERP_TODO` / `AGENERP_LLM_MODEL` / `AGENERP_MISSION`）。
  ⇒ 「站点相关环境被留在进程环境里」在本机**根本没有发生过**，而缺陷照样复现。
- **E3 · 直接量到全局对象被改。** 不经 pytest，裸 import 那个模块：
  ```
  before = pytest.skip                                   # <_pytest.outcomes._Skip object>
  exec_module(tests/gates/test_explain_service_live.py)
  after  = pytest.skip                                   # <function _skip_is_a_failure_here>
  before is not after                                    # True
  ```
  ⇒ **`pytest.skip` 被换成了一个必定 `pytest.fail` 的函数，换的是全局 `pytest` 模块本身。**

**肇事那一行逐字**（`tests/gates/test_explain_service_live.py:80`）：

```python
_BODY.pytest.skip = _skip_is_a_failure_here
```

`_BODY` 是按路径加载的 `tests/unit/test_explain_service_body.py`，
而 `_BODY.pytest` **就是全局 `pytest` 模块对象本身**（不是副本）
⇒ 赋值改的是 `pytest.skip`，**整个进程里此后每一次 `pytest.skip(...)` 都变成 `pytest.fail(...)`**。
`tests/` 下目录的收集顺序里 `gates` 排在 `routing` / `tools` / `ui` / `unit` **之前**
⇒ 后四个目录的每一条运行期 skip 都会变成 error。

### B3 · 这件事**仓库自己早就写下来了**，而立案文件写的是另一个方向

`tests/ui/test_sidebar.py:16-20` 逐字：

> 3. 把断言体的 `_unavailable` **这一个名字**重绑成 `pytest.fail`。
>    ⚠️ **重绑的是断言体模块自己的属性，不是 `pytest` 模块的属性** ——
>    先例那种 `_BODY.pytest.skip = …` 改的是全局 `pytest` 模块，属**进程级污染**
>    （同一轮里别的测试文件也被改）。本形态没有这个副作用……

- 该文件由 plan `2026-08-25-1743-1` 落地，**`git log --date=short` 实测日期 2026-08-26**；
- 立案文件 `docs/backlog/gates-and-tools-leak-env-across-directories.md` 的 `> Created:` 逐字也是 **2026-08-26**。

⇒ **同一天，仓里一处逐字写明机制，另一处登记了一个相反的方向，且没有任何判据把两者对上。**
这是本仓最近连续三个 plan 处置的同一失败形态（`2026-08-26-2101-1` 第 1 例 · `2026-08-26-2213-1` 第 2 例）的**第 3 例**，
但**与前两例有一处决定性差别**：前两例是「处置做完了、登记没跟上」，本例是「**登记把后来者指向了错误的方向**」——
一个照着立案文件去查的人，会去翻 fixture 与环境变量，而真因是一行赋值。

### B4 · 污染面只有一处，不是多处（已逐文件实测）

对 `tests/gates/test_*.py` **十二个文件逐个**做 E3 那道量测：

| 结果 | 文件 |
|---|---|
| **MUTATED** | `tests/gates/test_explain_service_live.py` |
| clean | 其余 **11** 个（`test_agent_seam_stays_swappable` · `test_assertions_have_no_escape_hatch` · `test_customization_roundtrip_delete` · `test_evidence_gate_blocks_single_hop` · `test_explain_cost_accounting` · `test_insight_rule_ablation` · `test_normalizer_idempotent` · `test_seed_dataset_absurdity` · `test_snapshot_diff_structured` · `test_tool_execution_live` · `test_zero_dep_boot`） |

`grep -rn 'pytest\.skip\s*=' tests/ --include='*.py'` → **命中一处**（`test_explain_service_live.py:80`）+ 一处注释（`tests/ui/test_sidebar.py:18`）。

⚠️ **量测有一个前提，漏了它复跑不出来**（独立评审第 1 轮实测指出）：
`pyproject.toml:40` 逐字 `pythonpath = ["."]` 是 **pytest 才读的配置**，裸 `python3 -c …` 不吃它
⇒ 子进程量测**必须自己把仓根放进 `sys.path`**（`PYTHONPATH=.` 或等价），否则十二个文件里
凡 import 了 `agenerp` 的都会在 import 期抛 `ModuleNotFoundError`。
⇒ **判据必须把「import 失败」判成红，不能吞掉当「干净」**（见 `D6`）。

### B5 · 修**因**是人的活；收**容**是 loop 的活，且已实测可行

**修因**：`tests/gates/**` 在 `AGENTS.md` 红线 1 内，**loop 改任何一个字节都是停机**。
修法本身已经不需要设计 —— **在仓先例就是安全形态**（B3 的 `tests/ui/test_sidebar.py`：重绑断言体自己的属性，不碰 `pytest` 模块）。
本 plan 把「怎么改、改哪一行、改完之后哪条判据会红、该怎么把表跟上」写成人可以直接执行的一段，**不代人改**。

🔴 **起草稿在这里写错过一句，照实记在最显眼处，不移到脚注**：首稿逐字写着
「让它变绿**必须**改 `tests/gates/**`（红线 1）」—— **那句是假的**，独立评审第 1 轮 B-3 实测推翻，
起草者随后在 `/tmp` 隔离副本上独立复现，接受推翻。**一个红线外的收容层就能让整仓一把跑退 0，且不削弱那份门禁。**

**收容层的实测形态与实测结果**（两侧各自跑过，数字逐条列出，不转述）：

| # | 形态 | 整仓 `pytest tests -q -m "not live"` | `AGENERP_LIVE=1 pytest -m live tests/gates/test_explain_service_live.py -q` |
|---|---|---|---|
| 0 | 无收容（今天） | `1353 passed, 44 deselected, **23 errors**` | `6 failed`（红，零 skip） |
| 1 | ❌ `tests/conftest.py` + autouse fixture | 仍 `23 errors` —— **autouse fixture 自己就是 setup 链的一环，跑不到 fixture setup 前面** | 未测 |
| 2 | ❌ `tests/conftest.py` + hook | `1352 passed, 23 skipped` 但 **`1 failed`** | `6 failed` |
| 3 | ⚠️ 目录级 `tests/unit/conftest.py` + `tests/tools/conftest.py`，`_REAL_SKIP` 取自 **私有** `_pytest.outcomes.skip` | `1353 passed, 23 skipped`，零 error | `6 failed`（未削弱） |
| 4 | ✅ **仓库根 `conftest.py`** + `pytest_collection_finish` 摘钩 + `pytest_runtest_setup` 按目录回绑 | `1353 passed, 23 skipped`，零 error | `6 failed`（未削弱） |

**形态 2 为什么出局，是实测出来的，不是推演**：`tests/` 下只要多一个 `.py` 文件，Python 就会建出
`tests/__pycache__/`，而 `.github/workflows/gates.yml:628-641` 第 ⑦ 步扫的是 `ls -d tests/*/`
⇒ **CI 元判据当场红**，同时 `tests/unit/test_ci_coverage_registration.py::test_01` 也红
（起草者实跑到的报文逐字 `仓里有、表里没有：['__pycache__']`）。修它要动 `.github/workflows/**`（**红线 2**）⇒ **出局**。
**放在仓库根则 `__pycache__` 落在 `tests/` 之外，第 ⑦ 步保持绿**（评审逐字模拟第 ⑦ 步跑过，两种位置各一次）。

**形态 4 未削弱裁判，是双向实测的**：单独跑那份门禁 `6 failed / 零 skip / exit 1`，与未打补丁**逐字相同**；
整个 `tests/gates` 目录 live 模式下打不打补丁都是 `6 failed, 1 passed, 29 deselected, 19 errors`。
唯一移动的六条**全在 `tests/unit/test_explain_service_body.py`**（`FAILED` → `SKIPPED`）——
而那正是 `tests/gates/test_explain_service_live.py:62-66` 逐字写明的**断言体应有行为**
（「断言体住在 `tests/unit/`，日常那一轮不该因为没起服务就整轮红，所以它**够不到服务时 skip**。门禁这一份不行」）
⇒ **收容层同时恢复了两份被写死的契约，不是拿一份换另一份。**

### B6 · 今天没有任何判据拦得住这一形态

- `tools/gates/check_expected_red.py` 判定面写死 `tests/gates` 且**默认注入 `-m "not live"`** ⇒ 那个文件在默认模式下被整体排除，判定器**看不见**它。
- CI 的 `unit-and-contracts` 把目录**逐个分开跑**（`gates.yml:603-625` 第 ①–⑥ 步），`tests/gates` 走另一条路
  ⇒ **两个目录从未进过同一个 pytest 进程，CI 因此永远绿**。
- **没有任何判据在盯这件事** —— 取证是两条，不是一条（独立评审第 1 轮 S-5 指出单靠 grep 立不住）：
  ① `grep -rn 'pytest\.skip\s*=' tests/unit tests/contracts tests/routing tests/context tests/experiments tests/ui` → **零命中**；
  ② 更强的一条：**把那一行删掉之后没有任何判据转红** —— 这一条由 Phase 3 的 **N10** 在 `/tmp` 副本上实测给出，
  **起草期只写成待测假设，不写成结论**（硬约束②：预测在前、结果在后）。

⇒ **CI 绿 ≠ 没有缺陷。今天挡住它的不是判据，是「碰巧分开跑」这一个 CI 布局细节，而那个布局在红线 2 内、随时可能被人正当地改。**

### B7 · 预算

`docs/plans/p1-insight/*.md` 起草时实点 **28 份**（本 plan 落盘后 29 份），按 `> Work Item:` 首行归组：
工作项 `10b` 名下**只有 1 份**（`2026-08-25-1118-1-gates-l2-live-intermittent-red.md`）⇒ 该格 **1/2**，
本 plan 用掉最后一格，**不需要人加预算、不需要在 `02-WBS.md` 拆行**（红线 5 不触碰）。

**剩下的缺口一句话**：一个**已确认、可复现、代价明确**的缺陷，它的立案文件把后来者指向了错误的根因，
而真因在仓库另一处被逐字写明过 —— **三份文字互不相识，没有任何判据把它们对上。**

## 归属 —— 独立评审第 1 轮判「非法」，本节逐条应答，并把相反判读原样记下

**先把评审的结论原样摆出来，不修饰**（独立评审第 1 轮，A 项）：

> **A. OWNERSHIP — illegitimate.** 10b is `done`; its 验收 is `gates-l2-live` × 3 green runs,
> which this plan neither touches nor advances. …… Same disease as 2213-2 …… red-line-5 / D-24 overreach.

**四条实读应答。前两条是事实核对，后两条是取舍，取舍处标明它是取舍。**

- **① 「`done` 的格不能派」这条读法**，本仓**最近两个通过独立收口审计的 plan 都与它相反**：
  `2026-08-26-2101-1` 派在工作项 3（`done`）· `2026-08-26-2213-1` 派在工作项 4（`done`）。
  两者的结果面都不是「推进那一行的验收命令」，而是**改准那一格自己的登记面**。
  ⇒ **`done` 本身不构成否决理由**；否则那两个 plan 都该被否，而它们都收口了。
  ⚠️ **这是取舍不是定论**：若人裁定「`done` 即封格」，那两个 plan 与本 plan 一起适用，**本 plan 不争**。
- **② 与 2213-2 的决定性差别，实读 `02-WBS.md` 得出，不是转述**：
  2213-2 被否的那条是 **BL-4 —— P1.9 的状态源列逐字是 `人`**，且交给 loop 的那一项已用尽。
  而 **`P1.8a-fix` 行的状态源列逐字是 `MD:p1-explain`**（`02-WBS.md` P1 表最后一列），
  **是一行明写交给 mission-driver 的工作项**，不是人保留行。
  ⇒ 2213-2 的病因（**权属**）在本 plan 上**不成立**；能不能派要另找理由，不能引 2213-2。
- **③ 主交付面 100% 落在 10b 自己的产物上**，这正是 2213-2 缺的那一条（它逐字自承「本 plan 100% 的交付内容都归别的格」）：
  `docs/backlog/gates-and-tools-leak-env-across-directories.md` 的文件头逐字
  「由 plan `docs/plans/p1-insight/2026-08-25-1118-1-…` 的**收口步产出**」，
  且 1118-1 的 `## Deferred But Adjudicated` 第 1 条逐字 `Successor Required: yes`。
  ⇒ **本 plan 改的是 10b 自己写下的那份登记，用的是 10b 自己剩下的那一格预算。**
- **④ 「由人定要不要排期」那句，全文引，正面回答**（评审第 2 条要求）：
  1118-1 逐字 `Successor Required: yes —— 已写进 docs/backlog/gates-and-tools-leak-env-across-directories.md，由人定要不要排期。`
  立案文件文件头逐字 `> Status: deferred（**登记，不处置**；处置需要人排期）`。
  **本 plan 的读法**：这两句管的是「**修那一行**」——而修那一行落在 `tests/gates/**`（红线 1），
  loop 本来就无权，**本 plan 也逐字不做**（Non-Goal 1、`D4`）。
  这两句**管不到**的是同一份文件里另一段逐字写着的东西：
  `## 未查明的一格（不许猜根因）：具体是哪个 fixture / 哪一行……本轮没查` +
  `方向（是方向不是结论）……**未经证实，不得当结论用**`。
  ⇒ **那是立案文件自己敞着的一格，本 plan 填的就是它。** 填空不是处置，**改准登记也不改变它的阻塞级别**（Non-Goal 6）。

**本 plan 就此不再往前推一步，两处硬边界写死**：

1. **不回退 10b 的状态词**，不改 `docs/backlog/p1-insight-roadmap.md` 的状态块，不改 `02-WBS.md` 一个字节（红线 5）。
2. **修那一行需要的是一条新 WBS 行，那是人的动作，本仓有两次在仓先例**：
   `P1.1-fix` 行逐字「（人 2026-08-26，同 `P1.8a-fix` 先例）：P1.1 已 `done` 且判据仍然成立，
   本条是**交付后发现的活缺陷**，不回退 P1.1 的状态，**给它独立的 plan 预算**」。
   ⇒ 本缺陷同形。**loop 不得自行加行**（`DECISIONS.md` D-24），
   本 plan 只把「那一行该写成什么」写清楚交人（P4-2），**不代人写进 `02-WBS.md`**。

⚠️ **若独立评审在下一轮仍判非法**：本 plan 按 `2026-08-25-0119-1` / `2026-08-26-2213-2` 的先例
**停在 `deferred`**，B0–B7 的实测证据留在盘上不删，**不转 `active`、不执行**。

## Goals

- **G0** **`python3 -m pytest tests -q -m "not live"` 退 0、零 error** —— 由一个**红线外**的收容层达成
  （仓库根 `conftest.py`，形态 4）。**收的是容，不是因**：肇事那一行原样留着，
  那份门禁单独跑时的 `6 failed / 零 skip / exit 1` **一个字节不变**。
- **G1** `docs/backlog/gates-and-tools-leak-env-across-directories.md` 的**标题、事实表、「未查明的一格」、「为什么此刻不阻塞」、「代价」、「重开事件」六处**与今天的仓库一致：
  根因写实（一行进程级重绑）、触发条件写实（不再是「与 `tests/tools`」）、影响面写实（**已含 `tests/unit`**）、修法与归属写实（红线 1，归人，附在仓先例）。
  原文**逐字留痕**进证据目录，不是删了了事。
- **G2** `docs/architecture/module-boundaries.md` 新增 **§7.27**，含一张成对 `machine-read` 标记包围的
  **「门禁模块 import 纯度」登记表**，作为「哪些 `tests/gates/**` 模块在 import 时改进程全局状态、改的是什么、炸到谁」这件事在本仓的**单一真相源**。
- **G3** 新增判据 `tests/unit/test_gate_import_purity.py`，把 §7.27 的表与**子进程实测结果**钉成双向同构：
  ① 新增一处污染而表没跟上 → 红 · ② 人把那一行修掉而表没跟上 → 红 · ③ 表被删空 → 红（存活守卫）·
  ④ 纳管的门禁文件集合漂移（新增/删除 `tests/gates/test_*.py`）而表没跟上 → 红 · ⑤ 表里写的「被改的属性名」与实测不符 → 红。
  **今天绿**（表恰好一行，与 B4 实测一致）。
- **G4** `docs/masterplan/STATE.md` §3 **只追加**：一条证据行（本 plan 的处置与复跑）+ 一条 needs-human（那一行修法在红线 1 内，附逐字修法与「修完之后要把表改成什么」）。
- **G5** 变异自查 N1–N8 逐条**先写死预测再施加**，**全部落在 `/tmp` 的整仓副本上，活仓工作树零变异**。

## Non-Goals

1. **不改 `tests/gates/**` 一个字节**（红线 1）。**特别地：不改那一行 `_BODY.pytest.skip = …`。**
   ⇒ 本 plan **不修因**，收口时**不得写成「已修」**，只能写成「**已收容，因仍在，修因归人**」。
   ⚠️ **「不修因」不等于「不作为」** —— 起草稿曾用「必须改红线内」当作不作为的理由，那句已被实测推翻（B5），
   G0 的收容层就是红线外能做的那一半，**做满**。
2. **不改 `.github/workflows/**` 一个字节**（红线 2）。本 plan **不新增门禁**，`门禁 29 项` 不变；
   新判据落在 `tests/unit/`，由既有的第 ① 步与 `commands.test` 自动复跑，**一行 workflow 都不用动**。
3. **不改 `missions/**` 一个字节**（自设围栏；⚠️ 它**不在** `AGENTS.md` 七条红线内，
   禁令出处是 `docs/context/ai-autonomy-policy.md:87` 的 Protected Areas 标 `blocked` —— **两者不许混为一谈**）。
4. **不改 `docs/masterplan/**` 已有的任何一行**（红线 5）；只往 `STATE.md` §3 追加。
5. **不改断言体去规避污染** —— `tests/unit/test_explain_service_body.py` 与 `tests/unit/test_desk_sidebar_body.py`
   一个字不动。把被害者改成「不用 `pytest.skip`」是**用改被害者换绿**，会让真因永久隐形。
   ⚠️ **收容层与它的区别要说准**：收容层**不碰任何断言、不删任何红**，它只把一次进程级重绑的作用域
   收窄回它自己的目录；被害者文件一个字节不动，且**恢复的是被害者自己文档里写死的行为**（B5 末段）。
   ⚠️ **同样不做**：给整仓跑加 `--ignore=tests/gates`、改 `check_expected_red.py` 的判定面、
   或把红改成 skip —— 三者都是**用掩盖换绿**。
6. **不把「整仓一把跑」写进 `02-WBS.md` 的验收列，也不改立案文件的 `> Status:` 那一行。**
   ⚠️ **这里要正面交代，不许绕**：立案文件的重开事件逐字是
   「任何人把「整仓一把跑」写进某条验收命令时，这一条立刻从 `deferred` 变成阻塞项」，
   而本 plan 的 `Closure Gates` **确实**把 `pytest tests -q -m "not live"` 退 0 写成了收口条件
   ⇒ **本 plan 主动触发了那条重开事件，并在同一份交付里当场满足它**（G0 的收容层）。
   **不做的是另外两件**：① 不动 `02-WBS.md`（红线 5）；② 不把立案文件的 `> Status: deferred` 改成别的词
   —— 那一行管的是「**修因**要不要排期」，而修因归人（`D4`），级别由人定。
7. **不给 `tools/gates/expected-red.txt` 加任何一行**（本 plan 不让任何门禁转绿也不让任何门禁转红，无行可加可划）。
8. **判据不纳管 conftest / fixture 期的污染** —— 它量的是**模块 import 期**的全局改动。
   理由与残余风险见 `D2`，并**逐字写进判据文件头**，不默默省掉。
9. **不裁定「整仓一把跑该不该进 CI」**。那要改 `.github/workflows/**`（红线 2），归人。
10. **不把仓库根 `conftest.py` 塞进 `ruff` 的作用域** —— 那八个目录的字面量是 `gates.yml:682` 的 `lint` job
    要照抄的真相源，改它等于改 CI 作用域（红线 2）。本 plan 只**登记**这条覆盖缺口（`D8`），并在本机手跑
    `ruff check conftest.py` 留证，**不假装它进了 CI**。

## Task Route

- Type: `bug investigation`（根因证实那一半）+ `implementation-only change`（判据那一半）+ `verification or audit work`（登记面改准）
- Owner Docs: `docs/architecture/module-boundaries.md` §7.27（新增，落点节）· §7.21 `D-b-10`（**纯指针追加**，10b 的落点在那里）·
  `docs/backlog/gates-and-tools-leak-env-across-directories.md`（立案面自身）·
  `docs/masterplan/STATE.md` §3（**只追加**）
- Skill Selection Basis: 实读 `docs/skills/README.md` 后**未选任何 skill** —— 本 plan 的三半
  （二分定位实验 / 写一条子进程量测判据 / 逐条改准登记文字）都不匹配任何既有 skill 的输入-输出约定。
  收口侧的独立审计口径沿用 `docs/skills/closure-audit-prompt.md`（不采信自报，逐条对活仓取证）——
  **那是审计者的输入，不是本 plan 的执行 skill**。

## Infrastructure And Config Prereqs

No infra prereqs beyond existing baseline —— 本 plan 全程离线：**不起 docker 栈、不打任何活站点、不调任何模型端点、零新增依赖**（`pyproject.toml` 一行不动）。
变异用的整仓副本落在 `/tmp`（`tar` 管道拷贝，每条施加后丢弃整份副本重新拷贝），用完删。

## Execution Plan

### Phase 1 — 把「未查明的一格」用可复跑实验填掉，落成证据

Status: planned
Targets: `docs/evidence/p1-gate-import-purity/`（新建）
Skill: `none`
Prereqs: 无

- Item Types: `Proof`（4/4，本阶段统一类型）
- 本阶段**一个字的产品代码 / 判据代码都不写**，只取证。

- [ ] **P1-1 `Proof` · 原样复跑 B1 三条并逐条记退出码与末行原文。**
      `python3 -m pytest tests -q -m "not live"` · `… tests/gates tests/tools …` · `… tests/gates tests/unit …`。
      ⚠️ **与立案文件的数逐条对照并写出差值**（`12 → 23`、新增的 11 条落在哪个文件），
      **不许把差值说成「测试变多了」** —— 要指名是 `tests/unit/test_desk_sidebar_body.py` 这一格新长出来的。
  - Skill: `none`
- [ ] **P1-2 `Proof` · 二分定位（E1）与环境排除（E2），两条命令原文 + 输出全文进证据。**
      E2 必须**同时**记下 `env | grep -i agenerp` 的实测（键名可留、值一律 `<redacted>`），
      证明「`AGENERP_SITE` 根本没设过」而缺陷照样复现 ⇒ 立案文件那个方向被排除。
  - Skill: `none`
- [ ] **P1-3 `Proof` · 直接量测（E3）+ 十二文件逐个量测（B4），脚本与输出全文进证据。**
      量测必须在**子进程**里做（一个进程只 import 一个门禁模块），否则前一个模块的污染会污染后一个的判定 ——
      **这一点本身就是判据要写成子进程的理由，写进证据而不是只写进代码注释。**
  - Skill: `none`
- [ ] **P1-4 `Proof` · 把 B3 的两处日期钉死**：`git log --date=short -1 -- tests/ui/test_sidebar.py`
      与立案文件 `> Created:` 那一行，逐字进证据。**这是「同一天、两处相反」这句话的唯一凭据，不许口述。**
  - Skill: `none`

Exit Criteria:

- [ ] `docs/evidence/p1-gate-import-purity/README.md` 存在，含 §1 复跑基线 · §2 E1/E2/E3 三条实验的**命令原文 + 完整输出** · §3 十二文件量测表 · §4 立案文件与 `tests/ui/test_sidebar.py` 的原文留痕
- [ ] 证据里**明确写出**「立案文件登记的方向已被 E2 排除」，且**不猜**为什么当初会写成那个方向
- [ ] 活仓工作树除 `docs/evidence/p1-gate-import-purity/` 外零改动（`git status --porcelain` 逐条核）
- [ ] `docs/logs/` 更新（可与后续阶段合并成一条收口条目，见 `Closure Gates`）

### Phase 2 — 收容层：让整仓一把跑退 0，且一个字节不碰裁判

Status: planned
Targets: `conftest.py`（**仓库根，新建**）
Skill: `none`
Prereqs: Phase 1（收容层的落点由 P1-2/P1-3 的实测决定，不许照抄本 plan 的 B5 表）

- Item Types: `Decision | Add | Proof`

- [ ] **P2-1 `Decision` · 收容层落在哪里、用什么接缝。** **选定形态 4：仓库根 `conftest.py` + hook。**
      四个备选与否决理由**全部由实测给出**（B5 的表；执行期必须自己重跑一遍，不许采信起草期与评审期的数）：
      · **(1) autouse fixture** —— 否决：那 23 个 error 在 **fixture setup 期**抛出，autouse fixture 自己就是 setup 链的一环，**跑不到它们前面**。实测仍 `23 errors`。
      · **(2) `tests/conftest.py` + hook** —— 否决：`tests/` 下多一个 `.py` 就有 `tests/__pycache__/`，
        `gates.yml` 第 ⑦ 步扫 `ls -d tests/*/` **当场红**，修它要动红线 2。实测报文逐字 `仓里有、表里没有：['__pycache__']`。
      · **(3) 目录级 `tests/unit/conftest.py` + `tests/tools/conftest.py`** —— 否决，**两条理由都要写**：
        ① 目录级 conftest 在**收集到该目录时**才 import，那时 `pytest.skip` **已经被改过了** ⇒ 只能改用**私有 API** `_pytest.outcomes.skip` 取真身，
        本仓无先例且随 pytest 升级会碎；② **纳管面只覆盖今天有 skip 的两个目录**，`tests/routing` / `tests/ui` 将来新增一条运行期 skip 就又漏出去。
      · **(4) 仓库根 `conftest.py`** —— **选定**：rootdir conftest 在一切之前 import ⇒ `_REAL_SKIP` 取到的是**真身，不用私有 API**；
        `__pycache__` 落在 `tests/` 之外 ⇒ 第 ⑦ 步与 §7.26 判据都不受影响；作用域天然覆盖所有目录。
      **残余风险**（不消除，逐条登记在 `D7` / `D8`）：hook 相对其他插件的执行次序是惯例不是契约 ·
      仓库根不在 `ruff` 的八目录作用域里 · 只收容 **import 期**对 `pytest.skip` 的重绑。
  - Skill: `none`
- [ ] **P2-2 `Add` · 写收容层。** 结构边界（**不是实现细节**）：
      · 模块 import 期把真的 `pytest.skip` 存下来（`_REAL_SKIP`）；
      · `pytest_collection_finish`：若 `pytest.skip` 已不是真身，**把被劫持的那个摘下来存着**并把全局还原；
      · `pytest_runtest_setup`：按 `item` 属于哪个目录回绑 —— `tests/gates/` 下的用**被劫持的那个**，其余一律用真身。
      🔴 **文件头必须逐字写清三件事**：① 它**不改也不削弱** `tests/gates/test_explain_service_live.py` 的契约；
      ② 为什么必须是 hook 而不是 autouse fixture；③ 为什么必须在仓库根而不是 `tests/`。
      🔴 **必须写明它不收容什么**：运行期（非 import 期）的重绑 · `pytest.skip` 之外的名字 · `os.environ` / `sys.path`。
  - Skill: `none`
- [ ] **P2-3 `Proof` · 差分实测，六条命令各跑「有收容 / 无收容」两次，输出全文进证据 §5。**
      ① `python3 -m pytest tests -q -m "not live"`（无 → `23 errors`；有 → **零 error**）·
      ② `AGENERP_LIVE=1 python3 -m pytest -m live tests/gates/test_explain_service_live.py -q`（**两次必须逐字相同**：`6 failed`，零 skip，exit 1）·
      ③ `AGENERP_LIVE=1 python3 -m pytest -m live tests/gates -q`（两次必须逐字相同）·
      ④ `python3 tools/gates/check_expected_red.py`（两次都 exit 0 且都 `门禁 29 项`）·
      ⑤ `python3 -m pytest tests/unit -q` 与 `python3 -m pytest tests/unit tests/tools -q`（两次逐条同值）·
      ⑥ **逐字模拟 `gates.yml` 第 ⑦ 步**（`ls -d tests/*/` 与 `COVERED` 比对）**在一次完整跑之后**执行，必须绿。
      ⚠️ ② 与 ③ 是**「没削弱裁判」的唯一凭据**，只跑单文件不算 —— 整个 `tests/gates` 目录也要跑。
      ⚠️ 六条里任何一条两侧不同（②③④⑤⑥）即**当场停下**，按裁判规则 3 原样复跑一次，仍不同就**放弃形态 4 回到 P2-1 重裁**，不许硬推。
  - Skill: `none`
- [ ] **P2-4 `Proof` · `ruff check conftest.py` → exit 0**，并**逐字记下它不在 CI lint 作用域里**（Non-Goal 10、`D8`）。
  - Skill: `none`

Exit Criteria:

- [ ] `python3 -m pytest tests -q -m "not live"` → **exit 0，零 error**（这是 G0，收口时必须给出这条命令的原文与退出码）
- [ ] ②③ 两条 live 命令**打不打补丁逐字相同** —— 有实测输出为证，不是声称
- [ ] `python3 tools/gates/check_expected_red.py` → exit 0 且仍 `门禁 29 项`
- [ ] `python3 -m pytest tests/unit -q` ≥ `847 passed`、`… tests/unit tests/tools -q` ≥ `928 passed`，均 exit 0
- [ ] 第 ⑦ 步模拟在一次完整跑之后仍绿（`ls -d tests/*/` 九个目录，无 `__pycache__`）
- [ ] 仓库根 `conftest.py` 的文件头三问 + 「不收容什么」齐全
- [ ] `docs/logs/` 更新（可与后续阶段合并成一条收口条目）

### Phase 3 — 判据：§7.27 登记表与子进程实测双向同构

Status: planned
Targets: `tests/unit/test_gate_import_purity.py`（新建）· `docs/architecture/module-boundaries.md`（新增 §7.27）
Skill: `none`
Prereqs: Phase 1（表里的行必须由 P1-3 的实测得出，不许照抄本 plan 的 B4）· Phase 2（收容层落地后，P3-4 的量测环境才与收口时一致）

- Item Types: `Add | Decision | Proof`

- [ ] **P3-1 `Add` · 在 `module-boundaries.md` 末尾新增 §7.27**，含成对
      `<!-- machine-read: gate-import-purity -->` / `<!-- /machine-read: gate-import-purity -->` 标记包围的表。
      列：`门禁模块` · `import 时改了进程全局的什么` · `炸到谁（可观测形态）` · `修法归谁` · `实测日期 · 证据路径`。
      🔴 **表里一行对一个 `tests/gates/test_*.py`，十二个一个不少**，干净的那十一个第 2 列逐字写 `—（无）`。
      **不是只登记「出污染的那一个」** —— 独立评审第 1 轮 B-4/B-5 实测指出，只登记污染者会同时踩两个坑：
      ① 「表的行 ⊆ 实扫文件」这条断言变成恒真的废断言，**新增一个门禁文件打不红**；
      ② 人把那一行修掉之后**污染者集合为空**，而存活守卫又要求表非空 ⇒ **判据进入怎么改都红的死锁**。
      按「一行一个门禁模块」写，两个坑同时消失：③ 变成「表的行集合 == 实扫的 `tests/gates/test_*.py` 集合」（实扫来自文件系统，不由表导出）；
      人修完之后只需把那一行第 2 列改成 `—（无）`，表仍非空。
      表外另起两节：**§7.27.1「这张表不管什么」**（至少写明：不管 conftest/fixture 期的污染 ·
      不管 `os.environ` / `sys.path` / `sys.modules` 一类非 `pytest` 模块的全局 · 不管「跑得到」是否等于「测得住」·
      **不管 live 面**——判定器默认注入 `-m "not live"`，那个文件在默认模式下根本不被判定器看见 ·
      并**逐字登记 D5 那条依赖**：今天挡住这个缺陷进 CI 的是 `gates.yml` 的逐目录分跑，而那在红线 2 内）与
      **§7.27.2「翻案条件」**（人修掉那一行时该怎么改表 · 新增/删除门禁文件时该怎么改表 · 判据自己红在 `GATE_VERIFY` 上时怎么办）。
  - Skill: `none`
- [ ] **P3-2 `Decision` · 判据落 `tests/unit/` 还是 `tests/gates/`。**
      **选定 `tests/unit/`。** 备选与否决理由：
      (A) `tests/gates/` —— **红线 1，loop 无权写**，直接出局；
      (B) 新建 `tests/meta/` —— 会让 `gates.yml:631` 的 `COVERED` 集合当场变化 ⇒ **第 ⑦ 步元判据立刻红**，
      而修它要改 `.github/workflows/**`（红线 2）⇒ 出局，**且这一条要在 plan 里写出来**（是实读 `COVERED` 得出的，不是推测）；
      (C) `tests/unit/` —— 既进 CI 第 ① 步，又进 `missions/p1-insight.json` 的 `commands.test`，
      是今天**唯一**两侧都覆盖的目录。**残余风险**：人修那一行时本条会红并拖停循环，见 `D1`。
  - Skill: `none`
- [ ] **P3-3 `Add` · 判据本体。** 形状（**不是实现细节，是结构边界**）：
      · 纳管文件集合 = `sorted(glob("tests/gates/test_*.py"))`，**由文件系统实扫得出，不由表导出**（否则表删空即 `A == B == ∅`，先例 `2026-08-26-2101-1` 起草稿犯过这个病）；
      · 每个文件在**独立子进程**里 import（一个子进程只 import 一个模块），
        比对 import 前后 `pytest` 模块的**属性名 → `id()`** 映射，得出「被改的属性名集合」；
        🔴 **子进程必须自己复现 `pyproject.toml:40` 的 `pythonpath = ["."]`**（pytest 才读那条配置，裸解释器不读），
        否则十二个文件里凡 import `agenerp` 的都会在 import 期抛 `ModuleNotFoundError`；
        🔴 **子进程非 0 退出 / import 抛异常 ⇒ 判据红，逐字打印 stderr**，**绝不吞掉当「干净」**（见 `D6`）。
      · 断言 ①「表里第 2 列非 `—（无）` 的行集合 == 实测出污染的文件集合」·
      ②「每行第 2 列写的属性名 == 实测被改的属性名（逐文件比集合，不比措辞）」·
      ③「**表的行集合 == 实扫的 `tests/gates/test_*.py` 集合**」（新增/删除门禁文件即红；实扫来自文件系统，不由表导出 ⇒ 非恒真）·
      ④ **存活守卫**：成对标记缺失、或截断后解析到 0 行、或解析到的行数 `< 2` ⇒ 当场红并打印该改哪里·
      ⑤ 第 5 列日期可解析 + 证据路径存在 ·
      ⑥ 🔴 **行为级守卫（不比文本，比行为）**：子进程跑
        `python3 -m pytest tests/gates/test_explain_service_live.py tests/unit/test_desk_sidebar_body.py -q -m "not live"`，
        断言 **exit 0 且零 error**（起草期实测：无收容 `11 errors` / 有收容 `11 skipped`，**墙钟 1.15 秒**）。
        这一条是**收容层唯一的守卫** —— 有人删掉仓库根 `conftest.py`，它当场红。
        ⚠️ 它不断言「整仓一把跑绿」（那要 15 秒，太贵），只断言**最小可复现对**上的那一格。
      ⚠️ **解析必须在闭合标记处截断**（`2026-08-26-2213-1` 的 N3 实测撞出过这个缺口：只用起始标记会越界读到下一节的表，**存活守卫从此永不触发**）。
      ⚠️ 失败文案必须**逐字指出该改哪个文件的哪一列**，不许只说「不一致」。
  - Skill: `none`
- [ ] **P3-4 `Proof` · 先红后绿**：判据写完后，先在**未建 §7.27 表**的状态下跑一次（必须红在存活守卫 ④ 上，
      **不是红在断言不相等上** —— 若实测红因不是 ④，照实记并当场把 ④ 补到能触发为止），再补表跑成绿。
      ⚠️ **再多跑一次「人已修完」的预演**：在 `/tmp` 副本上把那一行删掉、把表第 2 列改成 `—（无）`，
      判据必须**绿**（证明 B-5 那个死锁确实不存在）。三次的命令与输出都进证据 §5。
  - Skill: `none`

Exit Criteria:

- [ ] `python3 -m pytest tests/unit/test_gate_import_purity.py -q` → **exit 0**
- [ ] `python3 -m pytest tests/unit -q` → exit 0，条数相对 B0 的 `847 passed` **只增不减**
- [ ] `ruff check … tests/unit …` → exit 0
- [ ] `python3 tools/gates/check_expected_red.py` → exit 0 且**仍是 `门禁 29 项`**（本 plan 不新增门禁）
- [ ] §7.27 三节齐全（表 + 「不管什么」+ 「翻案条件」），且判据文件头逐字写明它**不纳管**什么
- [ ] P3-4 的「先红」有实测输出为证，且红因是存活守卫

### Phase 4 — 立案文件就地改准 + 变异自查 + 收口落盘

Status: planned
Targets: `docs/backlog/gates-and-tools-leak-env-across-directories.md` · `docs/masterplan/STATE.md`（**只追加**）· `docs/evidence/p1-gate-import-purity/` · `docs/logs/2026/08-27.md`
Skill: `none`
Prereqs: Phase 1、Phase 2、Phase 3

- Item Types: `Fix | Proof`

- [ ] **P4-1 `Fix` · 立案文件六处就地改准**（标题 / `## 事实` / `## 未查明的一格` / `## 为什么此刻不阻塞` / `## 代价` / `## 重开事件`）。
      口径**逐字沿用本仓已定的两条，不新造**：**「就地删被证伪的从句」只用于断言性散文；
      「只加时点限定、不改写」只用于带时点的账本 / 交付记录 / 探针快照**（出处 `module-boundaries.md` §7.26.2 末尾）。
      本文件是**断言性散文**（它自称「事实」并给出方向）⇒ 走前者。
      ⚠️ `> Status:` 那一行**保持 `deferred` 不动** —— 改级别是人的事（Non-Goal 6）。
      ⚠️ 原全文**逐字留痕**进证据 §4，删掉的每一句在证据里点名。
  - Skill: `none`
- [ ] **P4-2 `Fix` · 把修法写成人可直接执行的一段**（落在立案文件与 §7.27.2 各一处，**不重复第三处**）：
      指名 `tests/gates/test_explain_service_live.py:80` · 指名在仓安全形态 `tests/ui/test_sidebar.py:16-20` ·
      写明**修完之后 `tests/unit/test_gate_import_purity.py` 会红**、该把 §7.27 的表改成什么才转绿。
      ⚠️ **不许写成 diff 让人照贴** —— 那等于 loop 起草了红线内的改动；只写「哪一行、什么形态、为什么」。
  - Skill: `none`
- [ ] **P4-3 `Proof` · 变异自查 N1–N11，预测先写死在证据 §6 的表里再施加，全部在 `/tmp` 整仓副本上。**
      至少含：N1 表删掉污染那一行 · N2 表整个删空 · N3 闭合标记删掉 · N4 第 2 列属性名改成别的 ·
      N5 给另一个门禁文件加同形态污染（表不动 ⇒ 断言①红）· N6 新增一个 `tests/gates/test_*.py` 空文件（表不动 ⇒ 断言③红）·
      N7 第 5 列证据路径改成不存在 · N8 删掉一个既有门禁文件（表不动 ⇒ 断言③红）·
      **N9 must-stay-green**：只改动被引文件里与本表无关的一段，判据必须**仍绿**（防「一改就红」的假判别力）·
      **N10 must-stay-green · 「人已修完」预演**：把 `tests/gates/test_explain_service_live.py:80` 那一行删掉
      **并**把表第 2 列改成 `—（无）`，判据必须**绿**。
      ⚠️ N10 **只在 `/tmp` 副本上做**，活仓的 `tests/gates/**` 一个字节不碰（红线 1）·
      **N11 删掉仓库根 `conftest.py`** ⇒ 断言⑥必须红（守卫真的守得住收容层）。
      ⚠️ **实测与预测不符时照实记并当场补断言**，不许事后改预测（硬约束②）。
  - Skill: `none`
- [ ] **P4-4 `Proof` · 收尾复跑 B0 全部七条 + B1 三条，命令原文 + 退出码逐条落进证据 §7 与 `## Closure`。**
      ⚠️ **B1 那三条收尾时会从「红」变成「零 error」—— 措辞必须说准**：
      变绿的是**症状**（收容层，Phase 2），**因仍在**（那一行原样留着，红线 1，归人）。
      收口叙述**只能**写成「**整仓一把跑已退 0；肇事那一行未修，修因归人**」，
      **不得**写成「已修复」「缺陷已消除」。**并且必须同时给出**：
      `AGENERP_LIVE=1 pytest -m live tests/gates/test_explain_service_live.py -q` 仍 `6 failed / 零 skip`
      —— 那是「没削弱裁判」的凭据，缺了它上一句就是自报。
  - Skill: `none`
- [ ] **P4-5 `Fix` · `STATE.md` §3 追加两条**：一条 `[open]` 证据行（本 plan 的处置、命令与退出码、红线自证）+
      一条 `[needs-human]`（那一行的修法在红线 1 内，含 P4-2 的三要素）。
      ⚠️ **只追加，`git diff --numstat` 的删除列必须为 0。**
  - Skill: `none`

Exit Criteria:

- [ ] 立案文件六处与今天的仓库一致，且**没有一句是本 plan 新造的推测**
- [ ] `git diff --numstat <BASE> -- docs/masterplan/STATE.md` 的**删除列为 0**
- [ ] N1–N11 逐条有预测、有实测、有 `RESTORED OK`（或「整份副本已丢弃」）的记录；**打不红的变异照实记，不修饰**
- [ ] B0 七条收尾复跑逐条同值或只增不减；B1 三条**照实记为仍红**，并写明原因是「修法在红线 1 内，归人」
- [ ] `docs/architecture/module-boundaries.md` §7.27 与判据双向同构，两侧无一处只在一边存在
- [ ] `docs/logs/2026/08-27.md` 更新（本 plan 一条聚合条目）

## Draft Review Record

- **Independent draft review iteration 1: `needs revision`**（独立子代理，全新会话，非起草者；起草者对每一条都做了独立复现，**不采信自报**）。
  开出 6 条 blocking + 6 条 should-fix，逐条处置如下，**被推翻的地方按原样记，不修饰**：
  - 🔴 **BL-A（归属）判本 plan「illegitimate / 与 2213-2 同病」** —— **未全盘接受，逐条应答见 `## 归属`**：
    实读 `02-WBS.md` 的 `P1.8a-fix` 行，**状态源列逐字是 `MD:p1-explain` 而非 `人`**，
    这正是 2213-2 被否的那条（BL-4：P1.9 状态源为 `人`）**在本 plan 上不成立**；
    且本 plan 主交付面 100% 落在 10b 自己的产物上，与 2213-2 自承的「100% 归别的格」相反。
    **下一轮若仍判非法，本 plan 停在 `deferred`，不转 `active`。**
  - 🔴 **BL-B（B5/D4 的前提是假的）—— 完全接受，且是本轮最重的一条。**
    起草稿逐字写「让它变绿**必须**改 `tests/gates/**`」，评审实测推翻；
    **起草者随后在 `/tmp` 隔离副本上独立跑出四种形态**（B5 的表），确认红线外的收容层做得到。
    ⇒ 新增 **G0 + Phase 2**，`D4` 收窄成「因未修」那一半，原假句**留痕在 B5 最显眼处**。
    ⚠️ **评审自己也更正了一次**：它首报的落点 `tests/conftest.py` **是错的**（会建出 `tests/__pycache__/`
    ⇒ `gates.yml` 第 ⑦ 步当场红，修它属红线 2）。这一条**是起草者先撞到、评审复现并确认的**，两侧都照实记。
  - 🔴 **BL-C（判据①③恒真 / 修完之后死锁）—— 接受**：§7.27 的表改成**一行一个门禁模块、十二行齐全**，
    干净的写 `—（无）`；断言 ③ 改成「表的行集合 == 文件系统实扫集合」⇒ 非恒真，新增/删除门禁文件都红。
  - 🔴 **BL-D（import 失败被当成「干净」/ `sys.path` 未指定）—— 接受**：
    `pyproject.toml:40` 的 `pythonpath = ["."]` 是 pytest 才读的配置，子进程必须自己复现；
    import 失败**判红并打印 stderr**，登记为 `D6`。
  - **SF 逐条接受**：B1 第 3 行的 `GATE_VERIFY` 措辞收窄（不得写成「已被污染」）·
    `tests/ui/test_sidebar.py` 的引用行号 `16-21` → **`16-20`**（多引了两行）·
    B6 第 3 条不能只靠 grep 立论（改成「grep + N10 实测」两条，且实测结论**起草期不预写**）·
    B0 的 `git status → 0` 收尾时必然不成立（改成「除本 plan 交付物外零改动」）。
  - **评审逐条复现为真、无需再争的**：B0 七条基线 · B1 三条数字 · E1/E2/E3 · B4 十二文件 ·
    收集顺序 `gates` 在 `routing`/`tools`/`ui`/`unit` 之前 · 表规 3 下工作项 10b 为 `1/2` ·
    `tests/unit` 同时在 `commands.test` 与 CI 第 ① 步 · `missions/**` 不在 `AGENTS.md` 七条红线内 ·
    新建 `tests/meta/` 会踩 `gates.yml` 第 ⑦ 步 · 指南合规（item 类型 / `Skill:` / Anti-Slacking / 状态一致性）。
- Independent draft review iteration 2: <pending —— 必须由**另一个全新会话**复评，重点复核 `## 归属` 与 Phase 2>

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned（§7.27 · 立案文件 · `STATE.md` §3 追加行 · `docs/logs/`）
- [ ] verification has run：`python3 tools/gates/check_expected_red.py` · `python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/unit tests/tools -q` · `python3 -m pytest tests/contracts tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` ·
      `ruff check conftest.py` · `python3 -m pytest tests/unit/test_gate_import_purity.py -q` ·
      🔴 **`python3 -m pytest tests -q -m "not live"` → exit 0、零 error**（G0；这条命令在本 plan 之前从来跑不绿）
- [ ] **「没削弱裁判」有独立凭据**：`AGENERP_LIVE=1 python3 -m pytest -m live tests/gates/test_explain_service_live.py -q`
      与 `… -m live tests/gates -q` 两条，**打不打收容层逐字相同**，输出原文在证据里
- [ ] scoped verification is not conflated with full verification —— **本 plan 必然要写 `verification scope limited`**：
      未起 docker 栈（因此 `-m live` 那几条**全部红在「环境缺失」上，不是红在断言上** —— 它们证明的是「两侧相同」，**不证明门禁的实质断言成立**）·
      未经 CI 服务端复跑 · **整仓 `pytest tests -q -m "not live"` 虽已退 0，但那是「症状被收容」，`tests/gates/test_explain_service_live.py:80` 的因仍在**，不得读成缺陷已消除
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files
- [ ] 红线自证：`git diff --name-only <BASE> -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md` → 无输出；
      自设围栏 `git diff --name-only <BASE> -- missions/ agenerp/ docker-compose.yml industry-packs/ pyproject.toml tools/` → 无输出；
      `docs/masterplan/STATE.md` 删除列为 0；全程未对 `${XM_PATH}` 发起任何读写；未生成任何运行时 Server Script

## Deferred But Adjudicated

### D1 · 人修掉那一行时，本条判据会红在 `GATE_VERIFY` 上并拖停循环

- Classification: `watch-only residual`
- Why Not Blocking Closure: 这是 P3-2 选 (C) 的**已知代价**，不是遗漏 —— 与 `2026-08-26-2213-1` 的 `D2` 同一取舍、同一措辞。
  缓解已是执行项（P3-3 的失败文案逐字指出该改哪一列；P4-2 把「修完之后该怎么改表」写在人看得见的两处）。
  **不接受「把判据挪出 `commands.test` 以免拖红」这种缓解** —— 那是用降低判别力换绿。
- Successor Required: `no`
- 重开事件：**本仓实际发生一次「人修那一行 → 本条红 → 循环停机」**（有轨迹为证），届时由人裁定是否换落点。

### D2 · 判据只量 import 期，量不到 conftest / fixture 期的进程级污染

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 本 plan 实测到的唯一一处污染就发生在 import 期（B2 的 E3 是裸 import，不经 pytest）。
  把 fixture 期也纳管要在真实 pytest 会话里做前后快照，**判别力提升有限而复杂度陡增**，且今天**零实例**。
  该边界**逐字写进判据文件头与 §7.27.1**，不默默省掉。
- Successor Required: `no`
- 重开事件：**本仓出现第一处 conftest / fixture 期的进程级污染实例**（有可复跑命令为证）。

### D3 · 判据只盯 `pytest` 模块的属性，不盯 `os.environ` / `sys.modules` / `sys.path`

- Classification: `watch-only residual`
- Why Not Blocking Closure: 纳管面窄是**刻意的**：本 plan 的结果面是「已证实的那一类污染有人盯着」，
  不是「所有全局污染都有人盯着」。把纳管面铺开会让判据在正常的 `sys.modules` 增长上频繁误红 ⇒ 判别力下降。
  ⚠️ **立案文件原本登记的方向（环境变量）今天已被排除，但「将来不会有环境变量污染」不成立** —— 这一点写进 §7.27.1。
- Successor Required: `no`
- 重开事件：**本仓出现一处由 `os.environ` / `sys.path` 造成的跨目录测试互扰实例**。

### D4 · 肇事那一行未修 —— 收的是容，不是因

- Classification: `out-of-scope defect`
- Why Not Blocking Closure: 修因**必须**改 `tests/gates/test_explain_service_live.py:80`（红线 1，loop 改一个字节即停机）。
  ⚠️ **起草稿曾把这句写成「让它变绿必须改红线内」，那是假的，已被实测推翻**（B5）：
  收容层在红线外就做得到，且本 plan **已做**（G0 / Phase 2）。所以本条登记的**只剩「因」这一半**，不是整件事。
  按 `P1.1-fix` / `P1.8a-fix` 两次在仓先例，**交付后发现的活缺陷由人在 `02-WBS.md` 拆行**才有独立 plan 预算，
  `DECISIONS.md` D-24 逐字禁止 loop 自行加行 ⇒ **本 plan 把那一行该写成什么写清楚交人**（P4-2），不代人写。
- Successor Required: `yes`（**人** —— 一行修改 + 一行 WBS，红线 1 / 红线 5）
- 重开事件：**人修掉 `tests/gates/test_explain_service_live.py:80` 那一行**（届时按 `D1` 把 §7.27 的表第 2 列改成 `—（无）`），
  或**人在 `02-WBS.md` 为它拆出一行**（届时该行自带 plan 预算，loop 可承接）。

### D5 · `tests/gates` 与其余目录「从未同进程」这条 CI 事实由红线 2 内的布局保证，本 plan 管不到

- Classification: `watch-only residual`
- Why Not Blocking Closure: `gates.yml` 的逐目录分跑是今天唯一挡住这个缺陷进 CI 的东西，
  而它在红线 2 内 ⇒ loop 既不能改也不能加判据钉它。本 plan 只在 §7.27.1 与立案文件里**逐字登记这个依赖**，
  让下一个动 CI 布局的人看得见。
- Successor Required: `no`
- 重开事件：**人把 CI 改成多目录同进程跑**（届时 `unit-and-contracts` 会当场红，且红因已经写在 §7.27 里）。

### D6 · 子进程量测把「import 失败」判成红 —— 已知代价是环境问题会伪装成缺陷

- Classification: `watch-only residual`
- Why Not Blocking Closure: 反过来（吞掉 import 失败当「干净」）是**静默绿**，那才是本仓明令禁止的形态
  （`docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2「绿着的判据未必测它名字说的那件事」）。
  两害相权取「宁可红得吵」。缓解已是执行项：失败时**逐字打印子进程的 stderr 与它的 `sys.path` 前三项**，
  让「环境没配对」与「门禁真的坏了」在文案上一眼分得开。
- Successor Required: `no`
- 重开事件：**本仓实际发生一次「本条红了，但红因是环境而不是门禁」且排查超过一次复跑**（有轨迹为证）。

### D7 · 收容层只收容「import 期对 `pytest.skip` 的重绑」

- Classification: `watch-only residual`
- Why Not Blocking Closure: 纳管面窄是**刻意的**，与 `D3` 同理：铺开会让收容层变成一个「谁都能靠它兜底」的全局魔法，
  那比缺陷本身更难查。今天本仓**只有一处**进程级重绑（B4 实测），收容层对准的就是它。
  ⚠️ **`pytest_runtest_setup` 相对其他插件的执行次序是惯例不是契约** —— 本仓今天零第三方 pytest 插件
  （`pyproject.toml` 无 `pytest-*` 依赖），这条依赖**逐字写进 `conftest.py` 文件头与 §7.27.1**。
- Successor Required: `no`
- 重开事件：**本仓引入第一个第三方 pytest 插件**，或**出现一处运行期（非 import 期）的全局重绑**。

### D8 · 仓库根 `conftest.py` 不在 CI 的 `ruff` 作用域里

- Classification: `watch-only residual`
- Why Not Blocking Closure: `gates.yml:682` 的 `lint` job 逐字扫八个目录（`agenerp` + `tests/` 七个），
  仓库根的 `.py` 文件不在其中。把它接进去要改 `.github/workflows/**`（**红线 2**）。
  缓解：P2-4 在本机跑 `ruff check conftest.py` 并留证，**且逐字登记「它没进 CI」**（Non-Goal 10），
  **不写成「已被 lint 覆盖」**。同形态的登记面是 `module-boundaries.md` §7.26 那张表 —— 本条**不进那张表**
  （那张表管的是「测试目录被谁复跑得到」，不是 lint 作用域），只在 §7.27.1 登记，**避免第二处重复登记**。
- Successor Required: `no`
- 重开事件：**人把仓库根接进 `lint` job 的 ruff 参数**，或**仓库根出现第二个 `.py` 文件**。

## Closure

Status Note: <待收口填写 —— 未做完不得预填>

Closure Audit Evidence:

- Auditor / Agent: <独立子代理，全新会话，非本 plan 执行者>
- Evidence: <task id / 复跑命令与退出码 / 证据文件路径>

Follow-up:

- <仅非阻塞项；已确认的缺陷不得出现在这里 —— D4 那条已按「归人 + 重开事件」登记在 `Deferred But Adjudicated`，不重复登记>
