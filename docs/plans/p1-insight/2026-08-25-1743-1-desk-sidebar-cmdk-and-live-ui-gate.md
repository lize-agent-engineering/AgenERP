# P1.8b 下半 · ⌘K 侧边栏本体与 `tests/ui/test_sidebar.py` 活体门禁

> Plan Status: draft
> Review Hold: §0.5 的两条前置只有人能答（① 准不准把浏览器驱动引进本仓 —— 前一个 plan 逐字保留给人的依赖决策；
> ② `docs/references/playwright-e2e-guide.md` 算不算数）。**第 5 轮独立评审第四次实读复核、不是转述**
> （`HEAD` = `c19cf4a`，工作树**干净**）：`docs/masterplan/STATE.md:867` 仍是 `[needs-human]` 而非 `[resolved]`
> （全文**882 行**，其后只有 `:874` 那条 `[open] 14:05Z` 的事实登记，**不覆盖它**），
> `git log --grep=Approved-By` 今天是 **30 条**（第 4 轮是 20 条），**无一条涉及浏览器驱动**。
> ⇒ Phase 1 停机分支 4 仍是 100% 触发 ⇒ 不具备「可执行契约」，**不转 `active`**。人答完第 ① 条即可转。
> ⚠️ **新增一个必须挡住的误读（第 5 轮补，同 iteration 3 第 3 条的同族陷阱）**：新增的 10 条 `Approved-By`
> 里有 `e3afd77` / `758b7bc` 两条**就带着 `Gates-Change-Approved-By: lize`、且确实改了 `.github/workflows/gates.yml`**。
> **那两条批的是 CI 变量接线与失败取证步，与浏览器驱动毫无关系。**
> 执行期跑 `git log --grep=Approved-By` 会看到「有 trailer、还是 gates 面的」——
> **拿它们当第 ① 条的批准，就是把别人给另一件事的许可挪用到自己头上。免停条件必须逐字点名浏览器驱动。**
> ⚠️ **第 4 轮写在这里的「工作树有人侧未提交改动」已经不成立了**（第 5 轮实测）：
> 那两处改动**已由人落盘**（`e3afd77` + `758b7bc`），`git status --porcelain` 今天**无输出**。
> 处置与它留下的**真**影响（判定环境已配 AI 变量、行号全体漂移）改写在 **§0.6**。
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
5. ⚠️ **重取本文件引用的每一处 `gates.yml` / `project-context.md` 行号**（第 4 轮独立评审补，理由见 §0.6）：
   `grep -n "COVERED=\|ruff check agenerp\|作用域三个目录\|判据自身的判据：跳过就是没跑\|配上之后它走答案面\|把判据调整到迁就环境\|这几个目录由 loop 写在红线外\|pip install pytest certifi" .github/workflows/gates.yml`
   —— **按那几句注释原文定位，不认本文件写的行号**。人侧已两次改过 `gates.yml`（`e3afd77` / `758b7bc`，§0.6），
   行号**已经全体漂移**；**对不上不是本 plan 的错，硬按行号走才是。**
6. ⚠️ **本机 shell 里到底有没有 AI 变量**（第 5 轮独立评审新增，理由见 §5 与 `H7b`）：
   `env | grep -c '^AGENERP_LLM_'` + `env | grep -o '^AGENERP_LLM_[A-Z_]*'`（**只打变量名，绝不打值**）。
   ⇒ **这一条决定本 plan 的活体取证是不是真的零成本**：`docker-compose.yml:65` 今天是
   `AGENERP_LLM_BASE_URL: ${AGENERP_LLM_BASE_URL:-${AGENERP_LLM_ENDPOINT:-}}`（`e3afd77` 落的），
   **起栈时你 shell 里有什么，`agenerp-serve` 容器里就有什么**。
   **数出来非 0 ⇒ H6/H9 那一次「未打桩的真请求」会真调模型**（真烧 token、真花约 50 秒），
   按 `H7b` 走，**不许当没看见**。结果（**变量名与个数，不含值**）抄进 §1.9 的开工基线表。

## 0.5 ⚠️ 本 plan 为什么停在 `draft` —— 一件只有人能做的裁定卡在最前面

**独立评审 iteration 2 实测打出来的，不是推演**：

- `grep -rl -i "playwright\|selenium" docs/masterplan docs/backlog` → 起草期 iteration 2 实测**零命中**
- `git log --grep=Approved-By` 里**无一条**涉及浏览器驱动；`DECISIONS.md` 无对应条目

⚠️ **这条 grep 今天已经不是零命中了，别读错（第 3 轮独立评审实测补）**：
`docs/masterplan/STATE.md:868-870` 现在命中 —— 那是**本轮追加的 `[needs-human]` 提问本身**，
状态词是 `[needs-human]` 而**不是** `[resolved]`。
⇒ **命中 ≠ 已批准。** 免停条件仍然是「人已批准的具体出处」（`[resolved]` 行 / commit / trailer），
**拿这条 needs-human 行当批准，就是拿自己写的提问给自己发许可。**

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

## 0.6 ⚠️ 人侧那两处改动**已经落盘了**（第 5 轮独立评审实测改准）

**第 4 轮在这里写的是「工作树里有人侧未提交改动」。那句话今天不成立了，照实改，不留旧文当活事实。**

第 5 轮实跑（`HEAD` = `c19cf4a`）：`git status --porcelain` → **无输出，工作树干净**。
第 4 轮看到的那两处 ` M` 已由**人**分两个 commit 落盘，**两条都带 `Gates-Change-Approved-By: lize`**：

| commit | 改了什么 | 对本 plan 的**真**影响 |
|---|---|---|
| `e3afd77` | `docker-compose.yml:65` 加 `AGENERP_LLM_BASE_URL: ${AGENERP_LLM_BASE_URL:-${AGENERP_LLM_ENDPOINT:-}}`；`gates.yml` 把 AI 变量挪到 `gates-l2-live` 的**起栈步** | **两条**：① §1.7 那句「起栈时一个 AI 变量都不配」**已过期**（已改，见 §1.7）；② ⚠️ **本机起栈也会把 shell 里的 `AGENERP_LLM_*` 带进 `agenerp-serve` 容器** ⇒ 「零 token 成本」不再是无条件的（§0 第 6 条 / `H7b` / §5） |
| `758b7bc` | `gates-l2-live` 加一个 `if: failure()` + `continue-on-error` 的失败取证步（`gates.yml` +22 行） | **不改变成败判定**（它自己的 commit message 逐字写着）。⇒ 对本 plan 的判据形态**无影响**，但**行号又漂了一次** |

**本 plan 对此写死三条**（第 1、2 条**继续有效**，第 3 条按新基线改准）：

1. **一个字节都不碰这两个文件。** `.github/workflows/**` 是红线 2；`docker-compose.yml` 不在红线内，
   但**本 plan 没有任何一件 in-scope 的活需要动它**（§3 Non-Goals / 三个 Phase 的 `Targets` 里都没有它）。
   ⚠️ 第 4 轮那句「不许 `git checkout` / `git stash` 掉它们」**在今天没有对象了**（已落盘），
   但**规则本身保留**：执行期若又出现别人的未提交改动，照此办理。
2. **不许把别人的改动一并 commit。** 本 plan 的每一次提交都必须**显式列路径**，
   绝不用 `git commit -a` / `git add -A`。**这一条与工作树干不干净无关，永远有效。**
3. ⚠️ **本文件里所有 `gates.yml:<行号>` 的引用都是 `758b7bc` 之前记的，今天已经全体对不上。**
   第 5 轮实读的当前值（**只作对照，执行期仍须按 §0 第 5 条重取，仍然不认行号**）：

   | 锚点（按注释/字面原文定位） | 本文件旧记 | 第 5 轮实读 @ `c19cf4a` |
   |---|---|---|
   | `COVERED="contracts context experiments fixtures gates routing tools unit"` | `:560` | **`:597`** |
   | `- run: pip install pytest certifi`（`unit-and-contracts` 的） | `:530` | **`:567`** |
   | `run: python3 -m pytest tests/unit -q` | `:532-533` | **`:570`** |
   | `run: ruff check agenerp tests/unit …`（`lint` job） | `:609` | **`:646`** |
   | `# 作用域三个目录逐字照抄 …` | `:603` | **`:640`** |
   | `# 这几个目录由 loop 写在红线外，接进 CI 属红线 2，故由人做。` | `:542` | **`:579`** |
   | `# 判据自身的判据：…` | （第 ⑦ 步上方） | **`:528` / `:592` 两处** |
   | `# job 退 1。配上之后它走答案面，与起栈步同一套变量。` | `:304-310` | **`:321`** |
   | `# 于是 8 条红。摘掉它能让 CI 变绿，但那是**把判据调整到迁就环境**，` | `:275-279` | **`:293`** |

   ⚠️ **这张表本身也会过期** —— 它证明的不是「行号是多少」，而是「**行号会漂，别信它**」。

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
- ⚠️ **计数口径写死（第 3 轮独立评审补，起草期与前两轮都没把它说开）**：上面数的**十种是「来源」**，
  **不是十个可分辨的状态码** —— `502` 出现两次（服务端「上游模型坏了」与反代「`agenerp-serve` 不在」），
  而**面板只看得见状态码，看不见它是谁回的**。
  ⇒ **面板侧可分辨的码只有九个**：`400/401/403/404/405/500/502/503/504`，**加 `200`，加一条兜底态**。
  ⚠️ **两个 502 合并成同一态是正确行为，不是缺陷** —— 想把它们分开，只能靠嗅响应体
  （服务端 502 回 JSON、反代 502 回默认 HTML），而 `H8c` / `M11` 明令禁止兜底路径假设响应体形态。
  ⇒ **`H8` 的「两两全等比较必须全部为假」按这九个码 + `200` 判，共 10 条**；
  按十种来源判是**不可满足**的（两个 502 必然全等），会把正确行为判成缺陷。

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

### 1.4b ⚠️ 第二处正面冲突（第 4 轮独立评审实读新提）：断言体住进 `tests/unit/` 会在 **runner 上炸**，而且**不是** §1.4 那条红

`.github/workflows/gates.yml`（`HEAD` `d02b208` 的 `:530`）逐字 `- run: pip install pytest certifi`
—— `unit-and-contracts` 这个离线 job **只装 pytest 与 certifi**，
其第 ① 步（同 `HEAD` `:532-533`）跑 `python3 -m pytest tests/unit -q`。
⚠️ **行号按 `HEAD` 记；执行期按 §0.6 重取**（评审期工作树里那份 `gates.yml` 有人侧未提交改动，行号已漂移）。
⇒ **runner 上没有 `playwright`、也没有 `pytest-playwright`。**

⇒ 断言体 `tests/unit/test_desk_sidebar_body.py` 一旦**用了 `pytest-playwright` 插件提供的 fixture**
（`page` / `browser` / `context` / `browser_type` …）或**在模块顶层 `import playwright`**，
runner 上的结果是 **`fixture 'page' not found` / `ModuleNotFoundError` —— 那是 `error`，不是 `skip`**
⇒ **今天绿着的 `unit-and-contracts` 会红。**

⚠️ **这与 §1.4 那条红是两件事，不许混成一件**：§1.4 那条是「判据自身的判据」按设计报警、由人接进 CI 即消；
这一条是**本 plan 自己把一个绿 job 弄红**，没有任何守卫要求它发生，**属于纯回归**。
而 §1.4 的三重代价 (i)(ii)(iii) 与 §11 第一条**都没有覆盖它**。

⇒ **写死约束（`D-d-3` ④ 与 Phase 3 落实）**：
1. 断言体**不许**依赖 `pytest-playwright` 提供的任何 fixture，也不许依赖它的任何 CLI 选项（`--headed` / `--browser` …）；
2. 浏览器的启动与关闭由**断言体自己的 fixture** 承担，`import playwright` **写在那个 fixture 体内**；
   `ImportError` 在 `tests/unit` 那一轮 `skip`、经加载器收严后在 `tests/ui` 那一轮 `fail`（`D-d-3` ②）；
3. **可执行验证（不是承诺，是一条命令）**：
   `python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`
   —— `-p no:playwright` 关掉该插件，**等价模拟 runner 上没装它**；
   **必须 exit 0、全部 `skipped`、零 `error`**。这条进 Phase 3 的 Proof、Exit Criteria 与 §10。

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

⚠️⚠️ **本节的标题仍然成立，但它下面这句前提已经反了 —— 第 5 轮独立评审实测改准，不留旧文**：

> ~~`gates-l2-live` 起栈时一个 AI 变量都不配 ⇒ `/agenerp/explain` 走 **503**。~~

**今天（`c19cf4a`）的事实正相反**：`e3afd77` 已把 `AGENERP_LLM_BASE_URL` / `API_KEY` / `MODEL`
三个 secret 配到 `gates-l2-live` 的**起栈步**上（`gates.yml` 第 5 轮实读 `:279-286` 那个
「起栈（配上 AI 变量 —— 答案面那条门禁要的是服务容器的环境）」步），
且 `docker-compose.yml:65` 会把它们送进 `agenerp-serve` 容器。
⇒ **判定环境里 `/agenerp/explain` 现在会真调模型、走答案面，不再恒 503。**

**但本节的结论一个字不改，而且理由更强了**：正因为「配没配 AI 变量」**在人手里、还会来回变**
（`e3afd77` 之前是不配，之后是配上；fork 的 PR 又拿不到 secret ⇒ 那种 run 上仍回 503，
`gates.yml` 那段注释逐字「**这是预期，不是故障**」），
**任何把某一个具体状态码钉死进断言的判据都是环境相关判据，早晚红在环境上而不是红在缺陷上。**
如果侧边栏的判据只在「真答出来了」时才成立，那它在 fork PR 的 run 上**恒红**；
只在「503」时才成立，那它在配了 secret 的 run 上**恒红**。两头都是重蹈 P1.8a 那条覆辙。

⇒ 本 plan 的判据主线**建在「不需要模型答对」的那一半上**：⌘K 唤起 → 面板出现 → 带上当前单据上下文 →
**浏览器自动把 `sid` 带到 `/agenerp/explain`**（这一跳成立的直接证据是「回的**不是 401**」）→
面板把**实际拿到的那个码**渲染成**可分辨的、非空的**态。
**这一整条链上没有一个环节需要 AI 变量、需要烧 token、需要模型答对。**

⚠️ **但判据不许把「一定是 503」写进断言 —— 独立评审实读打回，此处已改准。**
判定步与起栈步**都已经配上** `AGENERP_LLM_*` 三件套（第 5 轮实读 `gates.yml:321` / `:279-286`），
注释逐字「**配上之后它走答案面**」⇒ **人已经把它修到「不是 503」了**（`e3afd77`，**不再是「正在修」**）。
把 503 钉死进断言，等于写一条**会因为环境变好而变红**的判据，
而 `gates.yml`（第 5 轮实读 `:293`）点名禁止的正是「把判据调整到迁就环境」这类动作的同一族。
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
**① 仍敞着，但红因已经完全换了一批 —— 第 5 轮独立评审实读改准，旧文不留**：

> ~~那条门禁最后一次实跑是 `1 failed, 5 passed`，红在断言体 `:223` 那条 503 分支的 `pytest.skip` 上。~~

**人已经把那条红查到根并修掉了**（`e3afd77`，commit message 逐字）：根因**不是模型答错、也不是那条 skip 本身**，
而是**变量名错了** —— 服务读 `AGENERP_LLM_BASE_URL`，而 compose 与 CI 传的都是 `AGENERP_LLM_ENDPOINT`，
「**服务因此永远拿不到端点**」⇒ 恒回 503 ⇒ 断言体在 503 分支上 skip。修完**本机 `6 passed in 48.87s`**。

**但那条门禁在 CI 上今天仍然红，红在另外两条上**（`758b7bc` commit message 逐字，人自己记的）：
`test_no_response_through_the_front_ever_echoes_the_sid`（**新红**）与
`test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to`，而**本机同一命令是 6 passed**。
人写死了第一条为什么要紧：「『响应绝不回显 `sid`』是**安全面**的判据，
它在服务开始真答之后才红，**不排除是某条错误路径把 `sid` 带了出去**」——
`758b7bc` 那个失败取证步就是为了不靠猜回答它。

⚠️ **这对本 plan 意味着两件事，都要说死**：
① **本 plan 的立场不变**（下一段），**不因为「本机 6/6」就声称工作项 10 已闭合** —— 它在 CI 上仍是红的，
且红在一条**安全面**判据上；② ⚠️ **那条新红与本 plan 的交付面在同一条链上** ——
它查的是「响应里会不会回显 `sid`」，而本 plan 要做的正是**把面板渲染成可见文本**。
⇒ **写死一条约束**：面板**任何一态都不许把响应体原样倾泻到 DOM 里**（`innerHTML = JSON.stringify(resp)` 这类），
渲染只取 §1.3 那四个已知键与状态码本身。**否则本 plan 有可能把那条正在被调查的安全面缺陷复制到界面上。**
这条落进 Phase 2 第 ⑤ 项与 `H8` 的判定口径（见该两处的 ⚠️ 标注）。

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
2. **失败形态一个都不许渲染成空白**：§1.3 那十种来源折成的**九个可分辨的码**各自渲染成**可分辨的、非空的**文案，
   **且必须有一条兜底态**接住**未枚举**的码（含将来新增的）；**不许停在永久 spinner** 上。
3. **`tests/ui/test_sidebar.py` 真的退 0** —— 用**真浏览器**驱动**真活栈**，
   **零 skip**（§1.6），且**不需要任何 AI 变量**（§1.7）。
4. **第一次直接观测**「浏览器把 `HttpOnly` 的 `sid` 自动带到 `/agenerp/*`」（§1.8）。
5. **不回归**：零依赖启动门禁仍绿 · `check_expected_red.py` 仍退 0 · `tests/unit` 只增不减 ·
   ⚠️ **`unit-and-contracts` 在「只装 `pytest certifi`」的 runner 上仍全绿**（§1.4b —— 断言体住进 `tests/unit/`
   却依赖驱动时，那里出的是 `error` 不是 `skip`；这一条由 `-p no:playwright` 那条命令实证，不靠承诺）·
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
- **AI 变量**：**本 plan 一个都不需要配**（§1.7）。
  ⚠️⚠️ **但「不需要配」≠「一定没配」—— 第 5 轮独立评审实读改准，旧文那句无条件的「零 token 成本」是错的**：

  > ~~⇒ 本 plan 的活体取证**零 token 成本**。~~

  `e3afd77` 之后 `docker-compose.yml:65` 是 `AGENERP_LLM_BASE_URL: ${AGENERP_LLM_BASE_URL:-${AGENERP_LLM_ENDPOINT:-}}`
  ⇒ **起栈时你 shell 里有什么，`agenerp-serve` 容器里就有什么**。
  而人侧刚刚在本机跑通过 `6 passed in 48.87s`（`e3afd77`）⇒ **执行者的 shell 里很可能正好是配着的**。
  ⇒ **`H6` / `H9` / `M5` 那一次「未打桩的真请求」会真的调模型。** 成本与耗时**照实写死**：
  一次解释**中位约 11 万 token**（`gates.yml` 那段注释逐字，P1.0 第二轮 12 次实测）、
  墙钟**约 50 秒**（`e3afd77` 实测 6 条 48.87 秒）。
  ⇒ **正确形态是「先测再说，不清环境」**（`H7b`，与 §1.7 / `H7` 的「不许清环境重跑」同一条纪律）：
  §0 第 6 条先数一遍变量、`H7b` 决定走哪一支，**成本落进证据文件，不假装它是零**。
  **无论走哪一支，本 plan 都不新增任何 AI 变量、不改 compose、不改 CI。**
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
| `H2b` | ⚠️ **浏览器怎么够到那个站点**（第 4 轮独立评审新提）：compose 栈**按 Host 分站**（`docker-compose.yml:333` `FRAPPE_SITE_NAME_HEADER: frontend`，nginx `server_name ${FRAPPE_SITE_NAME_HEADER}` + `proxy_set_header Host $host`），而 `tests/unit/test_explain_service_body.py:114` 逐字「**站点名决定 Host 头，compose 栈按 Host 分站**」并显式发 `Host: frontend`。**浏览器访问 `http://127.0.0.1:18080/app` 发出的 Host 是 `127.0.0.1:18080`，且 Chromium 不允许用 `set_extra_http_headers` 覆盖 `Host`** ⇒ 这一跳到底落不落到 `frontend` 站，**本仓无实证**。探法：真浏览器打开 `http://127.0.0.1:18080/login`，看拿到的是登录页还是站点解析失败 | 落到 `frontend`（Frappe 在 Host 不匹配任何站点目录时回落到 `currentsite.txt` 的默认站，而 `create-site` 用了 `--set-default`，`docker-compose.yml:186/205` 记着这一点） | ⚠️ **回落不成立时的出路现在就写死，不留执行期自选**：启浏览器时加 Chromium 参数 `--host-resolver-rules="MAP frontend 127.0.0.1"` 并把基址改成 `http://frontend:18080` —— 这样浏览器发出的 Host 就是 `frontend`，**与既有断言体那一跳同口径**，且**不改本机 `/etc/hosts`、不碰站点配置、不碰 nginx**。两条都不成立 ⇒ 照实记进探测记录并交人（**不许**改 compose / nginx 去迁就判据，那是 `gates.yml:275-279` 点名禁止的同一族动作） |
| `H3` | Frappe v15 Desk **自己**有没有占用 `Cmd/Ctrl+K`：真登录进 `/app`，按下该组合键，观测有无原生响应 | **不确定，这正是要测的**。倾向：Frappe 的 awesomebar 走 `Ctrl+G`，`K` 很可能空着 | 已被占用 ⇒ **不抢**（抢了就是破坏 Desk 既有行为）。**次选键现在就写死：`Cmd/Ctrl+Shift+K`**（不留执行期自选的口子），并把「WBS 那行写的是 ⌘K」这处偏差**显式登记**到 §11 + `STATE.md`，由人裁 |
| `H4` | 当前单据上下文从哪儿取最稳：URL 路径解析 · `frappe.get_route()` · `cur_frm?.doc`，三者在同一张单据页上各取一次 | 三者**都能取到**且 `doctype`/`name` 一致 | **优先级现在就写死：URL 路径 > `frappe.get_route()` > `cur_frm.doc`**（理由：URL 是浏览器地址栏里看得见的、不依赖任何 Frappe 内部对象，升级 Frappe 时最不容易悄悄变形；后两者是内部 API）。不一致 ⇒ 按该优先级取，并把不一致照实记进落点节；三者**都取不到**（例如在 Workspace 页而非单据页）⇒ 那是**合法的「无单据上下文」态**，请求体**不带** `doctype`/`name`（§1.3 逐字「必须同时给或同时不给」） |
| `H5` | 带真登录会话 `GET /app/<某真单据>`，看注入的 `<script src="/agenerp/desk.js">` 在不在、几次 | 在，**恰好 1 次**，且在 `</body>` 之前 | 不在 ⇒ 第 1 个 plan 的接缝回归了，**先修回归再往下**，不许绕过去 |
| `H6` | **浏览器**（不是 curl）从 `/app` 页面发出的 `POST /agenerp/explain`，服务端看到的 `Cookie` 里**有没有 `sid`**。⚠️ **观测方式写死：`page.expect_response` 观测那一次「未打桩」的真请求** —— `page.route` 打桩的那些请求**根本到不了服务端**，从它们身上取不到这个证据 | **有** —— 直接证据是回的**不是 401**（`handle_explain` 的顺序是 `_sid_from_cookie` → `parse_request` → `_resolve_identity`(401) → `config_factory`(503)，⇒ **任何非 401 的码都蕴含「站点已经认到人」**）。⚠️ 这是本仓第一次直接观测，此前只有推断 | 没有 ⇒ **这是一个真发现，不是本 plan 的失败**：说明 `HttpOnly` + 同源那套推断是错的。**当场停下**，把实测写进 `STATE.md` §3 needs-human 并交人重裁 D-19 的同源假设 |
| `H7` | 面板发出的那次真请求回什么码。⚠️ **第 5 轮改准了这一格的题面**：原文写的是「**一个 AI 变量都不配时**」，而配没配今天由 `H7b` 现测决定（`e3afd77` 之后判定环境是**配着**的）⇒ 题面改成无条件的「回什么码」，**「预测」列一个字未动**（§6 的规矩：只填实际、不改预测） | **503**，且体里**指名缺哪个变量**（⚠️ **这是起草期写死的预测，第 5 轮已知它很可能不吻合** —— 照 §6 的规矩**原样保留**，由执行期填实际值并按右列处置。**预测错了要照实记，不许回头改预测**） | ⚠️ **不许清环境重跑**（独立评审打回，此处已改准）：回 200 或别的码时，**照实记下那个码，并断言面板渲染的是该码对应的那一态**。理由 —— `gates.yml:304-310` 的判定步已配了三个 AI secret、注释逐字「配上之后它走答案面」，⇒ 「环境里有 AI 变量」是**人正在推进的正常状态**，为了让断言成立去清环境，与 `gates.yml:275-279` 点名禁止的「把判据调整到迁就环境」是同一族动作 |
| `H7b` | ⚠️ **本机 shell 里到底有没有 AI 变量**（第 5 轮独立评审新增，理由见 §5）：§0 第 6 条那两条命令（`env \| grep -c '^AGENERP_LLM_'`，**只看名字与个数，绝不打值**），在**起栈之前**跑 | **不确定，这正是要测的。** 倾向：**有** —— 人侧刚在本机跑通 `6 passed in 48.87s`（`e3afd77`） | ⚠️ **两支都写死，不留执行期自选，且两支都不许清环境**（同 `H7`）：**(甲) 数出来是 0** ⇒ 服务回 503，取证零 token 成本，照旧走。**(乙) 数出来非 0** ⇒ `H6`/`H9`/`M5` 那一次真请求**会真调模型**：① 把「本轮真实烧掉一次解释（中位约 11 万 token）」**逐字记进证据文件与收口表**，不写成零成本；② ⚠️ **自建 fixture 里那次 `expect_response` 的超时下限写死 ≥ 90 秒**（实测约 50 秒，Playwright 默认 30 秒**会先超时** ⇒ 判据红在超时上、长得像「面板坏了」，而实际是模型在正常作答 —— 这是一条会把人引向错误根因的假红）；③ **只此一次真请求**，其余全部 `page.route` 打桩，**不许为了「多测几遍」重复烧**。**两支都不许改 compose / 不许 `unset` 变量 / 不许加 `AGENERP_LLM_*`** |
| `H8` | **九个可分辨的已枚举码**（`400/401/403/404/405/500/502/503/504`，见 §1.3 计数口径：十种来源里两个 `502` 合并成一个码）**+ 200**，共 **10** 条，用浏览器内 `page.route` 打桩逐个喂给面板 | **各自**渲染出**互不相同**且**非空**的可见文本；**无一停在 spinner**。⚠️ **「互不相同」的判定口径现在就写死**：取面板可见文本，**这 10 条两两全等比较必须全部为假**，**且每一条都含该状态码的字面量** —— 不许留给执行期「人眼看着不一样」。⚠️ **不许把两个 `502` 拆成两条来凑数**（§1.3 计数口径：拆开只能靠嗅响应体，撞 `H8c`/`M11`） | 有两种渲染成同一句话 ⇒ **那是缺陷不是风格问题**（「未认到人」与「模型没配」混成一句，用户与判据都分不出），当场修 |
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

      **裁定写死六条**（①②③ 起草期已有；④⑤⑥ 是第 4 轮独立评审实读先例后补的 —— 起草期那三条**接不上**，
      理由逐条写在下面，不是加码）：
      ① **加载器在 `exec_module()` 之前自己 `import playwright`**，失败即 `pytest.fail`（不是 skip、不是 `importorskip`）；
      ② **断言体里禁用模块级 `pytest.importorskip` 与模块级 `pytest.skip`** —— 驱动导入与活栈探活
      **一律放进 fixture**，在 fixture 里**只调 ④ 那个间接层**，这样才落在收严的作用域内；
      ③ **`tests/unit/` 那份允许 skip、`tests/ui/` 那份必须 fail，这个取舍差是有意的**
      （日常那一轮不该因为没起 docker 就整轮红），**必须在落点节 §7.23 写清楚，不许含糊成「都一样」**。

      ④ ⚠️ **收严到底怎么做，现在就写死 —— 起草期这里是个洞**：③ 要求「`tests/ui` 那份必须 fail」，
      而 ①② 只管「skip 落在导入之后」，**根本没给出把 skip 变成 fail 的机制**；
      同一条 `D-d-3` 又把先例那个机制（`_BODY.pytest.skip = ...`）判为**不复制**
      ⇒ 起草期的三条**互相接不上**，执行期会被逼回去抄那个被自己否掉的写法。
      **补死**：断言体在**模块级**暴露一个**自己的**间接名（形如 `_unavailable(reason)`），
      默认实现就是 `pytest.skip(reason)`；**断言体里所有「跑不了」的出口一律只调它，不许直调 `pytest.skip`**；
      加载器在 `exec_module()` 之后**只重绑这一个名字**（`_BODY._unavailable = pytest.fail`）。
      ⚠️ **重绑的是断言体模块自己的属性，不是 `pytest` 模块的属性** ——
      先例那种 `_BODY.pytest.skip = ...` 改的是**全局 `pytest` 模块**、属进程级污染
      （**本 plan 不去改那份先例**，红线 1）；本形态没有这个副作用，且**新增的 skip 出口自动受管**
      （与先例同一条好处，写在那份的注释里）。
      ⑤ ⚠️ **加载器必须把断言体里的测试函数逐个重绑进自己的模块命名空间** —— 实读先例
      `tests/gates/test_explain_service_live.py` 结尾**逐条列了六个** `test_... = _BODY.test_...`，
      **起草期把这一步整个漏了**。漏掉的后果不是少跑几条，是
      **`pytest -m live tests/ui/test_sidebar.py` 一条都收集不到 ⇒ 退出码 5**（`no tests collected`），
      而 Exit Criteria 写的是「exit 0」⇒ **必然红在一个与实现无关的地方**。
      配套守卫写死（离线、进 CI）：**加载器重绑的名字集合，必须等于断言体里 `test_` 开头的函数名集合**，
      缺一即红 —— 落在 `tests/unit/test_desk_sidebar_static.py`（Phase 3 追加），**不是靠人眼数**。
      ⑥ ⚠️ **断言体不许依赖 `pytest-playwright` 插件的任何 fixture**（`page` / `browser` / `context` /
      `browser_type` …）与它的任何 CLI 选项 —— 完整理由与那条可执行验证命令见 **§1.4b**
      （runner 上只装 `pytest certifi`，用了就是 `error` 不是 `skip`，**今天绿着的 `unit-and-contracts` 会红**）。
      ⚠️ 这一条与 ② 是**两件事**：② 管「skip 出现在什么时机」，⑥ 管「fixture 从哪来」；
      ② 满足了 ⑥ 照样能违反（自己写的 fixture 里 `import playwright` 是对的，
      **函数签名里写 `page` 参数就是错的**）。
      - Skill: `none`
- [ ] **`D-d-4` 快捷键**（`Decision`，依赖 `H3` 的实际值）：`Cmd/Ctrl+K` 与 Desk 原生绑定是否冲突、
      冲突时选谁。**不抢已被占用的键**（见 `H3` 的「不吻合怎么办」）。
      同时裁死**关闭方式**（至少 `Esc` + 再按一次同一组合键）与**焦点归还**
      （关闭后焦点回到唤起前那个元素 —— 不还焦点在单据页上是实实在在的可用性缺陷）。
      - Skill: `none`
- [ ] **Proof**：探测记录 `docs/analysis/2026-08-25-1743-desk-sidebar-probe.md` 落盘，
      含 `H1`–`H5` 的命令原文 + 退出码 + 实际值，与四条裁定的完整理由。
      - Skill: `none`

**⚠️ Phase 1 的四条停机分支（触发即停，写进 `STATE.md` §3 needs-human，不自行绕过）**
（iteration 1 新增了第 4 条之后这里仍写着「三条」，第 3 轮独立评审改准）：

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
      ⑤ 按 §1.3 计数口径的**九个可分辨的已枚举码 + 200**（共 10 条）各渲染一种可分辨的非空态（`H8`），
      **外加一条兜底态**接住未枚举的码与网络层失败（`H8b`）—— **没有一条路径通向空白或永久 spinner**；
      ⚠️ **同时写死一条禁令（第 5 轮独立评审补，理由见 §1.8b）**：
      **任何一态都不许把响应体原样倾泻进 DOM** —— 禁 `innerHTML = <整个响应>`、
      禁 `JSON.stringify(resp)` 直接渲染、禁把响应头或 `document.cookie` 写进面板。
      渲染**只取** §1.3 那四个已知键（`user` / `answer` / `accepted` / `cost`）与**状态码本身**；
      兜底态只渲染**状态码 + 一句固定文案**，**不碰响应体**（这与 `H8c` 要求的「不假设响应体是 JSON」是同一条约束的两面）。
      **理由不是洁癖**：P1.8a 那条门禁今天在 CI 上正红在
      `test_no_response_through_the_front_ever_echoes_the_sid`（「响应绝不回显 `sid`」，安全面，人尚在查因）——
      **面板把响应体原样铺开，等于把一个正在被调查的疑似缺陷从接口面复制到界面上。**；
      ⑥ **保留既有资产判据钉着的四格**：`len>200` · `agenerpDesk` · **`Object.freeze`** · **结尾逐字 `)();`**
      （`test_desk_asset_route.py:165-168`）。
      ⚠️ 面板要挂状态时最容易顺手去掉的是 `Object.freeze` —— **挂状态请另起一个不冻结的内部变量，
      别把标记对象解冻**。
      ⚠️ **结尾那格是「判据钉死的形状」，不是风格偏好**（独立评审 iteration 2 补）：
      面板要注册 `document.addEventListener`、要拆成多个内部函数，收尾很容易在格式化时变成别的写法。
      **整份资产必须仍是一个以 `)();` 逐字收尾的 IIFE。**
      `version` 往上走一格、`plan` 改成本 plan 号。
      - Skill: `none`
- [ ] **`Add`** 判据 `tests/unit/test_desk_sidebar_static.py` —— **离线、零浏览器**，守**五**件事（第 5 轮独立评审把「响应体不外泄」补成第 ⑤ 件）：
      ① 资产里出现的请求路径与 `app.py` 的 `EXPLAIN_PATH` **各读一次再比**（**不写第三个字面量**，沿用 §7.22 口径）；
      ② 资产里出现的请求体键名集合 ⊆ `app.py` 的 `ALLOWED_BODY_KEYS`，**且与五个越权键的交集为空**
      （两个集合都从 `app.py` 读，不在判据里抄）；
      ③ `window.agenerpDesk` 标记仍在；
      ④ **九个可分辨的已枚举码的字面量在资产里各出现过**（§1.3 计数口径；`502` 只需出现一次）
      —— 挡「只写了 200 分支」的半成品；
      ⑤ ⚠️ **响应体不外泄（第 5 轮独立评审补，对应 Phase 2 ⑤ 那条禁令与 §1.8b）**：
      资产源码里 **`JSON.stringify(` 与 `innerHTML` 零命中**，且 **`document.cookie` 零命中**。
      ⚠️ **这三条同样是文本下限、不证运行时行为**（与本判据其余各条同口径）：
      它挡的是「整份响应被原样铺开」这个**最粗的**形态，挡不住逐字段拼接出来的等价泄漏；
      **运行时那一半由 `M16` 与 `H8` 的「每一条只含该码字面量 + 已知键」承担。**
      ⚠️ 用 `textContent` / `createTextNode` 建 DOM 是本条留下的正路，**不是变通**。
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
- [ ] **`Proof`** `ruff check` 跑一遍**现有七个目录**（`agenerp tests/unit tests/contracts tests/tools tests/routing
      tests/context tests/experiments`）仍 exit 0。⚠️ **本 Phase 不把 `tests/ui` 加进参数** ——
      那个目录要到 Phase 3 才建，此时传进去 ruff 会因路径不存在直接报错
      （第 3 轮独立评审补：前两版把它写在 Phase 2，会造一条假红）。
      `tests/ui` 从 **Phase 3 起**进参数，见 §10 verification 那条七命令清单。
      ⚠️ `ruff` 的 `exclude` 只排除 `tests/gates`，**`tests/ui` 建起来之后会被真扫**，别指望它被跳过。
      - Skill: `none`
- [ ] **`Proof`** `python3 -m pytest tests/unit -q` 只增不减；`check_expected_red.py` 仍 exit 0。
      - Skill: `none`
- [ ] **`Add`** 落点节 §7.23 补「渲染状态机」那一格：**九个可分辨的已枚举码 + 200 + 一条兜底态**的映射表
      （并写明 §1.3 那条计数口径：十种来源 → 九个码，两个 `502` 合并且**合并是正确的**），
      与 §1.3 的服务端表**逐条对齐**。
      ⚠️ **这张表必须写成「开放枚举 + 兜底」，不许写成封闭枚举** —— 它是要落进 owner doc 的**持久制品**，
      把封闭枚举写进架构文档，等于把「真实 500/504 渲染成空白」这个失败形态**固化成规范**
      （第一版正是在这里漏改，独立评审 iteration 2 打回）。
      同时写明维护义务：**服务端加一种码，这张表跟着加一行；但兜底态在任何时候都不许删。**
      - Skill: `none`

Exit Criteria:

- [ ] ⌘K（或 `D-d-4` 裁定的键，冲突时写死为 `Cmd/Ctrl+Shift+K`）唤起 / 关闭 / `Esc` / 焦点归还四条行为**都在代码里**，不是只有函数签名
- [ ] 失败模式说清：**九个可分辨的已枚举码各自的可见态互不相同、非空、不 spinner**（与 `200` 一起共 10 条两两不等），**且兜底态接得住未枚举的码**；成功模式：200 时渲染 `answer` 与 `cost`
- [ ] ⚠️ **响应体不外泄**：面板任何一态都不把响应体原样倾泻进 DOM（渲染只取 §1.3 四个已知键 + 状态码本身），判据⑤ 的三条源码守卫（`JSON.stringify(` / `innerHTML` / `document.cookie` 零命中）全绿（§1.8b / R9）
- [ ] 新判据 `tests/unit/test_desk_sidebar_static.py` 全绿；既有 22 条**零改动**（`git diff` 证）
- [ ] `docs/architecture/module-boundaries.md` §7.23 的状态机表落地
- [ ] `docs/logs/2026/08-25.md` 追加 Phase 2 条目

### Phase 3 — `tests/ui/test_sidebar.py` 活体门禁 + 变异自查 + 交接

Status: planned
Targets: `tests/ui/test_sidebar.py`（新建，加载器）· `tests/unit/test_desk_sidebar_body.py`（新建，断言体）·
**`tests/unit/test_desk_sidebar_static.py`（Phase 2 建的那份，本 Phase **追加**四条源码级守卫；第 4 轮独立评审补）** ·
`pyproject.toml`（`ui` extra）· `docs/evidence/p1-desk-sidebar/README.md`（新建）·
**`docs/context/project-context.md`（第 52 行 Lint / static check 那一格的作用域漂移，`Fix`，见本 Phase 交接项 (5) 下方；
第 3 轮独立评审补 —— 前两轮把这件事写进了正文却漏进 Targets）**
Skill: `closure-audit-prompt.md`（仅收口那一步）

- Item Types: `Proof`（5/7 项是 `Proof`）
- Prereqs: Phase 2 全部完成；活栈按 §5 起好并**真登录**过一次

- [ ] **`Add`** 断言体 `tests/unit/test_desk_sidebar_body.py`：真浏览器、真登录、真 Desk 页面，
      覆盖 `H6` / `H7` / `H8` / `H8b` / `H8c` / `H9` 六格。
      **驱动取不到或活栈够不到 ⇒ 在 fixture 里调 `D-d-3` ④ 那个间接层**（默认 `pytest.skip`），
      **模块级一律不 skip、不 `importorskip`**（`D-d-3` ①②④）。
      ⚠️ **不许出现 `pytest-playwright` 的 fixture 名（`page` / `browser` / `context` / `browser_type`）
      作为测试函数或 fixture 的参数**（`D-d-3` ⑥ / §1.4b）—— 浏览器由**本文件自己的 fixture** 起，
      `import playwright` 写在那个 fixture 体内。⚠️ 顺带写死：`H2b` 若判定要走
      `--host-resolver-rules`，那个参数也在这个自建 fixture 里给。
      ⚠️ `H6` 与 `M5` 的证据**只能取自那一次「未打桩」的真请求**（`page.expect_response`）——
      `page.route` 打桩的请求到不了服务端，从它们身上取不到「服务端看到了 `sid`」。
      - Skill: `none`
- [ ] **`Add`** 加载器 `tests/ui/test_sidebar.py`：`pytestmark = pytest.mark.live`；
      **先自己 `import playwright`（失败即 `pytest.fail`），再按路径加载断言体**，
      随后**重绑断言体的 `_unavailable` 间接层为 `pytest.fail`**（`D-d-3` ④ —— **不动 `pytest` 模块本身**），
      **再把断言体里每一个 `test_` 函数逐条重绑进本模块命名空间**（`D-d-3` ⑤ ——
      **漏了这一步就是 `no tests collected` / 退出码 5**）。⚠️ **零 skip 分支**（§1.6）。
      ⚠️ **basename 必须与断言体那份不同**（本 plan 是 `test_sidebar.py` vs `test_desk_sidebar_body.py`，**已不同**）
      —— `tests/` 下没有 `__init__.py`，同名 basename 会让整轮 `pytest` `import file mismatch` 收集失败
      （`tests/unit/test_explain_service_body.py` 文件头逐字记着这条，第 4 轮独立评审实读带回，**只是钉住现状，不需要改名**）。
      - Skill: `none`
- [ ] **`Add`** 给 `tests/unit/test_desk_sidebar_static.py` **追加四条源码级守卫**（离线、零浏览器、零 JS 运行时；
      第 4 轮独立评审补，全部是**纯文本判定**，与该文件既有口径同族）：
      ① 断言体源码里 **`pytest.skip(` 与 `pytest.importorskip` 零命中**（出口只许走 `_unavailable`，`D-d-3` ②④）；
      ② 断言体**模块顶层**没有 `import playwright` / `from playwright`（`D-d-3` ⑥ / §1.4b）；
      ③ 断言体里没有以 `page` / `browser` / `context` / `browser_type` 命名的**测试函数或 fixture 参数**
      （挡「顺手用了 `pytest-playwright` 的 fixture」）；
      ④ **加载器重绑的名字集合 == 断言体里 `test_` 开头的函数名集合**（`D-d-3` ⑤ ——
      挡「漏重绑 ⇒ `no tests collected`」与「漏重绑一条 ⇒ 静默少跑」）。
      ⚠️ **同 Phase 2 判据④ 的口径：这四条是文本下限，不证运行时行为。**
      运行时那一半由本 Phase 的 `-p no:playwright` 实跑与 `M13`–`M15` 承担，**这一份不承担、也不假装承担。**
      - Skill: `none`
- [ ] **`Proof`** ⚠️ **模拟 runner 上没装驱动**（§1.4b 那条可执行验证）：
      `python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`
      ⇒ **必须 exit 0、全部 `skipped`、零 `error`**。命令原文与退出码入证据文件。
      **这条不退 0 ⇒ 今天绿着的 `unit-and-contracts` 会在下一次推送时红，而那是纯回归、不是设计内的代价**
      （与 §1.4 那条红分开算，见 §1.4b）。
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
- [ ] **`Proof`** **变异自查**：至少 `M1`–`M16` **十六**条，逐条施加、逐条确认**被打红**、逐条复原并 `sha256` 校验 `RESTORED OK`。
      写死的十五条：`M1` 删掉快捷键注册 · `M2` 把 503 分支渲染成空字符串 · `M3` 把 401 与 503 渲染成同一句话 ·
      `M4` 请求体里偷偷加一个 `user` 键 · `M5` 把 `credentials` 改成 `omit`（`sid` 不再自动带）·
      `M6` 把请求路径改成 `/agenerp/explain2` · `M7` 把加载器里的 `skip→fail` 收严去掉 ·
      `M8` 把 `window.agenerpDesk` 标记删掉 · **`M9` 删掉渲染状态机的兜底分支**（`H8b` 那格必须打红）·
      **`M10` 把断言体里的 fixture 级 skip 改回模块级 skip**（`D-d-3` ①② 那条必须打红 ——
      这一条专挡「绿着的、不存在的门禁」那个失败形态）·
      **`M11` 让兜底分支假设响应体是 JSON**（`H8c` 那格必须打红 —— 专挡「真 nginx 502 上 `r.json()` 抛出、
      面板空白，而所有打桩判据全绿」）·
      **`M12` 把资产结尾从 `)();` 改成 `})();\n// end`**（`test_desk_asset_route.py:168` 必须打红 ——
      现有 `M1`–`M11` 没有一条守它）。
      **`M13` 把断言体改成用 `pytest-playwright` 的 `page` fixture**（或在模块顶层 `import playwright`）
      ⇒ 上面那条 `-p no:playwright` 必须打红，且源码守卫 ②③ 必须打红
      —— 专挡「本机绿、runner 上 `unit-and-contracts` 红」这个纯回归（§1.4b）·
      **`M14` 从加载器里删掉任意一条 `test_` 重绑** ⇒ 源码守卫 ④ 必须打红
      —— 专挡「漏重绑 ⇒ `no tests collected` / 静默少跑」（`D-d-3` ⑤）·
      **`M15` 在断言体里直调一次 `pytest.skip(...)` 绕过 `_unavailable`** ⇒ 源码守卫 ① 必须打红
      —— 专挡「收严间接层被绕过 ⇒ 门禁上又出现 skip」（`D-d-3` ④）。
      **`M16` 把某一态改成把整个响应体倾泻进面板**（`el.innerHTML = JSON.stringify(resp)`）
      ⇒ **Phase 2 判据⑤ 必须打红**（第 5 轮独立评审补）——
      专挡「面板把正在被调查的 `sid` 回显缺陷从接口面复制到界面上」（§1.8b / Phase 2 ⑤ 的禁令）。
      ⚠️ **这一条的打红面是离线源码守卫，不是浏览器** —— 因此它**不受**「本机有没有 AI 变量」影响，
      `H7b` 走哪一支都要施加它。
      ⚠️ **`M5` 与 `H6` 同理**：`credentials: "omit"` 只有在**未打桩的那条真请求断言**上才打得红，
      打桩那批对它无感 —— **变异表里写死这一句，免得事后把「没打红」解释成「不需要」。**
      ⚠️ **打不红的照实记在表里**，当场补断言后复跑；补不出来就**保留「这条守不住」的记录**，不许改成「全打红」。
      - Skill: `none`
- [ ] **`Fix | Follow-up` 交接**：往 `docs/masterplan/STATE.md` §3 **追加**（只追加）一条 needs-human。
      ⚠️ **起草期把它写成「加一行 `COVERED` 就好了」是错的**（独立评审实读打回）——
      `check_expected_red.py:73-74` 的判定面写死 `tests/gates`，加 `COVERED` **只让第 ⑦ 步不红，
      不会让这条门禁在 CI 上跑起来一次**。交接必须**逐件写清人要做的六件**
      （第 4 轮独立评审把原第 (5) 件拆成 (5a)(5b)，理由见该件下方）：
      **(1)** 把 `ui` 加进 `unit-and-contracts` 第 ⑦ 步的 `COVERED`（否则那一步红）；
      **(2)** 在 `gates-l2-live` 里装 `ui` extra 并 `playwright install --with-deps chromium`；
      **(3)** 在 `gates-l2-live` 里加一条 `python3 -m pytest -m live tests/ui/test_sidebar.py` 的 step
      —— **没有这一步，新门禁在 CI 上零覆盖**；
      **(4)** 那条 step 照抄 `gates.yml:492-495` 既有的**零 skip 断言**形态（否则 skip 又变成静默出口）；
      **(5a)** `lint` job（`gates.yml:609`）的 ruff 参数是七个目录的字面量 ⇒ 加上 `tests/ui`，否则它在 CI 上零 lint 覆盖；
      **(5b)** `gates.yml:603` 那句注释逐字写着「**作用域三个目录**逐字照抄 `docs/context/project-context.md` 的
      Lint / static check 一行」—— 「三个目录」今天就已经是错的（`:609` 是七个），本 plan 把真相源改准成八个之后**更错**。
      ⇒ 那句注释要跟着改准。**它在 `.github/workflows/**` 里，红线 2，loop 不碰。**
      ⚠️ **交接项 (5) 有一件邻接活是 loop 自己该做的，不许一起推出去**（独立评审 iteration 2 指出）：
      `gates.yml:603` 逐字声明 lint 作用域「照抄 `docs/context/project-context.md` 的 Lint / static check 一行」，
      而那一行（`project-context.md:52`）**今天还是三个目录、`gates.yml:609` 已经是七个 —— 本就已漂移**
      （行号经第 3 轮独立评审实读改准，原写 `:604`）。
      ⇒ **本 plan 就地把 `project-context.md` 那一行改准成七个目录并加上 `tests/ui`**（它不在任何红线内），
      否则交接项 (5) 没有真相源可照抄。**这是 `Fix`，不是 follow-up。**
      ⚠️ **但改完之后「漂移」并没有消除，照实说**（第 4 轮独立评审打回一句假陈述）：
      `gates.yml:603` 逐字写的是「**作用域三个目录**逐字照抄……」，改完之后那句「三个目录」**仍然是错的**；
      且真相源变成**八个**目录而 `:609` 是**七个**，两边**仍然不等**。
      ⇒ **交接项 (5) 因此是两件事，一并交人**：(5a) 把 `:609` 的 ruff 参数加上 `tests/ui`；
      (5b) 把 `:603` 那句注释里的「三个目录」改准。**两处都在红线 2，loop 一个字节都不碰。**
      **再加一件需人裁的**：`D-d-4` 若因 `H3` 冲突改成 `Cmd/Ctrl+Shift+K`，与 WBS 第 88 行「⌘K」字面的偏差归人。
      ⚠️ **六件全部落在 `.github/workflows/**` 里 ⇒ 红线 2，本 plan 一个字节都不碰，只写清楚交出去。**
      ⚠️ **交出去之前先读 §0.6**：评审期工作树里那份 `gates.yml` 已有**人侧未提交**的改动，
      交接文字里的行号必须**执行期按注释原文重取**（§0 第 5 条），不许照抄本文件写的数字。
      **同时往 §3 追加一条 `[Proof]` 证据行**（本 plan 的落地 sha + 命令原文 + 退出码）。
      - Skill: `none`

Exit Criteria:

- [ ] `AGENERP_LIVE=1 … pytest -m live tests/ui/test_sidebar.py -q -rs` → **exit 0，零 skip**（命令原文 + 退出码入证据文件），
      **且收集到的条数 > 0 并等于断言体里 `test_` 函数的条数**（`D-d-3` ⑤ —— `no tests collected` 退 5，
      「零 skip」这句话在一条都没跑的情况下也成立，**必须由条数把它钉住**）
- [ ] `python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright` → **exit 0、全 `skipped`、零 `error`**
      （§1.4b —— 证明 `unit-and-contracts` 在无驱动 runner 上不会被本 plan 弄红）
- [ ] `H6` 有**直接观测值**：浏览器发出的请求带上了 `sid`（回的不是 401）—— 本仓第一次
- [ ] `H2b` 有**实际值**：浏览器到底怎么够到 `frontend` 站（默认站回落 / `--host-resolver-rules`），落进探测记录
- [ ] `H7b` 有**实际值**：起栈前 `AGENERP_LLM_*` 的**个数与变量名**（不含值）已记；走了哪一支已记。⚠️ **走 (乙) 支时，「本轮真实烧掉一次解释（中位约 11 万 token）」必须逐字落进证据文件与收口表**，**不许写成零成本**（§5 / R8）
- [ ] 变异表 `M1`–`M16` 逐条有结论（打红 / 未打红 + 处置），全部 `RESTORED OK`
- [ ] 不回归三条全绿；`check_expected_red.py` exit 0；`tests/unit` 只增不减
- [ ] `docs/context/project-context.md` 第 52 行的 Lint / static check 作用域**已改准**：
      从今天的 `ruff check agenerp tests/unit tests/contracts`（三个目录，**实读确认**）
      改成 `gates.yml:609` 那七个目录 **加上 `tests/ui`**（共八个）
      —— 这是 `Fix` 不是 follow-up，**不许跟着交接一起推给人**
- [ ] ⚠️ **同一格里那句「改后 `gates.yml:603` 的『逐字照抄』重新成立」已删除，因为它是假的**
      （第 4 轮独立评审实读打回）：`gates.yml:603` 逐字是「**作用域三个目录**逐字照抄……一个字不加不减」，
      改完之后 ① 那句「三个目录」仍然错、② 文档八个 vs `:609` 七个**仍然不等**。
      ⇒ **残余的两处都落在 `.github/workflows/**`（红线 2）**，
      本 plan **不修、也不假装修好了**，逐字写进交接项 (5) 交人；
      收口文字里**不许**出现「照抄重新成立 / 漂移已消除」这类说法。
      **本 plan 只负责把真相源（`project-context.md:52`）摆正**，让人有得照抄
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
- **R7 · ~~工作树里有别人未提交的活~~ → 已落盘，风险形态跟着变了**（§0.6，第 5 轮实测改准）。
  第 4 轮记的那两处 ` M` 已由人提交为 `e3afd77` + `758b7bc`，**工作树今天干净**。
  ⇒ 原来那三条风险里，「一并 commit」与「`checkout` 掉别人的改动」**今天没有对象了**
  （规则仍保留在 §0.6，供执行期再次出现时用）；**剩下并且变得更重的是第三条**：
  **照抄本文件的 `gates.yml` 行号** —— 两次提交之后**全体漂移**（§0.6 那张对照表逐格实测）。
  处置：§0 第 5 条按注释原文重取，**不认行号**。
  ⚠️ **它不拦本 plan 转 `active`**（人答完 §0.5 第 ① 条即可转）。

- **R8 · 「零 token 成本」这个前提已经被 `e3afd77` 掀掉了**（第 5 轮独立评审新提，§5 / `H7b`）。
  compose 现在会把 shell 里的 `AGENERP_LLM_*` 送进服务容器 ⇒ 那一次未打桩的真请求**可能真调模型**：
  **一次约 11 万 token、约 50 秒**。两条真风险：① 成本被当成零、收口时无人记账；
  ② **Playwright 默认 30 秒超时先于模型返回触发 ⇒ 一条假红，长得像「面板坏了」**，
  而真因是模型在正常作答 —— 这正是本仓反复吃亏的「症状指向错误根因」那一族（`e3afd77` 自己就是一例）。
  处置写死在 `H7b`（先数变量、超时下限 ≥ 90 秒、只跑一次真请求、**两支都不许清环境**）。

- **R9 · P1.8a 那条安全面的红（`…never_echoes_the_sid`）与本 plan 的交付面在同一条链上**（第 5 轮新提，§1.8b）。
  人尚在查因（`758b7bc` 的取证步就是为此加的）。**本 plan 不去修它、不去碰那份门禁**（红线 1），
  但**必须保证自己不把同一个形态复制到界面上** ⇒ Phase 2 ⑤ 的「不许倾泻响应体」禁令 +
  判据⑤ 三条源码守卫 + 变异 `M16`。⚠️ **本 plan 不声称、也不许在收口文字里暗示自己澄清了那条红。**

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

- **Independent draft review iteration 3: `needs revision`（已就地修完）+ 维持 `可以转 active: no`**
  （mission-driver 评审步，2026-08-25）—— 复核前两轮的 14 条阻塞是否真落地，并**不受前两轮结论约束**地重审全文。

  **对前两轮的复核**：iteration 1 的 9 条、iteration 2 的 5 条，**逐条实读活仓确认已落进本文件**
  （含 iteration 2 揪出的「Phase 2 最后一项与 Non-Goals 1 仍写六种」—— 已确认改准为八种 / 十种）。
  §0.5 的两条实测证据**本轮重跑复核过**：`git log --grep=Approved-By` 无一条涉及浏览器驱动、
  `docs/masterplan/STATE.md:868-870` 的状态词是 `[needs-human]`（**不是** `[resolved]`）
  ⇒ **停在 `draft` 的裁定成立，本轮维持。**

  **本轮新提 3 条阻塞 + 3 条次要，全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Blocker** | `H8` 的「两两全等比较必须全部为假」**不可满足**：十种来源里 `502` 出现两次（服务端「上游模型坏了」/ 反代「`agenerp-serve` 不在」），而**面板只看得见状态码** ⇒ 两个 502 必然渲染成同一态，被 `H8` 的处置列判成「缺陷，当场修」；而想把它们分开只能嗅响应体，那又正好撞 `H8c` / `M11` 明令禁止的「兜底路径假设响应体是 JSON」。⇒ 执行期被逼进一个**两条判据互相否决**的死角 | §1.3 新增**计数口径**一格（十种**来源** → **九个可分辨的码** `400/401/403/404/405/500/502/503/504`，两个 502 合并**是正确行为不是缺陷**）· `H8` 改判为「九个码 + `200` 共 10 条两两不等」并写死「不许拆两个 502 凑数」· Goal 2 / Phase 2 ⑤ / 判据④ / §7.23 映射表 / Phase 2 Exit / §10 第 1 格**六处同步改准** |
  | 2 | **Major** | Phase 3 交接项 (5) 下方那件 loop 自己该做的 `Fix`（改准 `docs/context/project-context.md` 的 lint 作用域）**写在正文里、却不在任何 `Targets` 和任何 Exit Criteria / Closure Gates 里** ⇒ 违反指南 Minimum Rule 10（在范围内的项必须落在四态之一）与「Execution Plan covers all checklist items」，实际就是一件**没人认领、收口时查不到**的活 | Phase 3 `Targets` 补上该文件 · Phase 3 **新增一条 Exit Criteria**（写死今天是三个目录、改成七个 + `tests/ui`、并点明「不许跟着交接推给人」）· §10 `relevant docs are aligned` 那格补上它 |
  | 3 | **Major** | §0.5 逐字写着 `grep -rl -i "playwright\|selenium" docs/masterplan docs/backlog` → **零命中**，但**本轮追加的 needs-human 行已经让它命中**（`STATE.md:868-870`）⇒ 执行期按 §0 重跑这条 grep 会拿到命中，而停机分支 4 的免停条件正是「指得出人已批准的具体出处」—— 一行**自己写的提问**被读成批准，正是 §0.5 自己点名要挡的那件事 | §0.5 补一段：命中的是 `[needs-human]` 提问本身、状态词不是 `[resolved]`，**命中 ≠ 已批准** |
  | 4 | Minor | Phase 1 小标题写「**三条**停机分支」，其下实列**四条**（iteration 1 新增第 4 条时漏改标题） | 改准为「四条」并注明来历 |
  | 5 | Minor | Phase 2 的 ruff 项要求「把 `tests/ui` 加进那条命令的参数」，但 `tests/ui/` 要到 **Phase 3** 才建 ⇒ 在 Phase 2 传进去 ruff 直接报路径不存在，造一条**假红** | Phase 2 该项改成「跑现有七个目录」，并写死 `tests/ui` **从 Phase 3 起**才进参数 |
  | 6 | Minor | 行号漂移：`gates.yml:604` 实为 `:603`（`:604` 是下一句「一个字不加不减」） | 就地改准，并补上 `project-context.md:52` / `gates.yml:609` 两个实读行号 |

  **本轮实跑复核过的活仓事实**（不采信 plan 自报）：`gates.yml:560` 的 `COVERED` 八个目录 ·
  `ls -d tests/*/` 今天恰好是那八个（`H1` 预测成立）· `check_expected_red.py:74` 判定面写死 `tests/gates` ·
  `gates.yml:609` ruff 七个目录 · `project-context.md:52` 三个目录（漂移坐实）·
  `module-boundaries.md` 现存最末节是 **§7.22** ⇒ **§7.23 是正确的下一个编号** ·
  `pyproject.toml` 已注册 `live` marker、`testpaths = ["tests"]` ⇒ 加载器那条命令跑得通 ·
  `docs/references/playwright-e2e-guide.md:3` 逐字如 §0.5 所引。

  ⚠️ **本轮也复核了三件「不该改」**：**Minimum Rule 4 不该拆**（与前两轮同结论）；
  **Anti-Slacking 禁用词全文零命中**（`optional` 的四处全是 TOML 键名 `[project.optional-dependencies]`，非含糊语）；
  **红线合规面**逐项核过三个 Phase 的 `Targets` 与 §10 六条自证，**没找出必然越线的藏步**。

- **Independent draft review iteration 4: `needs revision`（已就地修完）+ 维持 `可以转 active: no`**
  （mission-driver 评审步，2026-08-25）—— 复核前三轮的 17 条阻塞是否真落地，并**不受前三轮结论约束**地重审全文。

  **对前三轮的复核**：逐条实读活仓确认已落进本文件。§0.5 的两条实测证据**本轮第三次重跑**：
  `git log --grep=Approved-By` 打出 20 条，**无一条**涉及浏览器驱动；
  `docs/masterplan/STATE.md` 全文 872 行、`:867` 那条的状态词是 `[needs-human]`，
  其后**没有任何 `[resolved]` 行**覆盖它 ⇒ **停在 `draft` 的裁定成立，本轮维持。**

  **本轮新提 5 条（2 Blocker + 3 Major），全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Blocker** | 断言体 `tests/unit/test_desk_sidebar_body.py` 一旦用 `pytest-playwright` 的 fixture（而 `H6`/`H8`/`H8b` 全文都在写 `page.route` / `page.expect_response`，执行期必然这么写），在 CI 上就炸：`gates.yml`（`HEAD` `:530`）逐字 `pip install pytest certifi`，runner 上**没有** playwright ⇒ `fixture 'page' not found` 是 **`error` 不是 `skip`** ⇒ **今天绿着的 `unit-and-contracts` 被本 plan 弄红**。这与 §1.4 那条「守卫按设计报警」**不是一件事**，是**纯回归**，而 §1.4 的三重代价与 §11 第一条**都没覆盖它** | 新增 **§1.4b**（写死约束 + 那条可执行验证 `pytest … -p no:playwright`）· `D-d-3` **新增 ⑥** · Goal 5 补一条不回归 · Phase 3 断言体项补约束 + **新增一条 Proof 项** · Phase 3 **新增 Exit Criteria** · §10 verification 七条→**八条** · 变异 **新增 `M13`** |
  | 2 | **Blocker** | `D-d-3` 起草期那三条**互相接不上**：③ 要求 `tests/ui` 那份「必须 fail」，但 ①② 只管「skip 落在导入之后」，**没给出把 skip 变成 fail 的机制**；同一条又把先例那个机制（`_BODY.pytest.skip = …`）判为「不复制」⇒ 执行期只能回去抄被自己否掉的写法。**且**实读先例发现它结尾**逐条重绑了六个 `test_` 函数**，而本 plan 全文没提这一步 ⇒ 加载器**一条都收集不到、退出码 5**，而 Exit Criteria 写的是 exit 0 | `D-d-3` 三条→**六条**：**新增 ④**（断言体自持 `_unavailable` 间接层，加载器**只重绑它**、不动 `pytest` 模块）· **新增 ⑤**（逐条重绑 `test_` 函数 + 条数守卫）· Phase 3 加载器项重写 · Phase 3 **新增源码级守卫项**（四条，落在已进 CI 的离线判据里）· Phase 3 Exit 补「收集条数 > 0 且等于断言体条数」· 变异 **新增 `M14`/`M15`** |
  | 3 | **Major** | **工作树里有人侧未提交改动**（`git status --porcelain` 实测：`M .github/workflows/gates.yml` · `M docker-compose.yml`，人正在接通 `AGENERP_LLM_BASE_URL`）。全文**零处提及** ⇒ 执行期有三个真风险：把别人的改动一并 commit（撞红线 2）、为了让红线自证第 2 条干净而 `checkout` 掉别人的活、以及**本文件所有 `gates.yml:<行号>` 引用已经对不上工作树** | 新增 **§0.6**（写死三条：不碰 / 不一并 commit / 行号按名字重取）· §0 **新增第 5 条**（按注释原文重取行号）· §10 红线自证那格补「这条 `git diff` 会非空且不是本 plan 干的」的正确判法 · §10 **新增一格**提交隔离自证 · Phase 3 交接项补一句 |
  | 4 | **Major** | Phase 3 那条 Exit Criteria 写「改后 `gates.yml:603` 那句『逐字照抄』重新成立」——**这是假的**：`:603` 逐字是「**作用域三个目录**逐字照抄……」，改完之后「三个目录」仍错，且真相源变八个、`:609` 仍是七个，两边仍不等。一条**判不成立**的 Exit Criteria 就是收口时的一个洞 | Exit Criteria 就地改准并**新增一格**写明残余的两处都在红线 2、**不修也不假装修好** · 交接项 (5) 拆成 **(5a)(5b)**（五件→**六件**）· §11 第一条「五件」→「六件」 |
  | 5 | **Major** | **浏览器怎么够到那个站点，全文没写**：compose 栈按 Host 分站（`FRAPPE_SITE_NAME_HEADER: frontend`），既有断言体 `tests/unit/test_explain_service_body.py:114` 逐字「站点名决定 Host 头」并显式发 `Host: frontend`；而浏览器访问 `127.0.0.1:18080` 发的 Host 是 `127.0.0.1:18080`，**Chromium 不允许用 `set_extra_http_headers` 覆盖 `Host`** ⇒ `H3`/`H5` 的「真登录进 `/app`」这一步可能直接走不通，而**没有写死的出路** | §6 **新增 `H2b`**（含写死的出路：Chromium `--host-resolver-rules="MAP frontend 127.0.0.1"` + 基址改 `http://frontend:18080`，**不改本机 hosts、不碰 compose / nginx**）· Phase 3 Exit 补 `H2b` 实际值 · Phase 3 断言体项写明这个参数落在自建 fixture 里 |

  ⚠️ **本轮实跑复核过的活仓事实**（不采信 plan 自报）：`ls -d tests/*/` 八个目录 = `gates.yml:560` 的 `COVERED`（`H1` 预测仍成立）·
  `check_expected_red.py:73-74` 判定面写死 `tests/gates` · `gates.yml:530` 只装 `pytest certifi` · `:532-533` 跑 `tests/unit` ·
  `:603` 三个目录 / `:609` 七个目录 / `project-context.md:52` 三个目录（漂移坐实）·
  `agenerp/serve/app.py` 实读出的服务端码恰好是 `400/401/403/404/405/500/502/503` **八种**（§1.3 计数口径成立）·
  `test_desk_asset_route.py:165-168` 四格逐字如 Goal 5 所引 · `module-boundaries.md` 现存最末节仍是 **§7.22** ·
  `pyproject.toml` 已注册 `live` marker、`testpaths = ["tests"]`、`exclude = ["tests/gates"]` ·
  `pytest-playwright` 的插件名实测为 `playwright`（⇒ `-p no:playwright` 这条命令有效）。

  ⚠️ **本轮也复核了三件「不该改」**：**Minimum Rule 4 不该拆**（与前三轮同结论）·
  **Anti-Slacking 禁用词全文零命中**（`optional` 的命中全是 TOML 键名）·
  **红线合规面**逐项核过三个 Phase 的 `Targets`、§10 六条自证与本轮新增的四处改动，**没找出必然越线的藏步**。

- **Independent draft review iteration 5: `needs revision`（已就地修完）+ 维持 `可以转 active: no`**
  （mission-driver 评审步，2026-08-25，`HEAD` = `c19cf4a`）—— 复核前四轮的 22 条阻塞，并**不受前四轮结论约束**地重审全文。

  **⚠️ 本轮与前四轮的性质不同：前四轮找的是「文本自身的洞」，本轮找到的主要是「仓库动了、plan 没跟上」。**
  第 4 轮之后仓库落了**三个** commit（`e3afd77` / `758b7bc` 人侧 + `c19cf4a` loop 的 STATE 追加），
  其中两个**正好落在本 plan 第 4 轮刚写进去的那些「活事实」上** ⇒ 本文件出现了**五处过期陈述**，
  有两处会直接把执行者引向错误动作。

  **对前四轮的复核**：22 条逐条实读确认仍在本文件内、未被后续编辑冲掉。
  §0.5 的证据**第四次重跑**：`STATE.md` 全文 **882 行**（第 4 轮是 872），`:867` 仍是 `[needs-human]`，
  其后只有 `:874` 那条 `[open] 14:05Z` 事实登记，**不覆盖它**；
  `git log --grep=Approved-By` **30 条**（第 4 轮 20 条），**无一条涉及浏览器驱动**
  ⇒ **停在 `draft` 的裁定成立，本轮维持。**

  **本轮新提 5 条（2 Blocker + 3 Major），全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Blocker** | **§5 那句无条件的「零 token 成本」已经是错的。** `e3afd77` 把 `docker-compose.yml:65` 改成 `AGENERP_LLM_BASE_URL: ${AGENERP_LLM_BASE_URL:-${AGENERP_LLM_ENDPOINT:-}}` ⇒ **起栈时 shell 里有什么，`agenerp-serve` 里就有什么**；而人侧刚在本机跑通 `6 passed in 48.87s`，执行者的 shell 极可能正配着。⇒ `H6`/`H9`/`M5` 那一次未打桩的真请求**会真调模型**（中位约 **11 万 token**、约 **50 秒**）。**两个后果**：① 成本被当成零、无人记账；② ⚠️ **Playwright 默认 30 秒超时会先于模型返回触发 ⇒ 一条假红，长得像「面板坏了」**，而真因是模型在正常作答 —— 正是本仓反复吃亏的「症状指向错误根因」那一族 | §0 **新增第 6 条**（起栈前先数 `AGENERP_LLM_*`，**只记名字与个数、不记值**）· §6 **新增 `H7b`**（两支都写死：(甲) 0 个照旧；(乙) 非 0 则**记账 + 超时下限 ≥ 90 秒 + 只跑一次真请求**，**两支都不许清环境**）· §5 那句就地改准并**保留旧文划掉** · **新增 R8** · Phase 3 **新增一条 Exit Criteria** |
  | 2 | **Blocker** | **§1.8b 的红因整段过期，且新红与本 plan 的交付面撞在一起。** `e3afd77` 查明工作项 10 那条红的根因**不是模型答错、也不是 `:223` 那条 skip**，而是**变量名错了**（服务读 `BASE_URL`、compose 与 CI 传 `ENDPOINT`）⇒ 恒 503；修完**本机 6/6**。但 `758b7bc` 记着 CI 上**仍红 2 条、其中一条是新红**：`test_no_response_through_the_front_ever_echoes_the_sid` —— 人逐字写着「『响应绝不回显 `sid`』是**安全面**的判据……**不排除是某条错误路径把 `sid` 带了出去**」。⚠️ **而本 plan 要做的正是把响应渲染成可见文本** ⇒ 若面板把响应体原样铺开，就是**把一个正在被调查的疑似安全缺陷从接口面复制到界面上** | §1.8b 整段改准（旧文划掉、两件事分开说）· Phase 2 ⑤ **新增禁令**（禁 `innerHTML = 整个响应` / 禁 `JSON.stringify(resp)` 直接渲染 / 禁写 `document.cookie`；只渲染四个已知键 + 状态码；兜底态只渲染码 + 固定文案）· Phase 2 判据**四件事→五件事**（新增源码守卫⑤，并**显式标注它是文本下限、挡不住逐字段拼接**）· 变异 **新增 `M16`**（十五条→**十六条**）· Phase 2 **新增 Exit Criteria** · **新增 R9**（并写死「不声称澄清了那条红」） |
  | 3 | **Major** | **§0.6 整节的前提没了。** 它逐字写着「工作树里有**人侧未提交**改动」并据此写死三条处置，其中「不许 `checkout` / `stash` 掉它们」在今天**没有对象**（已落盘为 `e3afd77` + `758b7bc`，`git status --porcelain` **无输出**）。更要紧的是 **§10 那条闭合门禁据此写着「这条 `git diff` 会**非空**，而那不是本 plan 干的」—— 今天它就该是干净的，非空即越线**。一条给越线预留了现成解释的闭合门禁，是收口时的真洞 | §0.6 整节重写（两个 commit 逐条列出「改了什么 / 对本 plan 的**真**影响」，三条处置逐条标明哪条仍有效、哪条今天没有对象）· §10 那格改准（**「那是别人的改动」这条解释在 `c19cf4a` 之后失效**；判法仍用区间比较，因为人侧随时可能再落提交）· **R7 改写** |
  | 4 | **Major** | **本文件所有 `gates.yml:<行号>` 今天全体对不上**（两次提交，`758b7bc` 一次就 +22 行）。§0.6 原文说它们「按 `HEAD` `d02b208` 记」，而基线已经走了三个 commit ⇒ 执行期若照抄，命中的是**别的行** | §0.6 第 3 条改准 + **新增一张九行对照表**（旧记 vs 第 5 轮实读：`:560→:597` · `:530→:567` · `:532-533→:570` · `:609→:646` · `:603→:640` · `:542→:579` · `:304-310→:321` · `:275-279→:293`），并写明**这张表本身也会过期，它证明的是「行号会漂，别信它」** · §0 第 5 条同步改准 |
  | 5 | **Major** | **`Approved-By` 那条免停证据出现了新的误读面。** 第 4 轮记「20 条里无一条涉及浏览器驱动」；今天是 **30 条**，且新增的里有 `e3afd77` / `758b7bc` **两条就带 `Gates-Change-Approved-By: lize`、还确实改了 `.github/workflows/gates.yml`**。执行期跑那条 grep 会看到「有 trailer、还是 gates 面的」⇒ **极易被当成第 ① 条的批准**。这与 iteration 3 第 3 条（把自己写的 needs-human 行读成批准）是**同族陷阱的第二次出现** | front matter `Review Hold` 整段改准：计数 20→**30**、点名那两条批的是**CI 变量接线与失败取证步、与浏览器驱动毫无关系**、写死「**免停条件必须逐字点名浏览器驱动**」 |

  ⚠️ **本轮实跑复核过的活仓事实**（不采信 plan 自报）：`git status --porcelain` **无输出** ·
  `python3 tools/gates/check_expected_red.py` → **exit 0**（`门禁 28 项：预期红 0，绿 28，跳过 0` —— §1.9 那个 28 **仍然准**）·
  `ls -d tests/*/` 仍是那八个目录 = `gates.yml:597` 的 `COVERED`（`H1` 预测仍成立）·
  `gates.yml:567` 仍只装 `pytest certifi`、`:570` 仍跑 `tests/unit`（**§1.4b 的前提未变，仍成立**）·
  `:640` 那句「作用域三个目录」与 `:646` 的七个目录 / `project-context.md:52` 的三个目录 —— **三处漂移原样还在**（交接项 (5a)(5b) 仍成立）·
  `docker-compose.yml:65` 的 `BASE_URL` 回落式 · `gates.yml:279-286` 起栈步已配三个 AI 变量 ·
  `module-boundaries.md` 现存最末编号节仍是 **§7.22**（`:3820`）⇒ **§7.23 仍是正确的下一个编号** ·
  `docs/masterplan/STATE.md` 882 行、`:867` `[needs-human]`。

  ⚠️ **本轮也复核了三件「不该改」**：**Minimum Rule 4 不该拆**（与前四轮同结论）·
  **Anti-Slacking 禁用词全文零命中**（`optional` 的命中仍全是 TOML 键名）·
  **红线合规面**逐项核过三个 Phase 的 `Targets`、§10 六条自证与本轮新增的七处改动，
  **没找出必然越线的藏步**；本轮自身只改了本文件一个文件。

- **本轮收敛结论：不转 `active`。** 五轮共 **27** 条阻塞已全部改进本文件，
  但 §0.5 那两条**只有人能答**的前置未答之前，这份 plan 不具备**可执行**契约
  （指南 Plan Status Flow：`active` 的含义是「独立评审已收敛成可执行契约」——
  一份 100% 会在 Phase 1 停机的 plan 不满足「可执行」）。
  ⇒ **`Plan Status` 保持 `draft`**，前置见 §0.5 与 front matter 的 `> Review Hold:` 行。
  人答完第 1 条即可转 `active`（第 2 条影响的是 `D-d-0` 的写法，不影响可执行性）。
  ⚠️ **第 5 轮独立评审维持这一裁定。** 本轮 5 条新发现里 2 条 Blocker 仍是
  「执行期第一天就会撞上、且撞上时长得像别的毛病」的那种（假红指向错误根因 / 把疑似安全缺陷复制到界面）——
  但剩下的门槛**不是文本质量问题，是一件红线内、只有人能做的裁定**。

  ⚠️ **本轮暴露出一件该照实说的事，写在这里不藏**：本轮 5 条里有 **4 条**的成因是
  **「仓库动了、plan 没跟上」**，不是起草不细 —— 第 4 轮到第 5 轮之间只隔了三个 commit，
  就让本文件出现五处过期陈述，其中两处会把执行者引向错误动作。
  ⇒ **这份 plan 每在 `draft` 上多停一轮，它记的「活事实」就多烂一分。**
  §0 的「执行前必做：重取基线」六条**不是形式**，是这份 plan 能不能用的前提；
  **人答完 §0.5 第 ① 条之后，越早执行越好** —— 拖得越久，§0 要重取的东西越多。
  这条不是催促，是把「延迟本身的代价」记在账上（同 §1.10 的预算账，只是这一格记的是时间）。

## 10. Closure Gates

- [ ] in-scope behavior is complete（唤起 / 上下文保留 / 同源请求 / 九个码 + `200` 共 10 态 + 兜底态渲染，五项都**有行为**不只有签名）
- [ ] ⚠️ **闭合判据本身（不可降级，独立评审打回后写死）**：
      `AGENERP_LIVE=1 … python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` **退 0 且零 skip**。
      **它没退 0 时本 plan 不得转 `completed`** —— 只能停在 `active` 并把实测退出码与红因交人。
      **它不是可降级项**（指南 Minimum Rule 14「确认的活体缺陷/契约漂移不得降级」+ Anti-Slacking 四态：
      `landed` / `adjudicated as residual-risk-only` / `moved to explicit successor ownership` / `removed from scope with recorded reason`
      —— 本条只能落 `landed`）。
      ⚠️ **不许把「没退 0」挪进 §11**：§11 里已登记的四条，**没有一条**是它。
- [ ] relevant docs are aligned（`module-boundaries.md` §7.23 · **`docs/context/project-context.md:52` 的 lint 作用域** ·
      `docs/logs/2026/08-25.md` · `docs/evidence/p1-desk-sidebar/`）；
      对 `docs/design/agents-and-roles.md` §9 风险档表 **`No owner-doc update required`**（理由见 §4）
- [ ] verification has run —— 至少这**八**条，命令原文 + 退出码入 `## Closure`：
      `python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/ui tests/contracts tests/tools tests/routing tests/context tests/experiments` ·
      `AGENERP_LIVE=1 … python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` ·
      **`python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`**（§1.4b，
      **必须 exit 0、全 `skipped`、零 `error`** —— 无驱动 runner 上 `unit-and-contracts` 不被弄红的唯一实证）·
      `docker compose up -d --wait --wait-timeout 900`（冷起）·
      `git diff -- .github/workflows tests/gates docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md` → **0 行**
      ⚠️ **第 4 轮在这里写死的那个陷阱已经消失了，第 5 轮实测改准**：
      第 4 轮说「工作树里有人侧未提交改动 ⇒ 这条 `git diff` 会非空」——
      那两处**已由人落盘**（`e3afd77` + `758b7bc`），`git status --porcelain` 今天**无输出**。
      ⇒ **今天这条 `git diff <基线sha>..HEAD -- …` 就该是干净的，非空就是本 plan 自己越线了**，
      **不许再拿「那是别人的改动」当解释** —— 那条解释在 `c19cf4a` 之后失效。
      ⚠️ **但判法仍然用区间比较，不用工作树比较**：`git diff --stat <本 plan 基线 sha>..HEAD -- <路径>`，
      理由是执行期人侧**随时可能又落新的提交**（本轮 24 小时内就落了两次）。
      **收口时把 `git status --porcelain` 原文照抄进 `## Closure`**：干净就记干净；
      若届时又出现别人的未提交改动，按 §0.6 第 1、2 条办 —— **不许 `checkout` / `stash` 掉它们**。
- [ ] scoped verification is not conflated with full verification —— 若未跑整仓 `pytest tests -q -m "not live"`
      或未经 CI 服务端复跑，**逐条写明 `verification scope limited`**
- [ ] no in-scope item downgraded to deferred/follow-up
- [ ] independent draft review completed and recorded（§9）
- [ ] text consistency verified: 顶部 `Plan Status` ↔ 三个 Phase `Status` ↔ 全部 Exit Criteria ↔ 本节 ↔ 日志，五处互不打架；
      `grep -B5 "\- \[ \]" <本文件> | grep "Status: completed"` → **空**
- [ ] closure audit was independent（独立子代理或人，**执行者自己复跑不算**）
- [ ] closure evidence exists in files
- [ ] ⚠️ **红线 2 / 别人未提交改动的隔离自证**（第 4 轮独立评审补）：本 plan 的每一次提交都**显式列路径**，
      `git show --stat <每个提交>` 里**不出现** `.github/workflows/**` 与 `docker-compose.yml`；
      `git log --oneline <基线sha>..HEAD` 与每个提交的文件清单入 `## Closure`

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
- Why Not Blocking Closure: 六件落点**全部**在 `.github/workflows/**`，**红线 2，loop 一个字节都不许改**
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
