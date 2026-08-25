# Desk 注入接缝 · 执行期探测记录（plan `2026-08-25-1615-1` Phase 1）

> Date: 2026-08-25
> Plan: [`docs/plans/p1-insight/2026-08-25-1615-1-desk-injection-seam-and-asset-route.md`](../plans/p1-insight/2026-08-25-1615-1-desk-injection-seam-and-asset-route.md)
> 落点节: `docs/architecture/module-boundaries.md` §7.22
> ⚠️ **本文件零 `sid` 真值**。所有带认证的命令一律写作 `sid=<真值不落盘>`，
> 真值只存在于执行期的进程环境与 `/tmp`（仓外），收口时对其前 8 位 grep 全仓自证无命中。

## 0. 这份记录回答什么

D-19 把「自建 Frappe custom app」这条路否掉了，**但没有给出替代的注入口**。
`www/app.py:47` 实读证明 Desk 全局 JS 的来源只有 `hooks["app_include_js"]` 与
`frappe.conf["app_include_js"]` 两项，**两项都要求进 Frappe 侧**。
⇒ 今天本仓唯一还能改 Desk 页面的位置是**反代那一层**。本记录就是去实测「借不借得成」。

## 1. `Explore` E-1 —— H1 / H2 / H3 / H4 的实际值

真登录会话取法（`sid` 真值不落盘）：

```
curl -s -o /dev/null -D- -X POST 'http://127.0.0.1:18080/api/method/login' \
  -H 'Content-Type: application/json' -d '{"usr":"Administrator","pwd":"admin"}'
```

→ 回 `Set-Cookie: sid=<真值不落盘>; …; HttpOnly; Path=/; SameSite=Lax`（56 位十六进制）。

### H1 · 反代那一层有没有改写响应体的能力

```
docker compose exec -T frontend nginx -V 2>&1 | tr ' ' '\n' | grep -c -- --with-http_sub_module
docker compose exec -T frontend nginx -V 2>&1 | tr ' ' '\n' | grep -c -- --with-http_addition_module
docker compose exec -T frontend nginx -v
```

| | 预测 | **实际** | 吻合 |
|---|---|---|---|
| `--with-http_sub_module` | `1` | **`1`** | ✅ |
| `--with-http_addition_module` | `1` | **`1`** | ✅ |
| 版本 | （未预测） | `nginx version: nginx/1.22.1` | — |

⇒ **停机分支 ① 不触发**（两项都不为 `0`）。候选 (H) / (I) / (M) 三条经验性候选全部保留在集合里。

### H2 · 登录后的 Desk 页面是不是一份可改写的 HTML

```
curl -s -D- -o /tmp/agenerp_app_body.html -H 'Cookie: sid=<真值不落盘>' http://127.0.0.1:18080/app
```

| | 预测 | **实际** | 吻合 |
|---|---|---|---|
| 状态码 | 200 | **`HTTP/1.1 200 OK`** | ✅ |
| `Content-Type` | 含 `text/html` | **`text/html; charset=utf-8`** | ✅ |
| 体含 `</body>` | 有 | **有，`grep -c -o '</body>'` → `1`** | ✅ |

体长 **277,440 字节**；响应带 `X-Page-Name: app`、`X-From-Cache: False`、`Vary: Accept-Encoding`。

⇒ **`</body>` 在体内出现恰好 1 次** —— 这正是 (H)/(I) 用 `sub_filter` 换字符串所需要的锚点，
且它天然保证「换一次」与「换全部」在本页上等价（`H7` 的「恰好 1 次」有了结构上的理由，不只靠 `sub_filter_once on`）。

### H3 · 上游回给 nginx 的那一跳压不压缩（本 plan 最可能被证伪的一条）

⚠️ **必须带真 `sid`** —— 不带只会拿到 301 空体，空体天然不压缩，那个探针对任何实现都「吻合」，是套套逻辑。

```
docker compose exec -T frontend sh -c "curl -H 'Host: frontend' -H 'Cookie: sid=<真值不落盘>' \
  -H 'Accept-Encoding: gzip' -sD- -o /dev/null http://backend:8000/app"
```

| | 预测 | **实际** | 吻合 |
|---|---|---|---|
| `Content-Encoding` | **不带** | **不带**（响应头逐字：`HTTP/1.1 200 OK` · `Server: gunicorn` · `Content-Type: text/html; charset=utf-8` · `Content-Length: 277459`，**全响应头无 `Content-Encoding` 一行**） | ✅ |

⇒ **H3 吻合，`H3b` 那条对冲未被触发**（无需在候选 (I) 的 location 里加 `proxy_set_header Accept-Encoding "";`）。

⚠️ **两处 gzip 分开记，不许混**：模板 `:149` 的 `gzip on` 是 **nginx→客户端**方向、跑在 `sub_filter`
**之后**，**无害**；本探针测的是 **上游→nginx** 这一跳，只有它压缩才会让 `sub_filter` 静默失效。
上游侧 `Content-Length: 277459` 与经 nginx 出去的 `277440` 相差 19 字节 —— 那是 nginx 侧的头部/体处理差异，
**与压缩无关**（两跳都是明文）。

### H4 · Desk 页面对 Guest 发不发 HTML

```
curl -s -D- -o /dev/null http://127.0.0.1:18080/app
```

| | 预测 | **实际** | 吻合 |
|---|---|---|---|
| 状态码 | 301 | **`HTTP/1.1 301 MOVED PERMANENTLY`** | ✅ |
| `Location` | 含 `/login` | **`Location: /login?redirect-to=%2Fapp`** | ✅ |
| `Content-Length` | `0` | **`Content-Length: 0`** | ✅ |

⇒ 未登录时 Desk 不发 HTML，注入段自然也发不出去。**这不是缺陷，是本接缝的天然边界**：
注入面与 Desk 的可见面**完全重合**，不会多出一条「未登录也能看见注入物」的路径。

## 2. `Explore` E-2 —— envsubst 之后那份配置里，哨兵在哪

```
docker compose exec -T frontend sh -c "grep -n 'listen \|server {\|>>> AgenERP\|<<< AgenERP\|location /agenerp/' /etc/nginx/conf.d/frappe.conf"
docker compose exec -T frontend sh -c "wc -l < /etc/nginx/conf.d/frappe.conf; ls -1 /etc/nginx/conf.d/"
```

实读逐字：

- `35:server {` · `36:	listen 8080;` —— **整份配置只有这一个 `server` 块**
- `51:	# >>> AgenERP …` · `78:	location /agenerp/ {` · `89:	# <<< AgenERP`
- 全文 **173** 行；`conf.d/` 下**只有 `frappe.conf` 一个文件**

⇒ 本仓那**一对**哨兵（`:51` / `:89`）确实落在**唯一那个 `listen 8080` 的 server 块**里，
且 envsubst **不改行号**（模板与渲染结果同为 173 行、哨兵同在 51/89）。
**本 plan 加的东西落在同一对哨兵之间时，它自动也在那个 server 块里** —— 判据⑧ 的那一格不受影响。

## 3. `Explore` E-3（本轮新增）—— 候选 (H) 的作用面**实测**，不是从配置推断

**为什么要多跑这一条**：plan 要求经验性候选的否决依据**必须引执行期探针格**。
只读配置文本能推出「server 级 `sub_filter` 会吃掉所有 `text/html`」，但那是**推论**。
本轮用一次**可复原的临时施加**把它变成实测。

施加物（**只加在那一对哨兵之间、server 级、`location /agenerp/` 之前**，上游一行不动）：

```
sub_filter '</body>' '<!--AGENERP-PROBE--></body>';
sub_filter_once on;
```

生效方式：`AGENERP_HTTP_PORT=18080 docker compose up -d --force-recreate --no-deps frontend`。

| 请求 | 走的是哪条 location | `AGENERP-PROBE` 出现次数 | 状态码 |
|---|---|---|---|
| `GET /app`（带真 `sid`） | `location /` → `@webserver` | **1** | 200 |
| `GET /login`（不带 Cookie，**门户页**） | `location /` → `@webserver` | **1** | 200 |
| `GET /files/agenerp-probe-does-not-exist.html` | `location ~ ^/files/.*.(htm\|html\|svg\|xml)` → `try_files` → `@webserver` | **1** | 404 |
| `GET /api/method/ping`（JSON） | `location /` → `@webserver` | **0**（体逐字 `{"message":"pong"}`） | 200 |

⇒ **(H) 的作用面实测为「所有 `text/html` 响应」**，逐条坐实：
① **误伤门户页**（`/login`，347,156 字节的 `text/html`）；
② **误伤走 `location ~ ^/files/…` 那条路的 HTML**；
③ JSON 不受影响（`sub_filter_types` 默认只吃 `text/html`）⇒ `frontend` 的 healthcheck 探针（打 `/api/method/ping`）不受影响。

⚠️ **边界照实记，不许把降级读成完整**（按 plan §6 写死的降级路径）：

- 活栈实读 `sites/frontend/public/files/` **目录在、文件 0 个**
  （`find … -type f | wc -l` → **`0`**）⇒ **今天这台栈上取不到一份真实 HTML 附件**，
  而唯一造得出对象的办法是往站点上传附件 —— plan Non-Goals 3 **逐字禁止**。
- 上表第三行测的是**代理回来的 404 体**（330,562 字节 `text/html`），**不是真实静态附件那条 `try_files` 命中路径**。
- **另照实记一处起草期未预见的细节**：该 404 响应**没有** `Content-disposition: attachment` 头 ——
  上游模板那条 `add_header Content-disposition "attachment";` 用的是 nginx `add_header` 的默认行为
  （只对 `200/201/204/206/301/302/303/304/307/308` 生效），**404 不在其列**。
  ⇒ 这条降级探针证到的是「**经这条 location 出去的 HTML 体会被改写**」，
  **没有**同时证到「浏览器会把它当附件下载」。
- ⇒ 「**真实静态附件被写进注入串（= 损坏用户文件）**」这一格：
  **推论成立**（`sub_filter` 是输出体过滤器，对 nginx 自己发的静态文件同样生效
  ⇒ 代理体被改写时静态体只会更确定被改写），但**本栈未实测**，
  按 plan 登记为 `D-c-1` 中 (H) 的**残余风险 + `not observed on this stack`**，
  **不得反过来当成已证或已排除**。

复原（施加物是临时的，**不进任何提交**）：

```
cp /tmp/ag_tpl.bak tools/nginx/frappe.conf.template
shasum -a 256 tools/nginx/frappe.conf.template   # → 与施加前逐字相同
```

→ **`RESTORED OK`**（`18ffe64a196186b3484b0f4e584ff064b3ee26d9274ca4260d2b277a7080a5ce`），
`git status --porcelain` 回到「只有本 plan 文件一行」，复原后复跑 `/app` 的 `AGENERP-PROBE` 计数 → **`0`**。

## 4. 四条裁定落在哪

`D-c-1`（注入接缝选型）· `D-c-2`（那段 JS 从哪儿来、由谁发）· `D-c-3`（风险档自评）·
`D-c-4`（与 §7.20 `D-a-2`「不加第三条」的冲突就地裁定）
**四条正文一律落 `docs/architecture/module-boundaries.md` §7.22**，本文件不重复，
只提供它们引用的探针格（§1–§3）。

## 5. 三条停机分支的判定（逐条对照 plan Phase 1 Exit Criteria 第 3 条）

| 分支 | 逐字条件 | 本轮判定 | 依据 |
|---|---|---|---|
| ① | H1 两项**都**为 `0` | **不触发** | §1 H1 实测两项均为 `1` |
| ② | (H) 与 (I) 与 (M) **三条都**被执行期探针证伪 | **不触发** | (I) 未被证伪 —— H3 实测上游**不回** `Content-Encoding`，`H3b` 对冲根本没被用上 |
| ③ | `D-c-3` 自评为 **L3**，**或**（`D-c-4` 判定 `D-a-2` 适用 **且** 具名 location / `try_files` 两条候选也被实测否掉） | **不触发** | `D-c-3` 自评 **L1**（§7.22）；`D-c-4` 裁定 `D-a-2` **不适用**于本条路由（§7.22），合取式的两半都不成立 |

⇒ **三条一条都没触发，Phase 2 / 3 照常执行。**
