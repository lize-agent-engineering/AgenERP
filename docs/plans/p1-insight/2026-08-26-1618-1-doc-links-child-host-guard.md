# 2026-08-26-1618-1 `doc.links` 子表分支缺守卫 —— 一个坏子表宿主仍能带走整次扫描

> Plan Status: active
> Mission: p1-insight
> Work Item: 1. 工具执行层：10 个只读契约的执行体（P1.0a）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个预算，本 plan 用掉最后一格）
> Last Reviewed: 2026-08-26
> Source: 人 2026-08-25T09:44Z 对 `docs/masterplan/STATE.md` §3 `[open] 2026-08-25T06:40Z` 内 **C1** 的裁定第 ② 条 —— 逐字「单个宿主查失败**不整次作废**，继续扫其余宿主」，且逐字「**实现交 loop**」。本轮起草步实测确认：人自己的 `5396e68` 把 ① 完整落地、把 ② **只落在 `else` 那一支**，子表那一支两处调用至今无守卫。
> Related: `docs/bugs/03-doc-links-dies-on-single-doctypes.md` · `docs/plans/p1-insight/2026-08-24-P1.0a-tool-execution-layer.md`
> Audit: required

## Current Baseline

**基线 sha `7302ebe`。`git status --porcelain` 的唯一条目是本 plan 文件自身（`?? docs/plans/p1-insight/2026-08-26-1618-1-doc-links-child-host-guard.md`），除此之外干净。以下每一条都是本轮起草期实跑/实读得出，不引转述。**

### 代码现状（实读 `agenerp/tools/documents.py:100-173`）

- `scan_links()` 对每个 Link 宿主分两支走：`is_child` 为真走子表支（`:125-146`），否则走主表支（`:147-160`）。
- **主表支有守卫**：`:151-156` 的 `try / except Exception: continue`，注释逐字写着 C1 裁定第 ② 条。
- **子表支没有任何守卫**，且那里有**两处**站点调用：
  - `:129` `session.list_rows(holder, …)` —— 查子表行；
  - `:139` `session.list_rows(parent_type, …)` —— 逐行回溯父单据（**在 `for row in rows` 循环里**，命中越多调用越多）。
- ⇒ 这两处任一抛错，异常穿透整个 `scan_links()`，`doc.links` 整次作废。`lineage_trace()`（`:183`）逐跳复用 `scan_links`，**同一个洞**。

### 缺陷已用两个探针实测坐实（不是推断）

探针只写 `/tmp`，**仓内零施加**，跑完即删。两次都在 `7302ebe` 的干净树上跑。

| 探针 | 构造 | 观测（逐字） |
|---|---|---|
| 子表宿主查询失败 | `Sales Order Item`（`istable: 1`）一被查就抛，`Sales Order` 健康 | `ABORTED whole scan -> RuntimeError 站点侧失败：HTTP 500（子表宿主）`，`calls: ['DocType', 'DocField', 'DocField', 'Sales Order Item']` —— **健康宿主 `Sales Order` 一次都没被扫到** |
| 回溯父单据失败 | 子表行查得到，回溯 `Sales Order` 时抛；`Delivery Note` 健康 | `ABORTED whole scan -> RuntimeError 站点侧失败：回溯父单据时 HTTP 500`，`calls: [… , 'Sales Order Item', 'Sales Order']` —— **健康宿主 `Delivery Note` 一次都没被扫到** |

### 既有判据为什么没挡住

`tests/unit/test_doc_links_skips_singles.py::test_one_failing_host_does_not_abort_the_whole_scan`
的坏宿主 `Broken DocType` 逐字是 `"istable": 0` ⇒ **它只走主表支**。子表支零覆盖。

### 为什么这不是边角情形

`docs/backlog/p1-insight-roadmap.md` 的「已知的坑」逐字：**「`lineage.trace` 必须扫子表：21 个指向 `Sales Order` 的 Link 里 14 个在子表」** ⇒ 子表支是**多数路径**，不是少数派。
而 C1 那条裁定本身是被一次 **136,331 token、答案为空** 的真实事故逼出来的（`docs/bugs/03`）：模型拿到失败会**原样重试**，直到撞熔断。守卫只落一半 ⇒ 同一事故形态在多数路径上仍然可达。

### 基线命令与退出码（本轮实跑，离线口径、一个 env 都不设）

| 命令 | 退出码 | 输出（逐字要点） |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | **0** | `判定模式：default` / `门禁 28 项：预期红 0，绿 28，跳过 0` / `✅ 与预期红名单完全一致` |
| `python3 -m pytest tests/unit tests/tools -q` | **0** | `903 passed, 29 skipped in 13.77s` |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui`（逐字取自 `.github/workflows/gates.yml:682`） | **1** | `F401 \`pytest\` imported but unused` → `tests/unit/test_doc_links_skips_singles.py:22:8`，`Found 1 error.`（`1 fixable`） |

⚠️ **那条 F401 现在是已入库代码**（随 `5396e68` 进仓），不再是「人的在飞草稿」⇒ **下一次推送时 `gates.yml` 的 `lint` job 会红**。它落在本 plan 要扩写的**同一个文件**里，因此在本 plan 范围内（见 Goals 第 4 条），不另起 plan。

### 活栈现状（本轮实测，供 Phase 3 用）

`docker compose ps` → 十个服务全 `running`、七个有探针的全 `healthy`；`frontend` 对外口 `127.0.0.1:18080`；`curl -H "Host: frontend" http://127.0.0.1:18080/api/method/ping` → **200**。

### 「改动前」的活站点观测**已在本轮起草期取得**（因此 Phase 3 只需复跑一次并比对）

⚠️ **它是在基线 sha `7302ebe` 的树上跑的**，`agenerp/**` 此刻一个字节未改。**脚本原文照抄下面这段 heredoc**，Phase 3 必须用**逐字节相同**的脚本与 env 复跑 —— 命令不同则比对无效：

```sh
cat > /tmp/doclinks_probe.py <<'PY'
import json
from agenerp.site import client_from_env
from agenerp.tools.runtime import execute
from agenerp.contracts import ReadOnlyContext
ctx = ReadOnlyContext({"doc_links_called_for": [], "documents_named_in_question": [], "doc_get_called_for": []})
out = execute("doc.links", {"doctype": "Item", "name": "HRD-PACK-5K"},
              client=client_from_env("frontend"), context=ctx)
rows = out.data or []
print("ok=", out.ok, "rows=", len(rows))
print(json.dumps(rows, ensure_ascii=False, sort_keys=True))
PY
AGENERP_HTTP_PORT=18080 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
  AGENERP_ADMIN_PASSWORD=admin PYTHONPATH=. python3 /tmp/doclinks_probe.py | tail -1 | shasum -a 256
```

**观测值（本轮实跑两次，两次逐字相同）**：`ok= True rows= 14`，规范化 JSON 的 `sha256` = **`203db3f89a095aa19b6c684f4a808137c63cf9ef33cc74f575a766970e668bd1`**。
14 行里 **8 行的 `linked_via` 是子表字段**（`Sales Order Item.item_code` / `Delivery Note Item.item_code` / `Purchase Order Item.fg_item` / `Sales Invoice Item.item_code` / `Stock Entry Detail.*` 等）⇒ **本站点上这条调用的多数命中来自那条无守卫的分支**，这不是构造出来的假设。

## Goals

1. **子表支的两处站点调用各自获得守卫**，使「一个坏宿主/一条坏行」不再带走整次 `doc.links` —— 即把 C1 裁定第 ② 条落到**它本来就该覆盖的全部路径**上。
2. **判据先红后绿**：新增的**前两条**判据（两个失败点各一条）在修改前必须因**这个缺陷**而红，且红因可辨（不是断言不等而已）。⚠️ **第三条不在这句话里** —— 它是反向守卫判据，**按构造在修改前就是绿的**（见 Phase 1 与 H3），它防的是修改**之后**的退化。
3. **不许「绿着坏掉」**：判据要能区分「守卫生效」与「守卫把一切都吞了、扫描退化成空集」。
4. 删掉 `tests/unit/test_doc_links_skips_singles.py:22` 那行未用的 `import pytest`，让本 plan 自己的 `ruff` 验收命令能退 0。
5. **把 `scanned_link_levels` 的过度声称就地裁定**：本 plan 让一个此前不可达的形态变得可达（见 Phase 2 的 `Decision` ②），它必须落在「改掉」或「登记为残余风险并写死翻案条件」之一，**不许悬着**。

## Non-Goals

1. **不碰 `tests/gates/**` 一个字节**（红线 1）。本 plan 的义务是**不改变**那些判据的判定结果，不是去改它们。
2. **不碰 `.github/workflows/**`**（红线 2）、不碰 `docs/masterplan/` 已有行（红线 5，只往 `STATE.md` 追加）。
3. **不重新裁定 C1 对 Single 宿主的「不留痕」取舍** —— 那是人 2026-08-25T09:44Z 已选定并写明取舍的，本 plan 原样沿用。
4. **不动 `doc.links` 正常路径的返回内容与顺序**。本改动只在异常路径上生效。
5. **不修 `docs/architecture/module-boundaries.md` §7.11 的 `MAX_TOOL_CALLS = 32` / `MAX_TURNS = 25` 漂移**（`40a6c33` 之后活代码是 50 / 40）—— 那是工作项 9（P1.7）的面，预算 `2/2` 已满，本轮起草步另行登记交人。
6. **不修 `docs/bugs/03` 的状态词**（该文件抬头仍写「未修」，而 `5396e68` 已修）—— 同上，另行登记交人。

## Task Route

- Type: `bug investigation` + `implementation-only change`（缺陷已确认、修法面已由人裁定，本 plan 做的是落地与取证）
- Owner Docs: `docs/architecture/module-boundaries.md` §7.6（契约层执行面落点）· 新增 §7.24（本 plan 的落点节）· `docs/bugs/03-doc-links-dies-on-single-doctypes.md`（同族缺陷的原始记录，**只读引用，不改它的状态词**）
- Skill Selection Basis: `superpowers:test-driven-development`（本 plan 的形状就是「先写会红的判据」）+ `superpowers:systematic-debugging` 已由起草期的两个探针提前完成其定位职能，执行期不再重复。

## Infrastructure And Config Prereqs

- Phase 1 / 2 **零基础设施依赖**：纯离线、纯 `tests/unit`，一个 env 都不设。
- Phase 3 需要活栈：`AGENERP_HTTP_PORT=18080`（**8080 被本机另一套常驻 ERPNext 栈占着**），站点 `frontend`，凭据由命令给（`AGENERP_SITE` / `AGENERP_SITE_URL` / `AGENERP_ADMIN_PASSWORD`），产品代码不内置口令默认值。栈此刻已在跑且 healthy，**Phase 3 不需要冷起**。
- 回滚策略：本 plan 只增守卫、不删行为，回滚 = `git revert` 单个提交；无 DDL、无站点写入、无迁移。

## Execution Plan

### Phase 1 - 判据先红

Status: planned
Targets: `tests/unit/test_doc_links_skips_singles.py`
Skill: `superpowers:test-driven-development`

- Item Types: `Proof`（3/4 项）
- Prereqs: 无

- [ ] `Proof` 加一条判据：**子表宿主查询失败**（`istable: 1` 的宿主一被查就抛）时，其余健康宿主的命中照常返回。
- [ ] `Proof` 加一条判据：**回溯父单据失败**时，其余健康宿主的命中照常返回。两条必须**分开写** —— 它们是两个不同的调用点，合成一条会让「只修了其中一处」蒙混过关。
- [ ] `Proof` 加一条**反「绿着坏掉」判据**：健康的子表宿主必须照常产出**回溯到父单据**的命中行（`child_hits_resolved_to_parent` 为真、`child_table_hits` 非零）。没有这一条，把整个子表支 `try: … except: continue` 包起来也能让上面两条绿。
- [ ] `Fix` 删掉 `:22` 的 `import pytest`（未使用）。

⚠️ **还有一条判据不在本 Phase**：钉住「回溯父单据失败时那一行怎么处置」的那条，正文取决于 Phase 2 `Decision` ① 的裁定结果，因此**随该裁定一起落在 Phase 2**。它不是可选项 —— 没有它，两种相反的实现都能让本 Phase 的判据全绿。

Exit Criteria:

- [ ] `python3 -m pytest tests/unit/test_doc_links_skips_singles.py -q` → **exit 1**，且新增的前两条各自红在**那个真实异常逐字冒出来**上（把红因原文抄进 plan），第三条**绿**（它描述的是现状里本就成立的行为）
- [ ] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → **exit 0**
- [ ] No owner-doc update required（本 Phase 只动判据）

### Phase 2 - 实现 + 裁定留痕口径 + 变异自查

Status: planned
Targets: `agenerp/tools/documents.py`
Skill: `none`

- Item Types: `Fix | Decision | Proof`
- Prereqs: Phase 1

- [ ] `Fix` 给子表支的两处调用各自加守卫，使单点失败降级为「跳过这一个宿主 / 这一行」而不是整次作废。**两处分别处理，不许一个 `try` 把整支包起来** —— 那会让「子表行查得到但回溯失败」的部分结果一起丢掉。
- [ ] `Decision` ① **回溯父单据失败时，那一条子表命中怎么处置**（`:139-145`）。这不是实现细节，是**会被人看见的语义**：
      - (a) **丢掉这一行** —— 少报一条真实关联，且 `docstatus` 未知时不冒充；
      - (b) **以 `docstatus` 未知（`None`）记入** —— ⚠️ **`:161` 的筛选逐字是 `row.get("docstatus") != CANCELLED`，`None != 2` 为真** ⇒ **一张已取消的单据会被当成有效关联漏出去**。roadmap 的「已知的坑」逐字写着「`doc.links` 的下游筛选是**排除已取消**」，(b) 直接违反它。
      **默认取 (a)**，选 (b) 必须在落点节写明为什么可以容忍已取消单据漏出。**无论选哪支，都要在本 Phase 补一条判据把它钉死**（Phase 1 末尾那条 ⚠️ 指的就是它）。
      ⚠️ 一并处理 `:138` 的 `child_level_rows.append(row)` —— 它在失败的那次调用**之前**，⇒ 选 (a) 时 `child_table_hits` 会把一条没进 `hits` 的行也算进去。**要么把 append 挪到成功之后，要么在落点节写明这个计数的口径是「扫到的子表行」而不是「产出的命中」。**
- [ ] `Decision` ② **`scanned_link_levels` 的过度声称**：`:122-123` 的 `levels.append(level)` 在两处调用**之前**，⇒ 本 plan 落地后会出现一个**此前不可达**的形态 —— 某一级的宿主**全部失败**时，返回的 `scanned_link_levels` 仍声称扫过那一级。
      ⚠️ **它是契约后置条件，不是内部字段**：`agenerp/tools_readonly.py:185-199` 逐字要求 `scanned_link_levels contains child_table`，并在 `tests/tools/test_executors.py` 与 `tests/contracts/test_postconditions.py` 上被断言 ⇒ **改它有让既有绿判据转红的实际风险**。
      两支：**(a) 改掉**（只在该级真产出过命中时才记）—— 必须先证明既有判据不由绿转红；**(b) 不改，登记为残余风险**并**写死翻案条件**（例如「一旦有一次真实归因因为这个声称而误判『已经扫过子表』，本条即回来重开」）。**两支都要写进落点节 §7.24**，选 (b) 时残余风险必须逐字写出来，不许只说「已知」。
- [ ] `Decision` ③ **失败留不留痕**：
      - (A) 静默 `continue`，与既有主表支 `:151-156` 等形；
      - (B) 在 `scan_links()` 返回的 `facts` 里记一个「因失败被跳过的宿主/行」计数，与 `docs/architecture/model-management.md` §12.1 ③「绝不静默降级」对齐。
      **决定性判据（按优先级）**：① 红线 1 —— 任何选择都不得让 `tests/gates/**` 任一条由绿转红，`tests/gates/test_tool_execution_live.py::test_every_tool_returns_a_shape_its_contract_allows` **对 `doc.links` 是参数化覆盖的**，因此 (B) 必须先证明它**不改变 `doc_links()` 的 `Outcome` 形状**（`doc_links` 现在逐字 `rows, _ = scan_links(...)`，把 `facts` 丢弃并自建一份）；② C1 对 **Single 宿主**的「不留痕」是人已选定的取舍，**它没有覆盖「宿主查崩」这一类**，别把两件事混成一件。选定后把选择、被否的那个、以及残余风险写进落点节。
- [ ] `Proof` 变异自查，逐条施加、逐条复原并 `sha256` 比对：
      - **M1** 守卫改成 `except: raise` → 新判据必红；
      - **M2** 守卫吞掉一切并让子表支直接 `continue`（连健康宿主也不产出命中）→ Phase 1 第三条判据必红；
      - **M3** 只给 `:129` 加守卫、不给 `:139` 加 → 第二条判据必红；
      - **M4** 只给 `:139` 加守卫、不给 `:129` 加 → 第一条判据必红；
      - **M5** 把守卫的 `except` 收窄成一个真站点上抛不出来的异常类型 → 至少一条新判据必红（防「守卫写了但抓不到」）。
      **任一变异没打红，就地补断言并登记为 M6…，不许把「没打红」写成「不需要」。**

Exit Criteria:

- [ ] `python3 -m pytest tests/unit tests/tools -q` → **exit 0**，且 passed **只增不减**（基线 `903 passed, 29 skipped`）
- [ ] `python3 tools/gates/check_expected_red.py` → **exit 0**，逐字仍是 `门禁 28 项：预期红 0，绿 28，跳过 0`
- [ ] `python3 -m pytest tests/contracts tests/routing tests/context -q` → **exit 0**
- [ ] `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` → **exit 0**
- [ ] 变异表逐条有观测值与复原确认
- [ ] `Decision` ①②③ 三条各自有选定结果、被否选项、残余风险；① 与（若选改）② 各有判据钉住
- [ ] `docs/logs/` 更新

⚠️ **本 Phase 的四条验收命令按构造探不到活体门禁的回归**：`tests/gates/test_tool_execution_live.py:64` 是 `pytestmark = pytest.mark.live`，而 `tools/gates/check_expected_red.py:196` 在默认模式下注入 `-m "not live"` ⇒ **它一条都不会跑**。那条覆盖 `doc.links` 的参数化断言的回归判定**只发生在 Phase 3**，见那里的**活体门禁复跑**那一条 Exit Criteria。**不得把本 Phase 的全绿读成「活体门禁没回归」。**

### Phase 3 - 活站点回归 + 落点节 + 收口

Status: planned
Targets: `docs/architecture/module-boundaries.md`（新增 §7.24）· `docs/evidence/`（本 plan 的证据落盘目录，**是仓内目录，不是 `evidence-repo.env` 那个冻结的证据仓**）· `docs/logs/2026/08-26.md` · `docs/masterplan/STATE.md`（**只追加**）
Skill: `none`

- Item Types: `Proof | Decision`
- Prereqs: Phase 2

- [ ] `Proof` 活站点回归：用 `## Current Baseline` 里那段 **逐字节相同**的 heredoc 与 env 复跑一次，与已取得的「改动前」观测比对 —— 期望 `ok= True rows= 14` 且 `sha256` 仍是 `203db3f89a095aa19b6c684f4a808137c63cf9ef33cc74f575a766970e668bd1`。本改动只碰异常路径，正常路径必须一个字不变。命令原文与两次输出（改动前的那次抄自本 plan）一并落盘到 `docs/evidence/`。
      ⚠️ **这一条证的是「没弄坏」，不是「守卫生效」** —— 守卫生效由 `tests/unit` 的判据与变异表证明，**两者不得互相冒充**。
      ⚠️ **`sha256` 不同不等于改坏了**：站点是活的，别人可能在两次之间动过数据。**不吻合时先原样复跑**（裁判规则 3），仍不吻合则逐行 diff 并把差异写进 plan；**在差异被解释清楚之前不得收口**。
- [ ] `Decision` 写落点节 §7.24：缺陷形态、两个探针的观测原文、留痕口径的裁定与被否选项、残余风险、翻案条件。
- [ ] `Proof` 往 `docs/masterplan/STATE.md` §2 追加一条证据行（命令原文 + 退出码 + sha），**只追加，不改写任何已有行**。

Exit Criteria:

- [ ] 活站点两跑的行数/内容逐字对照结果记进 plan（**吻合或不吻合都照实记**，不吻合则不得收口）
- [ ] §7.24 落地，且**不改** §7.6 / §7.11 / `docs/bugs/03` 的任何一个字
- [ ] `docs/logs/` 更新；`STATE.md` **只追加**，判据是 `git diff --numstat -- docs/masterplan/STATE.md` 的**删除列为 `0`**（⚠️ **不用 `--stat`** —— 它的 `+/-` 图是**按比例缩放**的，插入量一大，一行删除会被画成零个 `-`，那是个会骗人的判据）
- [ ] **活体门禁复跑（本 plan 唯一能判「`doc.links` 的裁判有没有回归」的一条）**：`AGENERP_HTTP_PORT=18080 AGENERP_LIVE=1 AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 AGENERP_ADMIN_PASSWORD=admin python3 -m pytest tests/gates/test_tool_execution_live.py -q` → **exit 0**。**这是只读复跑，`tests/gates/**` 一个字节不许动**（红线 1）。⚠️ 改动前后**各跑一次**，因为「它本来就红」与「本 plan 弄红了它」在单次退出码上分不开
- [ ] 红线自证：`git diff --name-only <BASE> -- tests/gates/ .github/workflows/ missions/ docker-compose.yml industry-packs/ docs/masterplan/ ':!docs/masterplan/STATE.md'` → **无输出**（⚠️ 用整个 `docs/masterplan/` 再排除 `STATE.md`，不是只点 `DECISIONS.md` 与 `02-WBS.md` —— 红线 5 保护的是**整个目录**）

## 开跑前写死的预测（H1–H8，事后逐条对照，不许事后改写）

| # | 预测 |
|---|---|
| H1 | Phase 1 第一条判据（子表宿主查询失败）在修改前**红**，红因是构造的那个异常**逐字穿透**到测试外层，而不是「断言不相等」 |
| H2 | Phase 1 第二条判据（回溯父单据失败）在修改前**红**，红因同 H1 |
| H3 | Phase 1 第三条判据（健康子表宿主照常回溯到父单据）在修改前**绿** |
| H4 | 修改后 `tests/unit tests/tools` 由 `903 passed, 29 skipped` 变成 `907 passed, 29 skipped`（Phase 1 三条 + Phase 2 钉 `Decision` ① 的一条 = 新增 4 条）。⚠️ **若变异自查补出更多判据，照实记实际值、不改本行原文** —— 补断言是 M1–M5 明文要求的动作，让它去伪造 H4 才是本末倒置。**`skipped` 数不变（29）是硬预测，它变了就要解释。** |
| H5 | `check_expected_red.py` 在修改前后**都是** `门禁 28 项：预期红 0，绿 28，跳过 0` —— 本改动不碰裁判，也不应让任何一条由绿转红 |
| H6 | 活站点上 `doc.links{Item, HRD-PACK-5K}` 修改前后**行数相同**（人 2026-08-26 在 `5396e68` 的提交信息里实测记为 **14 条关联单据**；若实际不是 14，照实记实际值，**不改 H6 原文**） |
| H7 | M1–M5 五个变异**全部打红**。⚠️ 若有任何一个没打红，那正是判据的窟窿，就地补断言并登记，**不修饰成「全打红」** |
| H8 | `tests/gates/test_tool_execution_live.py` 的活体复跑在改动**前后都是 exit 0**。⚠️ **若改动前就红**，那是一条与本 plan 无关的既有事实 —— 照实记、登记，**不得就此认定本 plan 无责**，也**不得**为了让它绿而动 `tests/gates/**`（红线 1） |

## Draft Review Record

- **Independent draft review iteration 1: `needs revision`**（独立子代理，起草者未参与；任务 `a670ccd0d53c83d1f`）。评审者**自己复跑了三条基线命令**并逐行实读 `agenerp/tools/documents.py:100-175`、`tests/unit/test_doc_links_skips_singles.py`、`tests/gates/test_tool_execution_live.py`，确认「基线一条都没写错」，但提出 **9 条必须修订**。其中**三条是真窟窿，会让半吊子实现绿着收口**：
  - **①②** Phase 3 原本要求「改动前后各跑一次」活站点，而 `Prereqs: Phase 2` 意味着开跑时改动已在树上 ⇒ **「改动前」那一跑按构造取不到**，执行者只能伪造或悄悄跳过；且全 plan 唯独那条命令没写原文。
  - **③** 本 plan 原来指望 `check_expected_red.py` 守住活体门禁的回归，而 `tests/gates/test_tool_execution_live.py:64` 是 `pytestmark = pytest.mark.live`、`tools/gates/check_expected_red.py:196` 默认注入 `-m "not live"` ⇒ **那条覆盖 `doc.links` 的参数化断言一次都不会跑**。
  - **④** 回溯父单据失败时那一行怎么处置**没有裁定**：`:161` 的筛选是 `docstatus != CANCELLED`，而 `None != 2` 为真 ⇒ **一张已取消的单据会漏出去**。
  - **⑤** `scanned_link_levels` 的过度声称（`levels.append` 在调用之前）**本 plan 让它从不可达变成可达**，而它是 `tools_readonly.py:185-199` 的契约后置条件、在两处判据上被断言。
  - 其余四条：H4 过度specific 且与 M6 自相矛盾 · Goal 2 与 Phase 1/H3 自相矛盾 · `git diff --stat` 的 `+/-` 图是**按比例缩放**的、拿它判「只追加」会骗人 · 红线 pathspec 只点了 `docs/masterplan/` 里的两个文件而红线 5 保护整个目录。
- **Independent draft review iteration 2: `acceptable as-is`**（同一独立子代理，带 iteration 1 的上下文）。逐条复核 9 条修订是否**真落地而不只是嘴上承认**，并**亲手复跑了 `## Current Baseline` 里那段 heredoc**，拿到逐字相同的 `ok= True rows= 14` 与 `sha256 203db3f8…e668bd1`；交叉引用编号（Goal 5 → `Decision` ②、Phase 1 前向引用 → `Decision` ①）逐个核对一致。另提 **5 条不阻塞的准确性修正**，**全部已改**：
  - 「14 行里 9 行是子表字段」→ **实为 8 行**（起草者本轮自己复测确认：`BOM` / `Bin` / `Stock Ledger Entry` ×3 / `Work Order` 六条是主表宿主，8 + 6 = 14）；
  - `child_level_rows.append(row)` 的行号 `:136` → **`:138`**（实读确认 `:136` 是 `if not parent_name:`）；
  - 预测表小节抬头 `H1–H7` → **`H1–H8`**（加了 H8 之后没跟着改，正是 Minimum Rule 11 要挡的那种不一致）；
  - Phase 2 那句指向「Phase 3 最后一条 Exit Criteria」→ 改为指名**活体门禁复跑那一条**（它是倒数第二条）；
  - Closure Gate 的 `verification has run` 补上活体门禁的两跑。
- **共识**：iteration 2 判 `acceptable as-is`，其后提出的 5 条已全部落地并各自实测复核 ⇒ 转 `active`。

## Closure Gates

- [ ] in-scope behavior is complete
- [ ] relevant docs are aligned
- [ ] verification has run（Phase 2 四条 + Phase 3 的活站点 `doc.links` 两跑 + **活体门禁 `tests/gates/test_tool_execution_live.py` 改动前后两跑**，命令原文与退出码逐条记录）
- [ ] scoped verification is not conflated with full verification —— 若未跑整仓 `pytest tests -q -m "not live"`（**已知基线即红**，`gates`×`tools` 环境泄漏已单列立案），必须逐字写「verification scope limited」
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded
- [ ] text consistency verified: status, phases, gates, and log all agree
- [ ] closure audit was independent
- [ ] closure evidence exists in files

## Deferred But Adjudicated

（起草期为空。执行期若产生，须写明分类与重开事件。）

## Closure

Status Note: <未收口>
