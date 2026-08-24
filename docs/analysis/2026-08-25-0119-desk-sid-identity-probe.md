# 探测记录 · `sid` 这条接缝到底走不走得通（P1.8 下半 Phase 1）

> Plan: [`docs/plans/p1-insight/2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md`](../plans/p1-insight/2026-08-25-0119-1-desk-sidebar-carrier-and-explain-request-surface.md) Phase 1
> Date: 2026-08-25
> 基线 sha: `7e7f5177c68e1b86b1a552452191484048d94c17`
> 站点: `frontend` @ `http://127.0.0.1:18080`（`AGENERP_HTTP_PORT=18080` 的 compose 栈，已 Up 16h）
> **本记录里零 `sid` 真值**（`system-baseline.md` §14「密钥不入源码、不入日志」）。
> 所有 `Set-Cookie` 行的 `sid=` 值一律替换成 `<REDACTED>`，替换由 `sed -E 's/(sid=)[^;]+/\1<REDACTED>/'` 做。

## 结论先行（三句）

1. **H1 不吻合，而且是决定性的**：`POST /api/method/login` 回的 `Set-Cookie: sid=…` **带 `HttpOnly`**。
   ⇒ Desk 里的 JS **读不到 `sid`**，`frappe.get_cookie("sid")` 对它按构造返回 undefined。
   ⇒ 触发本 plan Phase 1 Exit Criteria 第 4 条的停机分支：**Phase 2 跑完就停，Phase 3 / 4 / 5 整体转 `Deferred But Adjudicated`**。
2. **H2 也不吻合**：伪造 / 缺失 `sid` 回的是 **HTTP 403**，不是「200 + `Guest`」。
   但按 plan 的承重格注记，**「不许用状态码代替用户名判定」这条不因此放松**——两者都判是更严，不是更松。
3. **H3 完全吻合**：有效 `sid` 下 `frappe.auth.get_logged_user` 回的**就是登录时那个 `usr`**；
   受限身份「车间工人」读它读不到的 DocType 回 **HTTP 403**。

## Explore P1 — `POST /api/method/login` 的 `Set-Cookie` 逐字

命令原文：

```
curl -i -sS -X POST -H "Host: frontend" -H "Content-Type: application/json" \
  -d '{"usr":"Administrator","pwd":"<REDACTED>"}' http://127.0.0.1:18080/api/method/login
```

退出码 **0**，状态行 `HTTP/1.1 200 OK`，载荷 `{"message":"Logged In","home_page":"/app/home","full_name":"Administrator"}`。

五行 `Set-Cookie`（**逐字，仅 `sid` 值遮蔽**）：

```
Set-Cookie: sid=<REDACTED>; Expires=Mon, 31 Aug 2026 19:57:54 GMT; Max-Age=612000; HttpOnly; Path=/; SameSite=Lax
Set-Cookie: system_user=yes; Path=/; SameSite=Lax
Set-Cookie: full_name=Administrator; Path=/; SameSite=Lax
Set-Cookie: user_id=Administrator; Path=/; SameSite=Lax
Set-Cookie: user_image=; Path=/; SameSite=Lax
```

**逐条读属性**：`HttpOnly` **在**（起草期预测「不带」，**不吻合**）· `Secure` **不在**（本地是 http，符合预期）·
`SameSite=Lax` **在**（起草期未预测，照实记）。

⚠️ **`sid` 是这五个 cookie 里唯一带 `HttpOnly` 的一个** ——
另外四个（`system_user` / `full_name` / `user_id` / `user_image`）都读得到。
这不是「Frappe 不设 `HttpOnly`」，是**它专门只对 `sid` 设**。
⇒ D3⑦ 预设的那条接缝（浏览器 JS 读 `sid` → 放进自定义头 → 转发给本机服务）**按构造走不通**。

## Explore P2 — `GET /api/method/frappe.auth.get_logged_user` 三种输入

| # | 输入 | 状态码 | 载荷（前 300 字节，`sid` 已遮蔽） |
|---|---|---|---|
| a | 有效 `sid`（Administrator） | **200** | `{"message":"Administrator"}` |
| b | 乱写的 `sid`（`sid=zzzz-not-a-real-session-0000`） | **403** | `{"session_expired":1,"exception":"frappe.exceptions.PermissionError: <details><summary>You are not permitted to access this resource. Login to access</summary>Function <strong>frappe.auth.get_logged_user</strong> is not whitelisted.</details>",…}` |
| c | 整个不带 `Cookie` | **403** | `{"exception":"frappe.exceptions.PermissionError: <details><summary>You are not permitted to access this resource. Login to access</summary>Function <strong>frappe.auth.get_logged_user</strong> is not whitelisted.</details>",…}` |

命令原文（三条同形，只差 `-H "Cookie: …"`）：

```
curl -sS -w "HTTP %{http_code}\n" -H "Host: frontend" [-H "Cookie: sid=…"] \
  http://127.0.0.1:18080/api/method/frappe.auth.get_logged_user
```

三条退出码均 **0**（`curl` 层面成功，HTTP 状态码见表）。

**两条实读事实，起草期都没预测到**：

1. **回的不是「200 + Guest」，是 403** —— 因为 `frappe.auth.get_logged_user` 对 Guest **不在白名单里**
   （错误文本逐字 `Function frappe.auth.get_logged_user is not whitelisted`）。
   起草期 H2 假定它对 Guest 也放行并回 `"Guest"`，**这个前提本身是错的**。
2. **b 与 c 的载荷有一处可判的差别**：伪造 `sid` 多一个 `"session_expired":1`，不带 `Cookie` 没有。
   **本记录只记这个差别，不据此设计任何分支** —— 那是 Phase 3 的事，而 Phase 3 已转 Deferred。

## Explore P3 — 受限身份「车间工人」

`worker@hrd.example.com` / 角色 `车间工人` / 可读 `("Work Order", "Stock Entry", "Item")`
（出处 `agenerp/seedusers.py:28-39`）。口令取自 `~/.config/agenerp/secrets.env` 的 `AGENERP_WORKER_PASSWORD`。
⚠️ **本 phase 没有跑 `python3 -m agenerp.seedusers --load-users`**（plan §5 无条件不跑，它是写动作）——
该身份**开工时已在站点上**，登录直接成功，因此不触发那条停机。

| # | 请求 | 状态码 | 载荷摘要 |
|---|---|---|---|
| 1 | `POST /api/method/login`（worker） | **200** | `{"message":"Logged In","home_page":"/app","full_name":"车间工人"}` |
| 2 | `GET /api/method/frappe.auth.get_logged_user`（worker 的 `sid`） | **200** | `{"message":"worker@hrd.example.com"}` |
| 3 | `GET /api/resource/Item?limit_page_length=1`（**可读**） | **200** | `{"data":[{"name":"HRD-ASSY-SVC"}]}` |
| 4 | `GET /api/resource/Sales%20Order?limit_page_length=1`（**不可读**） | **403** | `frappe.exceptions.PermissionError` |
| 5 | `GET /api/resource/Sales%20Order/HRD-SO-0001`（**不可读的单据**） | **403** | `_server_messages` 逐字含 `User <strong>worker@hrd.example.com</strong> does not have doctype access via role permission for document <strong>Sales Order</strong>` |

⇒ **H3 吻合**（两半都吻合）：第 2 行证明「回的就是登录时那个 `usr`」，第 4/5 行证明「读不到的 DocType 回 403」。

⚠️ 第 5 行的 403 载荷里**带着用户名**。照实记：它对「服务面认出的是谁」有可观测性价值，
但**也意味着站点会把身份回给调用方** —— 这条与本 plan 无关，不据此改任何东西。

## Proof — 本 phase 对活站点零写

**读回一 · `bench --site frontend list-apps` 前后一致**

```
$ docker compose exec -T backend bench --site frontend list-apps   # 探测前
frappe  15.118.0 UNVERSIONED
erpnext 15.119.3 UNVERSIONED
exit=0

$ docker compose exec -T backend bench --site frontend list-apps   # 探测后
frappe  15.118.0 UNVERSIONED
erpnext 15.119.3 UNVERSIONED
exit=0
```

**读回二 · 四类可数文档计数**

```
$ curl -sS -G -H "Host: frontend" -H "Cookie: sid=<REDACTED>" \
    --data-urlencode "doctype=<D>" http://127.0.0.1:18080/api/method/frappe.client.get_count
Client Script            {"message":0}
Server Script            {"message":0}
Custom HTML Block        {"message":0}
Workspace Custom Block   {"message":0}
```

⚠️ **这一条的「前值」照实说清，不粉饰**：探测**前**那次计数尝试**没取到数** ——
当时用的是 `curl -u "Administrator:admin"`（HTTP Basic），站点回 `frappe.exceptions.AuthenticationError`，
四条全部无数值。**因此本条的「前值」不是本轮实测的**，而是上半 plan Closure 在
`2026-08-25T02:10Z`（基线 sha `e804143`）实测记录的**四类均 0**
（出处 `docs/analysis/2026-08-24-2311-desk-embed-carrier-probe.md` H1 那一格）。
两次读之间本仓对站点**没有发过任何写请求**（本轮全部请求逐条列在上文三节，
`POST` 只出现在白名单的 `login` / `logout` 两处）。
**「前后一致」这句话对 `list-apps` 是本轮实测的，对四类计数是「后值 = 上一份记录的前值」，口径不同，不合并成一句。**

**收尾 · 两个 `sid` 各打一次 `POST /api/method/logout`**

```
.adminsid  logout HTTP 200
.workersid logout HTTP 200
```

**白名单自查**：本 phase 发出的 `POST` 只有四次 —— 两次 `login`、两次 `logout`，
逐条落在 plan §5.1 见即停第 5 条的两条显式白名单内。其余请求全部是 `GET`。

## 零 `sid` 真值自查

对本文件 grep 本轮用过的两个 `sid` 的前 8 位，**均无输出**（记录见 `docs/logs/2026/08-25.md`）。
承载 `sid` 真值的两个临时文件（`/tmp/p1sb/.adminsid` / `.workersid`，0600，**仓库目录之外**）
在自查后已删除。

## 对下游的直接后果

Phase 1 Exit Criteria 第 4 条逐字命中：

> 若 H1 不吻合（`sid` 是 `HttpOnly`）→ **Phase 2 跑完就停**，
> **Phase 3 / 4 / 5 整体转 `Deferred But Adjudicated`**，重开事件逐字为
> 「`sid` 接缝被重新裁定（由人或一个新 plan）」，并把
> 「浏览器读不到 `sid`，D3⑦ 的接缝需重新裁定」写进 `STATE.md` §3。

⚠️ **不许只停 Phase 3 而让 Phase 4 继续** —— 那会产出「一条没有调用方的认证模式 +
一段取不到 `sid` 的 JS」两个各自关不掉 D3 的残件。本轮**照此执行**。

⚠️ **Phase 2 仍然要跑完**，理由是 plan 逐字写死的（不是本轮现编）：
`sid` 认证模式本身是 D3⑦ 要求的能力，它的正确性与「浏览器能不能读到 `sid`」**是两件事** ——
`sid` 从哪来（Desk JS / 反向代理 / 一个新裁定的接缝）是被 Deferred 的那部分。
