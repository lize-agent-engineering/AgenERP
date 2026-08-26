# p1-routing-guard-registration —— 门禁 `test_chat_adapter_is_only_constructed_inside_routing` 的牙口实测

> Plan: `docs/plans/p1-insight/2026-08-26-2101-1-routing-guard-registration-drift.md`
> 基线 commit（施加任何变异之前）：`7ed23c81dd8794bc9b0398d772b4cb48d6ce3261`
> 本文件的**预测表在施加第一条变异之前落盘并单独成一个 commit**，`git log` 可验先后。

本文件回答一个问题：`docs/architecture/model-management.md` §12.5 里那句
「今天**没有任何判据拦得住这条路**」今天到底假在哪、真在哪 ——
**由变异实测判定，不由读源码判定**（`docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2：
「核了门禁绿不绿，没核绿的门禁在测什么」）。

## 0. 预测表（写死在前，事后不改）

| 变异 | 施加处（全部是产品源码，不碰 `tests/gates/**`） | 预测 |
|---|---|---|
| M1 | `agenerp/explain/loop.py` 内直接写 `ChatAdapter(cfg, model="qwen3:14b")` | 门禁 **红** |
| M2 | 同处改成 `from agenerp.routing import ChatAdapter as _CA` + `_CA(...)` | 门禁 **绿**（别名逃逸） |
| M3 | 同处改成 `import agenerp.routing as _r` + `_r.ChatAdapter(...)` | 门禁 **绿**（属性式逃逸） |
| M4 | **零施加** —— 直接跑门禁，观测它对**今天已经存在**的域外构造 `tools/experiments/p1_insight_live/run.py:159` 的反应 | 门禁 **绿**（扫描域只有 `agenerp/`）|
| M5 | 在 `agenerp/routing/` **之内**新增一处直接构造 | 门禁 **绿**（允许面成立，确认它不是空话） |
| M6 | **把类名整体改掉**：`agenerp/routing/adapter.py` 的 `class ChatAdapter` 与 `agenerp/routing/` 内的引用一并改名 | 门禁 **绿**（判据静默失效）、`pytest tests/routing -q` **红**（collection 阶段 ImportError，**不是断言失败**） |

补充预测（M6）：改名会连带打断 `agenerp/explain/loop.py:53` 的 `from agenerp.routing.adapter import ChatAdapter, Usage` 导入。

⚠️ **一次起草期的更正，照实记不抹掉**：原起草版把 M6 打在 `agenerp/routing/router.py:90` 上是错的
（独立评审 `F1`）—— 判据 `:92` 逐字 `if rel.startswith(_ALLOWED_ADAPTER_PREFIX): continue`
⇒ `agenerp/routing/**` 整份跳过，在那里改名「门禁仍绿」是**定义上必然**，证明不了任何事。
M6 因此改成「把类名本身改掉」。

**M4 是零施加**，因此它只有命令原文与退出码，**没有也不该有 `RESTORED OK`**。

## 1. 基线（施加任何变异之前实跑）

| 命令 | 退出码 | 首行 |
|---|---|---|
| `python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q` | **0** | `2 passed` |
| `python3 tools/gates/check_expected_red.py` | **0** | `门禁 29 项：预期红 0，绿 29，跳过 0` |
| `python3 -m pytest tests/routing -q` | **0** | `179 passed, 1 skipped` |
| `python3 -m pytest tests/unit tests/tools -q` | **0** | `920 passed, 29 skipped` |

## 2. 实测结果（2026-08-26）

复原口径：**逐文件按施加前的 `sha256` 比对**，不用 `git checkout -- .` 兜底
（那会把本 plan 自己未入库的文件一并抹掉）。

### M1 · `agenerp/explain/loop.py` 内直接构造 `ChatAdapter`

- 预测：**红** —— **实测：红 ✅ 吻合**
- `python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q` → **exit 1**
- 失败文案首行逐字：

  ```
  E       AssertionError: `ChatAdapter` 在 routing 之外被构造：{'agenerp/explain/loop.py': [681]}
  ```
- `sha256 agenerp/explain/loop.py`：`954832d5…6bee6` → `954832d5…6bee6` **RESTORED OK**

### M2 · 别名导入 `from agenerp.routing import ChatAdapter as _CA` + `_CA(...)`

- 预测：**绿（别名逃逸）** —— **实测：绿 ✅ 吻合**
- 同一条命令 → **exit 0** · `2 passed in 0.15s`
- `sha256 agenerp/explain/loop.py`：`954832d5…6bee6` → 同值 **RESTORED OK**
- 判词：判据匹配条件是 `ast.Call` 且 `node.func` 为 `ast.Name` 且 `id == "ChatAdapter"`；
  别名把 `id` 变成 `_CA`，**逃出匹配形状**。

### M3 · 属性式 `import agenerp.routing as _r` + `_r.ChatAdapter(...)`

- 预测：**绿（属性式逃逸）** —— **实测：绿 ✅ 吻合**
- 同一条命令 → **exit 0** · `2 passed in 0.15s`
- `sha256 agenerp/explain/loop.py`：同值 **RESTORED OK**
- 判词：`node.func` 是 `ast.Attribute` 而不是 `ast.Name`，**逃出匹配形状**。

### M4 · 零施加 —— 观测今天已经存在的域外构造

- 预测：**绿（扫描域只有 `agenerp/`）** —— **实测：绿 ✅ 吻合**
- `python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q` → **exit 0** · `2 passed in 0.16s`
- `sed -n 159p tools/experiments/p1_insight_live/run.py` → **exit 0**，该行逐字：
  `self._poster = None if inner is not None else ChatAdapter(config)`
- **这不是假想的逃逸，是仓里今天就有的一处**：该文件 `:151` 逐字写明「打真端点」
  ⇒ **它在 `agenerp/` 之外，判据的扫描域 `_PKG = <repo>/agenerp` 够不着它，而它会真发请求。**
- **M4 是零施加，因此没有也不该有 `RESTORED OK`。**

### M5 · 在 `agenerp/routing/` 之内新增一处直接构造

- 预测：**绿（允许面成立）** —— **实测：绿 ✅ 吻合**
- 施加处：`agenerp/routing/__init__.py` 末尾追加一个返回 `ChatAdapter(config, model="qwen3:14b")` 的函数
- 同一条命令 → **exit 0** · `2 passed in 0.15s`
- `sha256 agenerp/routing/__init__.py`：`ed9677b0…55da4` → 同值 **RESTORED OK**
- 判词：判据 `:92` 逐字 `if rel.startswith(_ALLOWED_ADAPTER_PREFIX): continue` ⇒ 允许面**确实成立**，不是空话。

### M6 · 把类名整体改掉（判据会不会静默失效）

- 预测：门禁 **绿**、`pytest tests/routing -q` **红（collection 阶段 ImportError，不是断言失败）**
  —— **实测：两半都吻合 ✅**
- 施加：把 `ChatAdapter` → `ChatCaller`，改动 `agenerp/routing/adapter.py`（`class` 定义 + `__repr__` 文案）、
  `agenerp/routing/__init__.py`（import + `__all__` + 模块头）、`agenerp/routing/router.py`（返回类型注解 + 构造点）
- `python3 -m pytest tests/gates/test_agent_seam_stays_swappable.py -q` → **exit 0** · `2 passed in 0.15s`
  ⇒ **门禁对「守护对象整个消失」毫无反应，永久静默绿。**
- `python3 -m pytest tests/routing -q` → **exit 2**，逐字
  `ERROR collecting tests/routing/test_adapter.py` / `ERROR collecting tests/routing/test_router.py`
  · `2 errors during collection` · `E   ImportError: cannot import name 'ChatAdapter' from 'agenerp.routing.adapter'`
  ⇒ **红在 collection 阶段的 ImportError，不是断言失败**（预测已写死这一点）。
- 连带确认（预测里写死的补充项）：`python3 -c "import agenerp.explain.loop"` → **exit 1**，
  `ImportError: cannot import name 'ChatAdapter' from 'agenerp.routing.adapter'. Did you mean: 'ChatCaller'?`
  ⇒ `agenerp/explain/loop.py:53` 的导入确实被打断。
- `sha256`：`agenerp/routing/adapter.py` `3e9edc88…29553` · `agenerp/routing/__init__.py` `ed9677b0…55da4` ·
  `agenerp/routing/router.py` `f8658cd3…9c1d2` —— 三份**逐字节同值 RESTORED OK**
- ⚠️ **一处与 Targets 行的张力，照实记**：Targets 把 `agenerp/routing/router.py` 移出，
  针对的是**被否决的旧 M6**（打在 `router.py:90` 的改名）；**现在这条 M6 的定义**逐字是
  「`class ChatAdapter` 与 `agenerp/routing/` 内的引用一并改名」，`router.py` 正是那些引用之一，
  不改它这条变异根本立不起来。已按同一口径逐字节复原并比对。

### 复原自证

`git status --porcelain -- agenerp/ tools/ tests/` → **零行**（产品源码与实验设施零残留）。

## 3. 可引用的结论（供 §12.5 逐字引用）

**六条预测与实测逐条吻合，无一条不符**（因此本文件没有「以实测为准改写措辞」的条目要记）。

> `tests/gates/test_agent_seam_stays_swappable.py::test_chat_adapter_is_only_constructed_inside_routing`
> **盖住**：`agenerp/**`（`agenerp/routing/**` 除外）里**以裸名 `ChatAdapter(...)` 直接构造**这一种形态（M1 实测打红）。
> **不盖**四种形态，逐条实测：
> ① **别名导入**（`as _CA` 后调用）—— M2 绿；
> ② **属性式构造**（`_r.ChatAdapter(...)`）—— M3 绿；
> ③ **`agenerp/` 之外的调用方** —— M4 绿，且今天就有一个真实实例
>    `tools/experiments/p1_insight_live/run.py:159`（会打真端点）；
> ④ **判据自身没有存活守卫** —— M6：类名一改，`offenders` 恒空、门禁绿，
>    而同一次改名让 `pytest tests/routing -q` 在 collection 阶段红。
>    循环那条判据 `:74` 有一句 `assert found, …` 存活守卫，adapter 这条 `:100` 没有。
> **允许面成立**：`agenerp/routing/` 之内的直接构造照旧放行（M5 绿）。
> 实测日期 **2026-08-26**，基线 commit `7ed23c8`。

## 4. 这条打法本身值得记一句（CP9 §1.2 的可复用打法）

本 plan 的四轮独立评审里，**两次栽在同一个病上**：

- `F1` —— **门禁自己没有存活守卫**（`:100` 缺 `:74` 那句 `assert found`）；
- `S1` —— **本 plan 新增的判据也没有存活守卫**（上一版 `B` 取「表中出现的每个文件」
  ⇒ 表清空则 `A = B = ∅` ⇒ `A == B` 成立 ⇒ 绿）。

**两次都不是靠读文字发现的，是靠「按判据源码 / plan 正文口径做一个原型，然后真跑一遍」发现的。**
`F1` 由评审者在 `/tmp` 隔离副本上改名实测出来，`S1` 由评审者按上一版正文做出原型、
实测四格 `baseline GREEN / N1 RED / N2 RED / N3 RED / N4 GREEN ❌` 出来。

⇒ **可复用打法**：审「一条判据到底盖住什么」时，不要读它的名字、也不要只读它的断言，
**要给它造一个它本该拦住的东西，跑一次看它红不红；再造一个「守护对象消失」的场景，跑一次看它还红不红。**
后者正是 `docs/audits/2026-08-26-CP9-P1-retrospective.md` §1.2 逐字罚的那件事
（「核了门禁绿不绿，没核绿的门禁在测什么」）。

## 5. 本次实测顺带看见、但**不在本 plan 结果面内**的一处同形漂移（照实登记，不代改）

`docs/architecture/model-management.md:320-327` 逐字写着
「`tests/routing` 既**不在** `missions/p1-insight.json` 的 `commands.test` 里，也**不在**
`.github/workflows/gates.yml` 的任何 job 里」——
**前一半今天仍真**（`missions/p1-insight.json:16` 的 `commands.test` 确实只有
`check_expected_red.py && pytest tests/unit -q`），**后一半已假**
（`.github/workflows/gates.yml:617-618` 步骤 ④ 逐字 `python3 -m pytest tests/routing -q`）。

**本 plan 不改它**：Phase 2 的 Exit Criteria 逐字把 owner doc 的改动面限定在
「`:293-297` 那一段与新增表内」，改 `:320-327` 会越出该判定面。
同一句话在 `docs/backlog/p1-insight-roadmap.md:43` 的那一份**在本 plan 范围内**，已由 Phase 2 追加结清记录改准。
**这一处交人 / 交下一轮起草步。**
