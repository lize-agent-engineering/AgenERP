# 03 · `doc.links` 撞上 Single DocType 直接 HTTP 500 —— 归因在活站点上取不到 L1 要的那条证据

> 状态：**已确认、可复现、未修**（归属不在本 plan 的交付面）
> 发现于：2026-08-25，plan `2026-08-25-0225-2`（洞察 Agent 归因的首次活端点实跑）Phase 2
> 交接：`docs/masterplan/STATE.md` §3 的 needs-human

## 1. Problem

`doc.links`（`agenerp/tools/documents.py` 的 `scan_links`）会遍历**所有指向目标 DocType 的
Link 字段宿主**并逐个 `GET /api/resource/<宿主>`。宿主里只要有一个是
**Single DocType**（`issingle = 1`，值存在 `tabSingles`、**没有实体表**），
Frappe 就回 **HTTP 500**，而 `SiteError` 一抛，**整次 `doc.links` 调用作废**。

本站点上 `Item` 的 Link 宿主里就有一个：**`Quick Stock Balance`**。
⇒ `doc.links(doctype="Item", name="HRD-PACK-5K")` 在本站点上**必然失败**。

直接后果（这才是它值得单开一条的理由）：洞察 Agent 的归因题面里逐字带着物料号
`HRD-PACK-5K`，它是三段全大写数字，落进 `agenerp/explain/gate.py` 的 `DOC_NAME`，
于是 **L1 门禁要求「作答前必须对它调用过 `doc.links`」——而这条证据在本站点上取不到**。
循环因此永远满足不了前置，只能一路取证到轮数 / 工具调用上限：

| 跑次 | 模型调用 | 出口 | `accepted` | 答案 |
|---|---|---|---|---|
| `live-run-01` | 25 | `max-turns` | `false` | 空 |
| `live-run-02`（原样复跑） | 22 | `tool-call-runaway` | `false` | 空 |

影响面：**任何题面里点名了 `Item` 的解释 / 归因**（不只是洞察）。P1.4 的活跑没撞上，
是因为它那道题点的是 `SAL-ORD-2026-00001`，`Sales Order` 的 Link 宿主里没有 Single DocType。

### Reproduction

前置：本地 compose 栈已起、种子已装载（`frontend@http://127.0.0.1:18080`）。

```bash
AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
AGENERP_ADMIN_PASSWORD=admin python3 - <<'PY'
from agenerp.site import client_from_env
c = client_from_env("frontend")
print({k: c.get("/api/resource/DocType/Quick Stock Balance")["data"].get(k)
       for k in ("name", "istable", "issingle", "is_virtual")})
PY
```

实测输出：

```
{'name': 'Quick Stock Balance', 'istable': 0, 'issingle': 1, 'is_virtual': 0}
```

整条链的复跑就是那次实跑本身（`docs/evidence/p1-insight-live/`）：

```bash
python3 -m tools.experiments.p1_insight_live.run
```

证据里逐字留着站点原文（`attributions[0].tool_calls[].reasons`）：

```
站点侧失败：GET /api/resource/Quick Stock Balance → HTTP 500（站点 frontend）：
{"exception":"pymysql.err.ProgrammingError: ('DocType', 'Quick Stock Balance')", ...}
```

以及被它拦下的那一侧（同一份证据）：

```
前置未满足：问题点名了某张单据 → 接受 answer 之前，必须已对它调用过 doc.links
—— 未覆盖 ['HRD-PACK-5K']
```

`live-run-01` 出现 **14** 次（13 次 `query.read` + 1 次 `snapshot.read`）、`live-run-02` 出现 **17** 次（全部 `query.read`）。**两跑同一形态 ⇒ 可复现。**

## 2. Diagnostic Method

1. 一次活跑退 0 但 `accepted = false` 且 `answer` 为空 → **先原样复跑那条命令**
   （裁判规则 3）→ 第二跑同样为空，形态一致 ⇒ 可复现，不是偶发。
2. 读 `trace.tool_calls` 里 `ok = false` 的那些：两类理由交替出现 ——
   `doc.links` 的 `execute` 阶段站点 500，`query.read` / `snapshot.read` 的
   `preconditions` 阶段 L1 未覆盖。两者是同一件事的两端。
3. 500 的原文点名了 `Quick Stock Balance` → **直接读它的 DocType 元数据**
   → `issingle = 1`。
4. 读 `agenerp/tools/documents.py`：`doctype_flags()` 只取
   `("name", "istable", "is_submittable")` —— **`issingle` 从头到尾没被取过，也就没法被排除**。

**到此为止，不再往下猜。** 「Single DocType 上应该怎么查 Link 反向引用」「除了跳过它还有没有
别的正确语义」**没有实测取证，本文不写结论**。

## 3. Root Cause

**只写实测得到的那一半**：`scan_links` 把「Link 字段的宿主」一律当成有实体表的 DocType 去
`list_rows`，而 `doctype_flags()` 拿的三个标志里**没有 `issingle`**，因此 Single DocType
无从被识别、无从被跳过；Frappe 对它回 500，`SiteError` 让整次 `doc.links` 作废
（`agenerp/site.py` 第 1 条纪律：**绝不降级成空结果** —— 这条纪律本身是对的，
问题在于宿主清单里就不该有它）。

**为什么 ERPNext 会把 `Quick Stock Balance` 这类「查询表单」做成 Single、
以及本仓是否应当对所有 Single 一律跳过还是另有语义，未取证。**

## 4. Fix

**未修。** 归属不在 plan `2026-08-25-0225-2` 的交付面：那个 plan 是一次**验证**
（§3 Non-Goal 2 逐字「不改 `agenerp/insight/**` 与 `agenerp/inspection/**` 的任何行为」），
而本缺陷在 `agenerp/tools/documents.py`。**在同一个 plan 里既当运动员又当裁判，
会让「活跑抓到的问题」变成「顺手改到跑绿为止」** —— 那个 plan 的 D1 已就此裁定。

⚠️ **没有为了让归因跑出答案去动 L1 门禁、去改题面、或去把物料号从 `DOC_NAME` 里摘出去。**
那是照答案改考题。

修的时候要连带定的两件事（**留给人裁定，本文不代人定**）：
① 跳过 Single 宿主是不是正确语义，还是应当换一条查法；
② 单个宿主查失败时，`doc.links` 应该整次作废，还是应当把失败的宿主**记进 facts** 后继续
（后者会改变契约的后置事实面，属契约层的决定）。

## 5. Prevention

- 已落地的那一半：本缺陷是被**活跑 + 结构化判据**逼出来的 —— 脚本的
  `evidence_trace_enumerable` / `hits_unchanged` / 账本对账六项全绿，
  却仍然留下 `accepted = false` + 空答案这个刺眼的组合，证据里逐条留着拒绝理由。
  没有那份逐条轨迹，这个缺陷会以「模型这次不太行」的形态被糊过去。
- 尚缺的那一半：**没有任何一条判据钉住「`doc.links` 的宿主清单里不含没有实体表的 DocType」**。
  离线假站点（`tests/tools/conftest.py`）里一个 Single DocType 都没有，
  所以 `tests/tools` 全绿也说明不了什么。它的自然归属是工具执行层的判据面，
  **不是本 plan 的** —— 已交给人裁定，见 STATE §3。
