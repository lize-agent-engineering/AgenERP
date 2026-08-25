# 02 · 活站点上的销售订单没有被人工关闭 —— 「账面全绿陷阱」在站点侧不存在

> 状态：**已由人修复**（`484c123`，2026-08-25）—— 归属确实不在 P1.6 的交付面，
> 由人在**种子装载面**（`agenerp/seedsite.py`）处置
> 发现于：2026-08-24，plan `2026-08-24-2109-1`（P1.6 行业包 v0）的 H4 活站点核对
> 交接：`docs/masterplan/STATE.md` §3 的 needs-human —— **已闭环**，
> 同节 `:389` `[resolved] 2026-08-25T02:02Z`

## 1. Problem

离线种子数据集把销售订单声明为**被人工关闭**（`agenerp/seed/model.py:57`
`SALES_ORDER_STATUS = "Closed"`，`per_delivered = 99.0`）—— 这是整个数据集存在的理由之一：
「订单按完成计、实际只发了 990 台」那道账面全绿的缝。

**活站点上这件事不成立**：站点上那张订单的 `status` 是 `"To Deliver and Bill"`。
直接后果是，行业包里 `discrete/closed-order-short-delivered` 这条规则
**离线命中 10、站点零命中** —— 一条业务上正确的规则，在真站点上一声不吭。

影响面：所有依赖「订单已被人工关闭」这一前提的判据与演示。
它**不是**行业包的缺陷（规则表达是对的），是**站点侧的数据与离线数据集对不上**。

### Reproduction

前置：本地 compose 栈已起、种子已装载（`frontend@http://127.0.0.1:18080`）。

```bash
AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080 \
AGENERP_ADMIN_PASSWORD=admin python3 - <<'PY'
from agenerp.site import client_from_env
from agenerp.inspection.engine import SiteRows
rows = SiteRows(client_from_env("frontend"))
print(rows.rows("Sales Order", ["name", "status", "total_qty"]))
PY
```

实测输出（复跑一次结果相同）：

```
[{'name': 'SAL-ORD-2026-00001', 'status': 'To Deliver and Bill', 'total_qty': 1000.0}]
```

而 `agenerp/seed/model.py:57` 写的是 `SALES_ORDER_STATUS = "Closed"`。

## 2. Diagnostic Method

**难在它是一条「离线全绿」的缺陷**：`tests/unit` 里那条规则的阳性对照取自离线种子数据集，
一路绿到底；只有把整份行业包**放到活站点上跑一次**，两侧命中集合逐字比对，差异才现形。
这正是 `docs/masterplan/DECISIONS.md` **D-12** 点名的失败形态
（「规则的单测若跑离线数据集是绿的 —— 测试通过、线上零命中，且无任何信号」）。

顺序：
1. 整份包在活站点跑一次 → 命中集合与离线**不一致**（少了 `closed-order-short-delivered`）。
2. **先原样复跑那条命令**（裁判规则 3：复跑优先于分析）→ 结果相同，可复现。
3. 只读取那条规则用得到的三个字段 → 站点上的 `status` 是 `"To Deliver and Bill"`。
4. `grep -n "SALES_ORDER_STATUS\|\"Closed\"" agenerp/seedsite.py` → **零命中**：
   站点装载器全文没有写这个 `status` 的地方。

**到此为止，不再往下猜。** 「装载器从没写过它」是可观测事实；
「ERPNext 提交时会不会自己重算 `status`、`Closed` 该由哪一步来置」**没有实测取证，
本文不写结论**。

## 3. Root Cause

**只写实测得到的那一半**：离线数据集声明的 `Sales Order.status = "Closed"` 从未被写到站点上
（`agenerp/seedsite.py` 里没有任何一处设置它），因此站点上那张订单保持 ERPNext 自己算出来的
`"To Deliver and Bill"`。**为什么装载器没有这一步、以及正确的置法是什么，未取证。**

## 4. Fix

**已由人修复：`484c123`（2026-08-25）。** 归属的判断维持原样 —— 不在 P1.6（行业包）的交付面：
P1.6 交付的是规则与校验器，而这是种子装载面（`agenerp/seedsite.py`）与离线数据集之间的一致性问题。

⚠️ **规则一个字没改去迁就站点** —— 把规则改到能命中为止就是照答案写规则，
且会让它在真正的「订单被人工关闭」场景上失效。**修法落在装载面，规则至今一个字未改。**

### 人侧的两条裁定（逐字取自 `484c123` 的提交信息与 `docs/masterplan/STATE.md:389`）

1. **`status` 该由哪一步置** —— §2 逐字留白的那一问，取证结果是：ERPNext 的
   `Sales Order.status` 是**受控字段**，建档时送会被单据流程覆盖成 `To Deliver and Bill`。
   正规做法是**提交后调白名单方法**（容器内实读
   `sales_order.py:1700 @frappe.whitelist() def update_status(status, name)`）。
   装载器已加关单步，**放在发货单之后**（先发 990 再关单；顺序反了就成了「关了单又发货」，
   是另一个故事），幂等。
   顺带给 `SiteClient` 加了 `post_method`（只有副作用的调用面）：`call_method` 要求响应带
   `message`，而无返回值的方法 Frappe 回 `{}`，用它会误判成失败 ——
   **判据不靠 `message`，靠读回状态验副作用**。
2. **判据归属** —— §5「尚缺的那一半」点名的那条判据已落地，归**站点侧对账**
   （与 `_link_field_checks` 同族），**不是行业包**：行业包判「规则写得对不对」，
   这条判「站点上有没有那个可查的事实」。新增 `_trap_precondition_checks` 两条
   （订单状态为 `Closed`、交付缺口为 10），站点侧对账 30 → **32 项全过**。

⚠️ **本节只写实测得到或已入仓的那一半。** 上面两条的出处是 `484c123` 的提交信息与
`STATE.md:389`；「干净站点从头重建也得到 `Closed`」是**人做过的**，本文**引用、不复跑**。

⚠️ **这条修复没有让「两侧命中集合逐字一致」自动成立** —— 它消掉的是那个**成因**。
两侧是否真的一致，由 `docs/plans/p1-insight/2026-08-25-1026-1-industry-pack-live-parity.md`
的一次实测回答，结论落 `docs/architecture/module-boundaries.md` §7.10 与 §7.19。

## 5. Prevention

- 已落地的那一半：行业包的 H4 纪律是「**整份包在活站点跑一次，命中集合与离线逐字比对，
  且先断言集合非空**」（`docs/architecture/module-boundaries.md` §7.10「活站点验证范围」）。
  没有这条纪律，这个缺陷会以「离线全绿」的形态无限期存活。
- 尚缺的那一半：**没有一条自动判据钉住「站点上的订单状态与离线数据集一致」**。
  它的自然归属是种子自验（`agenerp/seed/checks.py` 的站点侧对应物），
  不是行业包的判据 —— 已交给人裁定，见 STATE §3。
  - **（追加 · 2026-08-25）这一半已由人补上**：`484c123` 的 `_trap_precondition_checks` 两条
    正落在上面点名的那个归属上（站点侧对账），见 §4 裁定 2。
    ⚠️ **它判的是「站点上有没有那个可查的事实」，不是「两侧命中集合逐字一致」** ——
    后者是另一件事，由 §4 末尾点名的那次比对回答。
