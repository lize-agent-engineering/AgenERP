# P1.8b Phase 3 证据 —— ⌘K 侧边栏活体门禁 `tests/ui/test_sidebar.py`

> plan: `docs/plans/p1-insight/2026-08-25-1743-1-desk-sidebar-cmdk-and-live-ui-gate.md`（第 2 个 plan，工作项 11 的最后一格）
> 执行日：**2026-08-26**（UTC）· 基线 sha **`393ef11`**
> 本文件只记**实跑到的**命令原文、退出码与观测值。**没跑到的一律写明 `verification scope limited`，不推演、不补写。**

---

## 0. 开工基线（§0 六条重取，2026-08-26 实跑）

| # | 命令 | 退出码 | 实读输出 |
|---|---|---|---|
| 1 | `git log --oneline -3` + `git status --porcelain` | 0 | `HEAD` = **`393ef11`**；工作树有**上一轮遗留的本 plan 自己的改动**（`M desk.js` / `M project-context.md` / `M test_desk_sidebar_static.py` / `?? tests/ui/` / `?? tests/unit/test_desk_sidebar_body.py`），**无一件是别人的** |
| 2a | `python3 tools/gates/check_expected_red.py` | 0 | `门禁 28 项：预期红 0，绿 28，跳过 0` · `✅ 与预期红名单完全一致` |
| 2b | `python3 -m pytest tests/unit -q` | 0 | `818 passed, 17 skipped in 14.06s`（⚠️ 与本文件起草期记的 `801 passed, 6 skipped` **不一致 —— 以执行期实读为准**，差额是 Phase 2 与上一轮 Phase 3 的新增） |
| 2c | `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` | 0 | `456 passed, 13 skipped in 0.59s`（与起草期逐字吻合） |
| 2d | `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments` | 0 | `All checks passed!` |
| 3 | `ls -d tests/*/ \| xargs -n1 basename \| sort \| tr '\n' ' '` | 0 | `context contracts experiments fixtures gates routing tools ui unit`（**九个**）；`gates.yml:597` 的 `COVERED` 是**八个**（`contracts context experiments fixtures gates routing tools unit`）⇒ **§1.4 那个正面冲突已成立**：`tests/ui` 不在 `COVERED` 里 |
| 4 | `python3 -c "import playwright, pytest_playwright"` | 0 | 成功。`pip list`：`playwright 1.58.0` · `pytest-playwright 0.7.2` · `selenium 4.39.0`。`ls ~/Library/Caches/ms-playwright` → `chromium-1208/1223/1228` · `chromium_headless_shell-1208/1223/1228` · `firefox-1509` · `webkit-2248` · `ffmpeg-1011` |
| 4a | `grep -n -A6 'optional-dependencies' pyproject.toml` | 0 | `:21 [project.optional-dependencies]` … `ui = ["playwright>=1.47"]` **仍在** |
| 4b | `grep -n 'D-25' docs/masterplan/DECISIONS.md` · `grep -n '\[resolved\].*浏览器驱动' docs/masterplan/STATE.md` | 0 | `DECISIONS.md:373` **D-25** · `STATE.md:504` `[resolved] 2026-08-26T01:47Z`。⚠️ **行号与 §0.5 写的 `STATE.md:425` 不同（今天是 `:504`）—— 正是「不认行号、认字面」那条规矩要挡的事。免停条件成立。** |
| 5 | `grep -n '^\| P1.8b' docs/masterplan/02-WBS.md` | 0 | **`:89`**（与 §1.1 改准后的数字吻合）。`gates.yml` 按注释原文重取：`COVERED=` **`:597`** · `ruff check agenerp` **`:646`** · `作用域三个目录` **`:640`** · `pip install pytest certifi`（`unit-and-contracts`）**`:567`** · `这几个目录由 loop 写在红线外` **`:579`** · `工具执行层门禁出现 skip` **`:530`** · `判据自身的判据` **`:528`**。**⚠️ 全体与本文件正文写的旧数字不同，一律以本表为准。** |
| 6 | `env \| grep -c '^AGENERP_LLM_'` + `env \| grep -o '^AGENERP_LLM_[A-Z_]*'` | 0 | **`1`** · **`AGENERP_LLM_MODEL`**（只打名字，不打值） |

## 0b. `H7b` 的实际值与**真实成本**（§5 / R8 逐字要求的那一格）

**走的是哪一支：`(乙) 数出来非 0` —— 但结论仍是本轮零 token，理由是实测出来的，不是假设的。**

1. **起栈前**宿主 shell：`AGENERP_LLM_*` **1 个**，名字 **`AGENERP_LLM_MODEL`**。
2. **起栈后**在 `agenerp-serve` 容器里逐个量（**只打「空 / 非空 + 长度」，绝不打值**）：

   ```
   AGENERP_LLM_API_KEY=<空>
   AGENERP_LLM_BASE_URL=<空>
   AGENERP_LLM_ENDPOINT=<空>
   AGENERP_LLM_MODEL=<非空, 12 字符>
   ```

3. ⇒ **能决定「调不调得成模型」的那两个（`API_KEY` / `BASE_URL`）在容器里是空的。**
4. **直接观测**：那一次未打桩的真请求回的是 **HTTP 401**（见 §2），
   而 `handle_explain` 的顺序是 `_sid_from_cookie` → `parse_request` → `_resolve_identity`(401) → `config_factory`(503)
   ⇒ **请求在 `config_factory` 之前就被挡下了，一次模型调用都没发生。**

⇒ **本轮真实烧掉的解释次数：0。本轮真实烧掉的 token：0。**
⚠️ **这不是「本 plan 零成本」这句话的普遍形式** —— 它成立只因为上面第 2、4 条今天恰好是这样。
`API_KEY` / `BASE_URL` 一旦配上，`H6`/`H9`/`M5` 那一次真请求**就会真调模型**（中位约 11 万 token、墙钟约 50 秒），
断言体的 `REAL_RESPONSE_TIMEOUT_MS = 120_000` 正是为那种情况留的。

---

## 1. 闭合判据（`02-WBS.md:89` 那条验收命令原文）

```
AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin \
  python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs
```

**退出码 0 · `11 passed` · 零 skip。** 连跑三次（都在 `down -v` 冷起之后、且在探活修法落地之后）：

| # | 退出码 | 输出逐字 |
|---|---|---|
| 1 | **0** | `11 passed in 41.54s` |
| 2 | **0** | `11 passed in 51.31s` |
| 3 | **0** | `11 passed in 40.25s` |

**条数把「零 skip」钉住**（`D-d-3` ⑤，防 `no tests collected` 退 5）：

```
$ python3 -m pytest -m live tests/ui/test_sidebar.py -q --collect-only   → 11 tests collected
$ grep -c '^def test_' tests/unit/test_desk_sidebar_body.py              → 11
```

⇒ **收集条数 11 == 断言体里 `test_` 函数条数 11**，且 11 条全跑、全绿、零 skip。

### ⚠️ 拿到这三次绿之前，本轮红过两次 —— 照实记，不修饰

| 序 | 现象 | 处置 |
|---|---|---|
| 1 | 起栈后第一次跑：`11 errors`，红因逐字 `http://127.0.0.1:18080 上换不到真会话（Page.fill: Timeout 30000ms exceeded / waiting for locator("#login_email")）`。**原样复跑一次（裁判规则 3），逐字相同。** 出仓外量：`curl /login` → **502**、`curl /app` → **502**，而 `curl /agenerp/health` → **200** | **不是本 plan 的缺陷，是起栈时序**：`docker inspect` 实读 `backend` 今天是 **`172.25.0.9`**，而 `frontend` 的 nginx 日志逐字 `connect() failed (111: Connection refused) … upstream: "http://172.25.0.8:8000/login"` ⇒ **nginx 拿的是旧 IP**。`docker compose restart frontend` 后 `/login` 立刻 **200** ⇒ 与 `P1.8a-fix`（工作项 10b）那条「起栈时序」是**同族**。**本 plan 不碰 compose / nginx**（§3 Non-Goals），只照实记 |
| 2 | `test_a_real_nginx_502_renders_without_assuming_the_body_is_json` **间歇红**，6 次整轮里**复现 2 次**，红因逐字 `playwright._impl._errors.TimeoutError: APIRequestContext.get: Timeout 30000ms exceeded. → GET http://127.0.0.1:18080/agenerp/health?agenerp-probe=0` | **量出来再改，没猜根因**，见 §5 |

---

## 2. `H6` / `H7` / `H9` 的**直接观测值**（本仓第一次有真浏览器侧实证）

一次性探针（复刻断言体的 `real_exchange`，`sid` 的**值一个字节都不打**）：

| 格 | 观测到的实际值 |
|---|---|
| **`H6`** | 浏览器那次 `POST /agenerp/explain` 的 `Cookie` 头 morsel 名：**`['full_name', 'sid', 'system_user', 'user_id', 'user_image']`** ⇒ **`sid` 在，值长 56 字符**。同一页 `document.cookie.includes('sid=')` → **`False`** ⇒ **`HttpOnly` 只挡 JS 读、不挡浏览器发**，这句话本仓此前一直是推断，**今天第一次被直接测到** |
| **`H7`** | 实际状态码 **`401`**，`content-type` = `application/json; charset=utf-8`。⚠️ **预测列写的是 `503`，不吻合。**照 §6 的规矩：**预测一个字不改**，实际值记这里，并按 `H7` 右列处置（**不清环境重跑**）。面板渲染的是该码对应的那一态，逐字 `未认到人（401）——站点不认这个会话 / 未认到人：请求里没有可用的 sid，或站点不认它` |
| **`H9`** | 请求体键集 **`['question', 'task_class']`** ⊆ `ALLOWED_BODY_KEYS`，与五个越权键交集为空，`doctype`/`name` **同时不给**（本机站点 `setup_complete=False`，够不到任何单据页，见 §7.23.2）。`method`/`url` = `POST http://127.0.0.1:18080/agenerp/explain` |
| 面板上下文提示 | 逐字 `当前不在单据页 —— 这次提问不带单据上下文` ⇒ 与请求体里确实没有 `doctype`/`name` 一致 |

### ⚠️ `H6` 的判法比 plan 原写的**更强**，不是更松

plan 原写「直接证据是回的**不是 401**」。**那个代理指标本轮被实测证伪**：
浏览器网页会话的 `sid` **确实带上了**（上表第一行是请求头本身的直接测量），
但站点因为**缺 CSRF token** 回 401 ⇒ **「401 ⇒ 没带 sid」这个逆否是假的**。
⇒ 断言体改用**直接读那次请求发出去的 `Cookie` 头**。详见 §4 那条发现。

### `H2b` 的实际值确已被自建 fixture 采用

探测记录（Phase 1）记的是：**浏览器发出的 `Host: 127.0.0.1:18080` 落到默认站 `frontend`**（`/login` 回 200、真登录表单在）
⇒ **不需要** `--host-resolver-rules`。
断言体 `_launch_browser()` 实读：`manager.chromium.launch(headless=True)`，**没有任何 `--host-resolver-rules` 参数**，
基址走 `http://127.0.0.1:<port>` ⇒ **fixture 里用的与探测记录里记的是同一条**。

---

## 3. `§1.4b` 那两条命令（各证一件事，缺一不可）

### (A) 插件面 —— 断言体不吃 `pytest-playwright` 的 fixture

```
$ python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright
exit=0 · 11 skipped in 0.49s · 零 error          （不带活栈变量：合法，两种都合法）

$ AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin \
    python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright
exit=0 · 11 passed in 39.89s · 零 error          （带活栈变量，Prereqs 那个条件下真跑起来）
```

### (B) 驱动面 —— 把 `playwright` 包本身遮掉

```
$ mkdir -p /tmp/agenerp-nodriver && \
    printf 'raise ImportError("simulated: playwright not installed")\n' > /tmp/agenerp-nodriver/playwright.py && \
    PYTHONPATH=/tmp/agenerp-nodriver python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright -rs
exit=0 · 11 skipped in 0.01s · 零 error
逐字 skip 原因：SKIPPED [1] tests/unit/test_desk_sidebar_body.py:…: driver missing: simulated: playwright not installed
```

⇒ **无驱动 runner 上 `unit-and-contracts` 不会被本 plan 弄红。**

---

## 4. `pyproject.toml` 的 `ui` extra —— 只读复核，本 plan 零改动

```
① $ grep -n -A6 'optional-dependencies' pyproject.toml
     :21 [project.optional-dependencies] … ui = ["playwright>=1.47"]                    exit=0

② $ python3 -c "import tomllib,pathlib;d=tomllib.loads(pathlib.Path('pyproject.toml').read_text());
                print(d['project']['dependencies'], d['project']['optional-dependencies'])"
     ['certifi>=2024.2.2'] {'ui': ['playwright>=1.47']}                                 exit=0

③ $ git diff --name-only 393ef11..HEAD -- pyproject.toml        → 无输出
   $ git status --porcelain -- pyproject.toml                    → 无输出
```

⇒ `[project].dependencies` **仍逐字只有 `certifi>=2024.2.2`**（D-25 的硬边界成立）；**本 plan 一个字节都没改它。**

---

## 5. 装 chromium 的时间成本实测（D-25 逐字压给 loop 的那件活）

### (a) `--dry-run`

```
$ python3 -m playwright install --dry-run chromium                                       exit=0
Chrome for Testing 145.0.7632.6 (playwright chromium v1208)
  Install location: ~/Library/Caches/ms-playwright/chromium-1208
  Download url:     https://cdn.playwright.dev/chrome-for-testing-public/145.0.7632.6/mac-arm64/chrome-mac-arm64.zip
Chrome Headless Shell 145.0.7632.6 (playwright chromium-headless-shell v1208)
  Download url:     https://cdn.playwright.dev/chrome-for-testing-public/145.0.7632.6/mac-arm64/chrome-headless-shell-mac-arm64.zip
FFmpeg (playwright ffmpeg v1011)
```

### (b) 冷装计时（**临时 `PLAYWRIGHT_BROWSERS_PATH`，跑完已 `rm -rf`，没污染 `~/Library/Caches/ms-playwright`**）

```
$ PLAYWRIGHT_BROWSERS_PATH=/tmp/agenerp-pw-cold /usr/bin/time -p python3 -m playwright install chromium
exit=0 · real 45.77 · user 4.77 · sys 2.78
下载：162.3 MiB（chromium）+ 91.1 MiB（headless-shell）+ 1 MiB（ffmpeg）= 254.4 MiB
$ du -sh /tmp/agenerp-pw-cold   → 524M   （chromium 334M · headless_shell 187M · ffmpeg 2.5M）

$ PLAYWRIGHT_BROWSERS_PATH=/tmp/agenerp-pw-shell /usr/bin/time -p python3 -m playwright install chromium-headless-shell
exit=0 · real 18.17 · user 2.12 · sys 1.07
下载：91.1 MiB + 1 MiB = 92.1 MiB   ·   $ du -sh → 190M
```

⚠️ **本机在国内网络下量到的数**，CI runner 的带宽不同，**墙钟不可照搬，体积可以**。

### (b2) ⚠️ 一条把方案三从「听起来更小」变成「可选」的实测

```
$ PLAYWRIGHT_BROWSERS_PATH=/tmp/agenerp-pw-shell python3 -c "…chromium.launch(headless=True)…"
launched OK; version= 145.0.7632.6
```

⇒ **只装 `chromium-headless-shell` 的那个路径下，本 plan 断言体真正启动的那句
`manager.chromium.launch(headless=True)` 起得来**（playwright 1.58 的 `headless=True` 走的就是 headless shell）。
⇒ 方案三那句「必须与断言体实际启动的浏览器形态一致」**已经实测过，不是纸上推断**。

### (c) 三个方案 + 各自代价（**只给方案与数，`.github/workflows/**` 一个字节不碰；选哪个归人**）

| 方案 | 做法 | 代价（带本轮实测数） |
|---|---|---|
| **一** | 塞进现有 `gates-l2-live` | 最简单，**每次 run 多 254.4 MiB 下载 / 本机 45.77 秒墙钟**（runner 带宽通常更好，但这是每一次 run 的固定加价）。**这正是 D-25 逐字点名的「不要默认塞进现有 job 就完事」** |
| **二** | 单独 job + `actions/cache`（键 = playwright 版本） | 缓存命中时下载 ≈ 0；代价 = 多一个 job 的调度开销 + **缓存失效那次仍是全价**，且 `playwright>=1.47` 是**浮动下界**（`D-d-2` (iii)）⇒ 上游发版即失效，失效频率不可控 |
| **三** | 只装 `chromium-headless-shell` | **下载 92.1 MiB / 本机 18.17 秒 / 落盘 190M —— 三项都约为方案一的 36%**；代价 = 与断言体启动形态必须一致，**本轮已实测一致（见 (b2)）**；残余风险 = 断言体哪天改成 `headless=False` 或换 `channel`，CI 会红在「二进制不在」上 |

---

## 6. 不回归三条

| 格 | 命令 / 观测 | 结果 |
|---|---|---|
| **`H10`** | `docker compose stop agenerp-serve` 之后 | `frontend` **`Health=healthy` `RestartCount=0`** · `/app` 不跟随重定向 **301**（→ `/login?redirect-to=%2Fapp`）、`-L` 跟随后 **200** · `/agenerp/desk.js` **502**。⚠️ **预测列写的是「`/app` 200」，实际不跟随重定向时是 301** —— 照实记；断言体用的 `_probe_status()` 跟随重定向，量到的是 200，与预测同义 |
| **`H11`** | `docker compose down -v` → `AGENERP_HTTP_PORT=18080 /usr/bin/time -p docker compose up -d --wait --wait-timeout 900` | `down` **exit 0** · `up` **exit 0**，`real 60.69` · **十个长期服务全 `running`**（`grep -c running` → 10）· **七个有探针的全 `healthy`**（`grep -c healthy` → 7）· `/login` 200 · `/agenerp/health` 200 · `/agenerp/desk.js` 200。**与预测逐条吻合** |
| **零依赖启动门禁** | `python3 -m pytest tests/unit/test_compose_zero_dep.py -q` | **exit 0 · `14 passed`**。**一条未改松**：`git status --porcelain -- tests/unit/test_compose_zero_dep.py` → 无输出；`git diff --name-only 393ef11..HEAD -- tests/unit/test_compose_zero_dep.py` → 无输出 |

---

## 7. 变异自查：`M1`–`M16` **十六条 / 18 次施加**

**每一次都：施加 → 跑那一格 → 记退出码与红因原文 → 复原 → `shasum -a 256 -c` 校验。**
**18 次全部 `RESTORED OK`。**

| # | 变异 | 施加在 | **是哪一格打的红** | 退出码 | 红因逐字 |
|---|---|---|---|---|---|
| `M1` | 删掉快捷键注册（`void 0 &&` 短路掉那次 `addEventListener`） | `desk.js` | 活体 `test_the_shortcut_opens_toggles_and_escapes_and_gives_focus_back` | **1** | `1 failed`（⌘K 没把面板唤起来） |
| `M2` | 503 分支渲染成空字符串 | `desk.js` | 活体 `H8` | **1** | `AssertionError: HTTP 503 渲染成了空白` |
| `M3` | 401 与 503 渲染成同一句话 | `desk.js` | 活体 `H8` 的**「每一条都含该码字面量」**那一格 | **1** | `AssertionError: HTTP 503 那一态的可见文本里没有 503：'未认到人（401）——站点不认这个会话\nstub'` |
| `M4` | 请求体里偷偷加一个 `user` 键 | `desk.js` | 活体 `H9` | **1** | `AssertionError: 请求体里有服务端不收的键：['user']` |
| `M5` | `credentials` 改成 `omit` | `desk.js` | 活体 `H6`（**那一次未打桩的真请求**） | **1** | `AssertionError: 那次请求的 Cookie 头是空的 —— 浏览器一个 cookie 都没带` |
| `M6` | 请求路径改成 `/agenerp/explain2` | `desk.js` | 离线判据① `test_request_path_in_the_asset_is_the_one_the_service_serves` | **1** | `1 failed, 11 passed` |
| `M7` | 加载器里的 `skip→fail` 收严去掉 | `tests/ui/test_sidebar.py` | ⚠️ **第一次施加：一格都没打红**，见下方专条 | 0 → **1** | 补上守卫⑤ 后：`FAILED …::test_the_loader_actually_rebinds_the_unavailable_indirection` |
| `M8` | 删掉 `window.agenerpDesk` 标记 | `desk.js` | 离线判据③ `test_the_window_marker_is_still_there` | **1** | `1 failed, 11 passed` |
| `M9` | 删掉渲染状态机的兜底分支 | `desk.js` | 活体 `H8b` | **1** | `AssertionError: 兜底态没带上那个码本身：'正在问……（还没有回音）'` ⇒ **正是「永久 spinner」那个失败形态** |
| `M10` | 断言体的 fixture 级 skip 改回模块级（`pytest.importorskip("playwright")`） | 断言体 | 离线守卫① | **1** | `FAILED …::test_the_body_never_takes_a_skip_exit_that_bypasses_the_indirection` |
| `M11` | 让兜底分支假设响应体是 JSON（去掉 `try/catch` 的裸 `JSON.parse`） | `desk.js` | 活体 `H8c`（**真 nginx 502**，不是打桩） | **1** | `AssertionError: 真 502 那一态没带上码本身：'请求没能发出去（Unexpected token '<', "<html>\r\n<h"... is not valid JSON）'` ⇒ **打桩那批对它全无感，这一格是唯一打得红的** |
| `M12` | 资产结尾 `)();` 改成 `})();\n// end` | `desk.js` | `tests/unit/test_desk_asset_route.py::test_asset_file_is_not_gutted` | **1** | `1 failed, 13 passed` |
| `M13a` | 断言体改用 `pytest-playwright` 的 `page` fixture | 断言体 | **命令 (A)** + 源码守卫③ | **1** | `E fixture 'page' not found` · `10 passed, 1 error` |
| `M13b` | 断言体**模块顶层** `import playwright` | 断言体 | **命令 (B)** + 源码守卫② | **2** / **1** | (B)：`1 error during collection` exit=2；守卫②：`FAILED …::test_the_body_never_imports_playwright_at_module_top_level` |
| `M14` | 从加载器里删掉一条 `test_` 重绑 | 加载器 | 源码守卫④ | **1** | `FAILED …::test_the_loader_rebinds_exactly_the_bodys_test_functions` |
| `M15` | 断言体里直调一次 `pytest.skip(...)` | 断言体 | 源码守卫① | **1** | `FAILED …::test_the_body_never_takes_a_skip_exit_that_bypasses_the_indirection` |
| `M16a` | `el.innerHTML = JSON.stringify(resp)` | `desk.js` | 判据 **⑤a** | **1** | `AssertionError: ⑤a 资产里出现了 innerHTML —— 建 DOM 只许走 textContent / createTextNode` |
| `M16b` | `el.textContent = JSON.stringify(resp)` | `desk.js` | 判据 **⑤c** | **1** | `AssertionError: ⑤c JSON.stringify( 命中 2 次（上限 1）—— 第 2 次起必有一次落在渲染面` |

### ⚠️ `M7` 是本轮唯一一条「起初一格都没打红」的，逐字记下经过

第一次施加 `M7`（把加载器里 `_BODY._unavailable = _unavailable_is_a_failure_here` 那一行删掉）之后：

```
$ python3 -m pytest tests/unit/test_desk_sidebar_static.py -q          → exit=0 · 11 passed   （四条守卫全绿）
$ AGENERP_LIVE=1 AGENERP_ADMIN_PASSWORD=admin \
    python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs          → exit=0 · 11 skipped  （门禁「绿」了）
```

⇒ **`M7` 把门禁变成了一条「绿着的、不存在的门禁」，而起草期写死的四条守卫一条都没接住它。**
这正是 §1.6 与本仓最硬那条口径（「一条会 skip 的门禁等于一条不存在的门禁」）要挡的东西。

**按变异表自己的规矩「打不红的当场补断言后复跑」，就地补了第五条离线守卫**
（`tests/unit/test_desk_sidebar_static.py::test_the_loader_actually_rebinds_the_unavailable_indirection`，
判三件：重绑发生了 · 没被绑成 `skip` 一族 · 重绑排在 `exec_module()` **之后**）。
复跑：

```
$ python3 -m pytest tests/unit/test_desk_sidebar_static.py -q   → exit=1 · 1 failed, 11 passed
FAILED …::test_the_loader_actually_rebinds_the_unavailable_indirection
```

⇒ **补后打红成立。** 该守卫**不是起草期就有的，是本轮变异自查逼出来的**，这一点已写进它自己的 docstring。

### ⚠️ `M13a` 有一处「plan 的预测只在特定条件下成立」，照实记

plan 写死「(13a) ⇒ **命令 (A)** 必须打红（`1 error` / `fixture 'page' not found`）」。**实跑分两种条件**：

| 条件 | 命令 (A) 的结果 |
|---|---|
| **不给**活栈变量 | **exit 0 · `11 skipped`** —— `desk` fixture 先 skip 掉了，`page` **根本没被解析到** ⇒ **(A) 无感** |
| **给**活栈变量（= Phase 3 Prereqs 逐字要求的条件） | **exit 1 · `10 passed, 1 error` · `fixture 'page' not found`** ⇒ **打红，与 plan 预测的形态逐字相同** |

⇒ **plan 的预测成立，但它默认了「活栈起着」这个前提。** 前提不在时 (A) 对 `M13a` 无感，
那一格由**源码守卫③** 兜住（两种条件下都红）。**两条合起来才是完整的挡法。**

---

## 8. 本轮两条**执行期实测出来的发现**（都不是起草期预见到的）

### 发现一 🔴 —— 网页会话的 `sid` 在 `/agenerp/explain` 上被 **CSRF** 挡下，而门禁自己的会话不会

**两条路拿到的 `sid` 在服务端的命运不同**（实测，不是推断）：

| `sid` 来源 | `frappe.auth.get_logged_user`（无 CSRF token） | `/agenerp/explain` |
|---|---|---|
| `POST /api/method/login`（**本仓既有活体门禁走的路**） | **200** | **200** |
| 浏览器 `/login` 网页表单（**真人走的路**） | **400 `CSRFTokenError`** | **401** |

⇒ **既有那份活体门禁之所以绿，是因为它用的会话是「真人永远不会有的那一种」。**
`agenerp-serve` 不带 CSRF token 去解析 `sid`，而 Frappe 对网页会话的 POST 要求它。

⚠️ **这不推翻 `H6`** —— 浏览器**确实**把 `sid` 带上了（§2 第一行是请求头本身的直接测量）。
被推翻的只是 plan 原写的那个**代理指标**「回的不是 401」。

**本 plan 不修它**：修法落在 `agenerp/serve/**` 的身份解析上，那是 P1.8a 的请求契约面，本 plan 的 Non-Goals 1 逐字禁止改它一个字。
**已交人**（`STATE.md` §3）。断言体 `test_the_site_rejects_a_browser_session_sid_without_a_csrf_token` **判的是现状不是应然**：
站点哪天不再要 CSRF、或服务端补上了 token，**它照样绿** —— 它不钉死任何一个码。

### 发现二 —— 驱动侧的请求路径在上游停掉时会挂满 30 秒，而反代侧不慢

`test_a_real_nginx_502_…` 在 6 次整轮里**间歇红 2 次**，红因逐字：

```
playwright._impl._errors.TimeoutError: APIRequestContext.get: Timeout 30000ms exceeded.
  → GET http://127.0.0.1:18080/agenerp/health?agenerp-probe=0
```

**量了再改，没猜根因。** 同一时刻从浏览器外面量（`agenerp-serve` 停着，连打 12 次、间隔 3 秒、跨过 `resolver valid=10s` 的窗口）：

```
 1  code=502 time=0.003209      5  code=502 time=0.012105      9  code=502 time=0.006754
 2  code=502 time=0.006172      6  code=502 time=0.007042     10  code=502 time=0.012365
 3  code=502 time=0.002895      7  code=502 time=0.020524     11  code=502 time=0.010951
 4  code=502 time=0.012371      8  code=502 time=0.013111     12  code=502 time=0.011334
```

⇒ **12/12 都是 502，墙钟 3–20 毫秒 —— 反代侧没有慢。挂住的是驱动侧的请求路径**
（与断言体 `_desk_tab` 那条注释记的「请求拦截残留」同族）。
⚠️ **本 plan 只测到「在里面挂、在外面不挂」，没测出是哪一层拦的 ⇒ 不写根因**（裁判规则：不许猜）。

**修法**：探活这件事本来就不该由被判对象所在的那个浏览器承担 —— 它是**同步屏障**，不是判据。
新增 `_probe_status()`（`urllib.request`，stdlib，零新增依赖），502 探活、恢复探活、`H10` 的 `/app` 断言三处改走它。
**判据那一半（面板把真 502 渲染成什么）一个字没动，仍然整条走浏览器**：
改后 `M11` 复核 **仍然打红**（`exit 1`，红因逐字同上表），⇒ **屏障变稳了，牙齿没变钝。**
改后连跑三次活体门禁：**3/3 exit 0，`11 passed`，零 skip。**

---

## 9. 整仓验证与作用域

| 命令 | 退出码 | 输出 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | **0** | `门禁 28 项：预期红 0，绿 28，跳过 0` · `✅ 与预期红名单完全一致` |
| `python3 -m pytest tests/unit -q` | **0** | `819 passed, 17 skipped in 13.93s`（开工时 `818 passed` ⇒ **只增不减**，增的是守卫⑤） |
| `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` | **0** | `456 passed, 13 skipped in 0.56s`（逐字不变） |
| `ruff check agenerp tests/unit tests/ui tests/contracts tests/tools tests/routing tests/context tests/experiments`（**八个目录，含 `tests/ui`**） | **0** | `All checks passed!` |
| `python3 -m pytest tests -q -m "not live"`（整仓） | **1** | `1313 passed, 44 deselected, 23 errors` |

### ⚠️ 整仓那条**红，而且它在本 plan 开工前就已经红** —— 逐条摆开，不含糊

**对照实跑**（把本 plan 新增的两份临时挪开再跑同一条命令）：

```
基线（无 tests/ui/ 与断言体）：exit=1 · 5 failed, 1308 passed, 33 deselected, 12 errors
本 plan 落地后：              exit=1 · 1313 passed, 44 deselected, 23 errors
```

⇒ **整仓这条命令在基线上就是红的**（`tests/gates` 是 expected-red 面，没有活站点时恒红；
roadmap 工作项 10b 已把其中 12 个 error 单列成 `gates-and-tools-leak-env-across-directories.md`）。
**新增的 11 个 error 是本 plan 的断言体，成因已实测定位，不是本 plan 的缺陷**：

```
$ python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -m "not live"                → 11 skipped   （单跑：绿）
$ python3 -m pytest tests/gates tests/unit/test_desk_sidebar_body.py -q -m "not live"    → 11 errors    （同轮：红）
$ grep -n 'pytest.skip *=' tests/gates/test_explain_service_live.py
  80:_BODY.pytest.skip = _skip_is_a_failure_here
```

⇒ **先例 `tests/gates/test_explain_service_live.py:80` 改的是全局 `pytest` 模块 —— 进程级污染。**
同一进程里跑到它之后，**本 plan 断言体的 `_unavailable` 默认那句 `pytest.skip` 也被换成了 `fail`** ⇒ 11 个 error。
**这正是 `D-d-3` ④ 当初写死「不复制先例那个写法」的理由，今天第一次量到它的具体后果。**

**三件必须分开说**：
1. **不影响 CI**：`unit-and-contracts` 跑的是 `pytest tests/unit -q` 与 `pytest tests/contracts -q` **两条独立命令**，
   `gates-l2-live` 只跑 `tests/gates` ⇒ **没有任何一个 job 会把这两个目录放进同一个进程**。
2. **不影响判定器**：`check_expected_red.py` **exit 0**（它只看 `tests/gates`）。
3. **修法在 `tests/gates/**` ⇒ 红线 1，loop 一个字节都不许碰。已交人**（`STATE.md` §3）。

⚠️ **`verification scope limited`（逐条）**：
- 整仓 `pytest tests -q -m "not live"` **已跑但未绿**，原因如上（**基线即红**，非本 plan 引入）；
- **未经 CI 服务端复跑** —— `tests/ui/` 今天不在任何 job 的作用域里（`COVERED` 八个目录不含它、`lint` job 的 ruff 参数七个目录不含它），
  ⇒ **本门禁在 CI 上的行为本轮零数据**，这一处只能等人把它接进 CI（交接项 1/3/4/5a）；
- **独立收口审计**：本轮由执行者自己复跑，`closure audit was independent` 这条 gate **留白**。

---

## 10. 红线自证（基线 sha `393ef11`，两步法：区间 + 工作树）

| # | 命令 | 结果 |
|---|---|---|
| 1 | `git diff --name-only 393ef11..HEAD -- tests/gates` · `git status --porcelain -- tests/gates` | **两条都无输出** |
| 2 | `git diff --name-only 393ef11..HEAD -- .github/workflows` · `git status --porcelain -- .github/workflows` | **两条都无输出** |
| 3 | `git diff 393ef11..HEAD -- docs/masterplan/DECISIONS.md` | **0 行**；工作树也无输出 |
| 4 | `git diff 393ef11..HEAD -- docs/masterplan/02-WBS.md` | **0 行**；工作树也无输出 |
| 5 | `git diff 393ef11..HEAD -- docs/masterplan/STATE.md \| grep -c '^-'` | **0**（只追加，零删除行） |
| 6 | `git -C /Users/lize/Documents/ChatGPT/XM status --porcelain` | **无输出**；`HEAD` = `1c622c8119755b36992c54ba98fbf6840cd22ed4` = 冻结 sha **逐字相同** |
| 7 | `git status --porcelain -- missions/` · `-- docker-compose.yml` | **两条都无输出** |

⚠️ **本 plan 的每一次提交都显式列路径，绝不用 `git commit -a` / `git add -A`。**
