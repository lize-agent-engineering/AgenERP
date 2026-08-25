# P1.8b 下半 · ⌘K 侧边栏本体与 `tests/ui/test_sidebar.py` 活体门禁

> Plan Status: draft
> Last Reviewed: 2026-08-25
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 11（P1.8b）· `docs/masterplan/02-WBS.md` §4 第 88 行 ·
> 前一个 plan `2026-08-25-1615-1` §11 第一条写死的后继指派（重开事件「该 plan 转 `completed`」已于 2026-08-25 触发）
> Related: `docs/plans/p1-insight/2026-08-25-1615-1-desk-injection-seam-and-asset-route.md`（第 1 个 plan，`completed`）·
> `docs/plans/p1-insight/2026-08-25-1423-1-explain-service-compose-and-same-origin.md`（P1.8a 第 2 个 plan）
> Work Item: 11. **Desk 侧边栏**（⌘K，调 P1.8a 的面）（P1.8b）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个预算，
> 本 plan 用掉**最后一格**；此后该格 `2/2` 满，任何后继只能由**人**在 `02-WBS.md` 拆行 / 加行，红线 5，loop 无权）
> Audit: required

## 0. 执行前必做：重取基线

本节的四条**在动手写任何一行代码之前**逐条实跑一遍，结果落进 §1 对应小节。
**不许拿本文件起草期的数字当已知事实** —— 起草与执行之间仓库会变。

1. `git log --oneline -3` + `git status --porcelain` —— 确认工作树干净、`HEAD` 是哪个 sha。
2. `python3 tools/gates/check_expected_red.py` · `python3 -m pytest tests/unit -q` ·
   `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` ·
   `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments`
   —— **四条的退出码与数字逐条抄进 §1.9 的开工基线表**。数字与本文件起草期记的不一致时，**以执行期实读为准**，
   并在 §1.9 就地改准（这不是「改 plan」，这是基线本来就该现取）。
3. `ls -d tests/*/ | xargs -n1 basename | sort | tr '\n' ' '` —— 与 `.github/workflows/gates.yml` 第 ⑦ 步的
   `COVERED` 逐字比对。**这是 §1.4 那个正面冲突的实测口径**，不引转述。
4. `python3 -c "import playwright, pytest_playwright"` + `python3 -m pip list | grep -iE 'playwright|selenium'` +
   `ls ~/Library/Caches/ms-playwright` —— 浏览器驱动在本机到底装没装、装的是哪一版。
   **取不到就走 §7 Phase 1 的停机分支 ①**，不许改成「用 curl 凑合」（那撞硬约束①）。

## 0.5 ⚠️ 本 plan 为什么停在 `draft` —— 一件只有人能做的裁定卡在最前面

**独立评审 iteration 2 实测打出来的，不是推演**：

- `grep -rl -i "playwright\|selenium" docs/masterplan docs/backlog` → **零命中**
- `git log --grep=Approved-By` 里**无一条**涉及浏览器驱动；`DECISIONS.md` 无对应条目

⇒ **`D-d-2` 那条「唯一的免停条件（人已批准的具体出处）」今天在仓里不存在。**
而 (c) 不用浏览器撞硬约束①、(d) 引 node 引第二套运行时，两条都已被否 ⇒
**`D-d-2` 必然裁成「必须引第三方驱动」⇒ Phase 1 停机分支 4 是 100% 触发的。**

**如果现在转 `active`**：执行到 Phase 1 就停，Phase 2 / 3 一行跑不到，
Goal 1–4 与 WBS 第 88 行全部落空 —— 而**工作项 11 的最后一格预算已经花掉**（§1.10），
后继只能由人在 `02-WBS.md` 拆行（红线 5）。
⇒ **那等于用最后一格预算换一份注定停在 `active` 出不来的 plan。不干。**

**⚠️ 与此纠缠的第二件事，同样只有人能定**（`D-d-0`）：
`docs/references/playwright-e2e-guide.md:3` 逐字
「**Playwright** is the fixed e2e testing framework. **Do not introduce alternatives.**」，
`docs/index.md:45` 还把「e2e / Playwright」这一类路由到它。
**但它是上游模板残留**：它引的 `playwright.config.ts` 本仓不存在（本仓是纯 Python），
它随 `a959410 chore(age): 安装 AGE 骨架（W0.2）` 进来，
**从未进 `DECISIONS.md` / `02-WBS.md` / `project-context.md`**；
且 `AGENTS.md` 逐字「**不得把强制规则藏在 `docs/references/`**」。
⇒ **它到底是「本项目已批准 Playwright」还是「模板垃圾」，只有人能定。
loop 不许顺势把它当批准用** —— 那正是「用一份自己找来的文件给自己发许可」。

### 本 plan 转 `active` 的前置（写死，两条都要人答）

1. **准不准把浏览器驱动引进本仓**（形态：`[project.optional-dependencies]` 的 `ui` extra，
   `[project].dependencies` 一个字不加）。**不准 ⇒ 本 plan 整体作废**，
   `tests/ui/test_sidebar.py` 这条验收命令的出路改由人在 `02-WBS.md` 定（表规 6 允许改字符串）。
2. **`docs/references/playwright-e2e-guide.md` 算不算数**（已批准 / 模板残留待清理）。

**这两条已由本轮 mission-driver 追加进 `docs/masterplan/STATE.md` §3 的 needs-human 队列**（只追加，不改写已有行）。
**人答完之前，本文件的 `Plan Status` 保持 `draft`，不执行。**

## 1. Current Baseline

### 1.1 WBS 那一行要什么

`docs/masterplan/02-WBS.md` §4 **第 88 行**逐字：

> | P1.8b | **Desk 侧边栏**（⌘K 唤起，保留当前单据上下文），调 P1.8a 的面 | P1.8a | `pytest -m live tests/ui/test_sidebar.py` 退 0 | `MD:p1-explain` |

**本 plan 声称满足这条验收命令**（这是它与第 1 个 plan 最大的不同 —— 那一个逐字声明「不声称满足」）。
⇒ 交付面因此**必须**包含 `tests/ui/test_sidebar.py` 这个**具体路径**，而那条路径撞上一条 CI 守卫（§1.4）。

### 1.2 第 1 个 plan 交了什么、**没**交什么（两句都要说）

交付 plan `2026-08-25-1615-1`（`completed`，sha `e615b46`，独立收口审计已补做）。**它交的是接缝，不是侧边栏**：

- `agenerp/serve/assets/desk.js`（1193 字节）—— **一段只证明自己到了的脚本**：
  `(function(){...})()` 里把冻结的 `{name:"agenerp-desk", version:"0.1.0", plan:"2026-08-25-1615-1"}`
  用 `Object.defineProperty` 挂到 `window.agenerpDesk` 上，然后 `console.log` 一行。
  **不注册快捷键、不发任何请求、不碰 DOM。**
- `agenerp/serve/app.py:61-68` —— `ASSET_FILENAME="desk.js"` / `ASSET_PATH="/agenerp/desk.js"` /
  `ASSET_CONTENT_TYPE="text/javascript; charset=utf-8"` / `ASSET_DIR=Path(__file__).resolve().parent/"assets"` /
  `SERVED_PATHS=(HEALTH_PATH, EXPLAIN_PATH, ASSET_PATH)`；`_respond_asset()` 真读文件真写 `wfile`，**不认人、不接受路径参数**。
- `tools/nginx/frappe.conf.template:114-129` —— 哨兵段内 `location ^~ /app { … sub_filter '</body>'
  '<script src="/agenerp/desk.js"></script></body>'; sub_filter_once on; proxy_pass http://backend-server; }`。
- 判据 `tests/unit/test_desk_asset_route.py`（357 行）+ `tests/unit/test_desk_injection_static.py`（252 行），**共 22 条**。

**没交的**（逐字引它的 Non-Goals 1 / 2 与 §11）：**⌘K、侧边栏 UI、任何调 `/agenerp/explain` 的前端逻辑、
`tests/ui/` 目录、`tests/ui/test_sidebar.py`**，以及 —— 最要紧的一条 —— **任何真浏览器侧的实证**。
它逐字记着：「**「HTML 里有 `<script>` 标签」≠「浏览器执行了它」，那是第 2 个 plan 的面**」。

### 1.3 服务面的请求契约（实读 `agenerp/serve/app.py`，本 plan **一个字不改**）

- `POST /agenerp/explain`。身份**只**从 `Cookie: sid=…` 来（`_sid_from_cookie`，取不到 401，**不回退到任何别的凭据**）。
- 请求体只收四个键：`ALLOWED_BODY_KEYS = {"question", "task_class", "doctype", "name"}`。
  `fields` / `role` / `view` / `actions` / `user` 五个是**越权向量**，给了**一律 400**（不是静默忽略）。
  `doctype` 与 `name` **必须同时给或同时不给**。
- 200 响应体四键：`user` / `answer` / `accepted` / `cost{calls, total}`。
- 失败码是**结构性**分开的。⚠️ **起草期第一版只数了六种，独立评审实读打回 —— 实际是八种服务端码 + 两种反代侧码，
  照实改准**：
  `400` 请求体不合法 · `401` 认不到人 · `403` 当前身份取不到该单据的字段表 ·
  **`404` 未知路径**（`app.py:362-369` `_not_found()`）· `405` 对 `/agenerp/explain` 发 GET ·
  **`500` 兜底**（`:327` `except Exception` · `:354` 读资产 `OSError`，文案恒为 `INTERNAL_ERROR`）·
  `502` 上游模型坏了 · **`503` 模型未配置且回里指名缺哪个变量**
  （`app.py` docstring 逐字「**绝不回 200 空回答**」）。
  **反代侧另有两种**：`502`（`agenerp-serve` 不在时 nginx 回它，§7.21 `D-b-8` 实测过）·
  `504`（`proxy_read_timeout 300` 掐断，§7.21 记着从未验证过）。
- ⇒ **前端能拿到的形态是「八种服务端码 + 两种反代码 + 200」，而且这个集合会长。**
  ⚠️ **因此渲染状态机不许写成封闭枚举** —— 必须有一条**兜底态**（未枚举的码也渲染成非空、可分辨、
  带上那个码本身的文本）。**一次真实的 500 / 504 打在没有兜底的面板上，就是 Goal 2 明令禁止的空白。**
  这是 §7 Phase 2 第 ⑤ 项与 §6 `H8` 的枚举依据 —— **不是本 plan 发明的分类**。

### 1.4 ⚠️ 正面冲突：`tests/ui/` 会让一条**今天是绿的** CI 步骤变红

`.github/workflows/gates.yml` `unit-and-contracts` job 第 ⑦ 步逐字：

```
COVERED="contracts context experiments fixtures gates routing tools unit"
ACTUAL=$(ls -d tests/*/ | xargs -n1 basename | sort | tr '\n' ' ' | sed 's/ $//')
… if [ "$ACTUAL" != "$EXPECTED" ]; then … exit 1
```

失败文案逐字：「**新增目录必须显式接进本 job（或列入 `COVERED` 并说明为何不跑）**」。
本仓今天 `tests/` 下**恰好**是那八个目录 ⇒ **一旦落下 `tests/ui/`，这一步在下一次推送时必红。**

**三件事必须同时说清，缺一就是含糊过去**：

1. **改它属红线 2 的面，loop 无权。** `gates.yml:542`（第 ③ 步上方，**不在**第 ⑦ 步那段里）的注释逐字：「这几个目录由 loop 写在红线外，
   **接进 CI 属红线 2，故由人做**」。⇒ 本 plan **一个字节都不碰 `.github/workflows/**`**。
2. **这条守卫红，正是它被写出来的目的**，不是它坏了。它的名字逐字叫「判据自身的判据」。
   本仓已有**同形态的先例**：`tests/tools` / `tests/routing` / `tests/context` / `tests/experiments`
   都是 loop 先落目录、**再由人接进 CI**（`STATE.md` `[resolved] 2026-08-24T09:11Z` / `10:12Z` 记着「已由人接进 CI」）。
3. ⚠️ **代价照实记，不许粉饰 —— 而且它比第一版写的更重**（独立评审实读打回，此处已改准）：
   代价是**两条**，不是一条。
   **(i)** `AGENTS.md` 裁判规则 4 的停机条件里有「**CI 连续 2 轮红**」，本 plan 落地后
   **人在下一次推送时会看到第 ⑦ 步红**。
   **(ii)** ⚠️ **更要紧的一条：新门禁在 CI 上是零覆盖的。** `tools/gates/check_expected_red.py:73-74`
   的判定面**写死** `"tests/gates"`，而 `gates-l2-live` 只有一条判定步就是跑它 ⇒
   **`tests/ui/test_sidebar.py` 不会被任何 job 跑到一次**；`unit-and-contracts` 是离线 job（无 docker / 活栈 / 浏览器），
   跑它也没意义。**把 `ui` 加进 `COVERED` 只让第 ⑦ 步不红，不会让这条门禁在 CI 上跑起来。**
   **(iii)** 同理 `gates.yml:609` 的 `lint` job ruff 参数是七个目录的**字面量** ⇒ **`tests/ui` 在 CI 上也零 lint 覆盖**
   （本地会被真扫，因为 `[tool.ruff]` 的 `exclude` 只排除 `tests/gates`）。
   ⇒ 交接必须**逐件写清人要做的四件**（§7 Phase 3 交接项），不能只写一句「归人」了事，
   **更不能写成「加一行 `COVERED` 就好了」——那句话是错的。**

### 1.5 浏览器驱动在本机的实读（起草期实测，**执行期须按 §0 第 4 条重取**）

| 探针 | 起草期实读值 |
|---|---|
| `python3 -c "import playwright"` | **OK** —— `/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/playwright/__init__.py` |
| `python3 -m pip list \| grep -i playwright` | `playwright 1.58.0` · `pytest-playwright 0.7.2` · （另有 `playwright-stealth 2.0.2`，本 plan 不用） |
| `ls ~/Library/Caches/ms-playwright` | `chromium-1208` / `chromium-1223` / `chromium-1228` / `chromium_headless_shell-*` **已下载** |
| `python3 -m pip list \| grep -i selenium` | `selenium 4.39.0`（备选，本 plan 不选，理由见 `D-d-2`） |
| `grep dependencies pyproject.toml` | 运行期依赖**只有** `certifi>=2024.2.2`；**没有任何 `optional-dependencies` 段** |

⇒ **「本机装着」与「本仓声明了」是两件事**（这正是 `pyproject.toml` 那段注释记着的旧亏：
「本机碰巧装着 certifi，所以直到把 `tests/routing` 接进 CI 才暴露」）。
`D-d-2` 要正面裁的就是这一格：**怎么声明才不把「本机碰巧有」当成「仓里有」。**

### 1.6 前车之鉴：**一条会 skip 的门禁等于一条不存在的门禁**

`tests/gates/test_explain_service_live.py`（人写的，`f09b8f0`）的模块 docstring 与收严段逐字记着：
`gates-l2-live` 的契约是「**全部绿、零 red、零 skip**」，因此那份门禁把断言体里的 `pytest.skip`
**整体换成 `pytest.fail`**。而 P1.8a 至今那条红，红的**就是**断言体 `:223` 那条 503 分支上的 `pytest.skip`
（roadmap 工作项 10 逐字：「**六条里五条转绿，第 4 条 skip**」）。

⇒ **本 plan 的 `tests/ui/test_sidebar.py` 里一个 `skip` 分支都不许有**，
且**不许把「活栈没起」「浏览器没装」写成 skip**。这两条各自的出路在 `D-d-3` 裁定。

### 1.7 「没配 AI 变量」不是本 plan 的障碍，是本 plan 的**主判定分支**

`gates-l2-live` 起栈时一个 AI 变量都不配 ⇒ `/agenerp/explain` 走 **503**。
如果侧边栏的判据只在「真答出来了」时才成立，那这条门禁**在判定环境里恒红**，重蹈 P1.8a 那条覆辙。

⇒ 本 plan 的判据主线**建在「不需要模型答对」的那一半上**：⌘K 唤起 → 面板出现 → 带上当前单据上下文 →
**浏览器自动把 `sid` 带到 `/agenerp/explain`**（这一跳成立的直接证据是「回的**不是 401**」）→
面板把**实际拿到的那个码**渲染成**可分辨的、非空的**态。
**这一整条链上没有一个环节需要 AI 变量、需要烧 token、需要模型答对。**

⚠️ **但判据不许把「一定是 503」写进断言 —— 独立评审实读打回，此处已改准。**
`gates.yml:304-310` 的判定步**已经配了** `AGENERP_LLM_ENDPOINT` / `API_KEY` / `MODEL` 三个 secret，
同处注释逐字「**配上之后它走答案面**」⇒ **人正在往「不是 503」的方向修**。
把 503 钉死进断言，等于写一条**会因为环境变好而变红**的判据，
而 `gates.yml:275-279` 点名禁止的正是「把判据调整到迁就环境」这类动作的同一族。
⇒ **正确形态**：用 `page.expect_response` **先观测实际状态码**，再断言「面板渲染的是该码对应的那一态」；
「浏览器带上了 `sid`」由**一条独立断言**承担（`status != 401`），**不依赖码是 503 还是 200**。

⚠️ 反过来也要说死：**这不等于「答得对」被验证了**。答得对不对是 P1.4 的面（工作项 6，`2/2` 已满），
本 plan **不声称**验证它，见 §3 Non-Goals 4。

### 1.8 本仓至今**没有任何**真浏览器侧实证 —— 本 plan 是第一次

roadmap 工作项 10 与 11 各记过一次同一条空缺：「**真浏览器会不会把 `sid` 带到 `/agenerp/*` 上，本仓仍无实证**」。
`sid` 是 `HttpOnly`（`STATE.md` `[open] 2026-08-25T04:05Z` 的起因），
`HttpOnly` **只挡 JS 读、不挡浏览器发**，而「不挡浏览器发」这句话本仓一直是**推断**。
⇒ 本 plan 的 `H6` 那格是它**第一次**被直接观测。**在此之前不许把它写成已证。**

### 1.8b ⚠️ 前置（工作项 10 / P1.8a）在 roadmap 上今天的状态词是 `todo`

`docs/backlog/p1-insight-roadmap.md:50` 工作项 10 的状态词是 **`todo`** —— 人在 2026-08-25 把 `done` 改回，
**人写的理由逐字是两条**：① `pytest -m live tests/gates/test_explain_service_live.py` **跑不了**（栈起不来）；
② **零依赖启动门禁不绿**（`down -v` 后 `frontend` 无限 `Restarting`，报 `host not found in upstream "backend:8000"`）。
**这两条今天的状态不一样，必须分开说**：**② 已被 P1.8a 第 2 个 plan 的实测冷起推翻**
（`up -d --wait --wait-timeout 900` → exit 0、墙钟 100 秒、七个有探针的全 healthy）；
**① 仍敞着** —— 那条门禁最后一次实跑是 `1 failed, 5 passed`，红在断言体 `:223` 那条 503 分支的 `pytest.skip` 上。
而 `02-WBS.md` 第 88 行明写 P1.8b 的前置**是 P1.8a**。

**本 plan 对此的立场写死，不含糊**：本 plan 依赖的**只是它已落盘、且已被本 plan 实读确认在仓的那部分** ——
`agenerp-serve` 在 compose 里 · nginx `location /agenerp/` 同源那一跳 · 资产路由与注入接缝（§1.2 / §1.3 逐项实读）。
**本 plan 不声称工作项 10 已闭合、不改它那一行的状态词、不替它宣布关闭**（它的预算 `2/2` 已满，
剩下那条红的处置面在 `tests/gates/**` 与 `.github/workflows/**` 里，归人）。

### 1.9 开工基线（执行期按 §0 第 2 条填，起草期的数只作对照）

| 命令 | 起草期已知值（**须复核**） |
|---|---|
| `python3 tools/gates/check_expected_red.py` | 期望 exit 0 · `门禁 28 项：预期红 0，绿 28，跳过 0`（起草期实跑值；**26 是错的，已改准**） |
| `python3 -m pytest tests/unit -q` | 期望 exit 0 · `801 passed, 6 skipped` |
| `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` | 期望 exit 0 · `456 passed, 13 skipped` |
| `ruff check …` | 期望 exit 0 · `All checks passed!` |

### 1.10 预算：这是工作项 11 的**最后一格**

按各 plan 的 `> Work Item:` 首行重数：工作项 11 今天 `1/2`（只有 `1615-1`）。
本 plan 用掉第 2 个 ⇒ **此后 `2/2` 满**。任何后继（含本 plan §11 里将要登记的每一条）
**只能由人在 `02-WBS.md` 拆行 / 加行**（表规 3 逐字「超过就拆行」；改 `docs/masterplan/**` 是红线 5）。
⇒ §11 的每一条都必须写死**重开事件**，且必须诚实标注「归人」。

## 2. Goals

1. **⌘K 侧边栏本体**落在 `agenerp/serve/assets/desk.js`：快捷键唤起 / 关闭、**保留当前单据上下文**
   （在某个真单据页上唤起时，把该 `doctype` / `name` 带进请求）、同源 `POST /agenerp/explain`。
2. **失败形态一个都不许渲染成空白**：§1.3 那**十种**已枚举的码各自渲染成**可分辨的、非空的**文案，
   **且必须有一条兜底态**接住**未枚举**的码（含将来新增的）；**不许停在永久 spinner** 上。
3. **`tests/ui/test_sidebar.py` 真的退 0** —— 用**真浏览器**驱动**真活栈**，
   **零 skip**（§1.6），且**不需要任何 AI 变量**（§1.7）。
4. **第一次直接观测**「浏览器把 `HttpOnly` 的 `sid` 自动带到 `/agenerp/*`」（§1.8）。
5. **不回归**：零依赖启动门禁仍绿 · `check_expected_red.py` 仍退 0 · `tests/unit` 只增不减 ·
   `agenerp-serve` 停掉时 `frontend` 仍 `healthy`（§7.21 `D-b-8` 的不回归）· 既有资产判据那**四格**仍绿 ——
   `tests/unit/test_desk_asset_route.py` 的 `:165` `len(text) > 200` · `:166` `"agenerpDesk" in text` ·
   `:167` `"Object.freeze" in text` · `:168` `endswith(")();")`。
   ⚠️ **改 `desk.js` 时最容易顺手弄丢的是 `Object.freeze`**（面板要挂状态，第一反应就是把冻结去掉），
   四格一起点名，不只点 `agenerpDesk` 那一格。

## 3. Non-Goals

1. **不改 `/agenerp/explain` 的请求契约一个字**（四键白名单、五个越权键的 400、**八种服务端状态码**的分法）。
   前端**适应**服务面，不是反过来。
2. **不写站点任何一行数据**（P1 是②端只读）；**不建 `apps/**`、不跑 `bench install-app`**。
3. **不碰 `tests/gates/**` / `.github/workflows/**` 任何一行**（红线 1 / 2）；
   `docs/masterplan/**` 只读，唯一允许的写动作是往 `STATE.md` §3 **追加**（红线 3 / 5）。
4. **不判「答得对不对」。** 那是 P1.4 的面（工作项 6，预算 `2/2` 满）。本 plan 判的是**渲染与传输**，
   ⚠️ 且**不许**在收口文字里把「面板显示了答案」写成「Agent 答对了」—— 那正是本 roadmap 顶部
   硬约束①点名的「『答对了』与『蒙对了』长得一模一样」。
5. **不做多轮会话 UI、不做历史记录、不做设计系统 / 主题**。侧边栏是一次问、一次答、一次关。
6. **不做真实长解释的 `proxy_read_timeout 300` 验证**（§7.21 记着它从未被验证过）。
   本 plan 的判据全部落在 503 分支与打桩分支上，**不产生长请求** ⇒ **它仍然是未验证的**，登记在 §11。

### 3.1 ⚠️ 「一个 plan 一个结果面」（Minimum Rule 4）本 plan 为什么不拆

本 plan 同时交四块：**UI 本体 · 活体门禁 · 依赖声明 · CI 交接**。看起来像四个面，**实际共享同一条闭合判据** ——
`02-WBS.md` 第 88 行那条 `pytest -m live tests/ui/test_sidebar.py` 退 0。
UI 不写它不退 0；门禁不写它不存在；驱动不声明它跑不起来；CI 交接是它落地后**必然溢出**的那一件。
Minimum Rule 4 原文同时禁止 over-split（「共享同一行为契约与闭合判据的多模块工作**仍是一个结果面**」）。

⚠️ **而且拆了没有出口**：工作项 11 的预算只剩这最后一格（§1.10），
拆出来的第二个 plan **只能由人在 `02-WBS.md` 拆行 / 加行**（表规 3 + 红线 5）。
⇒ **不拆是裁定，不是图省事**；独立评审 iteration 1 独立复核后同意这一条。

## 4. Task Route

- Type: `implementation-only change`（侧边栏本体）+ `verification or audit work`（活体 UI 门禁）
  + 一处 `architecture change`（判据目录 `tests/ui/` 的形态裁定 `D-d-1`，落 owner doc）
- Owner Docs: `docs/architecture/module-boundaries.md`（落点节 **§7.23**，新增；`§7.13/§7.20/§7.21/§7.22` **一个字不改**）·
  `docs/masterplan/DECISIONS.md` **D-19**（**只读**）· `docs/references/playwright-e2e-guide.md`（**只读**，见 `D-d-0` / §0.5）
- ⚠️ **`docs/design/agents-and-roles.md` §9 风险档表已从 Owner Docs 里去掉**（独立评审打回，理由采纳）：
  实读 `:212-222`，那张 L0–L3 表分的是**运行时 Agent 对站点做的动作**，
  与「开发期改一段前端资产 + 加一份测试」**不同维**。留着它就是挂一条没人认领的义务
  （三个 Phase 的 Targets、三组 Exit Criteria、§10 都没有它）。
  ⇒ 对该文件 **`No owner-doc update required`**。
  ⚠️ 这与 §7.22 `D-c-3` 当年自评 L1 **不冲突**：那一次评的是「新增一条对外 location + 一条资产路由」这个**运行期形态**，
  本 plan 不新增任何 location、不新增任何端点、不碰站点。
- Skill Selection Basis: 实现期 `Skill: none` —— `docs/skills/` 下 **15 份提示词**（16 个条目里有一份是 `README.md`）
  都是审计 / 评审 / 重构发现类，
  没有一份覆盖「写前端 + 驱动浏览器取证」这个工作方法。评审期用 `plan-audit-prompt.md`，收口期用 `closure-audit-prompt.md`。

## 5. Infrastructure And Config Prereqs

- **活栈**：`AGENERP_HTTP_PORT=18080 docker compose up -d --wait --wait-timeout 900`。
  ⚠️ **本机必须给 `18080`** —— `8080` 被另一个 compose 项目（项目名 `docker`）占着，
  不给会死在 `Bind for 0.0.0.0:8080 failed: port is already allocated`（roadmap 工作项 10 已记）。
- **登录**：`AGENERP_ADMIN_PASSWORD`（本机 `admin`）。浏览器侧走站点自己的 `/login` 表单拿 `sid`，
  **不手工伪造 Cookie** —— 伪造就等于把 `H6` 那格要证的东西假设掉了。
- **浏览器**：见 §1.5 与 §0 第 4 条。**取不到即走 Phase 1 停机分支 ①。**
- **AI 变量**：**一个都不需要配**（§1.7）。⇒ 本 plan 的活体取证**零 token 成本**。
- 新增依赖的声明形态由 `D-d-2` 裁定；**无论怎么裁，`[project].dependencies` 一个字不加**
  （那一段直接决定零依赖启动门禁与 CI 的安装面）。
- 无数据迁移 ⇒ 无回滚脚本。回滚形态是 `git revert`（产物全部在 git 里，符合北极星「可 diff、可回滚」）。

## 6. 开工前写死的假设（硬约束②：预测在前、结果在后、逐条吻合）

**下表在 Phase 1 第一条探针跑之前逐字写死，事后只填「实际」列，不改「预测」列一个字。**
不吻合**不等于**失败 —— 不吻合时按该行的「不吻合怎么办」走，且**照实记不吻合**。

| # | 探针 | 预测 | 不吻合怎么办 |
|---|---|---|---|
| `H1` | `ls -d tests/*/` 与 `gates.yml` 第 ⑦ 步 `COVERED` 逐字比对（**落目录之前**跑一次） | 两边**相等**（八个目录），即这一步今天是绿的 | 已经不相等 ⇒ 说明有人先动了，**停下来重读 §1.4 再决定**，不许直接往上叠 |
| `H2` | `python3 -c "import playwright, pytest_playwright"` + 启一次 chromium headless | 都成功；能起 chromium | ⇒ **Phase 1 停机分支 ①**：驱动不可用是一次**需人拍板的依赖决策**，交人，不自选替代品 |
| `H3` | Frappe v15 Desk **自己**有没有占用 `Cmd/Ctrl+K`：真登录进 `/app`，按下该组合键，观测有无原生响应 | **不确定，这正是要测的**。倾向：Frappe 的 awesomebar 走 `Ctrl+G`，`K` 很可能空着 | 已被占用 ⇒ **不抢**（抢了就是破坏 Desk 既有行为）。**次选键现在就写死：`Cmd/Ctrl+Shift+K`**（不留执行期自选的口子），并把「WBS 那行写的是 ⌘K」这处偏差**显式登记**到 §11 + `STATE.md`，由人裁 |
| `H4` | 当前单据上下文从哪儿取最稳：URL 路径解析 · `frappe.get_route()` · `cur_frm?.doc`，三者在同一张单据页上各取一次 | 三者**都能取到**且 `doctype`/`name` 一致 | **优先级现在就写死：URL 路径 > `frappe.get_route()` > `cur_frm.doc`**（理由：URL 是浏览器地址栏里看得见的、不依赖任何 Frappe 内部对象，升级 Frappe 时最不容易悄悄变形；后两者是内部 API）。不一致 ⇒ 按该优先级取，并把不一致照实记进落点节；三者**都取不到**（例如在 Workspace 页而非单据页）⇒ 那是**合法的「无单据上下文」态**，请求体**不带** `doctype`/`name`（§1.3 逐字「必须同时给或同时不给」） |
| `H5` | 带真登录会话 `GET /app/<某真单据>`，看注入的 `<script src="/agenerp/desk.js">` 在不在、几次 | 在，**恰好 1 次**，且在 `</body>` 之前 | 不在 ⇒ 第 1 个 plan 的接缝回归了，**先修回归再往下**，不许绕过去 |
| `H6` | **浏览器**（不是 curl）从 `/app` 页面发出的 `POST /agenerp/explain`，服务端看到的 `Cookie` 里**有没有 `sid`**。⚠️ **观测方式写死：`page.expect_response` 观测那一次「未打桩」的真请求** —— `page.route` 打桩的那些请求**根本到不了服务端**，从它们身上取不到这个证据 | **有** —— 直接证据是回的**不是 401**（`handle_explain` 的顺序是 `_sid_from_cookie` → `parse_request` → `_resolve_identity`(401) → `config_factory`(503)，⇒ **任何非 401 的码都蕴含「站点已经认到人」**）。⚠️ 这是本仓第一次直接观测，此前只有推断 | 没有 ⇒ **这是一个真发现，不是本 plan 的失败**：说明 `HttpOnly` + 同源那套推断是错的。**当场停下**，把实测写进 `STATE.md` §3 needs-human 并交人重裁 D-19 的同源假设 |
| `H7` | 一个 AI 变量都不配时，面板发出的那次请求回什么码 | **503**，且体里**指名缺哪个变量** | ⚠️ **不许清环境重跑**（独立评审打回，此处已改准）：回 200 或别的码时，**照实记下那个码，并断言面板渲染的是该码对应的那一态**。理由 —— `gates.yml:304-310` 的判定步已配了三个 AI secret、注释逐字「配上之后它走答案面」，⇒ 「环境里有 AI 变量」是**人正在推进的正常状态**，为了让断言成立去清环境，与 `gates.yml:275-279` 点名禁止的「把判据调整到迁就环境」是同一族动作 |
| `H8` | **十种已枚举的码**（400/401/403/404/405/500/502/503 + 反代 502/504）**+ 200**，用浏览器内 `page.route` 打桩逐个喂给面板 | **各自**渲染出**互不相同**且**非空**的可见文本；**无一停在 spinner**。⚠️ **「互不相同」的判定口径现在就写死**：取面板可见文本，**两两全等比较必须全部为假**，**且每一条都含该状态码的字面量** —— 不许留给执行期「人眼看着不一样」 | 有两种渲染成同一句话 ⇒ **那是缺陷不是风格问题**（「未认到人」与「模型没配」混成一句，用户与判据都分不出），当场修 |
| `H8c` | **真 nginx 502**（不是打桩）：`docker compose stop agenerp-serve` 之后，在面板里发一次问 | 面板渲染**非空、可分辨、带 `502`** 的文本 | ⚠️ **这一格是独立评审 iteration 2 逼出来的，理由必须写清**：`tools/nginx/frappe.conf.template` **没有 `error_page`、没有 `proxy_intercept_errors`** ⇒ 真 nginx 502/504 回的是**默认 HTML 错误页**，而服务端的 502/503 回的是 **JSON `{"error": …}`**。⇒ **打桩喂一个「JSON 体的假 502」走的是面板的 JSON 分支，真 502 上 `r.json()` 会直接抛**，正好落进 Goal 2 禁止的空白，而打桩判据全绿。⇒ **`H8` 那批打桩不能替代这一格。** 本格零额外成本（`H10` 本来就要停服）。不吻合 ⇒ 当场修兜底分支，让它**不假设响应体是 JSON** |
| `H8b` | **喂一个未枚举的码**（写死用 `418`）与**一次网络层失败**（`page.route` 直接 `abort`） | 两者都渲染出**非空、可分辨、带上那个码/失败原因本身**的文本；**不空白、不 spinner** | 空白或 spinner ⇒ **兜底态缺失，当场补**。⚠️ 这一格不是凑数：`500`（`app.py:327` 的 `except Exception` 兜底）与 `504`（`proxy_read_timeout`）在真环境里**会**发生，而封闭枚举接不住它们 |
| `H9` | 面板实际发出的请求体键集。⚠️ **与 `H6` / `M5` 同一约束：只能取自那一次「未打桩」的真请求**（`page.expect_response` / `request` 事件） | ⊆ `{question, task_class, doctype, name}`，**且不含** `fields`/`role`/`view`/`actions`/`user` | 含了 ⇒ 当场删。⚠️ 这一格不是形式主义：服务端对这五个键回 400，前端带上就是**必然 400**，而那种 400 在界面上和「问题不合法」长得一样 |
| `H10` | `docker compose stop agenerp-serve` 后：`frontend` 是否仍 `healthy`、`/app` 是否仍 200、资产是否 502 | `healthy` · `RestartCount=0` · `/app` **200** · `/agenerp/desk.js` **502** | 不吻合 ⇒ §7.21 `D-b-8` 回归了，**优先修回归** |
| `H11` | `down -v` 冷起：`up -d --wait --wait-timeout 900` | **exit 0**，十个长期服务全 `running`、七个有探针的全 `healthy` | 不吻合 ⇒ 按裁判规则 3 **原样复跑**一次；仍不吻合则记「不可复现」或坐实为回归，**不猜根因** |

## 7. Execution Plan

### Phase 1 — 先探测，再裁定（`D-d-1` … `D-d-4`），一行产品代码都还不写

Status: planned
Targets: `docs/analysis/2026-08-25-1743-desk-sidebar-probe.md`（探测记录，新建）·
`docs/architecture/module-boundaries.md` §7.23（落点节，新建）
Skill: `none`

- Item Types: `Decision | Proof`（4/6 项是 `Decision`）
- Prereqs: §0 四条重取基线已跑完；`H1` / `H2` 已有实际值

- [ ] **Explore**：跑 `H1`–`H5` 五条探针，逐条把实际值填进 §6 与探测记录。
      ⚠️ `H3` / `H4` 必须**带真登录会话在真 Desk 页面上**测，不许拿静态 HTML 推。
      - Skill: `none`
- [ ] **`D-d-0` `docs/references/playwright-e2e-guide.md` 的效力分类**（`Decision`，**前置于 `D-d-1` / `D-d-2`**）。
      把它分类为 **`已批准的技术选型`** 还是 **`上游模板残留（stale）`**，并写清依据。
      ⚠️ **loop 只能陈述证据、不能自己定**（§0.5）：本条的结论**必须来自人在 §0.5 前置第 2 条上的回答**；
      人没答就走停机分支 4。**不许用「反正它写着 Playwright」当批准。**
      - Skill: `none`
- [ ] **`D-d-1` 判据的目录与形态**（`Decision`）。候选三个，逐条写清否决/选中理由与残余风险：
      **(A)** 落 `tests/ui/test_sidebar.py`，形态**照抄本仓既有先例**——
      它是一个**薄加载器**（同 `tests/gates/test_explain_service_live.py` 的做法：
      「判据只有一份，门禁是它的严格模式」），断言体落在**已进 CI 的** `tests/unit/test_desk_sidebar_body.py`，
      加载器把体里的 `skip` 收严成 `fail`（§1.6）。
      **(B)** 不建 `tests/ui/`，判据全放 `tests/unit/` ⇒ **WBS 第 88 行的验收命令不成立**，工作项 11 无法转 `done`。
      **(C)** 建目录并自己去改 `gates.yml` 的 `COVERED` ⇒ **红线 2，禁，不进候选比较，只记它为什么被排除。**
      **裁定必须正面回答的三件事**：① (A) 会让 §1.4 那一步在下次推送时红，这个代价接不接受、
      凭什么接受（引先例与守卫自己的失败文案）；② 断言体为什么不能直接住在 `tests/ui/`
      （住进去就**不受** `pytest tests/unit -q` 那一轮保护，日常改坏了看不见）；
      ③ (B) 的出口是什么（也是归人 —— 预算已满、拆行只有人能做）。
      - Skill: `none`
- [ ] **`D-d-2` 浏览器驱动与依赖声明形态**（`Decision`）。候选：**(a)** playwright（本机 1.58.0 + chromium 已下载 +
      `pytest-playwright` 已在）· **(b)** selenium 4.39.0 · **(c)** 不用浏览器、用 `http.client` 打 HTML
      ⇒ **撞硬约束①**（「按下 ⌘K 之后发生了什么」根本没测，退化成验「调得通」）· **(d)** 引 node 跑 JS 环境
      ⇒ 引入第二套运行时与第二个包管理器，且仍不是真浏览器。
      **声明形态一并裁死**：写进 `[project.optional-dependencies]` 的一个 **`ui` extra**，
      **`[project].dependencies` 一个字不加**（§5）；并在探测记录里写明「本机装着 ≠ 仓里声明了」这条旧亏（§1.5）。
      ⚠️ **`D-d-2` 若判定「必须引第三方驱动」，那是一次需人拍板的依赖决策**（`1615-1` §11 逐字写死的）
      ⇒ 裁定文本必须**显式点名这一点**，并把「人不批怎么办」的出口写死（出口 = §11 登记 + 判据先建后绿）。
      - Skill: `none`
- [ ] **`D-d-3` 零 skip 怎么做到**（`Decision`）。⚠️ **起草期第一版这条是错的，独立评审实读打回，下面是改准后的形态。**

      **先把先例的机制读准**：`tests/gates/test_explain_service_live.py` 是 `:57` 先 `exec_module()`、
      `:80` 才把 `_BODY.pytest.skip` 换成 `fail` ⇒ **收严只对「导入完成之后才被调用」的 skip 生效**
      （既有断言体那三处 skip 在 `:114/:133/:144` 的 helper 里，所以先例成立）。
      ⇒ **模块级的 skip 收不严** —— `Skipped` 在 `exec_module()` 里就抛出来了，收严那一行**还没执行**，
      结果是**门禁退 0 且 `1 skipped`：一条绿着的、不存在的门禁**，正是 §1.6 要挡的那件事。

      **裁定写死三条**：
      ① **加载器在 `exec_module()` 之前自己 `import playwright`**，失败即 `pytest.fail`（不是 skip、不是 `importorskip`）；
      ② **断言体里禁用模块级 `pytest.importorskip` 与模块级 `pytest.skip`** —— 驱动导入与活栈探活
      **一律放进 fixture**，在 fixture 里 `pytest.skip(...)`，这样才落在收严的作用域内；
      ③ **`tests/unit/` 那份允许 skip、`tests/ui/` 那份必须 fail，这个取舍差是有意的**
      （日常那一轮不该因为没起 docker 就整轮红），**必须在落点节 §7.23 写清楚，不许含糊成「都一样」**。
      ⚠️ 顺带照实记一条**只记不改**的观测：先例那种 `_BODY.pytest.skip = ...` 的赋值改的是**全局 `pytest` 模块**，
      属进程级污染；**本 plan 不去改那份先例**（红线 1），但自己这一份**不复制该写法**，改用上面 ①②。
      - Skill: `none`
- [ ] **`D-d-4` 快捷键**（`Decision`，依赖 `H3` 的实际值）：`Cmd/Ctrl+K` 与 Desk 原生绑定是否冲突、
      冲突时选谁。**不抢已被占用的键**（见 `H3` 的「不吻合怎么办」）。
      同时裁死**关闭方式**（至少 `Esc` + 再按一次同一组合键）与**焦点归还**
      （关闭后焦点回到唤起前那个元素 —— 不还焦点在单据页上是实实在在的可用性缺陷）。
      - Skill: `none`
- [ ] **Proof**：探测记录 `docs/analysis/2026-08-25-1743-desk-sidebar-probe.md` 落盘，
      含 `H1`–`H5` 的命令原文 + 退出码 + 实际值，与四条裁定的完整理由。
      - Skill: `none`

**⚠️ Phase 1 的三条停机分支（触发即停，写进 `STATE.md` §3 needs-human，不自行绕过）**：

1. **`H2` 不吻合**（驱动不可用）⇒ 依赖决策归人。
2. **`H6` 若在 Phase 3 不吻合**（浏览器不带 `sid`）⇒ D-19 的同源假设需人重裁（红线 3，loop 无权开 `R-x`）。
3. **`D-d-1` 裁到 (C)**（即：论证下来只有改 `gates.yml` 一条路）⇒ **红线 2，立即停机交人**。
4. ⚠️ **`D-d-2` 裁定为「必须引第三方浏览器驱动」时也停一次**（独立评审打回后新增；起草期漏了这条）。
   前一个 plan `1615-1` §11 第二条逐字：「那是一次**需人拍板的依赖决策**……**本 plan 只指明，不代人选**」。
   ⇒ **`H2` 吻合（驱动可用）不是免停理由** —— 恰恰是「结论已确定」的那一刻。
   **动 `pyproject.toml` 之前**先往 `STATE.md` §3 **追加**一条 needs-human（写清：要装什么、装在哪、
   不装的后果是判据先建后绿），**然后停**。
   **唯一的免停条件**：能指出**人已批准**的具体出处（commit / `STATE.md` 里的 `[resolved]` 行 / `Gates-Change-Approved-By` trailer）。
   **指不出就是没批，不许用「本机已经装着」当批准。**

Exit Criteria:

- [ ] `H1`–`H5` 五格各有**实际值**（不是「预计」「应该」），且与 §6 预测列逐条对照过
- [ ] `D-d-1` / `D-d-2` / `D-d-3` / `D-d-4` 四条裁定各有：选中项、被否项、**否决依据是执行期探针还是外部规则（写明哪一条）**、残余风险
- [ ] 落点节 `docs/architecture/module-boundaries.md` **§7.23** 建好；`§7.13/§7.20/§7.21/§7.22` 经 `git diff` 确认**零行改动**
- [ ] `docs/logs/2026/08-25.md` 追加 Phase 1 条目

### Phase 2 — 侧边栏本体 + 离线判据（不需要浏览器就能判的那一半）

Status: planned
Targets: `agenerp/serve/assets/desk.js` · `tests/unit/test_desk_sidebar_static.py`（新建）
Skill: `none`

- Item Types: `Add`（5/6 项是 `Add`）
- Prereqs: Phase 1 四条裁定全部落定

- [ ] **`Add`** `desk.js` 扩成侧边栏本体，**六件事**：① 注册 `D-d-4` 裁定的快捷键（唤起 / 关闭 / `Esc` / 焦点归还）；
      ② 按 `H4` 裁定的取法拿当前单据上下文，**取不到就不带**（§1.3 的「同时给或同时不给」）；
      ③ 同源 `fetch("/agenerp/explain", {method:"POST", credentials:"same-origin", …})`；
      ④ 请求体**只放** `question` / `task_class` / `doctype` / `name`（`H9`）；
      ⑤ 按 §1.3 的**十种已枚举的码 + 200** 各渲染一种可分辨的非空态（`H8`），
      **外加一条兜底态**接住未枚举的码与网络层失败（`H8b`）—— **没有一条路径通向空白或永久 spinner**；
      ⑥ **保留既有资产判据钉着的四格**：`len>200` · `agenerpDesk` · **`Object.freeze`** · **结尾逐字 `)();`**
      （`test_desk_asset_route.py:165-168`）。
      ⚠️ 面板要挂状态时最容易顺手去掉的是 `Object.freeze` —— **挂状态请另起一个不冻结的内部变量，
      别把标记对象解冻**。
      ⚠️ **结尾那格是「判据钉死的形状」，不是风格偏好**（独立评审 iteration 2 补）：
      面板要注册 `document.addEventListener`、要拆成多个内部函数，收尾很容易在格式化时变成别的写法。
      **整份资产必须仍是一个以 `)();` 逐字收尾的 IIFE。**
      `version` 往上走一格、`plan` 改成本 plan 号。
      - Skill: `none`
- [ ] **`Add`** 判据 `tests/unit/test_desk_sidebar_static.py` —— **离线、零浏览器**，守四件事：
      ① 资产里出现的请求路径与 `app.py` 的 `EXPLAIN_PATH` **各读一次再比**（**不写第三个字面量**，沿用 §7.22 口径）；
      ② 资产里出现的请求体键名集合 ⊆ `app.py` 的 `ALLOWED_BODY_KEYS`，**且与五个越权键的交集为空**
      （两个集合都从 `app.py` 读，不在判据里抄）；
      ③ `window.agenerpDesk` 标记仍在；
      ④ **十种已枚举的码在资产里各出现过** —— 挡「只写了 200 分支」的半成品。
      ⚠️ **这一条是下限，它不证明任何分支「可达」，也不许被读成证明了兜底存在**
      （独立评审 iteration 2 打回第一版那句「兜底分支在源码里可达」）：
      本判据是**离线、零浏览器、零 JS 运行时**的，Python 读 `.js` 纯文本 ⇒
      可达性是控制流属性，**唯一能实现的手段就是关键字/正则匹配**，
      而那正是 roadmap `:186` 记着「走不通」的同一条路。
      **分工写死**：**「兜底态真的接得住」由 `H8b`（浏览器里真喂 `418` / 真 `abort`）与 `M9` 承担，
      离线这一份不承担、也不假装承担。**
      - Skill: `none`
- [ ] **`Proof`** 既有 22 条（`test_desk_asset_route.py` / `test_desk_injection_static.py`）**一条不许改松**，
      跑一遍确认仍全绿 —— 尤其那条「服务发出的体与仓里那份**逐字节相同**」（改了 `desk.js` 之后它必须仍绿）。
      - Skill: `none`
- [ ] **`Proof`** `ruff check` 覆盖面**加上新目录**（`D-d-1` 选 (A) 时把 `tests/ui` 加进那条命令的参数）。
      ⚠️ `ruff` 的 `exclude` 只排除 `tests/gates`，**`tests/ui` 会被真扫**，别指望它被跳过。
      - Skill: `none`
- [ ] **`Proof`** `python3 -m pytest tests/unit -q` 只增不减；`check_expected_red.py` 仍 exit 0。
      - Skill: `none`
- [ ] **`Add`** 落点节 §7.23 补「渲染状态机」那一格：**十种已枚举的码 + 200 + 一条兜底态**的映射表，
      与 §1.3 的服务端表**逐条对齐**。
      ⚠️ **这张表必须写成「开放枚举 + 兜底」，不许写成封闭枚举** —— 它是要落进 owner doc 的**持久制品**，
      把封闭枚举写进架构文档，等于把「真实 500/504 渲染成空白」这个失败形态**固化成规范**
      （第一版正是在这里漏改，独立评审 iteration 2 打回）。
      同时写明维护义务：**服务端加一种码，这张表跟着加一行；但兜底态在任何时候都不许删。**
      - Skill: `none`

Exit Criteria:

- [ ] ⌘K（或 `D-d-4` 裁定的键，冲突时写死为 `Cmd/Ctrl+Shift+K`）唤起 / 关闭 / `Esc` / 焦点归还四条行为**都在代码里**，不是只有函数签名
- [ ] 失败模式说清：**十种已枚举的码各自的可见态互不相同、非空、不 spinner**，**且兜底态接得住未枚举的码**；成功模式：200 时渲染 `answer` 与 `cost`
- [ ] 新判据 `tests/unit/test_desk_sidebar_static.py` 全绿；既有 22 条**零改动**（`git diff` 证）
- [ ] `docs/architecture/module-boundaries.md` §7.23 的状态机表落地
- [ ] `docs/logs/2026/08-25.md` 追加 Phase 2 条目

### Phase 3 — `tests/ui/test_sidebar.py` 活体门禁 + 变异自查 + 交接

Status: planned
Targets: `tests/ui/test_sidebar.py`（新建，加载器）· `tests/unit/test_desk_sidebar_body.py`（新建，断言体）·
`pyproject.toml`（`ui` extra）· `docs/evidence/p1-desk-sidebar/README.md`（新建）
Skill: `closure-audit-prompt.md`（仅收口那一步）

- Item Types: `Proof`（5/7 项是 `Proof`）
- Prereqs: Phase 2 全部完成；活栈按 §5 起好并**真登录**过一次

- [ ] **`Add`** 断言体 `tests/unit/test_desk_sidebar_body.py`：真浏览器、真登录、真 Desk 页面，
      覆盖 `H6` / `H7` / `H8` / `H8b` / `H8c` / `H9` 六格。
      **驱动取不到或活栈够不到 ⇒ 在 fixture 里 skip**，**模块级一律不 skip、不 `importorskip`**（`D-d-3` ①②）。
      ⚠️ `H6` 与 `M5` 的证据**只能取自那一次「未打桩」的真请求**（`page.expect_response`）——
      `page.route` 打桩的请求到不了服务端，从它们身上取不到「服务端看到了 `sid`」。
      - Skill: `none`
- [ ] **`Add`** 加载器 `tests/ui/test_sidebar.py`：`pytestmark = pytest.mark.live`；
      **先自己 `import playwright`（失败即 `pytest.fail`），再按路径加载断言体**，
      随后把体里的 `skip` 收严成 `fail`（`D-d-3` ①②③）。⚠️ **零 skip 分支**（§1.6）。
      - Skill: `none`
- [ ] **`Add`** `pyproject.toml` 加 `[project.optional-dependencies]` 的 `ui` extra
      （`D-d-2` 裁定的形态）。⚠️ **`[project].dependencies` 与 `[tool.pytest.ini_options]` 的
      `testpaths` / `markers` 逐字不动**；`ruff` 的 `exclude` 也不动。
      - Skill: `none`
- [ ] **`Proof`** 跑 WBS 那条命令原文：`AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin
      python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` ⇒ **必须 exit 0 且零 skip**。
      **退出码与输出逐字抄进 `docs/evidence/p1-desk-sidebar/README.md` 与收口表。**
      - Skill: `none`
- [ ] **`Proof`** 不回归三条：`H10`（停 `agenerp-serve` 后 frontend 仍 healthy）· `H11`（`down -v` 冷起 exit 0）·
      零依赖启动门禁 `tests/unit/test_compose_zero_dep.py` 全绿**且一条未改松**。
      - Skill: `none`
- [ ] **`Proof`** **变异自查**：至少 `M1`–`M12` 十二条，逐条施加、逐条确认**被打红**、逐条复原并 `sha256` 校验 `RESTORED OK`。
      写死的十二条：`M1` 删掉快捷键注册 · `M2` 把 503 分支渲染成空字符串 · `M3` 把 401 与 503 渲染成同一句话 ·
      `M4` 请求体里偷偷加一个 `user` 键 · `M5` 把 `credentials` 改成 `omit`（`sid` 不再自动带）·
      `M6` 把请求路径改成 `/agenerp/explain2` · `M7` 把加载器里的 `skip→fail` 收严去掉 ·
      `M8` 把 `window.agenerpDesk` 标记删掉 · **`M9` 删掉渲染状态机的兜底分支**（`H8b` 那格必须打红）·
      **`M10` 把断言体里的 fixture 级 skip 改回模块级 skip**（`D-d-3` ①② 那条必须打红 ——
      这一条专挡「绿着的、不存在的门禁」那个失败形态）·
      **`M11` 让兜底分支假设响应体是 JSON**（`H8c` 那格必须打红 —— 专挡「真 nginx 502 上 `r.json()` 抛出、
      面板空白，而所有打桩判据全绿」）·
      **`M12` 把资产结尾从 `)();` 改成 `})();\n// end`**（`test_desk_asset_route.py:168` 必须打红 ——
      现有 `M1`–`M11` 没有一条守它）。
      ⚠️ **`M5` 与 `H6` 同理**：`credentials: "omit"` 只有在**未打桩的那条真请求断言**上才打得红，
      打桩那批对它无感 —— **变异表里写死这一句，免得事后把「没打红」解释成「不需要」。**
      ⚠️ **打不红的照实记在表里**，当场补断言后复跑；补不出来就**保留「这条守不住」的记录**，不许改成「全打红」。
      - Skill: `none`
- [ ] **`Fix | Follow-up` 交接**：往 `docs/masterplan/STATE.md` §3 **追加**（只追加）一条 needs-human。
      ⚠️ **起草期把它写成「加一行 `COVERED` 就好了」是错的**（独立评审实读打回）——
      `check_expected_red.py:73-74` 的判定面写死 `tests/gates`，加 `COVERED` **只让第 ⑦ 步不红，
      不会让这条门禁在 CI 上跑起来一次**。交接必须**逐件写清人要做的五件**：
      **(1)** 把 `ui` 加进 `unit-and-contracts` 第 ⑦ 步的 `COVERED`（否则那一步红）；
      **(2)** 在 `gates-l2-live` 里装 `ui` extra 并 `playwright install --with-deps chromium`；
      **(3)** 在 `gates-l2-live` 里加一条 `python3 -m pytest -m live tests/ui/test_sidebar.py` 的 step
      —— **没有这一步，新门禁在 CI 上零覆盖**；
      **(4)** 那条 step 照抄 `gates.yml:492-495` 既有的**零 skip 断言**形态（否则 skip 又变成静默出口）；
      **(5)** `lint` job（`gates.yml:609`）的 ruff 参数是七个目录的字面量 ⇒ 加上 `tests/ui`，否则它在 CI 上零 lint 覆盖。
      ⚠️ **交接项 (5) 有一件邻接活是 loop 自己该做的，不许一起推出去**（独立评审 iteration 2 指出）：
      `gates.yml:604` 逐字声明 lint 作用域「照抄 `docs/context/project-context.md` 的 Lint / static check 一行」，
      而那一行**今天还是三个目录、gates.yml 已经是七个 —— 本就已漂移**。
      ⇒ **本 plan 就地把 `project-context.md` 那一行改准成七个目录并加上 `tests/ui`**（它不在任何红线内），
      否则交接项 (5) 没有真相源可照抄。**这是 `Fix`，不是 follow-up。**
      **再加一件需人裁的**：`D-d-4` 若因 `H3` 冲突改成 `Cmd/Ctrl+Shift+K`，与 WBS 第 88 行「⌘K」字面的偏差归人。
      ⚠️ **五件全部落在 `.github/workflows/**` 里 ⇒ 红线 2，本 plan 一个字节都不碰，只写清楚交出去。**
      **同时往 §3 追加一条 `[Proof]` 证据行**（本 plan 的落地 sha + 命令原文 + 退出码）。
      - Skill: `none`

Exit Criteria:

- [ ] `AGENERP_LIVE=1 … pytest -m live tests/ui/test_sidebar.py -q -rs` → **exit 0，零 skip**（命令原文 + 退出码入证据文件）
- [ ] `H6` 有**直接观测值**：浏览器发出的请求带上了 `sid`（回的不是 401）—— 本仓第一次
- [ ] 变异表 `M1`–`M12` 逐条有结论（打红 / 未打红 + 处置），全部 `RESTORED OK`
- [ ] 不回归三条全绿；`check_expected_red.py` exit 0；`tests/unit` 只增不减
- [ ] `STATE.md` §3 两条**追加**（needs-human + `[Proof]`），**已有行零改写**（`git diff` 证）
- [ ] `docs/evidence/p1-desk-sidebar/README.md` 落盘；`docs/logs/2026/08-25.md` 追加 Phase 3 条目

## 8. 风险

- **R1 · `tests/ui/` 让 CI 第 ⑦ 步变红（已知、已裁、已交接）。** 见 §1.4 与 Phase 3 交接项。
  ⚠️ 这是本 plan **明知会发生**的代价，不是意外。`AGENTS.md` 裁判规则 4 的停机条件含「CI 连续 2 轮红」——
  ⇒ 交接文字必须让人**一次就能修完**，且 §11 写死重开事件。
- **R2 · 真浏览器实证第一次做，失败形态未知。** 本仓零先例（§1.8）。
  处置：`H6` 不吻合当场停机交人（Phase 1 停机分支 2），**不猜根因**（裁判规则 3）。
- **R3 · 判据建在 503 分支上 ⇒ 「答得对」完全没测。** 这是**有意的收窄**（§1.7 / Non-Goals 4），
  不是遗漏。收口文字里**不许**把「面板显示了答案」写成「Agent 答对了」。
- **R4 · `desk.js` 从 1 KB 的自证脚本长成一个有状态的面板 ⇒ 既有 22 条判据里那条「逐字节相同」仍必须绿。**
  它比的是「服务发出的」与「仓里那份」两个源，改内容不该打破它；**但若打破了，那是真回归，必须修不许改判据。**
- **R5 · `proxy_read_timeout 300` 仍未在真实长解释上验证**（§7.21 记着，本 plan Non-Goals 6 明确不做）。
  ⇒ 侧边栏在一次**真**长解释上会不会被反代掐断，**本 plan 之后仍然不知道**。登记在 §11。
- **R6 · 本机 Docker 已知两处不稳定**（另一个 compose 项目占 `8080`；冷起偶发 `No such container`）。
  ⇒ 活体取证是在一台不稳定的机器上做的，**照实记，不粉饰**；遇失败按裁判规则 3 原样复跑。

## 9. Draft Review Record

- **Independent draft review iteration 1: `needs revision`**（独立子代理，fresh session，agent `ae6b4d3b92a4d098d`，
  2026-08-25）—— 审的是本文件第一版。评审者按 `docs/skills/plan-audit-prompt.md` 的口径，
  **逐条实读活仓核对**（不采信 plan 自报），给出 **9 条阻塞项 + 9 条非阻塞建议**。
  ⚠️ **它实跑了四条基线命令**，其中 `check_expected_red.py` 实测是 `门禁 28 项`，
  **打掉了本文件第一版写的 `26`**。**9 条阻塞项全部采纳并已改进本文件**，逐条对应：

  | # | 阻塞项 | 改在哪 |
  |---|---|---|
  | 1 | 状态码枚举漏了 `404` / `500` 与反代 `502` / `504`，封闭枚举 ⇒ 真实 500/504 必然渲染成空白 | §1.3 改准成「八种服务端码 + 两种反代码」· Goal 2 · `H8`/**新增 `H8b`** · Phase 2 ⑤ 与判据④ 加兜底态 · 变异表**新增 `M9`** |
  | 2 | `tests/ui` 在 CI 上**零覆盖**（`check_expected_red.py:73-74` 判定面写死 `tests/gates`），第一版那句「加一行 `COVERED` 就好」是错的 | §1.4 第 3 条改准成 (i)(ii)(iii) 三重代价 · Phase 3 交接项重写成**逐件五条** |
  | 3 | `D-d-3` 与先例机制不兼容：模块级 skip 在 `exec_module()` 里就抛，收严那行还没执行 ⇒ **绿着的、不存在的门禁** | `D-d-3` 整条重写（加载器先 `import playwright` 再加载体；体的 skip 一律进 fixture；禁模块级 `importorskip`）· 变异表**新增 `M10`** 专挡它 |
  | 4 | 把 503 钉死进断言是环境相关断言；`H7` 的「清干净重跑」与 `gates.yml:275-279` 禁止的「迁就环境」同族，且 `gates.yml:304-310` 已配三个 AI secret | §1.7 加「不许钉死 503」整段 · `H7` 的处置列改成「照实记该码并断言对应态，**不许清环境重跑**」· `H6` 独立成一条 `status != 401` 断言 |
  | 5 | `D-d-2` 把「需人拍板的依赖决策」自行降级；`H2` **吻合**时反而不停 | Phase 1 **新增第 4 条停机分支**（动 `pyproject.toml` 前先追加 needs-human 并停；免停条件必须指出人已批准的具体出处） |
  | 6 | §10 第 1 格把四件事并列，给「活体命令没退 0」留了降级口子 | §10 **新增一格**：该命令未退 0 则不得转 `completed`，只能停在 `active` 交人；引 Minimum Rule 14 + Anti-Slacking 四态，并写死「不许挪进 §11」 |
  | 7 | `agents-and-roles.md` §9 风险档表是无人认领的义务，且该表分的是**运行时动作**、与本次改动不同维 | §4 把它**从 Owner Docs 去掉**并写明 `No owner-doc update required` + 与 §7.22 `D-c-3` 为何不冲突 · §10 第 2 格补该口径 |
  | 8 | `tests/ui` 在 CI 上也**零 lint 覆盖**（`gates.yml:609` 是七个目录的字面量） | 并进 §1.4 (iii) 与 Phase 3 交接项第 (5) 件 |
  | 9 | §1 全文没提前置（工作项 10）在 roadmap 上今天是 `todo` | **新增 §1.8b**，写清「只依赖它已落盘且已实读确认的那部分，不声称它已闭合」 |

  **9 条非阻塞建议同样全部采纳**：门禁 26→**28**（§1.9）· `ASSET_DIR` 补 `.resolve()`（§1.2）·
  红线 2 那句注释的行号改准成 `gates.yml:542`（§1.4）· skills 16 条目→**15 份提示词**（§4）·
  既有资产判据从点 1 格改成点**四格**并点名 `Object.freeze` 最易丢（Goal 5 / Phase 2 ⑥）·
  `H6` 写死用 `page.expect_response` 观测**未打桩**那一次 · `M5` 同上写死 ·
  `H3` 次选键写死 `Cmd/Ctrl+Shift+K` · `H4` 优先级写死 `URL > frappe.get_route() > cur_frm.doc`。

  ⚠️ **评审者明确判定的两件「不该改」也照实记**：① **Minimum Rule 4 不该拆**（理由已写进 §3.1）；
  ② 红线合规面它逐项核过 `git diff` 那六条自证与三个 Phase 的 Targets，**没找出必然越线的藏步**。

- **Independent draft review iteration 2: `needs revision` + 明确判 `可以转 active: no`**
  （**第二位**独立子代理，fresh session，agent `a2fb6129ec828cf5f`，2026-08-25）——
  它同时做两件：复审上表 9 条、并**不受第一轮结论约束**地重审全文。

  **对上表 9 条的复核结论**：`2/3/4/6/8` **已修复**；`5` 机制对但**后果没跟着算**；
  `7` 已修但**换出一个新洞**（`docs/index.md:45` 路由到的 owner doc 全程未读）；`9` **满足字面但偏弱**；
  **`1` 判为「修得不对」** —— §1.3 / Goal 2 / `H8` / `H8b` / `M9` 都改成十种了，
  **但 Phase 2 最后一项与 Non-Goals 1 仍写「六种」**，而前者是要落进 owner doc §7.23 的**持久制品**
  ⇒ 封闭枚举原封不动写进架构文档。**已就地改准**（两处）。

  **它新提 5 条阻塞，逐条处置**：

  | # | 新发现 | 处置 |
  |---|---|---|
  | 1 | **`D-d-2` 的免停出处今天不存在**（实测：`docs/masterplan` / `docs/backlog` 里 playwright/selenium **零命中**；无 `Approved-By`）⇒ Phase 1 停机分支 4 **100% 触发**，本 plan 一执行就停，却已吃掉最后一格预算 | **采纳，且是本轮的决定性结论**：新增 **§0.5** 写死「转 `active` 的两条人裁前置」，**`Plan Status` 保持 `draft`**；两条同时追加进 `STATE.md` §3 needs-human |
  | 2 | `docs/references/playwright-e2e-guide.md:3` 逐字「Playwright is the fixed e2e testing framework」与 `1615-1` Non-Goals 5 正面冲突，而它是 `a959410` 带进来的**上游模板残留**（引的 `playwright.config.ts` 本仓不存在），plan 全程未分类 | **采纳**：§4 Owner Docs 补上它；Phase 1 新增 **`D-d-0`**（**前置于 `D-d-1`/`D-d-2`**），写死「loop 只能陈述证据、不能自己定」「不许用它当批准」 |
  | 3 | Phase 2 判据④「兜底分支在源码里可达」**离线写不出来** —— 纯文本读 `.js`、无 JS 运行时 ⇒ 只能退化成正则，而同一句话又把正则禁了 | **采纳**：删掉「可达」，判据④ 降为「十种码各出现过」并**显式标注这是下限、不证可达**；兜底的真证据交给 `H8b` + `M9`，分工写死 |
  | 4 | `page.route` 打桩的「假 502」与**真 nginx 502 不是一回事** —— 模板无 `error_page` / `proxy_intercept_errors` ⇒ 真 502 回**默认 HTML**、服务端 502/503 回 **JSON**；真 502 上 `r.json()` 会抛 ⇒ 空白，而打桩判据全绿 | **采纳**：新增 **`H8c`**（借 `H10` 已有的停服动作，**零额外成本**拿到真 502）+ 变异 **`M11`**；504 拿不到真的，照实记进 §11 |
  | 5 | `Object.freeze` 已点名，但真正的脆弱点是 `test_desk_asset_route.py:168` 的**结尾逐字 `)();`** —— 面板注册监听、拆函数后收尾极易变形，而 `M1`–`M10` 没有一条守它 | **采纳**：Phase 2 ⑥ 写明「那是判据钉死的形状不是风格」+ 新增变异 **`M12`** |

  **5 条非阻塞建议处置**：① §1.8b 补引人写的两条 `todo` 理由并**分开说哪条已被推翻、哪条仍敞着** —— 已改 ·
  ② `gates.yml:604` 声明 lint 作用域「照抄 `project-context.md`」而那一行今天仍是三个目录、已漂移 ⇒
  **这件是 loop 自己该做的 `Fix`，不许跟着交接一起推出去** —— 已写进 Phase 3 交接项 (5) 下方 ·
  ③ `H8`「互不相同」的判定口径写死（两两全等比较全为假 + 每条含码字面量）—— 已改 ·
  ④ `H9` 与 `H6`/`M5` 同约束、只能取自未打桩那一次 —— 已改 · ⑤ §1.9 的 28 未复跑（§0 已强制重取，无异议）。

  ⚠️ **它也复核了两件「不该改」**：**Minimum Rule 4 不该拆**（与 iteration 1 同结论，§3.1 已记）；
  **Phase 3 交接六件逐件核过，五件在红线 2 面、第六件在红线 5 面，没有一件是 loop 能自己做的**
  —— 唯一被它揪出来该由 loop 做的是那处 lint 作用域漂移（已归位）。

- **本轮收敛结论：不转 `active`。** 两轮共 14 条阻塞已全部改进本文件，
  但 §0.5 那两条**只有人能答**的前置未答之前，这份 plan 不具备**可执行**契约
  （指南 Plan Status Flow：`active` 的含义是「独立评审已收敛成可执行契约」——
  一份 100% 会在 Phase 1 停机的 plan 不满足「可执行」）。
  ⇒ **`Plan Status` 保持 `draft`**，前置见 §0.5。人答完第 1 条即可转 `active`（第 2 条影响的是 `D-d-0` 的写法，不影响可执行性）。

## 10. Closure Gates

- [ ] in-scope behavior is complete（唤起 / 上下文保留 / 同源请求 / 十种态 + 兜底态渲染，五项都**有行为**不只有签名）
- [ ] ⚠️ **闭合判据本身（不可降级，独立评审打回后写死）**：
      `AGENERP_LIVE=1 … python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` **退 0 且零 skip**。
      **它没退 0 时本 plan 不得转 `completed`** —— 只能停在 `active` 并把实测退出码与红因交人。
      **它不是可降级项**（指南 Minimum Rule 14「确认的活体缺陷/契约漂移不得降级」+ Anti-Slacking 四态：
      `landed` / `adjudicated as residual-risk-only` / `moved to explicit successor ownership` / `removed from scope with recorded reason`
      —— 本条只能落 `landed`）。
      ⚠️ **不许把「没退 0」挪进 §11**：§11 里已登记的四条，**没有一条**是它。
- [ ] relevant docs are aligned（`module-boundaries.md` §7.23 · `docs/logs/2026/08-25.md` · `docs/evidence/p1-desk-sidebar/`）；
      对 `docs/design/agents-and-roles.md` §9 风险档表 **`No owner-doc update required`**（理由见 §4）
- [ ] verification has run —— 至少这七条，命令原文 + 退出码入 `## Closure`：
      `python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/ui tests/contracts tests/tools tests/routing tests/context tests/experiments` ·
      `AGENERP_LIVE=1 … python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` ·
      `docker compose up -d --wait --wait-timeout 900`（冷起）·
      `git diff -- .github/workflows tests/gates docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md` → **0 行**
- [ ] scoped verification is not conflated with full verification —— 若未跑整仓 `pytest tests -q -m "not live"`
      或未经 CI 服务端复跑，**逐条写明 `verification scope limited`**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded（§9）
- [ ] text consistency verified: 顶部 `Plan Status` ↔ 三个 Phase `Status` ↔ 全部 Exit Criteria ↔ 本节 ↔ 日志，五处互不打架；
      `grep -B5 "\- \[ \]" <本文件> | grep "Status: completed"` → **空**
- [ ] closure audit was independent（独立子代理或人，**执行者自己复跑不算**）
- [ ] closure evidence exists in files

### 红线自证（收口时逐条实跑，结果入 `## Closure`）

| # | 命令 | 期望 |
|---|---|---|
| 1 | `git diff --name-only <基线sha>..HEAD -- tests/gates` | **无输出** |
| 2 | `git diff --name-only <基线sha>..HEAD -- .github/workflows` | **无输出** |
| 3 | `git diff <基线sha>..HEAD -- docs/masterplan/DECISIONS.md` | **0 行** |
| 4 | `git diff <基线sha>..HEAD -- docs/masterplan/02-WBS.md` | **0 行** |
| 5 | `git diff <基线sha>..HEAD -- docs/masterplan/STATE.md \| grep -c '^-'` | **0**（只追加，零删除行） |
| 6 | `git diff --name-only <基线sha>..HEAD -- "$XM_PATH"` | **无输出**（证据仓未被写入） |

## 11. Deferred But Adjudicated

### `tests/ui/` 接进 CI（`gates.yml` 第 ⑦ 步与 `gates-l2-live` 的驱动安装）

- Classification: `watch-only residual`
- Why Not Blocking Closure: 五件落点**全部**在 `.github/workflows/**`，**红线 2，loop 一个字节都不许改**
  （独立评审 iteration 2 逐件核过，无一件是 loop 能自己做的）。
  本仓已有同形态先例（`tests/tools` / `tests/routing` / `tests/context` / `tests/experiments` 均由人接进 CI）。
  ⚠️ **代价不是「第 ⑦ 步红」一条，是「第 ⑦ 步红 + 新门禁在 CI 上零覆盖 + `tests/ui` 零 lint 覆盖」三条**（§1.4）。
- Successor Required: `yes`，**归人**。重开事件：**人下一次推送 `main` 看到第 ⑦ 步红的那一刻**
  （交接文字已在 Phase 3 写死，含可直接照做的一行修法）。
- ⚠️ **这不是「顺手没做」，是「做了就越线」。** 本 plan 明知它会红仍然落目录，理由写在 §1.4 与 `D-d-1`。

### `proxy_read_timeout 300` 在一次**真实长解释**上的行为 · 以及**真 nginx 504 的渲染**

- Classification: `watch-only residual`
- Why Not Blocking Closure: 本 plan 不产生长请求（§1.7 / Non-Goals 6）。
  ⚠️ **两件事分开说，不许合并**：**真 nginx 502 本 plan 拿得到**（`H8c`，借 `H10` 的停服动作）；
  **真 nginx 504 拿不到** —— 造一次真超时要一次真长解释，而那要 AI 变量与约 10 万 token。
  ⇒ **「面板在真 504 上渲染成什么样」本 plan 之后只有打桩证据，没有活体证据**，照实记，不写成已证。
  §7.21 记着这条从未被验证过，**本 plan 没有把它关掉，也不假装关掉了**。
- Successor Required: `yes`，**归人**（工作项 11 预算 `2/2` 满，拆行只有人能做）。
  重开事件：**第一次在配了 AI 变量的活栈上跑一次完整解释的那一刻** —— 那一次要么正常返回、要么被反代掐断，
  两种结果都直接回答这个问题。

### 「Agent 答得对不对」在侧边栏这条链上的验证

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 那是 P1.4 的结果面（工作项 6），本 plan 的结果面是**渲染与传输**（Non-Goals 4）。
  两者失败模式不同：前者是「蒙对/答错」，后者是「界面空白/请求没带身份」。
- Successor Required: `no`（在本 mission 内）。重开事件：**人在 `02-WBS.md` 为「侧边栏端到端答题」拆出新行**时。

### `D-d-4` 若改了键位 ⇒ 与 WBS 第 88 行「⌘K」字面的偏差

- Classification: `watch-only residual`
- Why Not Blocking Closure: 表规 6 逐字「可改的是字符串，不可改的是形状」，但**改 `02-WBS.md` 是红线 5**。
- Successor Required: `yes`，**归人**。重开事件：**`H3` 实测判定 `Cmd/Ctrl+K` 已被 Desk 原生占用**的那一刻
  （未触发则本条自然消解，收口时照实写「未触发」）。

## Closure

<待收口时填：Status Note · Closure Audit Evidence（独立审计者 + 命令原文 + 退出码 + sha）· Follow-up>
