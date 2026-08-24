# P1.8 上半 · Desk 承载面只读探测记录

> Source Plan: `docs/plans/p1-insight/2026-08-24-2311-2-desk-embed-carrier-decision.md`
> 探测日期: 2026-08-25（宿主时钟；容器内 `date` 为 UTC，故 curl 响应头显示 `24 Aug 2026 16:47 GMT`）
> 基线 sha: `e804143e243eb4cfabca7605b368193c9d2bc08a`，`git status --porcelain` 无输出
> 站点: `frontend` @ `http://127.0.0.1:18080`，镜像 `frappe/erpnext:v15.119.3`（`bench version`：frappe 15.118.0 / erpnext 15.119.3）
> **全程只读。** 对活站点零写，读回证据见 §5。
> ⚠️ 结论只覆盖**本机这一套栈、这个镜像 tag、这一次**，不外推（D-16）。

## 0. 执行期基线（实读）

```
$ git log -1 --format=%H && git status --porcelain
e804143e243eb4cfabca7605b368193c9d2bc08a
（porcelain 无输出）                                                  exit 0

$ docker compose ps --format '{{.Service}} {{.Status}} {{.Ports}}'    exit 0
backend       Up 15 hours (healthy)
db            Up 15 hours (healthy) 3306/tcp
frontend      Up 15 hours (healthy) 127.0.0.1:18080->8080/tcp
queue-long / queue-short / scheduler   Up 15 hours
redis-cache / redis-queue / websocket  Up 15 hours (healthy)

$ grep -rn "^### 7\." docs/architecture/module-boundaries.md | tail -3   exit 0
:677  ### 7.10 …（P1.6）
:868  ### 7.11 …（P1.7）
:1001 ### 7.12 ① 即时上下文（当前单据）在解释循环里的落点（P1.8 前置 · 2026-08-25）
```

→ **落点节号定为 `### 7.13`**（`7.x` 族当时最大节号是 `7.12`，由本批第一个 plan 落下）。

`sed -n '77,90p' docs/context/ai-autonomy-policy.md` 与
`grep -n "Client Script\|Server Script" docs/architecture/system-baseline.md` 两条已实跑，
结论逐条引在下文（Protected Areas 全表 14 行；`system-baseline.md:370` 逐字「不建 `Server Script` / `Client Script` 任何一种」）。

## 1. 一处必须先说的执行偏离（照实记）

**§5.1 的见即停清单里有「任何 `POST` / `PUT` / `DELETE` 到站点」，而我在取
`Workspace Custom Block` 计数时先用了 `SiteClient.call_method`，它内部走
`POST /api/method/frappe.client.get_count`（`agenerp/site.py:299`）。**

- **它写了什么**：`frappe.client.get_count` 是只读白名单方法，**零写**。§5 的两种读回（§5）已实证。
- **它为什么被跑到**：`SiteClient.list_resource("Workspace Custom Block")` 回 **HTTP 403 PermissionError**，
  当时按「`SiteClient` 的只读方法」这一条白名单去换了个方法，**没有先看它用的是哪个 HTTP 动词**。
- **正确做法**：`c.get("/api/method/frappe.client.get_count", {"doctype": ...})` —— 纯 GET，事后实跑，
  取到同样的数（0）。§5 的读回一律用这一条。
- **判定**：这是**对 plan 自己 §5.1 字面的一次越界**，不是红线。照实记，不粉饰成「等价读操作」。
  教训写死：**白名单要按「实际发出的 HTTP 动词」判，不按「方法名听起来是不是只读」判** ——
  §5.1 对 `python3 -c` 已经做过同一次收紧（「不许 `import frappe`、不许建 DB 连接」），
  对 `SiteClient` 的方法名却没做，这就是那条缝。

## 2. 探测结果表（与 plan §1.4 同结构；§1.4 原文保留不改，两张表并排读）

| 候选 | 资产怎么到浏览器（**实测**） | 解释请求跑在谁的进程里 | 身份 | **结论** |
|---|---|---|---|---|
| **(A) 自建 Frappe app（构建期）** | **实证存在且是全局注入点**：`apps/frappe/frappe/www/app.py:47` 逐字 `include_js = hooks.get("app_include_js", []) + frappe.conf.get("app_include_js", [])`；`www/app.html:69-70` 把它逐条 `include_script(include)` 打进 Desk 页面 | app 里的 whitelisted method，跑在 backend 容器内 | 原生就是当前登录用户（`www/app.py:21` 对 `Guest` 直接 403 + 跳 `/login`） | **需人批**（外部规则见 §3.1） |
| **(B) `Client Script` 文档（运行期）** | **实证做不出全站注入**：`client_script.json` 的 `dt` 是 `reqd: 1` 的 `Link/DocType`；消费端 `frappe/desk/form/meta.py:146-152` 逐字 `filters={"dt": self.name, "enabled": 1}` —— 它挂在**每个 DocType 自己的 meta** 上 | 调不到 `agenerp` | 浏览器带当前用户 cookie | **不能**（结构性做不出全站 ⌘K） |
| **(C) 本机 HTTP 服务 + 浏览器跨源调用** | **到不了 Desk**：`www/app.py:47` 的两个来源之外，Desk 页面没有第三个 JS 注入口 | 本机 `python3 -m agenerp.serve` | 只有管理员凭据 | **不能**（单独满足不了「嵌 Desk」） |
| **(B′) `Website Script` / `Website Theme.js`** | **实证到不了 Desk**：`frappe/hooks.py:46` 逐字 `web_include_js = ["website_script.js"]` —— 是 **`web_include_js`**（门户页），不是 `app_include_js`（Desk）。`www/website_script.py:12` 只把它拼进 `/website_script.js` | — | — | **不能**（结构性不覆盖 Desk） |
| **(B″) `Custom HTML Block` / `Workspace Custom Block`** | **实证能在 Desk 里执行 JS，但只在一张 Workspace 页上**：`custom_block_widget.js` 逐字 `frappe.create_shadow_element(this.body[0], html, style, script)`；入口是 Workspace 上的一个 widget（`desk/desktop.py:379-383`） | 调不到 `agenerp` | 浏览器带当前用户 cookie | **不能**（非全局，且落运行期那扇门） |
| **(D) `Website Settings.head_html` / `banner_html` / `brand_html`** | **实证到不了 Desk**：`head_html` 的唯一消费处是 `templates/includes/head.html:1-2`，它只被 `templates/base.html:24` include；而 **`www/app.html` 既不 `extends base.html` 也不 include `head.html`**（实读：全文只有 `splash_screen.html` 与 `google_analytics.html` 两个 include） | — | — | **不能**（§6 洞四那个形状**在 Desk 上根本不成立**） |
| **(E) `frappe.conf["app_include_js"]`（新发现，起草期未列）** | **是第二个全局 Desk 注入点**：同一行 `www/app.py:47`。来源是 `sites/common_site_config.json` 或 `sites/frontend/site_config.json` —— **两者都在共用的 `sites:` volume 里**（`/proc/self/mountinfo` 实读 `agenerp_sites → /home/frappe/frappe-bench/sites`） | 取决于那段 JS 打谁 | 浏览器带当前用户 cookie | **需人批 + 落运行期那扇门**（§3.4） |
| **(F) 覆盖镜像层的 `apps/**` 或 `assets/**`** | 可行但**不持久**：`/home/frappe/frappe-bench/apps` 与 `.../assets` **不是 volume**（mountinfo 只有 `sites` 与 `logs` 两条），容器重建即丢 | — | — | **不能**（且落运行期那扇门） |
| **(G) 浏览器侧 userscript / 扩展 / bookmarklet** | 技术上可行、不改站点不改镜像 | 本机服务 | 浏览器 cookie | **落运行期那扇门 ⇒ 停机交人，loop 不选**（§3.5） |

## 3. 逐条依据（命令原文 + 退出码 / 源码出处）

### 3.1 (A) 探到的第一处「见即停」，与它触发的**外部规则**

按 §5.1 白名单倒推「资产怎么进 Desk」，(A) 的最短链是：

1. 在本仓写 app 源码（`apps/agenerp_desk/**`）—— 仓内动作，不触任何清单。
2. **把源码弄进容器** —— 三条子路，**每条都在这一步撞见即停**：
   - `docker compose exec -T backend bench new-app agenerp_desk` —— **`bench new-app` 在 §5.1 见即停清单里，写下来但没跑**；
     且实读证明它**白做**：`apps/` 不是 volume，容器重建即丢。
   - 改 `docker-compose.yml` 加 bind mount 或 `build:` —— **Non-Goals 3**（plan 自己的定界）。
   - `docker cp` —— 清单外，按「拿不准即见即停」处理。
3. **注册进 `sites/apps.txt`** —— 实读 `-rw-r--r-- 1 frappe frappe 15 .../sites/apps.txt` 内容 `erpnext\nfrappe`，
   而 `sites/` 是共用 volume ⇒ **「任何写 `sites/` 的命令」，见即停**。
4. `docker compose exec -T backend bench --site frontend install-app agenerp_desk` —— **见即停清单第一条，写下来但没跑。**
5. `bench build` + 重启 —— 见即停。

**H2 要求的「外部规则具体哪一行」——照实说，只引得到一条，而且不是 plan 起草期预测的那条：**

- ✅ **`docs/design/agents-and-roles.md` §9 风险档表 · L3 行**逐字：
  「**L3** | 系统形态变更 | 新建 DocType（DDL）、改权限、改 Workflow | **强制人批** + 落 git + 可回滚」。
  往活站点装一个 app、改 `sites/apps.txt`、改 `installed_apps` 全局值，是**系统形态变更**这个定义本身
  （例子列是「例子」不是穷举）。执行路径逐字「**强制人批** + 落 git + 可回滚」，
  与 D-10 的构建期那扇门（「代码进 git、走 PR 人审、`bench install-app` + **重启**才生效」）逐字同构。
- ❌ **plan §6 H2 预测的那两条判据，实读后不成立，撤回**：
  `tests/gates/test_zero_dep_boot.py` 全文只判「空环境 `config -q` 退 0 / 全部 healthy / 首页含『AI 能力未配置』」，
  一个自建 app 只要能起来就照样绿；`tests/unit/test_compose_zero_dep.py` 的 12 条里，
  `test_bootstrap_script_dir_is_mounted_literally` 的作用域**只有 `bootstrap-homepage` 那一个服务块**
  （实读 `_service_block(BOOTSTRAP_SERVICE)`），`test_no_floating_image_tags` 只扫 `image:` 行、
  管不到 `build:`。**这两条判据挡不住 (A)。**
- ❌ **不引 `DECISIONS.md` D-10 的「重估不早于 P2 跑通」**：D-10 的重估对象是**红线 7 / 运行期 Server Script**
  （「暂不解开红线 7」），不是「人手写一个 custom app」。D-10 反过来**背书**构建期那扇门。
  拿它去挡 (A) 是误读，不写。
- ❌ **不引 Protected Areas 的「对活站点的非破坏性写（建 / 改）」行**：那行的落点列点名的是
  `SiteClient.create_doc` / `ensure_doc` / `seedsite.py`，且 Rule 值是 `plan-first` 而非 `blocked` ——
  它要的是「有 plan」，本 plan 就是，挡不住。

**结论：(A) = `需人批`，外部规则是 §9 风险档表 L3 行。不是 `未测出`** ——
H2 的 `未测出` 分支（plan Phase 1 第二项）**不触发**，因为引到了外部规则的具体一行。

### 3.2 H2b · `bench install-app` 到底发不发 DDL（**只读查证，该命令一次没跑**）

实读 `apps/frappe/frappe/installer.py:273-341` `def install_app`，逐行看它做什么：

- `add_module_defs(name)` → 插 `Module Def` 行
- **`sync_for(name, force=force, reset_permissions=True)`** ← DDL 只可能从这里来。
  实读 `apps/frappe/frappe/model/sync.py:51+`：它按 `IMPORTABLE_DOCTYPES` 里的 18 组
  `(module, doctype)` 去 app 目录下收 `*.json` 文件，逐个 `import_file_by_path`。
  **一个零 DocType 的 app 贡献零个文件 ⇒ 不进 `import_file_by_path` ⇒ 不发 DDL。**
- `add_to_installed_apps` → 写全局 `installed_apps` + `Installed Applications` Single
- `frappe.get_doc("Portal Settings").sync_menu()` / `set_all_patches_as_completed` /
  `sync_jobs()` / `sync_fixtures()` / `sync_customizations()` / `sync_dashboards()` → **还会写更多行**

**H2b 预测：「对一个零 DocType 的最小 app，它不建表、不发 DDL，只插 `Module Def` / `Installed Application` 两类行」**
→ **前半吻合（不发 DDL），后半不吻合**：实读至少还会写 `Portal Settings`、`Patch Log`、
`Scheduled Job Type`、全局 `installed_apps`。**「只有两类行」是错的。**

⚠️ **一条对 §6 护栏有直接影响的实读**：`sync.py` 的 `IMPORTABLE_DOCTYPES` 里
**含 `("custom", "client_script")` 与 `("core", "server_script")`** ——
也就是说**一个「合规的」自建 app 可以把 `Client Script` / `Server Script` 当 fixture 带进站点**。
管道（app + 人审 + 重启）合规，**承载物仍是 DB 里的一行**。
这正是 §6 那句「**管道合规不豁免承载物**」的一个真实例子，记在这里给 P1.8 下半。

### 3.3 (B) `Client Script` —— H3 / H4 复核（**只读镜像内文件，一条文档都没建**）

`docker compose exec -T backend python3 -c "<纯 json.load 表达式，无 import frappe、无 DB 连接>"`
读 `apps/frappe/frappe/custom/doctype/client_script/client_script.json`，字段实读：

```
{'fieldname': 'dt',      'fieldtype': 'Link',   'options': 'DocType', 'reqd': 1}
{'fieldname': 'script',  'fieldtype': 'Code',   'options': 'JS'}
{'fieldname': 'enabled', 'fieldtype': 'Check'}
{'fieldname': 'view',    'fieldtype': 'Select', 'options': 'List\nForm'}
{'fieldname': 'module',  'fieldtype': 'Link',   'options': 'Module Def'}
issingle=None istable=None is_virtual=None module='Custom'
```

- **H3 吻合**：`dt` 是 `reqd: 1` 的 `Link/DocType` ⇒ 只能按 DocType 逐条挂 ⇒ **做不出全站 ⌘K**。
- **H4 吻合，且消费端更严**：`view` 的 `options` 只有 `List` / `Form`，`reqd` 未设 ——
  但消费端 `frappe/desk/form/meta.py:161-176` 实读只有 `if script.view == "List"` 与
  `elif script.view == "Form"` 两个分支，**`view` 为空的记录两个分支都不进，等于整条被丢掉**。
  ⇒ plan H4 那句「别据此推出『范围强制收窄』这种不存在的约束」**要补一句**：
  在**消费端**范围确实是收窄的，只是收窄的机制是「不填就不生效」，不是「必填」。
- **与 D-10 两扇门的对应**：`Client Script` 的承载物是 `tabClient Script` 里的一行文本，
  写完立刻生效（下一次 `meta` 取用即含），`git revert` 撤不掉 ⇒ **运行期那扇门**，逐条对上 D-10。

### 3.4 (E) `frappe.conf["app_include_js"]` —— 起草期完全没预料到的第四类

`www/app.py:47` 的 `include_js` 有**两个**来源，起草期只知道第一个：

```python
include_js = hooks.get("app_include_js", []) + frappe.conf.get("app_include_js", [])
```

`frappe.conf` 来自 `sites/common_site_config.json`（实读存在，226 字节）与
`sites/frontend/site_config.json`，**两者都在共用的 `sites:` volume 里**。
写它的命令是 `bench set-config` —— **§5.1 见即停清单第 6 项，写下来但没跑。**

按 §6 两问逐格答：

| 承载物 | 一① 代码进 git | 一② 走人审 | 一③ 装 app/重启才生效 | 二① 非 git 源的文本 | 二② 写完立刻生效 | 二③ revert+重起后仍在 | 判定 |
|---|---|---|---|---|---|---|---|
| **(E) `site_config.json` 里的 `app_include_js`** | 否 —— 那份 JSON 在 volume 里，不在 git | 否 | 否 | **是** | **是**（`frappe.conf` 按请求读，无重启闸） | **是**（`git revert` 撤不掉 volume 里的文件） | **触发停机交人** |

### 3.5 (C) / (F) / (G) 与「穷举第四类」

**(C) 本机 HTTP 服务，三个障碍逐条记（纸面 + 只读 `curl`，没起任何服务）：**

1. **注入点**（决定性）：Desk 页面的 JS 只有 `www/app.py:47` 那两个来源。(C) **没有任何办法让自己的 fetch 出现在 Desk 页面里**，
   必须借 (A) 或 (B)/(E) 的注入口 ⇒ **H5 的「单独满足不了」成立**。
2. **同源**：Desk 在 `http://127.0.0.1:18080`，(C) 在另一个端口 ⇒ **不同源**。
   实测站点侧对 `OPTIONS /api/method/ping`（带 `Origin`）回 **200 但无任何 `Access-Control-Allow-*` 头** ——
   跨源许可要由 (C) 自己发，这是 D3 ④ 要钉的地方。
3. **cookie / 身份**：`sid` 是站点域下的 cookie，浏览器**不会**把它带给另一个端口的 (C)；
   (C) 手里只有 `agenerp/site.py` 从环境变量取的管理员凭据（`credential_from_env`，`site.py:400`）。
   另记：站点响应头带 `X-Frame-Options: SAMEORIGIN`（实测），iframe 反向嵌 Desk 也不通。

**穷举：除上面三条之外还有没有别的办法把一段 JS 送进 `/app`？** 逐条记否决理由 ——

| # | 办法 | 否决理由（实读出处） |
|---|---|---|
| 1 | `hooks["app_include_js"]` | = **(A)**，需人批 |
| 2 | `frappe.conf["app_include_js"]` | = **(E)**，运行期那扇门 ⇒ 停机交人 |
| 3 | `Client Script` | = **(B)**，按 DocType 逐条挂，非全局 |
| 4 | `Website Script` / `Website Theme.js` | `hooks.py:46` 是 **`web_include_js`**，门户页专用，**Desk 不取** |
| 5 | `Website Settings.head_html` / `banner_html` / `brand_html` | 消费处 `templates/includes/head.html` 只被 `templates/base.html:24` include；**`www/app.html` 不 extends `base.html`** ⇒ Desk 不渲染 |
| 6 | `Custom HTML Block`（+ `Workspace Custom Block` 外壳） | 真在 Desk 里跑 JS（`create_shadow_element`），但**只在放了该 widget 的那一张 Workspace 页上**，且 shadow DOM 隔离 ⇒ 做不出全站 ⌘K；且落运行期那扇门 |
| 7 | `Report.javascript`（实读 `report.json` 有 `javascript` / `report_script` 两个 `Code` 字段） | 只在**那一张报表视图**上生效，非全局；且落运行期那扇门 |
| 8 | `Server Script` | **红线 7，无条件不做** |
| 9 | 覆盖 `apps/frappe/frappe/public/js/**` 或 `assets/**`（`docker cp` / bind mount / 自建镜像） | = **(F)**。实读 `/proc/self/mountinfo`：`frappe-bench` 下只有 `sites` 与 `logs` 两个 volume，`apps` / `assets` 在镜像层 ⇒ 容器重建即丢；且落运行期那扇门 |
| 10 | 浏览器 userscript / 扩展 / bookmarklet | = **(G)**。技术上确实做得到「不改站点不改镜像」，**这正是 plan H5 措辞的反例**（见 §4 H5 行）；但代码不进 git、写完立刻生效、`git revert` 撤不掉 ⇒ **§6 第二问三条全中 ⇒ 停机交人，loop 不选** |
| 11 | 反向代理在 `frontend` 前面注入 `<script>` | 要改 `docker-compose.yml`（Non-Goals 3）；且注入物不来自 git 的部署产物 ⇒ 与 (F) 同判 |
| 12 | `Page` DocType | 实读 `page.json` **没有任何 `Code` 字段** ⇒ 不是注入点 |

**穷举到此为止，边界是**：`www/app.py:47` 这一行就是 Desk 全局 JS 的**完整来源**（`hooks` + `frappe.conf` 两项，
再加 `sentry.bundle.js` 一个条件分支）。凡不经这两项的，要么只能覆盖单个 DocType/Workspace/报表视图（第 3、6、7 条），
要么是改镜像层文件（第 9、11 条），要么在浏览器侧（第 10 条）。
**未穷尽的部分照实说**：本次没有逐一读完 `frappe.get_hooks()` 的全部 hook 名，
只确认了 `app_include_js` 是 Desk `<script>` 的来源；若某个 hook 能在运行时改写 `hooks` 字典，本表会漏掉它。

## 4. §6 假设表逐条「实际」（预测列一个字未改，原文在 plan 里）

| # | 吻合？ | 实际 |
|---|---|---|
| **H1** | **部分吻合** | `Client Script` **0** · `Server Script` **0** · `Custom HTML Block` **0** · `Workspace Custom Block` **0**（前两条同时复核了 open-questions #20，**今天仍成立**）。**`Website Script` 不吻合，但不是数不对，是问法不成立**：实读 `website_script.json` 的 `issingle: 1` ⇒ 它是 **Single**，没有 `tabWebsite Script` 表，`get_count` 直接 HTTP 500 `pymysql.err.ProgrammingError: ('DocType', 'Website Script')`。**「五类都数条数」这个前提对它按构造无效** —— 与 §6 洞三对 `Website Settings` 说的是同一件事，起草期没把它认出来。改判值：`Website Script.javascript` = **NULL**。基准值：`Website Settings.head_html` = NULL · `.banner_html` = sha256 前16位 `0d6c2fcef48a3d44` / len 399（引导脚本写的那段静态文本）· `.brand_html` = NULL · `Website Theme` 实为**普通 DocType**（1 行，`name='Standard'`）不是 Single，`.theme_scss` = `5eed0b43b25e3b9d`/len 165、`.custom_overrides` = 空串、`.js` 载荷里**不存在**（NULL）· `Navbar Settings` 实读**一个 `Code` 字段都没有**（只有 `help_dropdown` / `settings_dropdown` 两张子表）—— Non-Goals 2 把它列进检测面是**多列了一个**，照实记 |
| **H2** | **不吻合** | 卡点**不是**「把 app 源码弄进容器」那一步撞判据 —— 预测点名的 `test_zero_dep_boot.py` 与 `test_compose_zero_dep.py` **实读后都挡不住 (A)**（§3.1）。真正引得到的外部规则是**另一条**：`docs/design/agents-and-roles.md` §9 **风险档表 L3 行**（「系统形态变更 … **强制人批**」）。⚠️ **「必须引到外部规则」这条硬要求本身是满足的**，`未测出` 分支不触发 |
| **H2b** | **前半吻合，后半不吻合** | 不发 DDL：吻合（`sync_for` 对零 DocType app 收不到文件）。「只插两类行」：**错** —— 还写 `Portal Settings` / `Patch Log` / `Scheduled Job Type` / 全局 `installed_apps`（§3.2）。**该命令一次没跑**，全部只读查证 |
| **H3**（复核项，不计入吻合统计） | **仍成立** | `dt` = `Link/DocType` + `reqd: 1`；消费端 `meta.py:148-151` 逐字按 `dt` 过滤 ⇒ 无全局注入点 |
| **H4**（复核项，不计入吻合统计） | **仍成立，且要补一句** | `view` = `Select`，`options` 只有 `List\nForm`，`reqd` 未设 —— 但消费端只有 `== "List"` / `== "Form"` 两个分支，**不填 `view` 的记录整条不生效**。「范围收窄」在消费端是真的，机制是「不填就不生效」而非「必填」 |
| **H5** | **不吻合（被 (G) 反证，且起草期 §6 洞三已预告）** | 存在**不改站点、不改镜像**就把 JS 送进 Desk 页面的办法：浏览器 userscript / 扩展 / bookmarklet。**H5 的措辞是错的。**⚠️ 但它不改变 (C) 的结论：**(C) 单独仍然满足不了「嵌 Desk」**，因为 (C) 指的是「本机 HTTP 服务」，userscript 是**另一个承载物**，且它落在 §6 第二问的三条全中 ⇒ 停机交人、loop 不选 |
| **H6a** | **吻合** | `www/app.py:21-26` 实读：`frappe.session.user == "Guest"` 直接 403 + 跳 `/login`；`Website User` 直接 `PermissionError`。⇒ 进到 Desk 的每一个请求都带着一个已解析的登录用户，app 内 whitelisted method 的调用帧里 `frappe.session.user` 天然就是那个人。**接缝 = 调用帧。本 plan 没有实跑解释。** |
| **H6b** | **吻合** | (B)/(B′)/(B″) 里那段 JS 用浏览器 cookie 打站点 —— 那一段是登录用户；但它**够不到 `agenerp`**（(B) 那格：调不到），真正作答的那一段身份未定。**接缝 = 浏览器 cookie。** |
| **H6c** | **吻合** | `agenerp/site.py:400` `credential_from_env` + `client_from_env(site)`：凭据只来自环境变量（`AGENERP_ADMIN_PASSWORD` / `AGENERP_API_KEY`+`SECRET`），服务端**认不出浏览器里那个人**。**接缝 = `agenerp/site.py` 的凭据来源。** |
| **H7** | **合取结论：吻合 —— 三条候选没有一条是 loop 今天走得完的** | (A) **需人批**（§9 风险档表 L3 行）· (B) **不能**（无全局注入点，且落运行期那扇门）· (C) **不能**（到不了 Desk）。新发现的 (E)/(F)/(G) 同样**一条都不是 loop 走得完的**：(E) 二①②③ 全中、(F) 同判且不持久、(G) 二①②③ 全中 ⇒ 全部触发 §6 停机交人。**H7 的「停机交人」分支不触发**，因为它的触发条件是「真有一条走得完」 |

**吻合统计（H3/H4 复核项不计入）**：8 条计入 —— 吻合 4（H6a/H6b/H6c/H7）· 部分吻合 2（H1/H2b）· 不吻合 2（H2/H5）。

## 5. 对活站点零写 —— 两种读回，逐条实证

**① `bench --site frontend list-apps` 前后一致，四类可数文档计数不变**

```
$ docker compose exec -T backend bench --site frontend list-apps          exit 0
frappe  15.118.0 UNVERSIONED
erpnext 15.119.3 UNVERSIONED
（探测前实读 sites/apps.txt 内容 = "erpnext\nfrappe"，apps/ 目录 = erpnext, frappe —— 一致）

计数（探测前 → 探测后，均经 GET /api/method/frappe.client.get_count）：
  Client Script            0 → 0
  Server Script            0 → 0
  Custom HTML Block        0 → 0
  Workspace Custom Block   0 → 0
  Website Script           —— Single，计数按构造无效，改由 ② 判值
```

**② Single / `Code` 字段的值前后逐字比对**（sha256 前16位 / 长度）

```
  Website Settings.head_html         None            → None
  Website Settings.banner_html       0d6c2fcef48a3d44/len=399 → 0d6c2fcef48a3d44/len=399
  Website Settings.brand_html        None            → None
  Website Script.javascript          None            → None
  Website Theme[Standard].theme_scss 5eed0b43b25e3b9d/len=165 → 同
  Website Theme[Standard].custom_overrides  空串     → 空串
  Website Theme[Standard].js         载荷中不存在（NULL） → 同
  Navbar Settings                    无任何 Code 字段 → 同
```

→ **对活站点零写成立。** §1 记的那次 `POST /api/method/frappe.client.get_count` 由这两条读回覆盖：它没写任何东西。

## 6. 交给 P1.8 下半的三条实读事实

1. **Desk 全局 JS 的完整来源是 `www/app.py:47` 一行两项**（`hooks["app_include_js"]` + `frappe.conf["app_include_js"]`）。
   任何承载面设计先回答「我走这两项里的哪一项」。
2. **(A) 的身份是白送的**：`www/app.py:21-26` 已经把 Guest 与 Website User 挡在外面，
   app 内 whitelisted method 的 `frappe.session.user` 就是登录用户 —— 但这只对**跑在容器内**的那段代码成立。
   凡把请求转手给本机 `agenerp` 进程的形状，身份都要重新回答（D2）。
3. **一个「合规的」自建 app 可以把 `Client Script` / `Server Script` 当 fixture 带进站点**
   （`sync.py` 的 `IMPORTABLE_DOCTYPES` 含这两项）——**管道合规不豁免承载物**，
   P1.8 下半的 app 里不得出现这两类 fixture。
