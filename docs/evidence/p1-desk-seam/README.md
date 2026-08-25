# Desk 注入接缝 · 活栈实证（plan `2026-08-25-1615-1` Phase 3）

> Date: 2026-08-25 · 落点节 `docs/architecture/module-boundaries.md` §7.22
> ⚠️ **本目录零 `sid` 真值。** 带认证的命令一律写作 `sid=<真值不落盘>`，收口时对其前 8 位 grep 全仓自证无命中。
> ⚠️ 页面片段**只留含注入标记的那几行，不落整页**（`/app` 整页 277KB，落进仓里是纯噪声）。

## 1. 注入标记与资产 URL 的取法（全程不写第三个字面量）

两者**都从 `tools/nginx/frappe.conf.template` 的注入段里读出来**，不在证据里另抄一份：

```python
t = pathlib.Path('tools/nginx/frappe.conf.template').read_text(encoding='utf-8')
body = t[t.index('# >>> AgenERP'):t.index('# <<< AgenERP')]
lines = [l.strip() for l in body.splitlines() if l.strip() and not l.strip().startswith('#')]
anchor, repl = re.findall(r"'([^']*)'", next(l for l in lines if l.startswith("sub_filter '")))
marker = repl.replace(anchor, '')
url = re.findall(r'<script src="([^"]+)"></script>', marker)[0]
```

实读结果：`marker` = `<script src="/agenerp/desk.js"></script>` · `url` = `/agenerp/desk.js`。

## 2. H5 … H11 八条的「预测 ↔ 实际」

| # | 探针 | 预测 | **实际** | 吻合 |
|---|---|---|---|---|
| `H5` | 一次性容器里 `nginx -t`；回归两条 | exit 0 · `/api/method/ping` 200 · `/agenerp/health` 200 | `nginx: configuration file /etc/nginx/nginx.conf test is successful`，**exit 0** · `ping=200` · `health=200` | ✅ |
| `H6` | 不带 Cookie 取资产 URL（从模板读出） | 200 · `text/javascript; charset=utf-8` | **`code=200`** · **`Content-Type: text/javascript; charset=utf-8`** · `Content-Length: 1193` | ✅ |
| `H7` | 带真 `sid` `GET /app`，数注入标记 | **恰好 1 次** | **`marker count = 1`**（`code=200`） | ✅ |
| `H8` | `stop agenerp-serve` → `up -d --force-recreate --no-deps frontend` | frontend 不进重启循环 · `/app` 仍 200 且标记仍在 · 资产 URL 回 502 | `frontend` **`Up 5 seconds (healthy)`**、**`RestartCount = 0`** · `app=200`、**`marker count = 1`** · **`asset(/agenerp/desk.js)=502`** · `ping=200` | ✅ |
| `H9` | `pytest tests/unit/test_compose_zero_dep.py -q` | exit 0，14 条全绿，一条未改松 | **`14 passed`**，exit 0（**冷起后复跑见 §4**） | ✅ |
| `H10a` | 不带 Cookie `GET /login`，数注入标记 | 选 **(I)** ⇒ **0 次** | **`count = 0`**（`code=200`，体 **347,156** 字节 —— **有体可数，不是空响应**） | ✅ |
| `H10b` | `GET /files/<不存在>.html`，数注入标记 | 选 **(I)** ⇒ **0 次** | **`count = 0`**（`code=404`，体 **330,562** 字节 —— **有体可数**） | ✅ |
| `H11` | 注入标记落在 `</body>` 之前还是 `</html>` 之后 | 选 (I) ⇒ **在 `</body>` 之前** | `marker@277444` · `</body>@277484` · `</html>@277492` ⇒ **在 `</body>` 之前**（也在 `</html>` 之前） | ✅ |

**八条全部吻合预测，无一条需要「照实记不吻合」。**

⚠️ **`H10a` / `H10b` 是选中项 (I) 的代价那一半，两条都不是「未观察」** ——
两次请求都**真回了几十万字节的 `text/html`**（347,156 / 330,562），**有体可数**，数出来是 0。
对照 Phase 1 的 `E-3`：**同样两条请求，在候选 (H) 下各数出 1 次**。
⇒ **(I) 与 (H) 的作用面差异是实测出来的，不是论证出来的。**

⚠️ **「真实静态附件会不会被损坏」不在本表内**（按 plan §6 写死的降级路径）：
本栈 `sites/frontend/public/files/` **文件 0 个**，造对象要往站点上传附件——Non-Goals 3 逐字禁止。
该格是 `D-c-1` 中 **(H) 的残余风险 + `not observed on this stack`**，
**不得反过来当成已证或已排除**。选中 (I) 之后本仓不再承担它，但记录留下。

## 3. 注入后的页面片段（只留含标记的那几行）
### /app（带真 sid，注入后）

**只留含标记的那几行，不落整页。**

```html
</audio>
		
		<audio preload="auto" id="sound-call-disconnect" volume=0.2>
			<source src="/assets/erpnext/sounds/call-disconnect.mp3"></source>
		</audio>
		
	<script src="/agenerp/desk.js"></script></body>
</html>
```

### /app（agenerp-serve 停掉后，H8）

**只留含标记的那几行，不落整页。**

```html
</audio>
		
		<audio preload="auto" id="sound-call-disconnect" volume=0.2>
			<source src="/assets/erpnext/sounds/call-disconnect.mp3"></source>
		</audio>
		
	<script src="/agenerp/desk.js"></script></body>
</html>
```

## 4. 变异自查 M1 … M12（每条只改一处、跑判据、记被打红的**具体那一条**、复原、`sha256` 比对）

判据集合：`tests/unit/test_desk_asset_route.py` + `tests/unit/test_desk_injection_static.py`
+ `tests/unit/test_explain_same_origin.py`（**共 45 条，基线全绿**）。

| # | 变异（只改一处） | 目标文件 | 退出码 | **被打红的具体那一条** | 复原 |
|---|---|---|---|---|---|
| **M1** | 改 `ROUTE_PREFIX` → `/agenerpX` | `agenerp/serve/app.py` | **1** | **11 条一起红**，含 `test_desk_injection_static::test_injected_url_prefix_equals_route_prefix` · `test_injected_filename_equals_asset_route_constant` · `test_desk_asset_route::test_404_message_enumerates_exactly_the_paths_this_module_serves` · 以及 P1.8a 既有的 `test_explain_same_origin::test_nginx_location_prefix_equals_route_prefix` 等 6 条 | `RESTORED OK` |
| **M2** | 改注入的文件名 → `desk2.js` | `tools/nginx/frappe.conf.template` | **1** | `test_desk_injection_static::test_injected_filename_equals_asset_route_constant` | `RESTORED OK` |
| **M3** | 把整段 `location ^~ /app` **挪到哨兵之外** | 模板 | **1** | **6 条**，其中点名那一格是 `test_injection_lives_between_the_agenerp_sentinels` | `RESTORED OK` |
| **M4** | 资产路由改成**读到 Cookie 才发** | `app.py` | **1** | `test_desk_asset_route::test_asset_is_served_without_any_cookie` | `RESTORED OK` |
| **M5** | `ASSET_CONTENT_TYPE` 改成 `application/json` | `app.py` | **1**（**第一轮是 0，见下方 🔴**） | `test_desk_asset_route::test_asset_content_type_is_javascript` | `RESTORED OK` |
| **M6** | 把资产内容改一个字节（`0.1.0` → `0.1.1`） | `agenerp/serve/assets/desk.js` | **0** | **没打红** —— 🔴 见下方逐字说明 | `RESTORED OK` |
| **M6b** | 只让**服务发出的字节**与磁盘不同（响应体尾部多一个 `\n`） | `app.py` | **1** | `test_desk_asset_route::test_asset_body_is_byte_identical_to_the_repo_file` | `RESTORED OK` |
| **M6c** | 把资产**掏空**成一行注释 | `desk.js` | **1** | `test_desk_asset_route::test_asset_file_is_not_gutted`（**本轮补的断言**） | `RESTORED OK` |
| **M7** | 改模板里 `/agenerp/` 的上游端口 `8330` → `8331` | 模板 | **1** | `test_desk_injection_static::test_template_upstream_port_equals_compose_serve_port` | `RESTORED OK` |
| **M8** | 删掉 `resolver 127.0.0.11 …` 那一行 | 模板 | **1** | `test_explain_same_origin::test_the_reverse_proxy_does_not_make_nginx_startup_depend_on_the_upstream`（§7.21 `D-b-8` 的不回归） | `RESTORED OK` |
| **M9** | **只**改 `_not_found()` 文案（少枚举一条） | `app.py` | **1** | `test_desk_asset_route::test_404_message_enumerates_exactly_the_paths_this_module_serves` | `RESTORED OK` |
| **M10** | 注入段**整段注释掉、URL 留在注释里** | 模板 | **1** | **6 条**，其中点名那一格是 `test_injection_is_on_effective_lines_not_commented_out` | `RESTORED OK` |
| **M11** | `sub_filter_once on` → `off` | 模板 | **1** | `test_desk_injection_static::test_sub_filter_once_is_on` | `RESTORED OK` |
| **M12** | 资产路由改成用**请求路径**拼文件名 | `app.py` | **1** | `test_desk_asset_route::test_the_asset_file_path_is_never_built_from_request_data` | `RESTORED OK` |

**14 次施加，13 次打红，1 次没打红（M6）。全部 `RESTORED OK`，变异后判据集合复跑仍 `45 passed`。**

### 🔴 M5 第一轮**没打红** —— 这是本轮抓到的一个真窟窿，照实记

**第一轮实测**：把 `ASSET_CONTENT_TYPE` 改成 `application/json` 之后，判据集合 **`44 passed`、退出码 0**。

**为什么**：当时那条判据写的是 `headers.get("Content-Type") == ASSET_CONTENT_TYPE` ——
**两边是同一个常量的两次读取**。它守得住「服务与自己的常量漂开」，
**守不住「常量本身被改成一个浏览器不会执行的类型」**。
而后者的失败形态正是最难发现的那种：HTML 里那个 `<script>` 标签**照样在**、`curl` **照样 200**、
`nginx -t` **照样绿** —— 只有浏览器不执行它。**绿着坏掉。**

**当场补的断言**（`test_asset_content_type_is_javascript` 改成两层一起判）：
① 服务实际发出的 == `ASSET_CONTENT_TYPE`（原有那层）；
② **`ASSET_CONTENT_TYPE` 的 media type 必须落在浏览器认得的 JavaScript MIME 集合里**
（`text/javascript` / `application/javascript` / `application/x-javascript`），且必须声明 `charset=utf-8`。

⚠️ **②里那个集合是本 plan 全部判据中唯一一处刻意写死的字面量，理由在判据 docstring 里逐字写清**：
它对齐的**不是本仓的另一个文件，而是浏览器那一侧的契约** —— 没有第二个仓内文件可以「各读一次再比」。
补后复跑 M5 → **退出码 1**，打红 `test_asset_content_type_is_javascript`。

### 🔴 M6 没打红 —— **按构造就打不红，不是判据漏了**

`test_asset_body_is_byte_identical_to_the_repo_file` 比的是
**「服务发出的字节」↔「磁盘上那份的字节」**，两个源。改了磁盘上那份，服务发出的**也跟着变**
⇒ 两边仍然相等，**它按构造照不红**。

**它守的到底是什么，说清楚**：守的是「**服务发出的 ≠ git 里那份**」
（服务把内容改了、缓存了旧的、发了别处的一份）—— 变异 **M6b** 实测打红它。

**能不能补一条让 M6 也红的断言？—— 不补，理由写清**：那要求判据里钉死一份内容或哈希，
于是**每次改这段 JS 都要同步改判据**，是纯 churn，且它挡的「内容被改坏」本来就该由 code review 挡。
**补的是一条只看形状的下限判据**（`test_asset_file_is_not_gutted`：非空、含 `agenerpDesk` 标记名、
含 `Object.freeze`、是收尾完整的 IIFE），它挡「掏空」这个真实失败形态 ——
变异 **M6c** 实测打红它。**M6 的「没打红」保留在表里，不粉饰。**

## 5. 上游副本差集复核

```
docker run --rm --entrypoint cat frappe/erpnext:v15.119.3 /templates/nginx/frappe.conf.template \
  | diff - tools/nginx/frappe.conf.template
```

退出码 **1**（有差集，符合预期）。差集逐字：

- 上游那份 **113** 行；本仓副本 **213** 行。
- **`< ` 行（上游有而本仓没有的）= `0` 条** ⇒ **上游一行都没被删、没被改。**
- **`> ` 行（本仓加的）= `100` 条**，落在**恰好两个 hunk** 里：
  **`0a1,20`**（文件头注释块，20 行，**无哨兵**）· **`30a51,130`**（那**一对**哨兵及其之间的全部内容，80 行）。

⇒ **K3 成立：副本与上游的差集只有本仓那两段。** 本 plan 加的 `location ^~ /app`
落在第二段（哨兵之间）里，**没有产生第三段**，也没有改动上游任何一行。
（本 plan 之前第二段是 39 行，之后是 80 行 —— **段数不变，只是第二段变长**。）

## 6. 一次真正的冷起（`down -v` → `up -d --wait --wait-timeout 900`）

```
docker compose down -v                                             # EXIT=0
AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 900   # EXIT=0
```

- **`up` 退出码 = 0**，**墙钟 = 68 秒**。
- ⚠️ **宿主对外口必须给 `18080`** —— 不给会死在
  `Bind for 0.0.0.0:8080 failed: port is already allocated`（本机 `8080` 被另一个 compose 项目占着）。
  本轮**实际撞到过一次**：Phase 1 里第一次 `--force-recreate frontend` 没带这个变量，逐字报了这条错，
  带上之后即成功。**照实记，不当作偶发。**
- **十个长期服务全部 `running`**（`agenerp-serve` / `backend` / `db` / `frontend` / `queue-long` /
  `queue-short` / `redis-cache` / `redis-queue` / `scheduler` / `websocket`），
  **有探针的七个全部 `healthy`**；一次性的 `configurator` 正常 `Exited`。
- **本轮冷起一次成功，没有复现** roadmap 工作项 10 记过的那个 `No such container` 偶发。

### 冷起后复跑（不是拿冷起前的数充数）

| 项 | 结果 |
|---|---|
| `H9` `python3 -m pytest tests/unit/test_compose_zero_dep.py -q` | **`14 passed`**，**退出码 0**，**一条未改松** |
| `H5` 容器内 `nginx -t` | **退出码 0** |
| `H5` 回归两条 | `/api/method/ping` **200** · `/agenerp/health` **200** |
| `H6` 不带 Cookie 取资产 URL | **200** · `Content-Type: text/javascript; charset=utf-8` |
| `H6` 补一格 | `cmp` 与 `agenerp/serve/assets/desk.js` → **逐字节相同** |
| `H7` 带真 `sid`（**冷起后重新登录取的新 `sid`**）`GET /app` | **200**，注入标记 **恰好 1 次** |

⇒ **冷起之后这一跳仍然成立** —— 注入不是靠某个手工改过的运行中容器撑着的。

## 7. `sid` 零落盘自证

```
grep -rn "<sid 前 8 位>" . --exclude-dir=.git | wc -l
```

→ **`0`**（Phase 1 与 Phase 3 各取的两个真 `sid` **各自跑过一次**，两次都是 `0`）。
真值只存在于执行期的进程环境与仓外的 `/tmp`，**没有任何一份落进本仓**。

## 8. `verification scope limited` —— 本轮**没做**的，逐条写明

- **未跑整仓 `pytest tests -q -m "not live"`**：本轮跑的是 `tests/unit`（**800 passed, 6 skipped**）
  + `tests/contracts tests/tools tests/routing tests/context`（**456 passed, 13 skipped**）。
  ⇒ **scoped verification，不等于 full verification。**
- **未经 CI 服务端复跑**：本轮全部证据来自本机。CI 是唯一不可被本地绕过的一层，**它还没跑过这份改动**。
- **未做任何浏览器验证**：本轮用 `curl` 证到「HTML 里确实有那个 `<script src>` 标签、且那个 URL 真回 200 JS」。
  ⚠️ **「HTML 里有 `<script>` 标签」≠「浏览器执行了它」** —— 本 plan **从不声称**已证浏览器行为
  （Non-Goals 5 / §8 R3），承接者是工作项 11 的第 2 个 plan。
- **未证「真实静态 HTML 附件不会被损坏」**：见 §2 末那一段 —— 那是 (H) 的残余风险，
  本栈 `files/` 为空、Non-Goals 3 禁止上传取证 ⇒ `not observed on this stack`。选 (I) 后本仓不再承担它。
- **未声称满足 WBS §4 P1.8b 的验收命令**（`pytest -m live tests/ui/test_sidebar.py`）：
  本 plan 不建 `tests/ui/`、不交付 `test_sidebar.py`（Non-Goals 2）。
