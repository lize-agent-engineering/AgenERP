# P1.8b 下半 · ⌘K 侧边栏执行期探测记录

> 交付 plan：`docs/plans/p1-insight/2026-08-25-1743-1-desk-sidebar-cmdk-and-live-ui-gate.md`
> 执行日：2026-08-26 · 基线 sha：`1663c05` · 工作树：`git status --porcelain` **无输出**
> 落点节：`docs/architecture/module-boundaries.md` §7.23

**本文件只记「跑了什么命令、退了什么码、看到了什么」与「五条裁定的理由」。**
一切结论的效力以命令原文与退出码为准，不以本文的措辞为准。

## 0. 执行前重取基线（plan §0 六条，逐条实跑）

| # | 命令 | 退出码 | 实读值 |
|---|---|---|---|
| 1 | `git log --oneline -3` + `git status --porcelain` | 0 | `HEAD = 1663c05`；`status` **无输出**（工作树干净） |
| 2a | `python3 tools/gates/check_expected_red.py` | **0** | `门禁 28 项：预期红 0，绿 28，跳过 0` —— 与 plan §1.9 起草期记的**逐字一致** |
| 2b | `python3 -m pytest tests/unit -q` | **0** | `807 passed, 6 skipped` —— ⚠️ **与 plan §1.9 记的 `801 passed` 不一致**，起草后仓里又加了 6 条。**以本行为准**（§0 第 2 条：以执行期实读为准） |
| 2c | `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` | **0** | `456 passed, 13 skipped` —— 与起草期**一致** |
| 2d | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | **0** | `All checks passed!` —— 与起草期**一致** |
| 3 | `ls -d tests/*/ \| xargs -n1 basename \| sort \| tr '\n' ' '` | 0 | `context contracts experiments fixtures gates routing tools unit` |
| 4 | `python3 -c "import playwright, pytest_playwright"` | **0** | `playwright 1.58.0` · `pytest-playwright 0.7.2` · `selenium 4.39.0`（备选）· `~/Library/Caches/ms-playwright` 下 `chromium-1208/1223/1228` + `chromium_headless_shell-*` 已下载 |
| 4a | `grep -n -A6 'optional-dependencies' pyproject.toml` | 0 | `:21 [project.optional-dependencies]`，内含 `ui = ["playwright>=1.47"]`（人落的，D-25） |
| 4a' | `python3 -c "import tomllib,…"` | 0 | `['certifi>=2024.2.2'] {'ui': ['playwright>=1.47']}` —— **`[project].dependencies` 仍逐字只有 `certifi`** |
| 4b | `grep -n 'D-25' docs/masterplan/DECISIONS.md` | 0 | **`:373` `### D-25 · 批准引入浏览器驱动，但**只作可选 extra**`** |
| 4b' | `grep -n '\[resolved\].*浏览器驱动' docs/masterplan/STATE.md` | 0 | **`:496`**（⚠️ **不是 plan §0.5 写的 `:425`** —— 行号已漂，按字面定位是对的）逐字：`[resolved] 2026-08-26T01:47Z · **答完 P1.8b plan §0.5 的最后一条 —— ① 浏览器驱动，人已批准。该 plan 的 Review Hold 两条前置全部解除。**` |
| 5 | `grep -n '^\| P1.8b' docs/masterplan/02-WBS.md` | 0 | **`:89`**（与 plan §1.1 第 7 轮改准后的数字一致）。验收命令逐字 `pytest -m live tests/ui/test_sidebar.py` 退 0 |
| 6 | `env \| grep -c '^AGENERP_LLM_'` + `env \| grep -o '^AGENERP_LLM_[A-Z_]*'` | 0 | **个数 = 1**；变量名**只有** `AGENERP_LLM_MODEL`（**值一个字未打印**） |

### §0 第 5 条：`gates.yml` 锚点行号执行期重取（**不认 plan 里写的数字**）

| 锚点（按注释/字面原文定位） | plan §0.6 第 5 轮记 | **本次实读 @ `1663c05`** |
|---|---|---|
| `COVERED="contracts context experiments fixtures gates routing tools unit"` | `:597` | **`:597`**（未漂） |
| `- run: pip install pytest certifi`（`unit-and-contracts` 的） | `:567` | **`:567`**（未漂；另有 `:104/:176/:252/:513` 四处同字面，属别的 job） |
| `run: ruff check agenerp tests/unit …`（`lint` job） | `:646` | **`:646`**（未漂） |
| `# 作用域三个目录逐字照抄 …` | `:640` | **`:640`**（未漂） |
| `# 这几个目录由 loop 写在红线外，接进 CI 属红线 2，故由人做。` | `:579` | **`:579`**（未漂） |
| `# 判据自身的判据：跳过就是没跑，没跑就是红。` | `:528` / `:592` 两处 | **`:528` 一处**；`:592` 今天是 `# 判据自身的判据：新增目录若忘了接进来，这一步会红。`（同族不同句） |
| `# job 退 1。配上之后它走答案面，与起栈步同一套变量。` | `:321` | **`:321`**（未漂） |
| `# 于是 8 条红。摘掉它能让 CI 变绿，但那是**把判据调整到迁就环境**，` | `:293` | **`:293`**（未漂） |
| `❌ 工具执行层门禁出现 skip …`（零 skip 断言形态） | `:529-530` | **`:530`** |

⚠️ **`STATE.md` 那一处漂了 71 行（`:425` → `:496`）。** 这正是 plan 反复写的那条：**行号会漂，按字面定位**。

### 停机分支 4 的免停条件：**执行期实读满足，本分支不触发**

三处出处**全部仍在仓里**：`DECISIONS.md:373` 的 **D-25** · `STATE.md:496` 的 **`[resolved]` 行** ·
`pyproject.toml:21-` 的 `ui = ["playwright>=1.47"]`（`d69b335` 落的形态，且 `dependencies` 一个字未加）。
⇒ **不往 `STATE.md` 追加那条 needs-human，不停机。**

## 1. 六条探针的实际值（plan §6 `H1` / `H2` / `H2b` / `H3` / `H4` / `H5`）

**顺序按 plan Phase 1 写死的：`H2b` 排在 `H3` / `H4` 之前。**

### `H1` —— `tests/` 目录集合 vs `gates.yml` 第 ⑦ 步 `COVERED`

命令：`ls -d tests/*/ | xargs -n1 basename | sort | tr '\n' ' '` → exit 0

```
context contracts experiments fixtures gates routing tools unit
```

`gates.yml:597`：`COVERED="contracts context experiments fixtures gates routing tools unit"`
（该步把两边都 `sort` 后比较）⇒ **两边相等，八个目录。**

**预测：两边相等 ⇒ 吻合。** ⇒ 这一步今天是绿的；本 plan 落下 `tests/ui/` 之后**必红**（plan §1.4，已裁、已交接）。

### `H2` —— 驱动可用性

| 命令 | 退出码 | 实际 |
|---|---|---|
| `python3 -c "import playwright, pytest_playwright"` | **0** | `/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/playwright/__init__.py` |
| `p.chromium.launch(headless=True)` + 打开 `data:text/html` 读 DOM | **0** | **chromium `145.0.7632.6` 真起来了**，`page.text_content("#x")` → `ok` |

**预测：都成功、能起 chromium ⇒ 吻合。** ⇒ **停机分支 ① 不触发。**

### `H2b` —— 浏览器发出的 `Host: 127.0.0.1:18080` 这一跳落不落到 `frontend` 站

**这是本仓第一次直接观测。** 起草期只有推断（Frappe 在 Host 不匹配时回落到 `currentsite.txt` 的默认站）。

活栈实读：`docker compose ps` → 十个长期服务 `running`，七个有探针的全 `healthy`；
`frontend` 端口映射 `127.0.0.1:18080->8080/tcp`。

```
pg.goto("http://127.0.0.1:18080/login")
```

| 观测项 | 值 |
|---|---|
| HTTP 状态 | **200** |
| 最终 URL | `http://127.0.0.1:18080/login`（**无重定向到错误页**） |
| `document.title` | **`Login`** |
| `#login_email` 存在 | **True** |
| `input[type=password]` 存在 | **True** |
| 响应体长度 | 357,913 字节 |

**预测：落到 `frontend`（默认站回落）⇒ 吻合。**
⇒ **`--host-resolver-rules="MAP frontend 127.0.0.1"` 那条对冲分支 _未被触发_**，
本 plan 的自建 fixture **不带**该参数，基址逐字是 `http://127.0.0.1:18080`。
⚠️ 它是**留了记录的备用件**：站点哪天不再 `--set-default`、或 compose 起多站，这一跳会静默落到别的站，
届时第一处置就是加上那个 Chromium 参数（**不改 compose / 不改 nginx / 不改 `/etc/hosts`**）。

### 真登录（`H3`/`H4`/`H5` 的共同前提，plan §5「不手工伪造 Cookie」）

走站点自己的 `/login` 表单：`#login_email = Administrator` · `input[type=password] = admin` · `button.btn-login`。

| 观测项 | 值 |
|---|---|
| 登录后 URL | `http://127.0.0.1:18080/app/setup-wizard/0` |
| Cookie 名集合 | `['full_name', 'sid', 'system_user', 'user_id', 'user_image']` |
| `sid` 的 `httpOnly` / domain / path | **`True`** / `127.0.0.1` / `/` |
| 页面内 `document.cookie` 能否看到 `sid` | **False** |

⇒ **`sid` 确实是 `HttpOnly`，JS 读不到它。**（这坐实了 plan §1.8 那半句；另一半「浏览器仍会自动发」由 Phase 3 的 `H6` 判。）

### `H5` —— 注入的 `<script src="/agenerp/desk.js">` 在不在、几次

带真登录会话，三条路径各取一次：

| 路径 | 状态 | 最终 URL | `'/agenerp/desk.js'` 在 HTML 里出现次数 | `window.agenerpDesk` |
|---|---|---|---|---|
| `/app` | 200 | `/app/setup-wizard` | **1** | `{"name":"agenerp-desk","version":"0.1.0","plan":"2026-08-25-1615-1"}` |
| `/app/user/Administrator` | 200 | `/app/setup-wizard` | **1** | 同上 |
| `/app/user` | 200 | `/app/setup-wizard` | **1** | 同上 |

**预测：在，恰好 1 次 ⇒ 吻合。**
⚠️ 而且比预测**更强一格**：`window.agenerpDesk` 读得到 ⇒ **脚本不只是「标签在 HTML 里」，它真的被浏览器执行了**。
这是 plan §1.2 引的那句「『HTML 里有 `<script>` 标签』≠『浏览器执行了它』」**第一次被正面回答**。

### `H3` —— Frappe v15 Desk 自己有没有占用 `Cmd/Ctrl+K`

**两路证据，都不是推断。**

**(a) 读 Frappe 自己的快捷键注册表**（`frappe.ui.keys.handlers`）：

```
["alt+h","alt+s","ctrl+down","ctrl+g","ctrl+h","ctrl+s","ctrl+up",
 "enter","esc","escape","shift+/","shift+ctrl+g","shift+ctrl+r"]
```

`handlers["k"]` → **`ABSENT`**。`standard_shortcuts` 共 8 条。

**(b) 真按下去看有没有原生响应**（在真登录的 Desk 页上，capture 阶段挂 `keydown` 观测器）：

| 动作 | `activeElement` 变化 | 打开的 modal 数 | `event.defaultPrevented` |
|---|---|---|---|
| `Control+K` | **无**（前后都是 `INPUT.input-with-feedback form-control bold`） | **0** | **false** |
| `Meta+K` | **无** | **0** | **false** |

**预测：「倾向：Frappe 的 awesomebar 走 `Ctrl+G`，`K` 很可能空着」⇒ 吻合，且两路互证。**
（`ctrl+g` 确实在注册表里，`shift+ctrl+g` 也在。）

⇒ **`D-d-4` 保留 `Cmd/Ctrl+K`，不动次选键。**
⇒ plan §11 那条「`D-d-4` 若改了键位 ⇒ 与 WBS 第 89 行『⌘K』字面的偏差」**未触发**，收口时照实写「未触发」。

### `H4` —— 当前单据上下文从哪儿取最稳

⚠️ **这一格是六条里唯一**没有**按预测走的，而且它暴露了一件 plan 起草期不知道的事。照实记。**

**预测**：URL 路径 · `frappe.get_route()` · `cur_frm?.doc` **三者都能取到**且 `doctype`/`name` 一致。

**实际**（真登录、真 Desk 页面，`goto("/app/user/Administrator")` 后等 4 秒）：

| 探法 | 实际值 |
|---|---|
| 最终 `location.pathname` | **`/app/setup-wizard/0`** —— **不是**请求的 `/app/user/Administrator` |
| `frappe.boot.sysdefaults.setup_complete` | **`False`** |
| `frappe.get_route()` | **`["setup-wizard","0"]`** |
| `cur_frm` | **`None`** |

**根因（一次观测就够，不猜）**：本机这个 compose 站点**没跑完 setup wizard** ⇒ Frappe Desk 的路由层
把**任何** `/app/**` 路由都强制改写成 `setup-wizard`。⇒ **本机上够不到任何一张真单据页。**

**按 plan §6 `H4` 第四列的写死处置走**：「三者**都取不到**（例如在 Workspace 页而非单据页）⇒
那是**合法的「无单据上下文」态**，请求体**不带** `doctype`/`name`」。
⇒ setup-wizard 页与 Workspace 页同族，**它就是那个合法态**。

⚠️ **但这一格顺带测出了一件 plan 没写、而实现必须知道的事** —— 记在这里，落进 §7.23：

`frappe.router.routes` 是一张 **slug → `{doctype}` 的映射表**，本机实读 **447 条**：

| 查询 | 实际返回 |
|---|---|
| `routes["user"]` | `{"doctype":"User"}` |
| `routes["sales-order"]` | `{"doctype":"Sales Order"}` |
| `routes["item-price"]` | `{"doctype":"Item Price"}` |
| `routes["setup-wizard"]` | **`ABSENT`** |
| `routes["home"]` | **`ABSENT`** |

**两条结论，各自要紧**：

1. **URL 路径是有损的。** `/app/sales-order/SO-0001` 里的 `sales-order` **不是** doctype 名，
   真名是 `Sales Order`。把 slug 原样当 `doctype` 发给 `/agenerp/explain`，服务端**必然**取不到字段表
   （403）或直接不认 —— 而那种失败在界面上和「问题不合法」长得一样（同 plan `H9` 的理由）。
   ⇒ **URL 给的是「哪两段」，把 slug 还原成 doctype 名这一步 URL 自己做不到。**
2. **URL 形状分不出「单据路由」与「页面路由」。** `/app/setup-wizard/0` 与 `/app/user/Administrator`
   **结构完全相同**（都是 `/app/<seg>/<seg>`）。只有 `routes` 这张表能分开：
   前者 `ABSENT`（是 Page），后者有 `{doctype:"User"}`（是 Doctype）。
   ⇒ **没有这张表就会在 setup-wizard / Workspace 这类页面上发出 `doctype:"Setup Wizard"` 这种假上下文。**

⇒ **`H4` 的优先级 `URL > frappe.get_route() > cur_frm.doc` 一个字不改**（plan 写死的，理由是 URL 最不易随 Frappe 升级悄悄变形），
**实现口径写死为**：**「取哪两段」由 URL 决定（第一顺位）；「slug 还原成 doctype 名」与「这到底是不是单据路由」
由 `frappe.router.routes` 这张 Frappe 自己的表回答**；表拿不到、或 slug 不在表里 ⇒ **落回 `frappe.get_route()`
的 `Form` 形态 → `cur_frm.doc` → 都没有就是「无单据上下文」，请求体不带这两个键**（§1.3「同时给或同时不给」）。
⚠️ **这不是把优先级改了** —— 值仍然优先取自 URL，`routes` 只承担 URL 自己给不出的那一半（反 slug + 类型判别）。

⚠️ **照实登记一条本 plan 关不掉的残余**：**「在一张真单据页上唤起时 `doctype`/`name` 真的被带进请求」
这条行为，本机站点上拿不到活体证据**（够不到单据页）。
本 plan 交的是：① 无上下文态的**活体**证据（setup-wizard 页，真浏览器）；
② 有上下文态的**离线**证据（`tests/unit/` 里对取值函数的直接调用 + 源码守卫）。
**收口文字里不许把 ② 写成 ①。** 重开事件与归属写进 plan §11 与 `STATE.md`。

## 2. 五条裁定（`D-d-0` … `D-d-4`）

每条写四件：**选中项 · 被否项 · 否决依据是「执行期探针」还是「外部规则（哪一条）」 · 残余风险。**

### `D-d-0` `docs/references/playwright-e2e-guide.md` 的效力分类

- **档位**：`constrained`（外部规则强制）—— **人已裁定，本 plan 只记录，不重新分类。**
- **选中**：**`上游模板残留（stale）`，不构成技术选型批准。**
- **否决**：「它写着 Playwright ⇒ 等于批准了 Playwright」。
- **否决依据：外部规则（不是探针）**，执行期实读两处：
  - `docs/masterplan/DECISIONS.md:382`（D-25 表内）逐字：
    「那份文档**本身不是批准**（2026-08-26 已裁定它是上游模板残留：masterplan/backlog 零命中、
    34 笔 `Approved-By` 提交里涉及浏览器驱动的是 0）。**批准来自本条 D-25，不来自它。**
    它的技术内容可以参考，但**权威性归本条**」。
  - `docs/masterplan/STATE.md:496` 的 `[resolved] 2026-08-26T01:47Z` 行（前置全部解除）。
- **残余风险（照实登记，本 plan 不修）**：`docs/index.md` 仍把「e2e / Playwright」这一类路由到那份指南
  ⇒ 下一个人仍可能把它读成批准。**本 plan 对 `docs/references/**` 与 `docs/index.md` 都是只读**
  （不在任何 Target 内）。它**不阻塞收口**，因为权威性问题已由人就地加的抬头解决。

### `D-d-1` 判据的目录与形态

- **选中 (A)**：`tests/ui/test_sidebar.py` 是一个**薄加载器**（`pytestmark = pytest.mark.live`），
  断言体落在**已进 CI 的** `tests/unit/test_desk_sidebar_body.py`，加载器把体里的「跑不了」出口收严成 `fail`。
- **否决 (B)**（不建 `tests/ui/`，判据全放 `tests/unit/`）：**依据是外部规则** ——
  `docs/masterplan/02-WBS.md:89` 逐字把验收命令写成 `pytest -m live tests/ui/test_sidebar.py` 退 0。
  不建那个路径，**这条命令不成立**，工作项 11 无法转 `done`。
  **(B) 的出口是什么**：只能由**人**在 `02-WBS.md` 改那条验收命令（红线 5，loop 无权）。**归人。**
- **否决 (C)**（建目录并自己去改 `gates.yml` 的 `COVERED`）：**依据是外部规则 —— 红线 2**。
  `gates.yml:579` 注释逐字「这几个目录由 loop 写在红线外，**接进 CI 属红线 2，故由人做**」。
  **不进候选比较**，只记它为什么被排除。⇒ **停机分支 3 不触发**（本 plan 没有裁到 (C)）。
- **正面回答 plan 写死要答的三件**：
  1. **(A) 会让 `gates.yml:597` 第 ⑦ 步在下次推送时红，这个代价接受。凭什么** ——
     那一步的名字逐字叫「判据自身的判据」，失败文案逐字「**新增目录必须显式接进本 job**」：
     **它红正是它被写出来的目的，不是它坏了**。本仓已有**四个同形态先例**
     （`tests/tools` / `tests/routing` / `tests/context` / `tests/experiments` 均是 loop 先落目录、
     再由人接进 CI，`STATE.md` 的 `[resolved] 2026-08-24T09:11Z` / `10:12Z` 记着）。
  2. **断言体为什么不能直接住在 `tests/ui/`** —— 住进去就**不受** `pytest tests/unit -q` 那一轮保护
     （`tests/ui` 既不在 `unit-and-contracts` 里、也不在本机日常那一条命令里），
     日常改坏了**看不见**；而 `tests/unit` 那一轮每次都跑。
  3. **代价照实数是三条不是一条**（plan §1.4）：① 第 ⑦ 步红；
     ② **新门禁在 CI 上零覆盖**（`tools/gates/check_expected_red.py` 的判定面写死 `"tests/gates"`，
     `gates-l2-live` 只跑它 ⇒ `tests/ui/test_sidebar.py` 不会被任何 job 跑到一次）；
     ③ **`tests/ui` 在 CI 上零 lint 覆盖**（`gates.yml:646` 的 ruff 参数是七个目录的字面量）。
     **「加一行 `COVERED` 就好了」是错的**，三条都写进交接。
- **残余风险**：上面 ②③ 两条在人接进 CI 之前一直存在；本 plan 只能在**本机**跑绿它，
  CI 服务端复跑那一层**本轮拿不到** ⇒ 收口逐字记 `verification scope limited`。

### `D-d-2` 浏览器驱动与依赖声明形态

- **档位**：**声明形态那一半是 `constrained`**（D-25 已裁死，本 plan 不重裁、一个字节不改 `pyproject.toml`）；
  **驱动选型那一半仍要记理由**。
- **选中 (a) playwright**。**依据：执行期探针 `H2`** —— `import playwright, pytest_playwright` exit 0、
  chromium `145.0.7632.6` 真起得来。
- **否决 (b) selenium 4.39.0**：**依据是外部规则** —— D-25 逐字把 extra 写成 `ui = ["playwright>=1.47"]`，
  **extra 里只有 `playwright`**。改选 selenium 等于改 D-25 的形态裁定 ⇒ **红线 3**。
  （本机确实装着 `selenium 4.39.0`，**装着不是理由**。）
- **否决 (c) 不用浏览器、用 `http.client` 打 HTML**：**依据是外部规则** ——
  撞 roadmap 顶部硬约束①：「按下 ⌘K 之后发生了什么」根本没测，退化成验「调得通」。
  本仓已有 22 条静态判据在验「调得通」（`test_desk_asset_route.py` / `test_desk_injection_static.py`），
  再加一份同族的**不产生新证据**。
- **否决 (d) 引 node 跑 JS 环境**：**依据是外部规则** —— 引入第二套运行时与第二个包管理器
  （零依赖启动门禁与 CI 安装面都要跟着长），**且仍然不是真浏览器**，成本更高而证据更弱。
- **残余风险三条，逐条登记**：
  1. **`ui` extra 不含 `pytest-playwright`**（D-25 的 extra 里只有 `playwright`）
     ⇒ 本机那份 `pytest-playwright 0.7.2` **仍然是「本机碰巧装着」**，
     **断言体明令不许依赖它**（`D-d-3` ⑥ / plan §1.4b）。这不是巧合，是 extra 的形态与 `D-d-3` ⑥ 互相印证。
  2. **`ui` extra 不含浏览器二进制** —— D-25 逐字「装包不等于能跑」，
     还要 `python -m playwright install chromium`，否则运行期报 `Executable doesn't exist`。
     它的**时间成本由 Phase 3 那条 `Proof` 实测**，方案交人（D-25 逐字压给 loop 的活）。
  3. **`playwright>=1.47` 是浮动下界**：本机 `1.58.0`，CI 上会装当时最新版，
     而 `playwright install chromium` 装的 chromium 版本**由 playwright 包版本决定**
     ⇒ CI 与本机可能不同版。**本 plan 不去钉版本**（钉它要改人刚落的那一行，属重开 D-25 的形态裁定），
     只照实登记并写进交接项 (2)。

### `D-d-3` 零 skip 怎么做到（六条，逐条落地形态）

**先把先例的机制读准**（实读 `tests/gates/test_explain_service_live.py`）：它是 `:57` 先 `exec_module()`、
`:80` 才把 `_BODY.pytest.skip` 换成 `fail` ⇒ **收严只对「导入完成之后才被调用」的 skip 生效**。
⇒ **模块级的 skip 收不严**（`Skipped` 在 `exec_module()` 里就抛了，收严那一行还没执行），
结果是**门禁退 0 且 `1 skipped`：一条绿着的、不存在的门禁**。

| # | 裁定 | 落地形态 |
|---|---|---|
| ① | 加载器在 `exec_module()` **之前**自己 `import playwright`，失败即 `pytest.fail` | `tests/ui/test_sidebar.py` 顶部；**不是** `importorskip` |
| ② | 断言体里**禁用**模块级 `pytest.importorskip` 与模块级 `pytest.skip` | 驱动导入与活栈探活**一律放进 fixture** |
| ③ | `tests/unit/` 那份**允许** skip、`tests/ui/` 那份**必须** fail —— 取舍差是**有意的** | 日常那一轮不该因为没起 docker 就整轮红；门禁那一轮「跑不了 = 没跑 = 红」。写进 §7.23 |
| ④ | 收严机制：断言体在**模块级**暴露**自己的**间接名 `_unavailable(reason)`（默认 `pytest.skip`），所有「跑不了」出口只调它；加载器 `exec_module()` 之后**只重绑这一个名字**（`_BODY._unavailable = pytest.fail`） | ⚠️ **重绑的是断言体模块自己的属性，不是 `pytest` 模块的属性** —— 先例那种 `_BODY.pytest.skip = …` 改的是**全局 `pytest` 模块**、属进程级污染。**本 plan 不去改那份先例**（红线 1），只在自己这份用无副作用的形态 |
| ⑤ | 加载器必须把断言体里的测试函数**逐个重绑**进自己的模块命名空间 | 漏了就是 `pytest -m live tests/ui/test_sidebar.py` **一条都收集不到 ⇒ 退出码 5**。配套守卫：**重绑的名字集合 == 断言体里 `test_` 开头的函数名集合**，落在 `tests/unit/test_desk_sidebar_static.py`，**不靠人眼数** |
| ⑥ | 断言体**不许**依赖 `pytest-playwright` 的任何 fixture（`page`/`browser`/`context`/`browser_type`）与它的任何 CLI 选项 | runner 上只装 `pytest certifi`（`gates.yml:567`）⇒ 用了就是 `error` 不是 `skip`，**今天绿着的 `unit-and-contracts` 会红**（纯回归）。②⑥ 是两件事：② 管 skip 出现的**时机**，⑥ 管 fixture 从**哪来** |

- **依据**：① ② ③ ④ ⑤ 的依据是**执行期实读先例源码**（`tests/gates/test_explain_service_live.py:57/:80` 与结尾的六条重绑）；
  ⑥ 的依据是**外部规则**（`gates.yml:567` 的 `pip install pytest certifi`）。
- **残余风险**：④ 的收严只覆盖「调了 `_unavailable`」的出口；**直调 `pytest.skip` 能绕过它**
  ⇒ 由源码守卫①（断言体里 `pytest.skip(` / `pytest.importorskip` **零命中**）挡住，
  并由变异 `M15` 实证那条守卫真的打得红。**守卫是文本下限，不证运行时行为**，这句照实写在判据里。

### `D-d-4` 快捷键 · 关闭方式 · 焦点归还

- **选中：`Cmd/Ctrl+K`（不改键）。依据：执行期探针 `H3`**，两路互证（注册表里 `handlers["k"]` 为 `ABSENT`；
  真按下去 `defaultPrevented=false`、无 modal、焦点不动）。
- **否决：次选键 `Cmd/Ctrl+Shift+K`** —— 它是 plan 写死的**冲突时**才启用的备用件，`H3` 判定不冲突 ⇒ **未启用**。
  ⇒ plan §11 那条「与 WBS 第 89 行『⌘K』字面的偏差」**未触发**。
- **关闭方式（裁死两条，都要有）**：`Esc` · **再按一次同一组合键**（toggle）。
- **焦点归还（裁死）**：唤起前把 `document.activeElement` 存下来，关闭时 `focus()` 回去
  （元素已不在文档里就不还，不抛）。**不还焦点在单据页上是实实在在的可用性缺陷**，不是风格问题。
- **残余风险**：`Cmd/Ctrl+K` 是浏览器**自身**在某些形态下的地址栏快捷键（Firefox 的搜索栏）。
  本 plan 的判据只在 chromium 上跑，**其余浏览器未测** ⇒ 照实登记，不声称跨浏览器。
