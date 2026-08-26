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

（见下一节；本节在预测落盘 commit 里为空，由变异 commit 补齐。）
