# P1.8b 下半 · ⌘K 侧边栏本体与 `tests/ui/test_sidebar.py` 活体门禁

> Plan Status: active
> Review Hold Released: 2026-08-26 —— §0.5 那两条**只有人能答**的前置，人已在 2026-08-26T01:47Z 全部答完。
> **第 9 轮独立评审逐条实读复核、不是转述**（`HEAD` = `d69b335`，工作树只有另一份 plan 的 ` M`，本文件之外零改动）：
> ① **准不准引浏览器驱动 —— 已批准**：`docs/masterplan/DECISIONS.md` **D-25**（人逐字「批准，加 ui extra」）·
> `docs/masterplan/STATE.md:425` **`[resolved] 2026-08-26T01:47Z`**（逐字「该 plan 的 Review Hold 两条前置全部解除」）·
> commit **`d69b335`**（`pyproject.toml` 已落 `[project.optional-dependencies]` 的 `ui = ["playwright>=1.47"]`，
> `[project].dependencies` 实读仍只有 `certifi>=2024.2.2` 一条）。
> ② **`docs/references/playwright-e2e-guide.md` 算不算数 —— 已裁定「不算数，是上游模板残留」**：
> `STATE.md:450` + 该文件 `:1-9` 已由人加上抬头，逐字「**权威性归 D-25**」。
> ⇒ **Phase 1 停机分支 4 的免停条件今天已满足**（免停出处见该分支改写后的正文），
> ⇒ 本 plan 具备「可执行契约」，**转 `active`**。
> ⚠️ **前八轮写在这里的那两条误读防线仍然有效，已挪进 §0.5 保存，不随本行删除**：
> (一) `Approved-By` 命中里的 `e3afd77` / `758b7bc` 批的是 CI 变量接线与失败取证步，**与浏览器驱动无关**；
> (二) 那些命中里有 6 条是本 plan 自己的评审提交（正文引用了「免停条件」这句话而已）。
> **今天的免停出处是 D-25 / `[resolved]` 行 / `d69b335` 三者，不是它们。**
> ⚠️ **第 9 轮实跑复核了 §1.9 那四条开工基线，四条全部与本文件所记逐字吻合、均 exit 0**
> （`门禁 28 项：预期红 0，绿 28，跳过 0` · `801 passed, 6 skipped` · `456 passed, 13 skipped` · `All checks passed!`）。
> ⚠️ **`active` 不等于「§0 可以跳过」** —— §0 那六条重取基线**逐条照跑**，
> 本行记的一切（含上面那三处出处）执行期都要按 §0 第 4/5 条**重取一次**，行号一律不认。
> Last Reviewed: 2026-08-26
> Source: `docs/backlog/p1-insight-roadmap.md` 工作项 11（P1.8b）· `docs/masterplan/02-WBS.md` §4 第 89 行 ·
> 前一个 plan `2026-08-25-1615-1` §11 第一条写死的后继指派（重开事件「该 plan 转 `completed`」已于 2026-08-25 触发）
> Related: `docs/plans/p1-insight/2026-08-25-1615-1-desk-injection-seam-and-asset-route.md`（第 1 个 plan，`completed`）·
> `docs/plans/p1-insight/2026-08-25-1423-1-explain-service-compose-and-same-origin.md`（P1.8a 第 2 个 plan）
> Work Item: 11. **Desk 侧边栏**（⌘K，调 P1.8a 的面）（P1.8b）—— **本 plan 是它的第 2 个 plan**（表规 3 的 1–2 个预算，
> 本 plan 用掉**最后一格**；此后该格 `2/2` 满，任何后继只能由**人**在 `02-WBS.md` 拆行 / 加行，红线 5，loop 无权）
> Audit: required

## 0. 执行前必做：重取基线

本节的**六条**（⚠️ **第 6 轮独立评审改准：正文原写「四条」，而第 5、6 条是第 4 / 5 轮补进来的 —— 照「四条」跑就会正好跳过「重取行号」与「数 AI 变量」这两条，把 R8 那条假红和行号漂移原样放回来**）**在动手写任何一行代码之前**逐条实跑一遍，结果落进 §1 对应小节。
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
   ⚠️ **同一条里再重取两件（第 9 轮独立评审补，理由见 §0.5）**：
   **(a)** `grep -n -A6 'optional-dependencies' pyproject.toml` —— 人已在 `d69b335` 落了 `ui` extra，
   **确认它还在、且 `[project].dependencies` 仍只有 `certifi`**；不在了就是被 revert 了 ⇒ 停机分支 4 重新触发。
   **(b)** `grep -n 'D-25' docs/masterplan/DECISIONS.md` + `grep -n '\[resolved\].*浏览器驱动' docs/masterplan/STATE.md`
   —— 免停出处的**执行期实读**（**不认 §0.5 写的行号**）。
5. ⚠️ **重取本文件引用的每一处 `gates.yml` / `project-context.md` / `02-WBS.md` 行号**（第 4 轮独立评审补，
   `02-WBS.md` 一项由第 7 轮补，理由见 §0.6 与 §1.1）：
   先跑 `grep -n '^| P1.8b' docs/masterplan/02-WBS.md` —— **本 plan 的验收命令就在那一行**，
   前六轮全文记的 `:88` 已被人插入的 `P1.8a-fix` 行顶掉（今天是 `:89`）；**不认本文件写的数字，认 `P1.8b` 三个字**。
   再跑：
   `grep -n "COVERED=\|ruff check agenerp\|作用域三个目录\|判据自身的判据：跳过就是没跑\|配上之后它走答案面\|把判据调整到迁就环境\|这几个目录由 loop 写在红线外\|pip install pytest certifi\|工具执行层门禁出现 skip" .github/workflows/gates.yml`
   —— **按那几句注释原文定位，不认本文件写的行号**。人侧已两次改过 `gates.yml`（`e3afd77` / `758b7bc`，§0.6），
   行号**已经全体漂移**；**对不上不是本 plan 的错，硬按行号走才是。**
6. ⚠️ **本机 shell 里到底有没有 AI 变量**（第 5 轮独立评审新增，理由见 §5 与 `H7b`）：
   `env | grep -c '^AGENERP_LLM_'` + `env | grep -o '^AGENERP_LLM_[A-Z_]*'`（**只打变量名，绝不打值**）。
   ⇒ **这一条决定本 plan 的活体取证是不是真的零成本**：`docker-compose.yml:65` 今天是
   `AGENERP_LLM_BASE_URL: ${AGENERP_LLM_BASE_URL:-${AGENERP_LLM_ENDPOINT:-}}`（`e3afd77` 落的），
   **起栈时你 shell 里有什么，`agenerp-serve` 容器里就有什么**。
   **数出来非 0 ⇒ H6/H9 那一次「未打桩的真请求」会真调模型**（真烧 token、真花约 50 秒），
   按 `H7b` 走，**不许当没看见**。结果（**变量名与个数，不含值**）抄进 §1.9 的开工基线表。

## 0.5 ✅ 那两条**只有人能做**的裁定，人已在 2026-08-26 答完 —— 本节改成「答案与出处」

**前八轮这一节写的是「本 plan 为什么停在 `draft`」。那件事今天已经结束了，照实改，不留旧文当活事实。**
（旧文的完整推演见 §9 iteration 1–8 的记录，那是**有日期的评审记录**，不是活事实，原样保留。）

### 前置① 准不准把浏览器驱动引进本仓 —— **已批准**

**第 9 轮独立评审逐条实读（`HEAD` = `d69b335`），三处出处彼此独立、任取其一即满足免停条件**：

| 出处 | 实读到的逐字内容 |
|---|---|
| `docs/masterplan/DECISIONS.md` **D-25 · 批准引入浏览器驱动，但只作可选 extra** | 裁定栏逐字「人 2026-08-26：**「批准，加 ui extra」**。形态：`[project.optional-dependencies]` 的 `ui = ["playwright>=1.47"]`，**`[project].dependencies` 一个字不加**」 |
| `docs/masterplan/STATE.md:425` | `[resolved] 2026-08-26T01:47Z ·` 逐字「**答完 P1.8b plan `§0.5` 的最后一条 —— ① 浏览器驱动，人已批准。该 plan 的 Review Hold 两条前置全部解除。**」 |
| commit **`d69b335`**（`feat(deps): D-25 批准浏览器驱动，只作 ui extra —— 解除 P1.8b 的最后一条前置`） | `pyproject.toml` 已落 `ui = ["playwright>=1.47"]`；实读 `[project].dependencies` **仍只有** `certifi>=2024.2.2` 一条 |

⚠️ **`d69b335` 本身不带 `Approved-By` trailer，带的是 `Co-Authored-By`。这不影响免停** ——
Phase 1 停机分支 4 写死的免停条件是三选一（`commit` / `STATE.md` 的 `[resolved]` 行 / `Gates-Change-Approved-By` trailer），
**`[resolved]` 行与 D-25 各自独立成立**，且 `DECISIONS.md` 是红线 3（只有人能写）。

⚠️⚠️ **D-25 同时给 loop 压了三条硬约束，一条都不许漏**（逐字抄自 `STATE.md:428` 与 D-25「未决」栏）：

1. **装包不等于能跑** —— `pip install agenerp[ui]` 之后还要 `python -m playwright install chromium`，
   否则运行期报 `Executable doesn't exist`。⇒ 落进 §5、Phase 3 断言体的自建 fixture 与交接项 (2)。
2. **UI 门禁跑不起来必须红，不许 skip** —— 沿用 P1.8a 那条收严。⇒ 本 plan 的 `D-d-3` ①–⑥ 正是它的实现，一个字不改。
3. ⚠️ **CI 装 chromium 会显著拉长 `gates-l2-live`；是否单独 job 或加缓存，逐字「由 loop 在 plan 里给方案并实测，
   **不要默认塞进现有 job 就完事**」。** ⇒ **这是 D-25 新压给本 plan 的一件在范围内的活**，
   落进 **Phase 3 新增的那条 `Proof`（装驱动的时间成本实测）** 与**改写后的交接项 (2)**（给方案 + 带实测数，不是一句「装上去」）。

### 前置② `docs/references/playwright-e2e-guide.md` 算不算数 —— **已裁定：不算数，是上游模板残留**

`STATE.md:450` 逐字：「**裁定：不算数，它是上游模板残留。**……**一份没有决策背书的文档，说得再确定也不是决策**。
⚠️ **这不等于说 Playwright 是错的选择**，只是说**这件事还没被决定过**。」
人并已就地给该文件加了抬头（实读 `:1-9`）：逐字「**本文件是上游模板残留，它本身不构成本项目的技术选型批准**」·
「**真正的批准在 `docs/masterplan/DECISIONS.md` 的 D-25**」·「本文的技术内容可参考，**权威性归 D-25**」。

⇒ **`D-d-0` 因此变成一条「记录已有裁定」的 `Decision`，不是要 loop 自己去分类**（指南 Minimum Rule 9 的
`constrained`（外部规则强制）那一档）。**本 plan 对该文件仍是只读**（§4 Owner Docs）。

### ⚠️ 前八轮立起来的两条误读防线**继续有效**，挪到这里保存

**这两条不因为「已经批了」而作废** —— 它们挡的是**下一次**有人拿错东西当批准：

- **误读一**：`git log --grep=Approved-By` 的命中里有 `e3afd77` / `758b7bc` 两条**确实**带
  `Gates-Change-Approved-By: lize`、也确实改了 `.github/workflows/gates.yml`。
  **那两条批的是 CI 变量接线与失败取证步，与浏览器驱动毫无关系。**
  **拿它们当第 ① 条的批准，就是把别人给另一件事的许可挪用到自己头上。**
- **误读二**：那批命中里有 6 条（`7550b3f` / `d02b208` / `ede9944` / `2163e19` / `45ee997` / `b02fd7a`）
  **是本 plan 自己的评审提交** —— 命中只因为正文引用了「免停条件」这句话本身，**无一带真 trailer、无一是人写的**。
  **拿它当批准，就是拿自己的评审记录给自己发许可。**
- **误读三（本轮新增）**：`grep -rn -i "playwright\|selenium" docs/masterplan docs/backlog` 今天**会命中很多行**
  —— 其中既有 D-25（**真批准**），也有 `STATE.md` 里本 plan 自己那条早已被 `[resolved]` 覆盖的 `[needs-human]` 提问。
  **命中数不是判据，`[resolved]` 行 + D-25 才是。**

⇒ **今天的免停出处只有三个：D-25 · `STATE.md:425` 的 `[resolved]` 行 · commit `d69b335`。**

⚠️ **执行期仍须按 §0 第 4 / 5 条重取一次**（行号会漂，本文件写的数字一律不认；
按 `D-25` 三个字定位 `DECISIONS.md`、按 `[resolved]` + `浏览器驱动` 定位 `STATE.md`）。
**若届时三处出处都不在了（例如被 revert），那就是停机分支 4 重新触发，照它走。**

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
   | `❌ 工具执行层门禁出现 skip …`（Phase 3 交接项 (4) 要人照抄的**零 skip 断言**形态；⚠️ **第 6 轮补 —— 前五轮这一处既不在本表、也不在 §0 第 5 条的 grep 里**） | `:492-495` | **`:529-530`** |

   ⚠️ **这张表本身也会过期** —— 它证明的不是「行号是多少」，而是「**行号会漂，别信它**」。

## 0.7 ⚠️ 第 6 轮之后仓库又动了三处，各自改掉本文件的一段说理（第 7 轮独立评审实读补）

`git diff --name-only 4f81de8..HEAD` 实读只有六个文件，**没有一个是产品代码或判据**
（`02-WBS.md` · `DECISIONS.md` · `STATE.md` · `p1-insight-roadmap.md` + 两个 plan 文件）。
**但其中三处是人侧的新裁定，且每一处都正好落在本文件的一段说理上。** 逐条摆开，不合并：

| # | 人侧新动作 | 实读出处 | 它改掉了本文件的哪一段 |
|---|---|---|---|
| **(甲)** | 新拆出 **`P1.8a-fix`** 一整行（`frontend` 间歇不可达 —— 起栈时序缺陷，🔴，验收是「`gates-l2-live` 连续 **3 次** run 全绿零跳过，且 3 次都在修复 commit 之后」） | `02-WBS.md:88`（**插在 P1.8b 之前**）· `p1-insight-roadmap.md` 工作项 **10b** · `STATE.md:901` `[needs-human] 11:18Z` | **① 行号**：P1.8b 从 `:88` 移到 **`:89`**（§1.1 已改准，全文 8 处）· **② 新风险**：见 **R10** |
| **(乙)** | 新裁 **`D-24` · 常设授权：plan 预算满了就加，不必逐次请示**（人逐字「预算满了就再加预算」；拆出来的行**预算独立计**） | `DECISIONS.md` D-24 | §1.10 / §3.1 / §0.5 里「预算满了就**没有出口**」那半句说理（三处已改准）。⚠️ **第 9 轮补**：§0.5 本轮整节重写，该段说理今天的落点是 §1.10 与 §3.1 |
| **(丙)** | 人已把 P1.8a 那条 CI 红**查到根并单独立行**：症状逐字「**`127.0.0.1:8080` 够不到（timed out）—— 同源前端没在跑**」，且「**服务容器自己正常**……**掉的是 `frontend`**」 | `02-WBS.md:88` 的 `P1.8a-fix` 行 · 断言体 `tests/unit/test_explain_service_body.py:133` 逐字 `pytest.skip(f"{host}:{port} 够不到（{exc}）—— 同源前端没在跑")` | **§1.8b 后半段与 R9 那段「不排除是某条错误路径把 `sid` 带了出去」已过期**（两处已改准） |

⚠️ **(乙) 的边界必须一起抄下来，不许只抄授权那半句**（D-24 自己写死的两条）：
① **「loop 仍然不得自行加行。它判『无 plan 可派』并停下来是正确行为，本条不改这一点」** —— **红线 5 一个字没松**；
② **「加预算的前提是上一轮有真实进展。若同一工作项连续第 3 次要预算而判据没有任何前进，那不是预算问题，是方法问题 —— 此时停下来报人」**。
⇒ **D-24 改的是「人侧响应有多快」，不是「loop 能不能自己拆」。** 本 plan 的一切「归人」写法**一条都不改**。

⚠️ **(丙) 是本轮最要紧的一条，因为它是「结论碰巧还对、理由是假的」那一族**（同 iteration 6 第 2 条）：
Phase 2 ⑤ 的禁令（不许把响应体原样倾泻进 DOM）**仍然正确、一个字不删**，
变异 `M16` 与判据⑤ 的三条源码守卫**照旧**；
**被打掉的只是它援引的那条理由** —— 「那条门禁正红在一个疑似 `sid` 外泄上」今天已不成立。
**改准后的理由写在 §1.8b 与 Phase 2 ⑤。**

## 1. Current Baseline

### 1.1 WBS 那一行要什么

`docs/masterplan/02-WBS.md` §4 **第 89 行**逐字：

> | P1.8b | **Desk 侧边栏**（⌘K 唤起，保留当前单据上下文），调 P1.8a 的面 | P1.8a | `pytest -m live tests/ui/test_sidebar.py` 退 0 | `MD:p1-explain` |

⚠️ **这个行号第 7 轮独立评审实读改准过一次，前六轮全文写的都是「第 88 行」（本轮共改 8 处）**：
人在 2026-08-25 往 `:88` 插进了一整行 **`P1.8a-fix`**（`frontend` 间歇不可达，🔴，见 §0.7），
**P1.8b 那一行因此整体下移到 `:89`**（`:88` 今天是 `P1.8a-fix`、`:90` 是 `P1.9`，实读确认）。
⚠️ ⚠️ **执行期不认这个数字，按 `P1.8b` 三个字定位**（同 §0 第 5 条对 `gates.yml` 的口径）：
`grep -n '^| P1.8b' docs/masterplan/02-WBS.md`。
**理由与 §0.6 那张 `gates.yml` 对照表同族 —— 行号会漂，而这一次漂的是本 plan 的验收命令所在的那一行。**
⚠️ **顺带照实记一处本 plan 不代改的下游漂移**：`docs/backlog/p1-insight-roadmap.md` 工作项 11 那条
也写着「WBS §4 第 88 行」，同样已过期。**它归 roadmap 的回写面，本 plan 不代改**（措辞归属不在本步职责内，
同 `STATE.md` 第十三次盘点已立的定界），只在此登记「别拿它当第二个真相源」。

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
3. ⚠️ **可执行验证是两条命令，不是一条 —— 第 8 轮独立评审实跑打回，旧文不留**：

   > ~~`python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`
   > —— `-p no:playwright` 关掉该插件，**等价模拟 runner 上没装它**；**必须 exit 0、全部 `skipped`、零 `error`**。~~

   **实跑证伪**（第 8 轮在 `/tmp` 用一个同形态的最小样本跑的，不是推演）：`-p no:playwright` 只关掉
   **pytest 插件**，**不影响 `import playwright` 这个包本身**。而 §1.5 实读本机**装着** `playwright 1.58.0`
   ⇒ 断言体自建 fixture 里那句 `import playwright` **照样成功**，那批用例会**真跑起来**（`1 passed`），
   **不是 `skipped`**。⇒ 「全部 `skipped`」这条期望**在执行者本机不可满足**，
   而 Phase 3 的 Prereqs 又逐字要求「活栈按 §5 起好并**真登录**过一次」⇒ 活栈在的时候更是真跑。
   **一条不可满足的 Exit Criteria 就是收口时被逼着造假的洞**（同第 4 轮打回的那条「判不成立的 Exit Criteria」）。

   **改准后写死两条，各证一件事，缺一不可**：

   **(A) 插件面** —— `python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`
   ⇒ **必须 exit 0、零 `error`**（**不断言全 `skipped`**：跑起来还是跳过，取决于本机装没装驱动、活栈起没起，
   **两种都合法**）。它证的是**「断言体不吃 `pytest-playwright` 提供的 fixture」** ——
   第 8 轮实跑确认：函数签名里写 `page` 参数时，这条命令给的是 `1 error`（`fixture 'page' not found`），
   与 runner 上的形态**逐字相同**。

   **(B) 驱动面** —— **真正等价模拟「runner 上没装 playwright」的是把包本身遮掉**：

   ```
   mkdir -p /tmp/agenerp-nodriver && \
     printf 'raise ImportError("simulated: playwright not installed")\n' > /tmp/agenerp-nodriver/playwright.py && \
     PYTHONPATH=/tmp/agenerp-nodriver python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright -rs
   ```

   ⇒ **必须 exit 0、全部 `skipped`、零 `error`**。第 8 轮实跑同形态样本确认它**确实**打出
   `1 skipped ... driver missing: simulated: playwright not installed`、exit 0。
   ⚠️ **`-p no:playwright` 在 (B) 里不能省**：不关插件的话，插件自己加载时就会 `import playwright`，
   撞上那个遮蔽模块 ⇒ 整轮起不来，红在插件上而不是红在断言体上。
   ⚠️ **(B) 才是唯一能挡住「断言体在模块顶层 `import playwright`」的运行时证据** ——
   (A) 在本机对它**无感**（包装着，导入成功）。⇒ 那个变体的打红面是 **(B) + 源码守卫 ②**，**不是 (A)**（见 `M13`）。

   两条都进 Phase 3 的 Proof、Exit Criteria 与 §10。

### 1.5 浏览器驱动在本机的实读（起草期实测，**执行期须按 §0 第 4 条重取**）

| 探针 | 起草期实读值 |
|---|---|
| `python3 -c "import playwright"` | **OK** —— `/Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/playwright/__init__.py` |
| `python3 -m pip list \| grep -i playwright` | `playwright 1.58.0` · `pytest-playwright 0.7.2` · （另有 `playwright-stealth 2.0.2`，本 plan 不用） |
| `ls ~/Library/Caches/ms-playwright` | `chromium-1208` / `chromium-1223` / `chromium-1228` / `chromium_headless_shell-*` **已下载** |
| `python3 -m pip list \| grep -i selenium` | `selenium 4.39.0`（备选，本 plan 不选，理由见 `D-d-2`） |
| `grep dependencies pyproject.toml` | ⚠️ **第 9 轮独立评审实读改准，旧文不留**：原文写的是「~~没有任何 `optional-dependencies` 段~~」，**`d69b335` 之后不成立**。今天是：`[project].dependencies` **仍只有** `certifi>=2024.2.2`（一个字未动），**且已有** `[project.optional-dependencies]` 段，内含 `ui = ["playwright>=1.47"]`（人落的，D-25） |

⇒ **「本机装着」与「本仓声明了」是两件事**（这正是 `pyproject.toml` 那段注释记着的旧亏：
「本机碰巧装着 certifi，所以直到把 `tests/routing` 接进 CI 才暴露」）。
⚠️ **这一格今天已经由人补齐了，`D-d-2` 因此不再是「要正面裁的那一格」，而是「记录已落地的裁定」**（§0.5 前置①）：
声明形态由 **D-25** 定死（`ui` extra，`[project].dependencies` 一个字不加），**本 plan 不重裁、也不改它**。
⚠️ **但那条旧亏没有被消掉，只是换了位置** —— `ui` extra 声明的是 **`playwright` 包**，
**不含 `pytest-playwright`**，也**不含浏览器二进制**（D-25 逐字「装包不等于能跑」）。
⇒ ① 本机那份 `pytest-playwright 0.7.2` **仍然是「本机碰巧装着」**，本 plan 因此**明令不许依赖它**（`D-d-3` ⑥ / §1.4b）——
**这不是巧合，是 `ui` extra 的形态与 `D-d-3` ⑥ 正好互相印证**；
② 浏览器二进制要靠 `python -m playwright install chromium` 单独装，**它的时间成本是本 plan 要实测的一件活**（§0.5 硬约束 3）。

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

**那条门禁在 CI 上今天仍然红。⚠️⚠️ 但红因第 7 轮独立评审实读改准，第 5、6 轮写在这里的那一版已过期，旧文不留**：

> ~~红在 `test_no_response_through_the_front_ever_echoes_the_sid`（**新红**）与
> `test_the_user_in_the_answer_is_the_person_the_real_sid_resolves_to` 两条上。
> 人写死了第一条为什么要紧：「『响应绝不回显 `sid`』是**安全面**的判据，
> 它在服务开始真答之后才红，**不排除是某条错误路径把 `sid` 带了出去**」。~~

**人已经把它查到根并单独立成一行了**（`02-WBS.md:88` 的 `P1.8a-fix`，2026-08-25，见 §0.7 (甲)(丙)）。
**两条实读证据，都不是转述**：

1. `P1.8a-fix` 行逐字记的症状：CI live 判定 **54 项里绿 53 红 1，红的那条每轮不固定**
   （`758b7bc` 红两条、`4f81de8` 只红 `echoes_the_sid`），**断言正文逐字「`127.0.0.1:8080` 够不到（timed out）—— 同源前端没在跑」**；
   且「**服务容器自己正常**（日志里 `POST /agenerp/explain` 持续正常响应）—— **掉的是 `frontend`**」。
2. 断言体 `tests/unit/test_explain_service_body.py:133` 逐字：
   `pytest.skip(f"{host}:{port} 够不到（{exc}）—— 同源前端没在跑")`
   —— 而 `tests/gates` 那份加载器把 `skip` 收严成 `fail`（§1.6）⇒ **「够不到」在门禁上长出来就是一条红**。

⇒ **红的不是「响应回显了 `sid`」，是「那一刻前端根本不在」。** 那条断言压根没跑到比较响应体那一步。
⚠️ **本 plan 因此必须收回一句话**：第 5、6 轮写的「那条新红与本 plan 的交付面在同一条链上」**不成立** ——
它们不在同一条链上，一条是**起栈时序**，一条是**渲染**。

⚠️ **但 Phase 2 ⑤ 那条禁令一个字不删，理由改基**（这正是 §0.7 (丙) 说的「结论对、理由假」）：
面板**任何一态都不许把响应体原样倾泻到 DOM 里**（`innerHTML = JSON.stringify(resp)` 这类），
渲染只取 §1.3 那四个已知键与状态码本身。**改准后的理由是两条，都不依赖那条已被证伪的推测**：
**(i)** `sid` 是 `HttpOnly`，其存在意义就是「不进 JS 可读面、更不进 DOM」（§1.8）——
把整份响应铺进 DOM，等于**自己造一个绕过 `HttpOnly` 的显示面**，这条判断不需要任何 CI 现状支撑；
**(ii)** 与 `H8c` / `M11` 是同一条约束的两面 —— **真 nginx 502/504 回的是默认 HTML 不是 JSON**，
任何「把响应体当结构化数据铺开」的写法在真 502 上都会抛，正好落进 Goal 2 禁止的空白。
这条落进 Phase 2 第 ⑤ 项与 `H8` 的判定口径（见该两处的 ⚠️ 标注）。

⚠️ **本 plan 的立场仍然不变**：**不因为「本机 6/6」就声称工作项 10 已闭合** —— 它在 CI 上仍是红的，
只是红因换成了一个**基础设施缺陷**，而那个缺陷**人已经单独开了行**（`P1.8a-fix`，验收是「连续 3 次 run 全绿零跳过」）。
**本 plan 不碰它、不声称澄清它、不声称受它阻塞**（P1.8b 那一行的前置逐字是 `P1.8a`，不是 `P1.8a-fix`）。
它对本 plan 的**真**影响是一条**取证面**的风险，写在 **R10**，不写在这里。

而 `02-WBS.md` 第 89 行明写 P1.8b 的前置**是 P1.8a**。

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

⚠️ **第 7 轮独立评审实读补：`D-24` 改了这一格的「代价」，但没改它的「归属」**（§0.7 (乙)）。
人 2026-08-25 新裁 `DECISIONS.md` **`D-24 · 常设授权：plan 预算满了就加，不必逐次请示`**，逐字「预算满了就再加预算」，
授权范围是「当 **loop 判『无 plan 可派』且原因是预算满**时，**人侧代理可直接拆行 / 加行**，不必逐次请示」，
且「拆出来的行**预算独立计**」。本仓已有它的第一个实例：**`P1.8a-fix`**（§0.7 (甲)）。
⇒ **「预算满了就再也出不来」这个说法今天过强，本 plan 不再这么写**（第 7 轮在 §0.5 / §3.1 / §11 三处同步改准）。
⚠️ **第 9 轮补一句指路**：§0.5 已在本轮**整节重写**成「答案与出处」（那两条前置人已答完），
**第 7 轮写在那里的这段 `D-24` 说理不再在 §0.5 里** —— 它今天的落点就是本节与 §3.1，§0.7 (乙) 是它的出处记录。
⚠️ **但下面三条一个字不松，逐条抄自 D-24 自己**：
① **「loop 仍然不得自行加行。它判『无 plan 可派』并停下来是正确行为，本条不改这一点」** ⇒ **红线 5 原样有效**，
本 plan 的一切「归人」写法**一条都不改**；
② **「加预算的前提是上一轮有真实进展……若同一工作项连续第 3 次要预算而判据没有任何前进，那不是预算问题，是方法问题 —— 停下来报人」**
⇒ 工作项 11 若真走到第 3 格，**必须先能指出上一轮具体推进了什么**（哪条判据由红转绿）；指不出来就是该停的信号，
**本 plan 不预支这一格**；
③ D-24 改的是**人侧响应有多快**，**不是** loop 的权限边界 —— **拿它当「我可以自己拆行」用，就是把授权读反**。

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
   却依赖驱动时，那里出的是 `error` 不是 `skip`；这一条由 §1.4b 的 **(A)(B) 两条**命令实证，不靠承诺 ——
   ⚠️ **(A) 一条不够**：它只挡「吃了插件 fixture」，挡不住「模块顶层 `import playwright`」，第 8 轮实跑改准）·
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
   ⚠️ **第 6 轮独立评审改准了这一条的理由，旧文不留** —— 原文写的是
   「~~本 plan 的判据全部落在 503 分支与打桩分支上，**不产生长请求**~~」，
   **第 5 轮把 §1.7 / §5 / `H7b` / R8 全改了之后，这句话已经是假的**：
   `H7b` **(乙) 支**（shell 里有 `AGENERP_LLM_*`，而 §5 判定「倾向：有」）下，
   `H6` / `H9` / `M5` 那**一次**未打桩的真请求**会真调模型 —— 中位约 11 万 token、墙钟约 50 秒**。
   ⇒ **正确的理由是量级，不是「没有真请求」**：50 秒 ≪ 300 秒 ⇒
   **那一次真请求碰不到 `proxy_read_timeout` 的上限**，**真 504 仍然拿不到、仍然是未验证的**。
   ⚠️ **两件事分开记，不许合并**：「一次正常长度的解释没被掐断」是 (乙) 支**顺带得到的一个数据点**，
   **它不等于「300 秒这个上限被验证了」** —— 收口文字里不许把前者写成后者。登记在 §11（该条已按两支改写）。

### 3.1 ⚠️ 「一个 plan 一个结果面」（Minimum Rule 4）本 plan 为什么不拆

本 plan 同时交四块：**UI 本体 · 活体门禁 · 依赖声明 · CI 交接**。看起来像四个面，**实际共享同一条闭合判据** ——
`02-WBS.md` 第 89 行那条 `pytest -m live tests/ui/test_sidebar.py` 退 0。
UI 不写它不退 0；门禁不写它不存在；驱动不声明它跑不起来；CI 交接是它落地后**必然溢出**的那一件。
Minimum Rule 4 原文同时禁止 over-split（「共享同一行为契约与闭合判据的多模块工作**仍是一个结果面**」）。

⚠️ **拆了要多花一格，而那一格只有人能开**：工作项 11 的预算只剩这最后一格（§1.10），
拆出来的第二个 plan **只能由人在 `02-WBS.md` 拆行 / 加行**（表规 3 + 红线 5）。
⚠️ **第 7 轮改准措辞：原文写的是「拆了**没有出口**」，`D-24` 之后那句过强**（§0.7 (乙) / §1.10）——
人已常设授权「预算满了就再加预算」⇒ 出口存在，只是**仍然只有人能开**（D-24 逐字「loop 仍然不得自行加行」）。
⇒ **不拆的理由因此不再靠「没有出口」撑着，而是靠上面那条 —— 四块共享同一条闭合判据，拆开就是 over-split**
（Minimum Rule 4 原文同时禁止 over-split）。**这仍然是裁定，不是图省事**；
独立评审 iteration 1–6 逐轮独立复核后均同意「不该拆」，第 7、8、9 轮维持（第 9 轮实读复核，结论未变）。

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

Status: completed
Targets: `docs/analysis/2026-08-25-1743-desk-sidebar-probe.md`（探测记录，新建）·
`docs/architecture/module-boundaries.md` §7.23（落点节，新建）
Skill: `none`

- Item Types: 逐项标注为准（本 Phase 共 **7** 项：`Decision` **5**（`D-d-0`…`D-d-4`）· `Explore` 1 · `Proof` 1）。
  ⚠️ **第 9 轮独立评审改准：旧文写「4/6 项是 `Decision`」，实数是 5/7** —— 不足指南 Minimum Rule 7 的 80% 阈值，
  故**不作 Phase 级统一声明**，以每一项自己的类型标注为准。（同族计数不一致本文件已挡过三处，这是第四处。）
- Prereqs: §0 **六条**重取基线已跑完（⚠️ 第 6 轮改准，原写「四条」）；`H1` / `H2` 已有实际值

- [x] **Explore**：跑 `H1` / `H2` / **`H2b`** / `H3` / `H4` / `H5` **六条**探针，逐条把实际值填进 §6 与探测记录。
      ⚠️ `H3` / `H4` 必须**带真登录会话在真 Desk 页面上**测，不许拿静态 HTML 推。
      ⚠️ **`H2b` 必须排在 `H3` / `H4` 之前跑，这是第 6 轮独立评审改准的（前五轮把它整个漏出了 Phase 1）**：
      `H2b` 问的是「**浏览器发出的 Host 是 `127.0.0.1:18080`，这一跳到底落不落到 `frontend` 站**」——
      而 `H3` / `H4` 逐字要求「真登录进 `/app`、按下组合键」，**那一步成立的前提就是 `H2b` 已经成立**。
      前五轮只在 **Phase 3** 提到它（断言体的 fixture 参数 + Phase 3 Exit Criteria）⇒
      执行者按清单走会在 **Phase 1 第一天**撞上它，却在 Phase 1 找不到处置。
      **处置就写在 §6 `H2b` 那一行的第四列（默认站回落 / `--host-resolver-rules="MAP frontend 127.0.0.1"`；
      两条都不成立 ⇒ 记进探测记录并交人，不许改 compose / nginx 去迁就判据），执行期照它走。**
      `H2b` 的实际值（走了哪一条）**同时是 Phase 3 自建 fixture 的输入**，两处引同一个值，不各测一遍。
      - Skill: `none`
- [x] **`D-d-0` `docs/references/playwright-e2e-guide.md` 的效力分类**（`Decision`，**前置于 `D-d-1` / `D-d-2`**）。
      ⚠️ **第 9 轮独立评审改准：这一条已由人答完，本项从「去分类」变成「记录已有裁定」**（指南 Minimum Rule 9 的
      `constrained` 那一档 —— 外部规则已强制，不做完整备选分析）。
      **裁定（人 2026-08-26，出处见 §0.5 前置②）：`上游模板残留（stale）`。**
      依据逐字二选一即可：`STATE.md:450`「**不算数，它是上游模板残留**……一份没有决策背书的文档，
      说得再确定也不是决策」· 该文件 `:1-9` 人加的抬头「**权威性归 D-25**」。
      **残余风险**：`docs/index.md:45` 仍把「e2e / Playwright」这一类路由到它 ⇒
      下一个人仍可能把它读成批准。**本 plan 不改 `docs/index.md`**（不在任何 Target 内，也不在本 plan 的结果面上），
      **只把这条残余登记进探测记录**；它不阻塞收口，因为权威性问题已由人加的抬头就地解决。
      ⚠️ **执行期照做的只有两件**：① 按 §0 第 4 条 (b) 重取那两处出处、抄进探测记录；
      ② **不许用「反正它写着 Playwright」当批准** —— 批准来自 D-25，不来自它。
      **三处出处若届时都不在了 ⇒ 停机分支 4 重新触发。**
      - Skill: `none`
- [x] **`D-d-1` 判据的目录与形态**（`Decision`）。候选三个，逐条写清否决/选中理由与残余风险：
      **(A)** 落 `tests/ui/test_sidebar.py`，形态**照抄本仓既有先例**——
      它是一个**薄加载器**（同 `tests/gates/test_explain_service_live.py` 的做法：
      「判据只有一份，门禁是它的严格模式」），断言体落在**已进 CI 的** `tests/unit/test_desk_sidebar_body.py`，
      加载器把体里的 `skip` 收严成 `fail`（§1.6）。
      **(B)** 不建 `tests/ui/`，判据全放 `tests/unit/` ⇒ **WBS 第 89 行的验收命令不成立**，工作项 11 无法转 `done`。
      **(C)** 建目录并自己去改 `gates.yml` 的 `COVERED` ⇒ **红线 2，禁，不进候选比较，只记它为什么被排除。**
      **裁定必须正面回答的三件事**：① (A) 会让 §1.4 那一步在下次推送时红，这个代价接不接受、
      凭什么接受（引先例与守卫自己的失败文案）；② 断言体为什么不能直接住在 `tests/ui/`
      （住进去就**不受** `pytest tests/unit -q` 那一轮保护，日常改坏了看不见）；
      ③ (B) 的出口是什么（也是归人 —— 预算已满、拆行只有人能做）。
      - Skill: `none`
- [x] **`D-d-2` 浏览器驱动与依赖声明形态**（`Decision`）。候选：**(a)** playwright（本机 1.58.0 + chromium 已下载 +
      `pytest-playwright` 已在）· **(b)** selenium 4.39.0 · **(c)** 不用浏览器、用 `http.client` 打 HTML
      ⇒ **撞硬约束①**（「按下 ⌘K 之后发生了什么」根本没测，退化成验「调得通」）· **(d)** 引 node 跑 JS 环境
      ⇒ 引入第二套运行时与第二个包管理器，且仍不是真浏览器。
      **声明形态一并裁死**：写进 `[project.optional-dependencies]` 的一个 **`ui` extra**，
      **`[project].dependencies` 一个字不加**（§5）；并在探测记录里写明「本机装着 ≠ 仓里声明了」这条旧亏（§1.5）。
      ⚠️ **第 9 轮独立评审改准：声明形态这一半已由人裁死，本项不重裁**（Minimum Rule 9 的 `constrained` 档）。
      **D-25 逐字**：`[project.optional-dependencies]` 的 `ui = ["playwright>=1.47"]`，
      **`[project].dependencies` 一个字不加**；且 `d69b335` **已经落盘**（§1.5 实读确认）。
      ⇒ **`D-d-2` 今天要交的是三件，不是「选一个驱动」**：
      **(i)** 记录**选中 (a) playwright、否决 (b)(c)(d) 的理由**（(c) 撞硬约束①、(d) 引第二套运行时，两条起草期已否；
      (b) selenium 是**被 D-25 的形态排除的** —— extra 里逐字只有 `playwright`，改选它等于改 D-25，红线 3）；
      **(ii)** 记录**残余风险两条**：① `ui` extra **不含 `pytest-playwright`** ⇒ 断言体不许依赖它（`D-d-3` ⑥ / §1.4b），
      本机那份是「碰巧装着」；② `ui` extra **不含浏览器二进制** ⇒ `python -m playwright install chromium` 是**另一件事**
      （D-25 逐字「装包不等于能跑」），它的时间成本由本 Phase 之外那条新增 `Proof` 实测；
      **(iii)** 记录**`playwright>=1.47` 是浮动下界**这一处残余：本机是 `1.58.0`，CI 上会装当时的最新版，
      而 `playwright install chromium` 装的 chromium 版本**由 playwright 包版本决定** ⇒
      **本 plan 不去钉版本**（钉它要改 `pyproject.toml` 里人刚落的那一行，属重开 D-25 的形态裁定），
      只把这一处**照实登记**进探测记录与交接项 (2)。
      ⚠️ **「人不批怎么办」那条出口今天已经用不上了（人已批），但规则保留**：
      三处出处若届时都不在 ⇒ 停机分支 4 重新触发，出口仍是 §11 登记 + 判据先建后绿。
      - Skill: `none`
- [x] **`D-d-3` 零 skip 怎么做到**（`Decision`）。⚠️ **起草期第一版这条是错的，独立评审实读打回，下面是改准后的形态。**

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
- [x] **`D-d-4` 快捷键**（`Decision`，依赖 `H3` 的实际值）：`Cmd/Ctrl+K` 与 Desk 原生绑定是否冲突、
      冲突时选谁。**不抢已被占用的键**（见 `H3` 的「不吻合怎么办」）。
      同时裁死**关闭方式**（至少 `Esc` + 再按一次同一组合键）与**焦点归还**
      （关闭后焦点回到唤起前那个元素 —— 不还焦点在单据页上是实实在在的可用性缺陷）。
      - Skill: `none`
- [x] **Proof**：探测记录 `docs/analysis/2026-08-25-1743-desk-sidebar-probe.md` 落盘，
      含 **`H1` / `H2` / `H2b` / `H3` / `H4` / `H5` 六格**的命令原文 + 退出码 + 实际值，
      与 **`D-d-0` … `D-d-4` 五条**裁定的完整理由。
      ⚠️ **第 8 轮独立评审改准：旧文写的是「`H1`–`H5`」与「四条裁定」** ——
      `H2b`（第 6 轮补进 Phase 1、且是 `H3`/`H4` 的硬前置）与 `D-d-0`（第 2 轮补、且是 `D-d-1`/`D-d-2` 的前置）
      **都被这条 Proof 漏在外面**，而探测记录正是它们唯一的落盘处
      ⇒ 照旧文走，两件在范围内的活会「做了但无处存证」，撞指南 Minimum Rule 10。
      **本条与同 Phase 那两条 Exit Criteria（六格 / 五条）现在逐字一致。**
      - Skill: `none`

**⚠️ Phase 1 的四条停机分支（触发即停，写进 `STATE.md` §3 needs-human，不自行绕过）**
（iteration 1 新增了第 4 条之后这里仍写着「三条」，第 3 轮独立评审改准）：

1. **`H2` 不吻合**（驱动不可用）⇒ 依赖决策归人。
2. **`H6` 若在 Phase 3 不吻合**（浏览器不带 `sid`）⇒ D-19 的同源假设需人重裁（红线 3，loop 无权开 `R-x`）。
3. **`D-d-1` 裁到 (C)**（即：论证下来只有改 `gates.yml` 一条路）⇒ **红线 2，立即停机交人**。
4. ⚠️ **`D-d-2` 裁定为「必须引第三方浏览器驱动」时也停一次**（独立评审打回后新增；起草期漏了这条）。
   前一个 plan `1615-1` §11 第二条逐字：「那是一次**需人拍板的依赖决策**……**本 plan 只指明，不代人选**」。
   ⇒ **`H2` 吻合（驱动可用）不是免停理由** —— 恰恰是「结论已确定」的那一刻。
   **唯一的免停条件**：能指出**人已批准**的具体出处（commit / `STATE.md` 里的 `[resolved]` 行 / `Gates-Change-Approved-By` trailer）。
   **指不出就是没批，不许用「本机已经装着」当批准。**

   ✅ **这条免停条件在 2026-08-26 已经满足，本分支因此不触发**（第 9 轮独立评审实读，出处见 §0.5 前置①）：
   `DECISIONS.md` **D-25** · `STATE.md:425` 的 **`[resolved] 2026-08-26T01:47Z`** · commit **`d69b335`**。
   ⇒ **执行期不必再往 `STATE.md` 追加那条 needs-human，也不必停**；
   `pyproject.toml` 那件事**人已经做完了**，本 plan 只复核不改（Phase 3 该项已由 `Add` 改成 `Proof`）。
   ⚠️ **但免停是「实读到出处」换来的，不是本行写着就算**：执行期按 §0 第 4 条 (b) **重取一次**；
   **三处出处若届时都不在了（例如被 revert），本分支重新 100% 触发，照上面的原文走。**

Exit Criteria:

- [x] `H1` / `H2` / **`H2b`** / `H3` / `H4` / `H5` **六格**各有**实际值**（不是「预计」「应该」），且与 §6 预测列逐条对照过
      （⚠️ 第 6 轮补进 `H2b`：它是 `H3` / `H4` 的硬前置，前五轮只挂在 Phase 3 上）
- [x] **`D-d-0`** / `D-d-1` / `D-d-2` / `D-d-3` / `D-d-4` **五条**裁定各有：选中项、被否项、**否决依据是执行期探针还是外部规则（写明哪一条）**、残余风险
      （⚠️ **第 6 轮补进 `D-d-0`**：它是 Phase 1 的执行项、且被写死为 `D-d-1` / `D-d-2` 的**前置**，
      前五轮却不在任何一条 Exit Criteria 里 —— 指南 Minimum Rule 10「在范围内的项必须落在四态之一」。
      ⚠️ **第 9 轮改准：`D-d-0` 与 `D-d-2` 的「选中项」这一半已由人裁定**（`stale` / `ui` extra，见 §0.5），
      ⇒ 这两条落 `constrained` 档，**执行期交的是「记录裁定 + 出处 + 残余风险」，不是重新分类/重新选型**；
      **仍然不许拿「反正它写着 Playwright」当依据** —— 依据必须是 D-25 或那条 `[resolved]` 行的实读原文）
- [x] 落点节 `docs/architecture/module-boundaries.md` **§7.23** 建好；`§7.13/§7.20/§7.21/§7.22` 经 `git diff` 确认**零行改动**
- [x] `docs/logs/2026/<执行当天>.md` 追加 Phase 1 条目 —— ⚠️ **第 9 轮改准：旧文写死 `08-25.md`，而起草日已过、今天是 `2026-08-26`** ⇒ **按执行当天的日期建/追加**（指南 When Executing 第 9 条：日志与 plan 进度同步；跨天的 Phase 各自入自己那天的文件，不许回写到起草日）

### Phase 2 — 侧边栏本体 + 离线判据（不需要浏览器就能判的那一半）

Status: completed
Targets: `agenerp/serve/assets/desk.js` · `tests/unit/test_desk_sidebar_static.py`（新建）
Skill: `none`

- Item Types: 逐项标注为准（本 Phase 共 **6** 项：`Add` **3** · `Proof` **3**）。
  ⚠️ **第 9 轮独立评审改准：旧文写「5/6 项是 `Add`」，实数是 3/6** —— 远不足 80% 阈值，不作 Phase 级统一声明。
- Prereqs: Phase 1 四条裁定全部落定

- [x] **`Add`** `desk.js` 扩成侧边栏本体，**六件事**：① 注册 `D-d-4` 裁定的快捷键（唤起 / 关闭 / `Esc` / 焦点归还）；
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
      ⚠️ **理由第 7 轮改准，旧文不留**（`~~面板把响应体原样铺开，等于把一个正在被调查的疑似 `sid` 外泄缺陷复制到界面上~~`
      —— 那条红已被人查明是「`frontend` 够不到」，与 `sid` 无关，见 §1.8b / §0.7 (丙)）。
      **改准后的两条理由都不依赖 CI 现状**：**(i)** `sid` 是 `HttpOnly`，其存在意义就是不进 JS 可读面、更不进 DOM；
      把整份响应铺进 DOM 等于**自己造一个绕过 `HttpOnly` 的显示面**。**(ii)** 与 `H8c` / `M11` 同一条约束的两面 ——
      **真 nginx 502/504 回默认 HTML 不回 JSON**，任何「把响应体当结构化数据铺开」的写法在真 502 上都会抛，
      正好落进 Goal 2 禁止的空白。**禁令本身与 `M16`、判据⑤ 一个字不改。**；
      ⑥ **保留既有资产判据钉着的四格**：`len>200` · `agenerpDesk` · **`Object.freeze`** · **结尾逐字 `)();`**
      （`test_desk_asset_route.py:165-168`）。
      ⚠️ 面板要挂状态时最容易顺手去掉的是 `Object.freeze` —— **挂状态请另起一个不冻结的内部变量，
      别把标记对象解冻**。
      ⚠️ **结尾那格是「判据钉死的形状」，不是风格偏好**（独立评审 iteration 2 补）：
      面板要注册 `document.addEventListener`、要拆成多个内部函数，收尾很容易在格式化时变成别的写法。
      **整份资产必须仍是一个以 `)();` 逐字收尾的 IIFE。**
      `version` 往上走一格、`plan` 改成本 plan 号。
      - Skill: `none`
- [x] **`Add`** 判据 `tests/unit/test_desk_sidebar_static.py` —— **离线、零浏览器**，守**五**件事（第 5 轮独立评审把「响应体不外泄」补成第 ⑤ 件）：
      ① 资产里出现的请求路径与 `app.py` 的 `EXPLAIN_PATH` **各读一次再比**（**不写第三个字面量**，沿用 §7.22 口径）；
      ② 资产里出现的请求体键名集合 ⊆ `app.py` 的 `ALLOWED_BODY_KEYS`，**且与五个越权键的交集为空**
      （两个集合都从 `app.py` 读，不在判据里抄）；
      ③ `window.agenerpDesk` 标记仍在；
      ④ **九个可分辨的已枚举码的字面量在资产里各出现过**（§1.3 计数口径；`502` 只需出现一次）
      —— 挡「只写了 200 分支」的半成品；
      ⑤ ⚠️ **响应体不外泄（第 5 轮独立评审补；⚠️ 第 8 轮独立评审实读改准了它的写法，旧文不留）**：

      > ~~资产源码里 **`JSON.stringify(` 与 `innerHTML` 零命中**，且 **`document.cookie` 零命中**。~~

      **为什么改**：`JSON.stringify(` **零命中做不到，而且不该做到** —— 实读
      `agenerp/serve/app.py:145` 的 `parse_request()` 逐字 `payload = json.loads(raw.decode("utf-8"))`
      ⇒ **请求体必须是 JSON**，而本 Phase 第 ③ 件事写死了同源 `fetch(..., {method:"POST", ...})`
      ⇒ **desk.js 必然要 `JSON.stringify` 一次来拼请求体**。
      旧写法等于**同一个 Phase 里第 ③ 件事和判据⑤ 互相否决**（同第 3 轮打回的那个「两条判据互相否决」的死角），
      执行期只剩两条出路：要么违反判据、要么手工拼 JSON 串（转义一错就是静默 400，**比它挡的那件事更糟**）。

      **改准后写死三格**（口径都仍是**纯文本**，可离线判定）：
      **⑤a 渲染面 sink 零命中**：`innerHTML` / `outerHTML` / `insertAdjacentHTML` **各零命中**
      —— 建 DOM 只走 `textContent` / `createTextNode`（这是正路，不是变通）；
      **⑤b `document.cookie` 零命中**；
      **⑤c `JSON.stringify(` 命中次数 ≤ 1** —— **1 次是正常的**（拼请求体，见上），
      **2 次起必有一次落在渲染面**（⑤a 只挡 `innerHTML` 一族，挡不住 `el.textContent = JSON.stringify(resp)`，
      而那同样是「把整份响应铺进 DOM」）。
      ⚠️ **≤1 是下限不是等价物**：它挡不住「逐字段拼接出来的等价泄漏」，那一半由 `M16` 与 `H8`
      的「每一条只含该码字面量 + 已知键」承担（同下）。
      ⚠️ **这三格同样是文本下限、不证运行时行为**（与本判据其余各条同口径）：
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
- [x] **`Proof`** 既有 22 条（`test_desk_asset_route.py` / `test_desk_injection_static.py`）**一条不许改松**，
      跑一遍确认仍全绿 —— 尤其那条「服务发出的体与仓里那份**逐字节相同**」（改了 `desk.js` 之后它必须仍绿）。
      - Skill: `none`
- [x] **`Proof`** `ruff check` 跑一遍**现有七个目录**（`agenerp tests/unit tests/contracts tests/tools tests/routing
      tests/context tests/experiments`）仍 exit 0。⚠️ **本 Phase 不把 `tests/ui` 加进参数** ——
      那个目录要到 Phase 3 才建，此时传进去 ruff 会因路径不存在直接报错
      （第 3 轮独立评审补：前两版把它写在 Phase 2，会造一条假红）。
      `tests/ui` 从 **Phase 3 起**进参数，见 §10 verification 那条**九**命令清单（⚠️ 第 6 轮由「七」改准成「八」，第 8 轮把 §1.4b 那条拆成 (A)(B) 后成「九」）。
      ⚠️ `ruff` 的 `exclude` 只排除 `tests/gates`，**`tests/ui` 建起来之后会被真扫**，别指望它被跳过。
      - Skill: `none`
- [x] **`Proof`** `python3 -m pytest tests/unit -q` 只增不减；`check_expected_red.py` 仍 exit 0。
      - Skill: `none`
- [x] **`Add`** 落点节 §7.23 补「渲染状态机」那一格：**九个可分辨的已枚举码 + 200 + 一条兜底态**的映射表
      （并写明 §1.3 那条计数口径：十种来源 → 九个码，两个 `502` 合并且**合并是正确的**），
      与 §1.3 的服务端表**逐条对齐**。
      ⚠️ **这张表必须写成「开放枚举 + 兜底」，不许写成封闭枚举** —— 它是要落进 owner doc 的**持久制品**，
      把封闭枚举写进架构文档，等于把「真实 500/504 渲染成空白」这个失败形态**固化成规范**
      （第一版正是在这里漏改，独立评审 iteration 2 打回）。
      同时写明维护义务：**服务端加一种码，这张表跟着加一行；但兜底态在任何时候都不许删。**
      - Skill: `none`

Exit Criteria:

- [x] ⌘K（或 `D-d-4` 裁定的键，冲突时写死为 `Cmd/Ctrl+Shift+K`）唤起 / 关闭 / `Esc` / 焦点归还四条行为**都在代码里**，不是只有函数签名
- [x] 失败模式说清：**九个可分辨的已枚举码各自的可见态互不相同、非空、不 spinner**（与 `200` 一起共 10 条两两不等），**且兜底态接得住未枚举的码**；成功模式：200 时渲染 `answer` 与 `cost`
- [x] ⚠️ **响应体不外泄**：面板任何一态都不把响应体原样倾泻进 DOM（渲染只取 §1.3 四个已知键 + 状态码本身），判据⑤ 的三格源码守卫全绿 —— **⑤a** `innerHTML` / `outerHTML` / `insertAdjacentHTML` 零命中 · **⑤b** `document.cookie` 零命中 · **⑤c** `JSON.stringify(` **命中 ≤ 1 次**（⚠️ 第 8 轮独立评审改准：**不是零命中** —— 请求体必须是 JSON，见 `app.py:145`）（§1.8b / R9）
- [x] 新判据 `tests/unit/test_desk_sidebar_static.py` 全绿；既有 22 条**零改动**（`git diff` 证）
- [x] `docs/architecture/module-boundaries.md` §7.23 的状态机表落地
- [x] `docs/logs/2026/<执行当天>.md` 追加 Phase 2 条目 —— ⚠️ **第 9 轮改准：旧文写死 `08-25.md`，而起草日已过、今天是 `2026-08-26`** ⇒ **按执行当天的日期建/追加**（指南 When Executing 第 9 条：日志与 plan 进度同步；跨天的 Phase 各自入自己那天的文件，不许回写到起草日）

### Phase 3 — `tests/ui/test_sidebar.py` 活体门禁 + 变异自查 + 交接

Status: planned
Targets: `tests/ui/test_sidebar.py`（新建，加载器）· `tests/unit/test_desk_sidebar_body.py`（新建，断言体）·
**`tests/unit/test_desk_sidebar_static.py`（Phase 2 建的那份，本 Phase **追加**四条源码级守卫；第 4 轮独立评审补）** ·
**`pyproject.toml`（⚠️ 第 9 轮改准：`ui` extra 已由人在 `d69b335` 落盘 ⇒ 本 plan 对它是**只读复核**，
一个字节不改，见本 Phase 那条 `Proof`）** · `docs/evidence/p1-desk-sidebar/README.md`（新建）·
**`docs/context/project-context.md`（第 52 行 Lint / static check 那一格的作用域漂移，`Fix`，见本 Phase 交接项 (5) 下方；
第 3 轮独立评审补 —— 前两轮把这件事写进了正文却漏进 Targets）**
Skill: `closure-audit-prompt.md`（仅收口那一步）

- Item Types: 逐项标注为准（本 Phase 共 **10** 项：`Proof` **6** · `Add` **3** · `Fix | Follow-up` **1**）。
  ⚠️ **第 9 轮独立评审改准：旧文写「5/7 项是 `Proof`」，当时实数是 4/9；本轮把 `pyproject` 那项由 `Add` 改成 `Proof`
  并新增一条 `Proof`（装驱动的时间成本实测）⇒ 今天是 6/10** —— 不足指南 Minimum Rule 7 的 80% 阈值，
  故**不作 Phase 级统一声明**，以每一项自己的类型标注为准。
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
      运行时那一半由本 Phase 的 **(A)(B) 两条实跑**（§1.4b）与 `M13`–`M15` 承担，**这一份不承担、也不假装承担。**
      - Skill: `none`
- [ ] **`Proof`** ⚠️ **模拟 runner 上没装驱动 —— 两条命令，各证一件事**（§1.4b，第 8 轮独立评审实跑改准；
      **原来只写 (A) 一条、且期望写成「全部 `skipped`」，那在本机不可满足**）：
      **(A)** `python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`
      ⇒ **必须 exit 0、零 `error`**（**不断言全 `skipped`**）—— 证「不吃 `pytest-playwright` 的 fixture」；
      **(B)** `mkdir -p /tmp/agenerp-nodriver && printf 'raise ImportError("simulated: playwright not installed")\n' > /tmp/agenerp-nodriver/playwright.py && PYTHONPATH=/tmp/agenerp-nodriver python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright -rs`
      ⇒ **必须 exit 0、全部 `skipped`、零 `error`** —— 证「驱动不在时走 `_unavailable` 而不是 `error`」。
      **两条的命令原文与退出码都入证据文件。**
      **任一条不退 0 / (A) 出 `error` / (B) 出 `error` ⇒ 今天绿着的 `unit-and-contracts` 会在下一次推送时红，
      而那是纯回归、不是设计内的代价**（与 §1.4 那条红分开算，见 §1.4b）。
      - Skill: `none`
- [ ] **`Proof`** ⚠️ **`pyproject.toml` 的 `ui` extra —— 人已在 `d69b335` 落盘，本项由 `Add` 改成 `Proof`**
      （第 9 轮独立评审改准；旧文是「**`Add`** 加 `[project.optional-dependencies]` 的 `ui` extra」，
      **照旧文走要么写出第二个同名 TOML 表 ⇒ 解析报错，要么发现「已经有了」而无处存证**）。
      **本项要做的是复核 + 存证，一个字节都不改 `pyproject.toml`**：
      ① `grep -n -A6 'optional-dependencies' pyproject.toml` ⇒ 实读到 `ui = ["playwright>=1.47"]`；
      ② `python3 -c "import tomllib,pathlib;d=tomllib.loads(pathlib.Path('pyproject.toml').read_text());
      print(d['project']['dependencies'], d['project']['optional-dependencies'])"`
      ⇒ **`dependencies` 仍逐字只有 `certifi>=2024.2.2`**（D-25 的硬边界）；
      ③ `git diff --name-only <本 plan 基线 sha>..HEAD -- pyproject.toml` ⇒ **无输出**（本 plan 未改它的自证）。
      **三条的命令原文与输出入证据文件。**
      ⚠️ **`[tool.pytest.ini_options]` 的 `testpaths` / `markers` 与 `ruff` 的 `exclude` 同样一个字不动**
      （`live` marker 已注册、`testpaths = ["tests"]`、`exclude = ["tests/gates"]`，均已实读确认）。
      ⚠️ **不在仓里了（被 revert）⇒ 停机分支 4 重新触发**，不许自己补写那一段。
      - Skill: `none`
- [ ] **`Proof`** ⚠️ **装浏览器二进制的时间成本实测 —— D-25 逐字压给 loop 的一件活**
      （第 9 轮独立评审新增；D-25「未决」栏与 `STATE.md:428` ③ 逐字：「**CI 装 chromium 会显著拉长 `gates-l2-live`**……
      **由 loop 在 plan 里给方案并实测，不要默认塞进现有 job 就完事**」）。
      **它是在范围内的活，不是 follow-up** —— 旧版交接项 (2) 只写「装 `ui` extra 并 `playwright install --with-deps chromium`」，
      **那正是 D-25 点名禁止的「默认塞进现有 job 就完事」**。
      **写死三步，全部离线、零红线面**：
      **(a)** `python3 -m playwright install --dry-run chromium` ⇒ 抄下**安装位置与下载 URL**
      （实读确认该命令可用、exit 0）；
      **(b)** **冷装一次并计时**：`PLAYWRIGHT_BROWSERS_PATH=/tmp/agenerp-pw-cold /usr/bin/time -p
      python3 -m playwright install chromium` ⇒ **墙钟秒数 + 下载字节数**（`du -sh /tmp/agenerp-pw-cold`）逐字入证据文件。
      ⚠️ **必须用临时 `PLAYWRIGHT_BROWSERS_PATH`，不许污染 `~/Library/Caches/ms-playwright`**（那是 `H2` 的判定面）；
      跑完 `rm -rf /tmp/agenerp-pw-cold`。
      ⚠️ **拿不到网络就照实记 `verification scope limited`**，只交 (a) 的下载体积推算，**不许拿本机已缓存的秒数冒充冷装**。
      **(c)** 用 (b) 的数**给出至少两个方案并各写一句代价**（交接项 (2) 照抄它，不许只给一句「装上去」）：
      **方案一** 塞进现有 `gates-l2-live`（最简单，代价 = 每次 run 多这么多墙钟）·
      **方案二** 单独 job + artifact/缓存（`actions/cache` 键为 playwright 版本，代价 = 多一个 job 与缓存失效时的回退成本）·
      **方案三** 只装 `chromium-headless-shell`（体积更小，代价 = 与本 plan 断言体实际启动的浏览器形态必须一致，否则 CI 与本机不同源）。
      ⚠️ **本项只给方案与数，不动 `.github/workflows/**` 任何一个字节**（红线 2）—— **选哪个方案归人。**
      - Skill: `none`
- [ ] **`Proof`** 跑 WBS 那条命令原文：`AGENERP_LIVE=1 AGENERP_HTTP_PORT=18080 AGENERP_ADMIN_PASSWORD=admin
      python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` ⇒ **必须 exit 0 且零 skip**。
      **退出码与输出逐字抄进 `docs/evidence/p1-desk-sidebar/README.md` 与收口表。**
      - Skill: `none`
- [ ] **`Proof`** 不回归三条：`H10`（停 `agenerp-serve` 后 frontend 仍 healthy）· `H11`（`down -v` 冷起 exit 0）·
      零依赖启动门禁 `tests/unit/test_compose_zero_dep.py` 全绿**且一条未改松**。
      - Skill: `none`
- [ ] **`Proof`** **变异自查**：`M1`–`M16` **十六条**，其中 **`M13` 与 `M16` 各有两个变体**（`13a/13b`、`16a/16b`，
      打红面各不相同，见下）⇒ **实际施加 18 次**；逐次施加、逐次确认**被打红**、逐次复原并 `sha256` 校验 `RESTORED OK`。
      ⚠️ **第 8 轮独立评审改准计数**：旧文这里写「写死的十五条」而其下逐条列的是 `M1`–`M16` **十六**条
      —— 与本文件反复挡的「正文写四条实列六条」是同一族计数不一致，照实改准。
      逐条写死如下：`M1` 删掉快捷键注册 · `M2` 把 503 分支渲染成空字符串 · `M3` 把 401 与 503 渲染成同一句话 ·
      `M4` 请求体里偷偷加一个 `user` 键 · `M5` 把 `credentials` 改成 `omit`（`sid` 不再自动带）·
      `M6` 把请求路径改成 `/agenerp/explain2` · `M7` 把加载器里的 `skip→fail` 收严去掉 ·
      `M8` 把 `window.agenerpDesk` 标记删掉 · **`M9` 删掉渲染状态机的兜底分支**（`H8b` 那格必须打红）·
      **`M10` 把断言体里的 fixture 级 skip 改回模块级 skip**（`D-d-3` ①② 那条必须打红 ——
      这一条专挡「绿着的、不存在的门禁」那个失败形态）·
      **`M11` 让兜底分支假设响应体是 JSON**（`H8c` 那格必须打红 —— 专挡「真 nginx 502 上 `r.json()` 抛出、
      面板空白，而所有打桩判据全绿」）·
      **`M12` 把资产结尾从 `)();` 改成 `})();\n// end`**（`test_desk_asset_route.py:168` 必须打红 ——
      现有 `M1`–`M11` 没有一条守它）。
      **`M13` 两个变体分开施加、打红面不同**（⚠️ 第 8 轮独立评审实跑改准 —— 旧文把两者都记在 (A) 头上，其中一半是假的）：
      **(13a)** 把断言体改成用 `pytest-playwright` 的 `page` fixture ⇒ **命令 (A)** 必须打红
      （实跑形态：`1 error` / `fixture 'page' not found`），且源码守卫 ③ 必须打红；
      **(13b)** 在断言体**模块顶层** `import playwright` ⇒ ⚠️ **命令 (A) 对它无感**（本机装着，导入成功），
      打红面是**命令 (B)**（遮蔽模块 ⇒ 收集期 `ImportError`）**与源码守卫 ②**。
      —— 两个变体合起来专挡「本机绿、runner 上 `unit-and-contracts` 红」这个纯回归（§1.4b）·
      **`M14` 从加载器里删掉任意一条 `test_` 重绑** ⇒ 源码守卫 ④ 必须打红
      —— 专挡「漏重绑 ⇒ `no tests collected` / 静默少跑」（`D-d-3` ⑤）·
      **`M15` 在断言体里直调一次 `pytest.skip(...)` 绕过 `_unavailable`** ⇒ 源码守卫 ① 必须打红
      —— 专挡「收严间接层被绕过 ⇒ 门禁上又出现 skip」（`D-d-3` ④）。
      **`M16` 把某一态改成把整个响应体倾泻进面板 —— ⚠️ 第 8 轮独立评审拆成两个变体，各自的打红格不同**
      （旧文只写 `innerHTML` 那一种，而判据⑤ 改准后 `JSON.stringify` 不再是零命中 ⇒ 必须点名是哪一格打红）：
      **(16a)** `el.innerHTML = JSON.stringify(resp)` ⇒ **判据 ⑤a 必须打红**（`innerHTML` 由零变一）；
      **(16b)** `el.textContent = JSON.stringify(resp)` ⇒ **判据 ⑤c 必须打红**（`JSON.stringify(` 由 1 次变 2 次）
      —— **(16b) 是第 8 轮新补的，它正是「改准判据⑤ 之后唯一还能钻的那个洞」**，
      不施加它就等于把 ⑤c 那格的 `≤ 1` 写成没人验过的空话。
      两个变体都属**第 5 轮补的那条禁令**（Phase 2 ⑤）——
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
      **(2)** ⚠️ **第 9 轮独立评审改准，旧文不留** —— 原文是「~~在 `gates-l2-live` 里装 `ui` extra 并
      `playwright install --with-deps chromium`~~」，**那正是 D-25 逐字点名禁止的「默认塞进现有 job 就完事」**。
      改准后交出去的是**三个方案 + 本 plan 实测的墙钟与体积**（由本 Phase 那条 `Proof` 产出）：
      方案一塞进现有 job · 方案二单独 job + 缓存 · 方案三只装 `chromium-headless-shell`，**各带一句代价**；
      **选哪个归人**。同时逐字交代 D-25 的两条边界：**装包不等于能跑**（还要 `playwright install chromium`）·
      **`ui` extra 不含 `pytest-playwright`**（本 plan 的断言体本来就不依赖它，`D-d-3` ⑥）·
      以及 `playwright>=1.47` 是**浮动下界**这一处残余（`D-d-2` (iii)）；
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
      **再加一件需人裁的**：`D-d-4` 若因 `H3` 冲突改成 `Cmd/Ctrl+Shift+K`，与 WBS 第 89 行「⌘K」字面的偏差归人。
      ⚠️ **六件全部落在 `.github/workflows/**` 里 ⇒ 红线 2，本 plan 一个字节都不碰，只写清楚交出去。**
      ⚠️ **交出去之前先读 §0.6**：评审期工作树里那份 `gates.yml` 已有**人侧未提交**的改动，
      交接文字里的行号必须**执行期按注释原文重取**（§0 第 5 条），不许照抄本文件写的数字。
      **同时往 §3 追加一条 `[Proof]` 证据行**（本 plan 的落地 sha + 命令原文 + 退出码）。
      - Skill: `none`

Exit Criteria:

- [ ] `AGENERP_LIVE=1 … pytest -m live tests/ui/test_sidebar.py -q -rs` → **exit 0，零 skip**（命令原文 + 退出码入证据文件），
      **且收集到的条数 > 0 并等于断言体里 `test_` 函数的条数**（`D-d-3` ⑤ —— `no tests collected` 退 5，
      「零 skip」这句话在一条都没跑的情况下也成立，**必须由条数把它钉住**）
- [ ] §1.4b 的**两条**命令都已实跑并入证据文件（第 8 轮独立评审改准，原来只有一条且期望不可满足）：
      **(A)** `… -q -p no:playwright` → **exit 0、零 `error`**（**不断言全 `skipped`** —— 本机装着驱动时它会真跑，那是合法的）；
      **(B)** `PYTHONPATH=/tmp/agenerp-nodriver … -q -p no:playwright -rs`（遮蔽 `playwright` 包）→ **exit 0、全 `skipped`、零 `error`**
      （§1.4b —— 两条合起来才证明 `unit-and-contracts` 在无驱动 runner 上不会被本 plan 弄红）
- [ ] `H6` 有**直接观测值**：浏览器发出的请求带上了 `sid`（回的不是 401）—— 本仓第一次
- [ ] `H2b` 的实际值（Phase 1 已测出、已落进探测记录）**确已被自建 fixture 采用**：
      浏览器到底怎么够到 `frontend` 站（默认站回落 / `--host-resolver-rules`），fixture 里用的与探测记录里记的**是同一条**
- [ ] ⚠️ **`pyproject.toml` 的 `ui` extra 已复核且本 plan 零改动**（第 9 轮新增）：三条命令的原文与输出入证据文件
      （`grep` 实读到 `ui = ["playwright>=1.47"]` · `tomllib` 读出 `dependencies` 仍只有 `certifi>=2024.2.2` ·
      `git diff --name-only <基线sha>..HEAD -- pyproject.toml` **无输出**）
- [ ] ⚠️ **装 chromium 的时间成本已实测并折成方案**（第 9 轮新增，D-25 逐字压给 loop 的活）：
      `--dry-run` 输出 + **冷装墙钟秒数 + 下载体积**（用临时 `PLAYWRIGHT_BROWSERS_PATH`，跑完已清理）入证据文件；
      交接项 (2) 里**至少三个方案各带一句代价**，且**没有替人选**。
      ⚠️ 拿不到网络 ⇒ 逐字记 `verification scope limited`，**不许拿本机已缓存的秒数冒充冷装**
- [ ] `H7b` 有**实际值**：起栈前 `AGENERP_LLM_*` 的**个数与变量名**（不含值）已记；走了哪一支已记。⚠️ **走 (乙) 支时，「本轮真实烧掉一次解释（中位约 11 万 token）」必须逐字落进证据文件与收口表**，**不许写成零成本**（§5 / R8）
- [ ] 变异表 `M1`–`M16` **十六条 / 18 次施加**（`M13`、`M16` 各两变体）逐次有结论（打红 / 未打红 + 处置 + **是哪一格打的红**），全部 `RESTORED OK`
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
- [ ] `docs/evidence/p1-desk-sidebar/README.md` 落盘；`docs/logs/2026/<执行当天>.md` 追加 Phase 3 条目（⚠️ 同上，第 9 轮改准，不再写死 `08-25.md`）

## 8. 风险

- **R1 · `tests/ui/` 让 CI 第 ⑦ 步变红（已知、已裁、已交接）。** 见 §1.4 与 Phase 3 交接项。
  ⚠️ 这是本 plan **明知会发生**的代价，不是意外。`AGENTS.md` 裁判规则 4 的停机条件含「CI 连续 2 轮红」——
  ⇒ 交接文字必须让人**一次就能修完**，且 §11 写死重开事件。
- **R2 · 真浏览器实证第一次做，失败形态未知。** 本仓零先例（§1.8）。
  处置：`H6` 不吻合当场停机交人（Phase 1 停机分支 2），**不猜根因**（裁判规则 3）。
- **R3 · ~~判据建在 503 分支上~~ ⇒ 「答得对」完全没测。**
  ⚠️ **第 7 轮独立评审改准前半句，旧文不留** —— 第 5 轮已把 §1.7 改成「**不许把 503 钉死进断言**」
  （判定环境自 `e3afd77` 起是**配着** AI 变量的，钉死 503 就是一条会因环境变好而变红的判据）。
  ⇒ **正确的说法是：判据建在「不需要模型答对」的那一半上** —— 唤起 / 上下文 / `sid` 那一跳 /
  **把实际拿到的那个码渲染成可分辨的非空态**（`page.expect_response` 先观测、再断言对应态）。
  **结论一个字不变**：「答得对」在本 plan 里**完全没测**，这是**有意的收窄**（§1.7 / Non-Goals 4），不是遗漏。
  收口文字里**不许**把「面板显示了答案」写成「Agent 答对了」。
  ⚠️ 这与 §0.7 (丙) 同族 —— **前六轮改了活事实、没扫干净引用它的下游条目**，本轮一并扫掉。
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

- **R9 · ~~P1.8a 那条安全面的红与本 plan 的交付面在同一条链上~~ → 前提已被人查明推翻，风险形态跟着变了**
  （第 5 轮提出，**第 7 轮独立评审实读改准，旧文不留**，§1.8b / §0.7 (丙)）。
  第 5、6 轮据以立此条的推测是「不排除某条错误路径把 `sid` 带了出去」。
  **人已把该红查到根**：断言正文逐字「`127.0.0.1:8080` 够不到（timed out）—— 同源前端没在跑」，
  **服务容器正常、掉的是 `frontend`**（`02-WBS.md:88` 新拆的 `P1.8a-fix` 行）⇒
  **那是起栈时序缺陷，与 `sid` 外泄无关，也与本 plan 的渲染面不在同一条链上。**
  ⇒ **本条作为「安全面同链风险」不再成立，照实降级并说明**：
  它留下的**真**残余只有一条 —— **Phase 2 ⑤ 的禁令仍然必要，但必须靠自身理由站住**
  （`HttpOnly` 的存在意义 + 真 502 不回 JSON，见 §1.8b 改准后的 (i)(ii)），
  **不许再拿「那条红」当它的依据** —— 那条依据今天是假的。
  Phase 2 ⑤ 的禁令 + 判据⑤ 三条源码守卫 + 变异 `M16` **一个字不改**。
  ⚠️ **本 plan 不去修它、不去碰那份门禁**（红线 1），**不声称、也不许在收口文字里暗示自己澄清了那条红**。
  ⚠️ 它换出来的那条**新**风险（取证面）记在 **R10**，不并进本条。

- **R10 · 本 plan 的活体门禁会复刻 `P1.8a-fix` 那个缺陷的失败形态 —— 一条红长得像「面板坏了」，实际是「前端不在」**
  （第 7 轮独立评审新提，§0.7 (甲)(丙)）。**这是 R9 换出来的那条真风险，不是它的改写。**
  **机制是本 plan 自己设计的，逐条对得上**：`D-d-3` ④ 要求断言体所有「跑不了」的出口走 `_unavailable`（默认 `skip`），
  加载器在 `tests/ui` 那一轮把它**重绑成 `pytest.fail`** ⇒ **「够不到 `frontend`」在 `tests/ui/test_sidebar.py` 上就是一条红**
  —— **与 P1.8a 那条门禁今天在 CI 上红的机制逐字相同**（那份也是 `skip("…够不到…")` 被收严成 `fail`）。
  而人刚刚把这个缺陷单独立成 🔴 `P1.8a-fix`：**间歇、每轮红的那条不固定、本机稳定只在 CI 复现**。
  ⚠️ **两个后果，都要说死**：
  ① **本 plan 的 Exit Criteria 写的是「exit 0 且零 skip」** ⇒ 前端只要在取证那一刻不在，判据就红，
  而**红因与本 plan 的实现毫无关系**；
  ② ⚠️ **更要紧的是误诊面** —— 那条红出现在一份名叫 `test_sidebar.py` 的文件上，
  **第一直觉必然是「侧边栏写坏了」**，而真因是起栈时序。这与 R8 记的那条假红（模型正常作答 vs Playwright 30 秒超时）
  是**同一族**：本仓反复吃亏的「症状指向错误根因」。
  ⚠️ **处置写死三条，不留执行期自选**：
  **(i)** `tests/ui/test_sidebar.py` 红时，**先看失败正文里有没有「够不到」/ `timed out` / 「同源前端没在跑」这一族字样**；
  有 ⇒ **不是本 plan 的缺陷**，按裁判规则 3 **原样复跑一次**，并**当场核一遍** `docker compose ps` 里 `frontend` 的状态；
  **(ii)** 复跑仍红且仍是同一族字样 ⇒ **照实记「不可复现 / 疑似 `P1.8a-fix` 同族」并交人，不许猜根因、不许改判据去绕**
  （改判据绕过去正是 `gates.yml`（按注释原文重取）点名禁止的「把判据调整到迁就环境」）；
  **(iii)** ⚠️ **不许反过来用**：**只有失败正文真的是那一族字样时**才走 (i)(ii)。
  拿「可能是 `P1.8a-fix`」去解释一条**正文写着别的东西**的红，就是给自己的缺陷找现成挡箭牌 ——
  与 §10 那条「不许再拿『那是别人的改动』当解释」是同一条纪律。
  ⚠️ **本 plan 不修 `P1.8a-fix`、不碰它那一行、不声称受它阻塞**（P1.8b 的前置逐字是 `P1.8a`）。
  它的后继归人（`02-WBS.md` 已有独立行，预算独立计）。

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

- **Independent draft review iteration 6: `needs revision`（已就地修完）+ 维持 `可以转 active: no`**
  （mission-driver 评审步，2026-08-25，`HEAD` = `4f81de8`）—— 复核前五轮的 27 条阻塞，并**不受前五轮结论约束**地重审全文。

  **⚠️ 本轮的性质：一半是「第 5 轮修了 A 没修 B」，一半是「五轮都没人看的那两处清单缺口」。**
  第 5 轮把 §1.7 / §5 / `H7b` / R8 整体改成「(乙) 支会真调模型、约 11 万 token、约 50 秒」，
  **但 Non-Goals 6 与 §11 第 2 条仍写着「本 plan 不产生长请求」「造一次真超时要 AI 变量与约 10 万 token」**
  —— 与新写死的 (乙) 支**正面矛盾**，且 §11 那条的**重开事件会被本 plan 自己触发**。
  这与 iteration 2 揪出的「§1.3 改成十种了、Phase 2 与 Non-Goals 1 仍写六种」是**同一族**：
  **改活事实时没有把引用它的下游条目一起扫过。**

  **对前五轮的复核**：27 条逐条实读确认仍在本文件内、未被后续编辑冲掉。
  §0.5 的证据**第五次重跑**：`STATE.md` 全文 **891 行**（第 5 轮 882），`:867` 仍是 `[needs-human]`，
  其后 `:874` / `:884` 两条 `[open]` 事实登记**都不覆盖它**；
  `git log --grep=Approved-By` **31 条**（第 5 轮 30），**无一条涉及浏览器驱动**；
  `grep -rli "playwright\|selenium" docs/masterplan docs/backlog` 仍只命中 `STATE.md` 自己那条 needs-human
  ⇒ **停在 `draft` 的裁定成立，本轮维持。**

  **本轮新提 8 条（2 Blocker + 4 Major + 2 Minor），全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Blocker** | **§11 第 2 条（`proxy_read_timeout 300`）的重开事件会被本 plan 自己触发。** 它逐字写「第一次在配了 AI 变量的活栈上跑一次完整解释的那一刻」，而 §5 / R8 / `H7b` 判「倾向：有 AI 变量」⇒ **(乙) 支下那一刻就在本 plan 执行期内**；同条「造一次真超时要 AI 变量与约 10 万 token」又与 §5「(乙) 支就要烧约 11 万」正面矛盾。**一条被自己触发的 deferral 不成立**（指南：`Deferred But Adjudicated` 必须命名一个会重开它的事件） | §11 第 2 条**整条改写**：按 `H7b` 两支分别裁定 · 写死「50 秒 ≪ 300 秒 ⇒ 碰不到上限，真 504 两支都拿不到」· (乙) 支强制把**墙钟秒数**与「上限仍未验证」逐字入证据文件 · **重开事件改成「第一次出现一次墙钟 > `proxy_read_timeout` 的解释请求」**（本 plan 触发不了） |
  | 2 | **Blocker** | **Non-Goals 6 的理由整句过期**：「~~本 plan 的判据全部落在 503 分支与打桩分支上，不产生长请求~~」—— 第 5 轮已把 §1.7 改成「不许把 503 钉死进断言」、把 §5 改成「(乙) 支会真调模型、约 50 秒」。结论（仍未验证）碰巧还对，**但理由是假的**，而这条理由正是 §11 第 2 条援引的依据 | Non-Goals 6 **改写成按量级说理**：(乙) 支确有一次真请求，**50 秒碰不到 300 秒上限** ⇒ 真 504 仍未验证；并写死「一次正常长度的解释没被掐断 ≠ 300 秒上限被验证了」，禁止收口时把前者写成后者 |
  | 3 | **Major** | **§0 正文与 Phase 1 `Prereqs` 都写「四条」，而 §0 实列六条** —— 第 5、6 条恰恰是第 4 / 5 轮补进来的「重取行号」与「数 AI 变量」。照「四条」跑就正好跳过它们 ⇒ 把 R8 那条假红（Playwright 30 秒默认超时先于模型返回）与行号漂移**原样放回来**。（同 iteration 3 第 4 条「三条停机分支实列四条」的同族） | §0 正文与 Phase 1 `Prereqs` 均改准为**六条**，并写明漏跑第 5、6 条的具体后果 |
  | 4 | **Major** | **`D-d-0` 是 Phase 1 的执行项、且被写死为 `D-d-1` / `D-d-2` 的前置，却不在 Phase 1 任何一条 Exit Criteria 里** —— Exit Criteria 只点 `D-d-1`…`D-d-4`「四条裁定」。违反指南 Minimum Rule 10（在范围内的项必须落在四态之一）与评审口径「Execution Plan covers all checklist items」。（同 iteration 3 第 2 条的同族） | Phase 1 Exit Criteria 改成**五条裁定**并点名 `D-d-0`；同时写死「人没答 ⇒ 记『未满足 · 卡在停机分支 4』，**不许拿「反正它写着 Playwright」填绿**」 |
  | 5 | **Major** | **`H2b` 没有任何执行项负责跑它，却是 Phase 1 `H3` / `H4` 的硬前置。** `H3` / `H4` 逐字要求「真登录进 `/app`、按下组合键」，那一步成立的前提正是 `H2b`（浏览器发的 Host 是 `127.0.0.1:18080`，落不落到 `frontend` 站）。而 Phase 1 Explore 只写「跑 `H1`–`H5` 五条探针」，`H2b` **只挂在 Phase 3**（fixture 参数 + Phase 3 Exit Criteria）⇒ 执行者按清单走会在 **Phase 1 第一天**撞上它、却在 Phase 1 找不到处置 | Phase 1 Explore 改成**六条探针**并写死「`H2b` 必须排在 `H3` / `H4` 之前」+ 处置指回 §6 该行第四列 · Phase 1 Exit Criteria 补 `H2b` · Phase 3 那条 Exit Criteria 改成「**fixture 里用的与探测记录里记的是同一条**」，两处引同一个值、不各测一遍 |
  | 6 | **Major** | **front matter `> Review Hold:` 的活事实全体过期**：`HEAD` 仍写 `c19cf4a`（今天 `4f81de8`）· `STATE.md` 写 882 行（今天 **891**）· `Approved-By` 写 30 条（今天 **31**）。第 5 轮自己在收敛结论里写死「这份 plan 每在 `draft` 上多停一轮，它记的『活事实』就多烂一分」—— **本轮就是那一分** | `> Review Hold:` **整块改准**为第 6 轮实测值 |
  | 7 | Minor | Phase 2 的 ruff 项引「§10 verification 那条**七**命令清单」，而 §10 今天写死的是**八**条（第 4 轮加 `-p no:playwright` 时漏改此处） | 就地改准为「八」 |
  | 8 | Minor | **Phase 3 交接项 (4) 要人「照抄 `gates.yml:492-495` 既有的零 skip 断言形态」，而这一处既不在 §0.6 的行号对照表里、也不在 §0 第 5 条那条 grep 的锚点里** ⇒ 行号已漂（今天在 `:529-530`）而执行者无从重取 | §0 第 5 条 grep 加锚点 `工具执行层门禁出现 skip` · §0.6 对照表补一行（`:492-495` → **`:529-530`**） |

  ⚠️ **本轮实跑复核过的活仓事实**（不采信 plan 自报）：`git status --porcelain` **无输出**、`HEAD` = `4f81de8` ·
  `ls -d tests/*/` 仍是那八个目录 = `gates.yml:597` 的 `COVERED`（`H1` 预测仍成立）·
  `gates.yml:567` 仍只装 `pytest certifi`（**§1.4b 的前提未变**）· `:646` ruff 七个目录 / `project-context.md:52` 三个目录
  （**两处漂移原样还在，交接项 (5a)(5b) 仍成立**）· `check_expected_red.py:73-74` 的判定面仍写死 `tests/gates` ·
  `module-boundaries.md` 现存最末编号节仍是 **§7.22**（`:3820`，全文 4129 行）⇒ **§7.23 仍是正确的下一个编号** ·
  `pyproject.toml`：`dependencies` 仍只有 `certifi>=2024.2.2`、**仍无 `optional-dependencies` 段**、
  `testpaths = ["tests"]` · `markers` 含 `live` · `exclude = ["tests/gates"]` + `force-exclude = true` ·
  `tests/unit/test_desk_asset_route.py:165-168` 四格逐字如 Goal 5 所引 ·
  `docs/skills/` 16 个条目其中一份是 `README.md` ⇒ **15 份提示词**（§4 成立）·
  `gates.yml` 的零 skip 断言实读在 `:529-530`。

  ⚠️ **本轮的 `verification scope limited`，照实写**：**§1.9 那四条基线命令本轮未复跑**
  （`check_expected_red.py` / `pytest tests/unit` / `pytest tests/contracts …` / `ruff check`）——
  第 5 轮跑过且 `HEAD` 之后只落了两个 commit（`2163e19` 改本文件、`4f81de8` 追加 `STATE.md`），
  **两个都不碰产品代码与判据**；即便如此，**§0 第 2 条仍强制执行期重取**，本文件的数字只作对照。
  另：**活栈、浏览器、docker 本轮一概未起**（评审轮不做活体取证）。

  ⚠️ **本轮也复核了三件「不该改」**：**Minimum Rule 4 不该拆**（与前五轮同结论）·
  **Anti-Slacking 禁用词全文零命中**（`optional` 的命中仍全是 TOML 键名 `[project.optional-dependencies]`）·
  **红线合规面**逐项核过三个 Phase 的 `Targets`、§10 六条自证与本轮新增的八处改动，
  **没找出必然越线的藏步**；本轮自身只改了本文件一个文件。

- **Independent draft review iteration 7: `needs revision`（已就地修完）+ 维持 `可以转 active: no`**
  （mission-driver 评审步，2026-08-25，`HEAD` = `caa051e`，工作树**干净**）—— 复核前六轮的 33 条阻塞，
  并**不受前六轮结论约束**地重审全文。

  **⚠️ 本轮的性质：与第 5 轮同族 ——「仓库动了、plan 没跟上」，不是「文本自身的洞」。**
  第 6 轮之后仓库落了 5 个 commit；`git diff --name-only 4f81de8..HEAD` 实读只有**六个文件、无一个是产品代码或判据**，
  **但其中三处是人侧的新裁定，且每一处都正好落在本文件的一段说理上**（整理进**新增的 §0.7**）。

  **对前六轮的复核**：33 条逐条实读确认仍在本文件内、未被后续编辑冲掉。
  §0.5 的证据**第六次重跑**：`STATE.md` 全文 **908 行**（第 6 轮 891），那条 needs-human 已从 `:867` 漂到 **`:875`**，
  状态词仍是 `[needs-human]`；其后 `:882` / `:892` / `:901` 三条**都不覆盖它**；
  `git log --grep=Approved-By` **32 条**（第 6 轮 31），**无一条涉及浏览器驱动**；
  `grep -rli "playwright\|selenium" docs/masterplan docs/backlog` 仍**只命中 `STATE.md` 自己那条 needs-human**，
  `02-WBS.md` / `DECISIONS.md` **零命中**（含本轮新裁的 `D-23` / `D-24`）
  ⇒ **停在 `draft` 的裁定成立，本轮维持。**

  **本轮新提 6 条（5 Major + 1 Minor），全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Major** | **§1.8b / Phase 2 ⑤ / R9 的前提已被人查明推翻。** 三处都写着 P1.8a 那条 CI 红是「安全面、不排除某条错误路径把 `sid` 带了出去、人尚在查因」。**实读两处证据都不支持**：① 人 2026-08-25 新拆的 `02-WBS.md:88` `P1.8a-fix` 行逐字记「断言正文『`127.0.0.1:8080` 够不到（timed out）—— 同源前端没在跑』」「**服务容器自己正常**……**掉的是 `frontend`**」；② 断言体 `tests/unit/test_explain_service_body.py:133` 逐字 `pytest.skip(f"{host}:{port} 够不到（{exc}）—— 同源前端没在跑")`，被 `tests/gates` 那份加载器收严成 `fail`。⇒ **那条红压根没跑到比较响应体那一步**，与 `sid` 外泄无关，**也不与本 plan 的渲染面同链**。这是 iteration 6 第 2 条的同族：**结论（禁令）碰巧还对，理由是假的** | §1.8b 后半段**整段改写**（旧文划掉、两条实读证据摆出、**收回「同一条链上」那句话**）· Phase 2 ⑤ 的理由**改基**为不依赖 CI 现状的两条（`HttpOnly` 的存在意义 / 真 502 不回 JSON，与 `H8c`·`M11` 同族）· **R9 改写并降级** · 新增 **§0.7 (丙)**。⚠️ **禁令本身、判据⑤ 三条源码守卫、变异 `M16` 一个字未改** |
  | 2 | **Major** | **本 plan 的活体门禁会复刻 `P1.8a-fix` 那个缺陷的失败形态，全文零处覆盖。** `D-d-3` ④ 让断言体所有「跑不了」的出口走 `_unavailable`、加载器在 `tests/ui` 那轮重绑成 `pytest.fail` ⇒ **「够不到 `frontend`」在 `tests/ui/test_sidebar.py` 上就是一条红**，**与 P1.8a 那条门禁今天红的机制逐字相同**。而人刚把这个缺陷立为 🔴 `P1.8a-fix`：**间歇、每轮红的那条不固定、本机稳定只在 CI 复现**。⇒ ① Exit Criteria 要 exit 0 零 skip，前端一不在判据就红、且红因与实现无关；② ⚠️ **误诊面更要紧** —— 红出现在一份叫 `test_sidebar.py` 的文件上，第一直觉必然是「侧边栏写坏了」。与 R8 那条假红同族（症状指向错误根因）。**R6 只覆盖「本机 Docker 两处不稳定」，不覆盖这一条** | 新增 **R10**，写死三条处置：(i) 先看失败正文有无「够不到 / timed out / 同源前端没在跑」一族字样 ⇒ 有则按裁判规则 3 原样复跑 + 核 `docker compose ps` 的 `frontend`；(ii) 复跑仍红仍同族 ⇒ 记「不可复现 / 疑似 `P1.8a-fix` 同族」交人，**不猜根因、不改判据去绕**；(iii) ⚠️ **不许反过来用** —— 正文写着别的东西的红不许拿它当挡箭牌（与 §10「不许再拿『那是别人的改动』当解释」同一条纪律） |
  | 3 | **Major** | **本 plan 唯一那条闭合判据所在的 WBS 行号已被人顶掉，全文 8 处仍写「第 88 行」。** 人把 `P1.8a-fix` **插在 `:88`** ⇒ **P1.8b 移到 `:89`**（实读：`:88` = `P1.8a-fix`、`:89` = `P1.8b`、`:90` = `P1.9`）。而 §0 第 5 条只强制重取 `gates.yml` / `project-context.md` 的行号，**独独漏了 `02-WBS.md`** | 全文 **8 处** `第 88 行` → `第 89 行` · §1.1 补一段写明漂移来历并写死「**执行期按 `P1.8b` 三个字定位，不认数字**」（`grep -n '^\| P1.8b' docs/masterplan/02-WBS.md`）· **§0 第 5 条扩进 `02-WBS.md`**（**不新增第 7 条**，避免再造一次「正文写四条实列六条」那种计数不一致）· 顺带登记 roadmap 工作项 11 那处同样过期的「第 88 行」，**照既有定界不代改** |
  | 4 | **Major** | **人新裁的 `DECISIONS.md` `D-24 · 常设授权：plan 预算满了就加` 全文零处提及**，而 §0.5 / §1.10 / §3.1 三处说理都建在「预算满了就**没有出口**」上。D-24 逐字「预算满了就再加预算」，授权人侧代理**直接拆行/加行不必逐次请示**，拆出来的行**预算独立计**（`P1.8a-fix` 就是第一个实例）⇒ 那半句说理**今天过强**。⚠️ **而它极易被读反成「卡住就加预算」** | §1.10 补一整段（引 D-24 原文 + **逐条抄下它的两条边界**：「loop 仍然不得自行加行」「同一工作项连续第 3 次要预算而判据没前进 ⇒ 是方法问题，停下来报人」）· §0.5 改准（该段**降为成本记账**，不再作为停在 `draft` 的理由；停机理由收敛到「免停出处不存在 + 指南对 `active` 的定义」这一条）· §3.1 改准（不拆的理由回到 Minimum Rule 4 的 over-split 条款，不再靠「没有出口」撑着）· 新增 **§0.7 (乙)** |
  | 5 | **Major** | **front matter `> Review Hold:` 的活事实第二次全体过期**（同 iteration 6 第 6 条）：`HEAD` 写 `4f81de8`（今天 `caa051e`）· `STATE.md` 写 891 行（今天 **908**）· needs-human 写 `:867`（今天 **`:875`**）· `Approved-By` 写 31 条（今天 **32**）· 「4 条是本 plan 自己的评审提交」今天是 **5 条** | `> Review Hold:` **整块改准**为第 7 轮实测值，并**新增三行**把 (甲)(乙)(丙) 三处新变更摆在最前面、指向 §0.7 |
  | 6 | Minor | **`R3` 的前半句是第 5 轮改活事实时漏扫的下游引用**：它写「判据建在 **503 分支**上」，而第 5 轮已把 §1.7 改成「**不许把 503 钉死进断言**」（判定环境自 `e3afd77` 起是配着 AI 变量的）。结论（「答得对」没测）仍对，**前半句的描述已假** —— 与本轮第 1 条、iteration 6 第 2 条同族 | `R3` 前半句就地改准（旧文划掉）为「判据建在**不需要模型答对**的那一半上」，**结论与处置一个字未改** |

  ⚠️ **本轮实跑复核过的活仓事实**（不采信 plan 自报）：`git status --porcelain` **无输出**、`HEAD` = `caa051e` ·
  `ls -d tests/*/` 仍是那八个目录 = `gates.yml:597` 的 `COVERED`（`H1` 预测仍成立）·
  `gates.yml:567` 仍只装 `pytest certifi`（**§1.4b 的前提未变**）· `:646` ruff 七个目录 · `:640` 那句「作用域三个目录」·
  `:530` 的零 skip 断言 · `project-context.md:52` 仍是三个目录 —— **三处漂移原样还在，交接项 (5a)(5b) 仍成立**；
  ⇒ **`gates.yml` 自第 6 轮起一行未动，§0.6 那张对照表本轮逐格复核仍准** ·
  `module-boundaries.md` 现存最末编号节仍是 **§7.22**（`:3820`，全文 4129 行）⇒ **§7.23 仍是正确的下一个编号** ·
  `pyproject.toml`：`dependencies` 仍只有 `certifi>=2024.2.2`、**仍无 `optional-dependencies` 段** ·
  `docs/skills/` 16 个条目其中一份是 `README.md` ⇒ **15 份提示词**（§4 成立；⚠️ 新裁的 `D-23` 谈的是
  **产品侧 skills 系统**的 `SKILL.md` 格式，而 `agenerp/skills` 今天不存在 ——
  **与 `docs/skills/` 这批评审提示词不同物，不影响 §4**）·
  `DECISIONS.md` 的 `## 3. 重开记录` 仍逐字「（暂无）」⇒ **零 `R-x`，红线 3 面无新裁定**。

  ⚠️ **本轮也复核了三件「不该改」**：**Minimum Rule 4 不该拆**（与前六轮同结论，且本轮把它的**依据**
  从「没有出口」换回 Minimum Rule 4 自己的 over-split 条款 —— **结论未变、理由更硬**）·
  **Anti-Slacking 禁用词全文零命中**（`optional` 的 9 处命中逐处实读，全是 TOML 键名 `[project.optional-dependencies]`）·
  **红线合规面**逐项核过三个 Phase 的 `Targets`、§10 六条自证与本轮新增的六处改动，**没找出必然越线的藏步**；
  本轮自身只改了本文件一个文件。

  ⚠️ **本轮的 `verification scope limited`，照实写**：**§1.9 那四条基线命令本轮未复跑**
  （`check_expected_red.py` / `pytest tests/unit` / `pytest tests/contracts …` / `ruff check`）——
  第 5 轮跑过，其后五个 commit **全部只碰 `docs/**`**（`git diff --name-only` 实证，无一个碰产品代码或判据）；
  即便如此，**§0 第 2 条仍强制执行期重取**，本文件的数字只作对照。
  另：**活栈、浏览器、docker 本轮一概未起**（评审轮不做活体取证）。

- **Independent draft review iteration 8: `needs revision`（已就地修完）+ 维持 `可以转 active: no`**
  （mission-driver 评审步，2026-08-25，`HEAD` = `96a208f`）—— 复核前七轮的 39 条，并**不受前七轮结论约束**地重审全文。

  **⚠️ 本轮与第 5、7 轮的性质又不同**：那两轮找的是「仓库动了、plan 没跟上」；
  **本轮仓库对本 plan 而言几乎没动**（`caa051e..HEAD` 只有三个文件：`STATE.md` 追加两条 + 两个 plan 文件），
  而本轮的两条 Blocker 都是**这份文件自己写死的判据不可满足 / 自相否决** ——
  **前七轮 39 条里没有一条碰到它们，因为前七轮没有人去实跑那两条命令、也没有人去读 `parse_request()` 的那一行。**

  **对前七轮的复核（逐条实读活仓，不采信 plan 自报）**：
  `git status --porcelain` **无输出** · `STATE.md:875` 仍 `[needs-human]`（**本轮行号未漂**，全文 908 → **916 行**，
  新增两条 `:901` / `:910` 都在其后且不覆盖它）· `Approved-By` **33 条**，无一涉及浏览器驱动，
  其中 **6 条是本 plan 自己的评审提交**（逐条实读确认无真 trailer；`2163e19` 那条「看似带 trailer」实为正文引用）·
  `grep -rn -i "playwright\|selenium" docs/masterplan docs/backlog` 只命中 `STATE.md` 那条 needs-human 的正文四行
  ⇒ **免停出处仍不存在，停在 `draft` 的裁定成立，本轮维持。**
  `ls -d tests/*/` 仍是那八个目录 = `gates.yml:597` 的 `COVERED`（`H1` 预测仍成立）·
  **`gates.yml` 自第 6 轮起一行未动，§0.6 那张对照表本轮逐锚点复核仍准**（含「判据自身的判据」实读为 `:528` / `:592` 两处）·
  `project-context.md:52` 仍是三个目录、`gates.yml:646` 仍是七个 ⇒ **交接项 (5a)(5b) 仍成立** ·
  `check_expected_red.py:74` 判定面仍写死 `tests/gates` · `module-boundaries.md` 现存最末编号节仍是 **§7.22**（`:3820`，全文 4129 行）
  ⇒ **§7.23 仍是正确的下一个编号** · `pyproject.toml` `dependencies` 仍只有 `certifi>=2024.2.2`、**仍无 `optional-dependencies` 段**、
  `live` marker 已注册、`testpaths = ["tests"]`、`exclude = ["tests/gates"]` + `force-exclude = true` ·
  `02-WBS.md:89` 逐字仍是 P1.8b 那一行（`:88` = `P1.8a-fix`、`:90` = P1.9）· `DECISIONS.md` `## 3. 重开记录` 仍逐字「（暂无）」⇒ **零 `R-x`**。
  ⚠️ **本轮补跑了第 7 轮记为 `verification scope limited` 的那一项** —— §1.9 的四条开工基线**全部实跑**，
  四条**均 exit 0**且与本文件所记**逐字吻合**：`门禁 28 项：预期红 0，绿 28，跳过 0` · `801 passed, 6 skipped` ·
  `456 passed, 13 skipped` · `All checks passed!`。⇒ **§1.9 那一格本轮无需改动**（仍按 §0 第 2 条在执行期重取）。
  ⚠️ **另一条本轮实读的新事实（用来排除一个没人查过的风险）**：`gates.yml` 里**没有任何一个 job 跑整仓 `pytest tests`**
  —— 九处 `pytest` 调用逐处实读，全部点名到具体目录/文件 ⇒ **`tests/ui/` 落地不会被任何现有 job 导入**，
  §1.4 (ii) 的「CI 上零覆盖」成立，且**不存在第三条被本 plan 弄红的 job**（§1.4b 只覆盖 `unit-and-contracts`，本轮确认无遗漏）。

  **本轮新提 4 条（2 Blocker + 2 Major），全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Blocker** | **Phase 2 判据⑤ 的 `JSON.stringify(` 零命中与同一个 Phase 第 ③ 件事正面互相否决。** 实读 `agenerp/serve/app.py:145` 的 `parse_request()` 逐字 `payload = json.loads(raw.decode("utf-8"))` ⇒ **请求体必须是 JSON**；而 Phase 2 第 ③ 件事写死同源 `fetch(..., {method:"POST", …})` ⇒ **desk.js 必然要 `JSON.stringify` 一次**。执行期只剩两条出路：违反判据，或手工拼 JSON 串（转义一错就是静默 400，**比它挡的那件事更糟**）。**与第 3 轮打回的「两条判据互相否决的死角」是同一族**，只是这一次两条都在同一个 Phase 里 | 判据⑤ **整格重写**（旧文划掉）成三格：**⑤a** `innerHTML`/`outerHTML`/`insertAdjacentHTML` 零命中 · **⑤b** `document.cookie` 零命中 · **⑤c** `JSON.stringify(` **命中 ≤ 1 次**（1 次=拼请求体是正常的；2 次起必有一次落在渲染面，专挡 `el.textContent = JSON.stringify(resp)` 这个 ⑤a 挡不住的形态）· Phase 2 Exit Criteria 同步改准 · **变异 `M16` 拆成 (16a)(16b) 两个变体**，各自点名由哪一格打红（**(16b) 是改准后唯一还能钻的洞，不施加它 ⑤c 就是空话**）。⚠️ **Phase 2 ⑤ 那条禁令本身、§1.8b 的两条理由、`H8` 的判定口径一个字未改** |
  | 2 | **Blocker** | **`-p no:playwright` 不等价于「runner 上没装 playwright」，而 §1.4b 全篇建在这个等价上。** 第 8 轮**实跑**同形态最小样本证伪（不是推演）：该选项只关掉 **pytest 插件**，**不影响 `import playwright` 这个包**；而 §1.5 实读本机**装着** `playwright 1.58.0` ⇒ 断言体自建 fixture 里那句 `import playwright` 照样成功，用例**真跑起来**（`1 passed`）而**不是 `skipped`** ⇒ **「必须 exit 0、全部 `skipped`、零 `error`」这条 Exit Criteria 在执行者本机不可满足**，而 Phase 3 的 Prereqs 又要求活栈起着 ⇒ 更是真跑。**一条不可满足的 Exit Criteria 就是收口时被逼着造假的洞**（同第 4 轮打回的那条）。⚠️ 连带：`M13` 的「模块顶层 `import playwright`」变体**在本机根本打不红**，旧文把它记在这条命令头上是假的 | §1.4b 第 3 条**整段重写**（旧文划掉）成 **(A)(B) 两条命令**：**(A)** `-p no:playwright` ⇒ **exit 0、零 `error`**，**不断言全 `skipped`**（证「不吃插件 fixture」；实跑确认写 `page` 参数时给的是 `1 error` / `fixture 'page' not found`，与 runner 形态逐字相同）· **(B)** `PYTHONPATH=/tmp/agenerp-nodriver`（内含一行 `raise ImportError` 的遮蔽模块）+ `-p no:playwright` ⇒ **exit 0、全 `skipped`、零 `error`**（实跑确认）· Phase 3 Proof 项 / Phase 3 Exit Criteria / §10 verification（**八→九条**）三处同步改准 · **`M13` 拆成 (13a)(13b)**，点明 (13b) 的打红面是 **(B) + 源码守卫 ②**，**不是 (A)** |
  | 3 | **Major** | **Phase 1 最后那条 `Proof` 把两件在范围内的活漏在落盘面之外**：它逐字写「含 `H1`–`H5` …与**四条**裁定的完整理由」，而同一个 Phase 的执行项与两条 Exit Criteria 早已是**六格探针**（`H2b` 第 6 轮补进、且是 `H3`/`H4` 的硬前置）与**五条裁定**（`D-d-0` 第 2 轮补、且是 `D-d-1`/`D-d-2` 的前置）。⇒ 探测记录是它们**唯一**的落盘处，照旧文走就是「做了但无处存证」，撞指南 Minimum Rule 10。**与本文件自己反复挡的「正文写四条实列六条」是同一族** | Phase 1 该 `Proof` 项改准成「六格 + 五条」，并写明漏的是哪两件、为什么要紧；**与同 Phase 两条 Exit Criteria 现已逐字一致** |
  | 4 | **Major** | **变异表的自报数与实列数对不上**：正文逐字「写死的**十五**条」，其下逐条列的是 `M1`–`M16` **十六**条（第 5 轮补 `M16` 时漏改这句）。同族计数不一致本文件已挡过两次（Phase 1「三条/四条」停机分支、§0「四条/六条」重取基线），这一处漏网 | 改准成「`M1`–`M16` **十六条**，其中 `M13`/`M16` 各两变体 ⇒ **实际施加 18 次**」· Phase 3 Exit Criteria 那格同步改准成「十六条 / 18 次施加」并要求逐次记**是哪一格打的红** |

  ⚠️ **本轮也复核了三件「不该改」**：**Minimum Rule 4 不该拆**（与前七轮同结论）·
  **Anti-Slacking 禁用词全文零命中**（`optional` 的命中逐处实读，全是 TOML 键名 `[project.optional-dependencies]`）·
  **红线合规面**逐项核过三个 Phase 的 `Targets`、§10 六条自证与本轮新增的六处改动，**没找出必然越线的藏步**；
  本轮自身只改了本文件一个文件。

  ⚠️ **本轮的 `verification scope limited`，照实写**：**活栈、浏览器、docker 本轮一概未起**（评审轮不做活体取证）
  ⇒ `H2b`–`H11` 那批探针**全部仍是预测值**，本轮一格都没落实际值。
  §1.4b 那两条命令本轮是拿 `/tmp` 下一个**同形态最小样本**跑的（断言体尚不存在）——
  **它证的是「命令的语义」，不是「本 plan 的断言体会怎样」**，后者只能由 Phase 3 实跑。

- **第 8 轮收敛结论：不转 `active`。** 八轮共 **43** 条（第 8 轮 2 Blocker + 2 Major）已全部改进本文件，
  但 §0.5 那两条**只有人能答**的前置未答之前，这份 plan 不具备**可执行**契约
  （指南 Plan Status Flow：`active` 的含义是「独立评审已收敛成可执行契约」——
  一份 100% 会在 Phase 1 停机的 plan 不满足「可执行」）。
  ⇒ **`Plan Status` 保持 `draft`**，前置见 §0.5 与 front matter 的 `> Review Hold:` 行。
  人答完第 1 条即可转 `active`（第 2 条影响的是 `D-d-0` 的写法，不影响可执行性）。
  ⚠️ **第 8 轮维持这一裁定，理由与第 7 轮逐字相同，且本轮把它的两条实测证据又核了一遍**
  （`STATE.md:875` 仍 `[needs-human]`、`Approved-By` 33 条无一涉及浏览器驱动、
  masterplan/backlog 里 playwright 只命中那条 needs-human 自己的正文）。
  ⚠️ **但第 8 轮必须补记一句，因为它改了「多停一轮的代价」这笔账的性质**：
  前七轮的账记的是「**每多停一轮，plan 记的活事实就多烂一分**」——
  **本轮仓库对本 plan 几乎没动，却仍然找出 2 条 Blocker**，
  而且**两条都不是过期，是这份文件从第一版起就写错、且前七轮 39 条都没碰到的判据缺陷**
  （一条要求资产源码 `JSON.stringify(` 零命中，而请求体必须是 JSON；
  一条把 `-p no:playwright` 当成「等价模拟没装驱动」，而它只关插件）。
  **两条的共同成因也是一条**：前七轮**没有人去实跑那两条命令、也没有人去读 `parse_request()` 的那一行**
  —— 全是**在文本层面互相核对**，核不出「这条命令在真机上到底打出什么」。
  ⇒ **这笔账因此要改写成两笔**：① 停得越久活事实越烂（前七轮的账，仍然有效）；
  ② ⚠️ **一份从未被执行过的 plan，它写死的每一条「可执行验证」都只是一句没跑过的话** ——
  本轮两条 Blocker 就是这么来的，**而剩下的 `H2b`–`H11` 十格探针今天仍然一格都没落实际值**。
  这一笔不是催促，是把「纯文本评审的天花板」记在账上：**第 8 轮已经撞到它了。**
  ⚠️ **第 7 轮独立评审当时把理由收敛成唯一一条，那段照旧保留**：
  人新裁的 **`D-24`** 让「预算满了就没有出口」这条**次要**理由变轻了（§0.7 (乙) / §1.10）
  ⇒ 停在 `draft` 的理由现在只剩下、也只需要这一条 ——
  `D-d-2` 的免停出处（**人已批准、且逐字点名浏览器驱动**的具体出处）**今天在仓里不存在**，
  Phase 1 停机分支 4 **100% 触发**，而指南给 `active` 的定义逐字要求「实现可以开始」。
  ⚠️ **本轮 6 条新发现里有 3 条（第 1、3、4 条）的成因是「仓库动了、plan 没跟上」**，
  **另有 1 条（第 6 条）是「plan 自己动了、plan 的另一半没跟上」**（第 6 轮记的那条账，本轮又兑现一次），
  而第 6 轮记的那条账本轮又被兑现了一次：`gates.yml` 一行没动、`tests/` 一行没动、**产品代码一行没动**，
  仅仅是人侧新拆一行 WBS、新裁一条 `D-`、新查明一条红因，
  就让这份文件出现**五处过期陈述**，其中两处（「疑似 `sid` 外泄」与「第 88 行」）**会把执行者引向错误动作**。
  ⚠️ **第 6 轮当时的裁定摘要照旧保留**：那一轮 8 条新发现里 2 条 Blocker 一条是
  「一条被自己触发的 deferral」、一条是「第 5 轮修了活事实、没扫下游引用」——
  两条都不是新的技术风险，**是这份 plan 在 `draft` 上反复重写留下的接缝**。
  剩下的门槛仍然**不是文本质量问题，是一件红线内、只有人能做的裁定**。

  ⚠️ **本轮暴露出一件该照实说的事，写在这里不藏**：第 5 轮 5 条里有 **4 条**的成因是
  **「仓库动了、plan 没跟上」**，不是起草不细 —— 第 4 轮到第 5 轮之间只隔了三个 commit，
  就让本文件出现五处过期陈述，其中两处会把执行者引向错误动作。
  ⚠️ **第 6 轮把这句话推得更远，也更难看**：本轮仓库**几乎没动**（两个 commit，一个改本文件、一个追加 `STATE.md`），
  8 条新发现里却有 **2 条 Blocker + 1 条 Major** 的成因是**上一轮自己的修改没扫干净下游引用**
  （§5 / `H7b` 改了 ⇒ Non-Goals 6 与 §11 第 2 条没跟上；`> Review Hold:` 的活事实又烂了一轮）。
  ⇒ **不只是「仓库动了 plan 没跟上」，还有「plan 自己动了、plan 的另一半没跟上」。**
  一份 1100 行、被六轮改写过的文件，**每多改一轮就多一处自相矛盾**，这条账也记在这里。
  ⇒ **这份 plan 每在 `draft` 上多停一轮，它记的「活事实」就多烂一分。**
  §0 的「执行前必做：重取基线」六条**不是形式**，是这份 plan 能不能用的前提；
  **人答完 §0.5 第 ① 条之后，越早执行越好** —— 拖得越久，§0 要重取的东西越多。
  这条不是催促，是把「延迟本身的代价」记在账上（同 §1.10 的预算账，只是这一格记的是时间）。

- **Independent draft review iteration 9: `needs revision`（已就地修完）+ 裁定 `可以转 active: yes`**
  （mission-driver 评审步，2026-08-26，`HEAD` = `d69b335`，工作树只有另一份 plan `1118-1` 的 ` M`，本文件之外零改动）
  —— **不受前八轮结论约束**地重审全文，并逐条实读活仓核对（不采信 plan 自报）。

  **⚠️ 本轮的性质是第三种，与前八轮都不同**：第 5、7 轮是「仓库动了、plan 没跟上」，第 8 轮是「plan 自己的判据不可满足」，
  **本轮是「挡了八轮的那道门被人从外面打开了」** —— `d69b335` 落地之后，
  §0.5 那两条只有人能答的前置**全部有了答案**，而这份文件从 front matter 到 Phase 3 有**一整条链**仍写着「答案不存在」。

  **对停机裁定的复核（三处出处逐条实读，任取其一即满足免停条件）**：
  `DECISIONS.md` **D-25**（人 2026-08-26 逐字「批准，加 ui extra」，形态写死为 `ui = ["playwright>=1.47"]`）·
  `STATE.md:425` **`[resolved] 2026-08-26T01:47Z`**（逐字「该 plan 的 Review Hold 两条前置全部解除」）·
  commit **`d69b335`**（`pyproject.toml` 实读已含 `[project.optional-dependencies]` 的 `ui` extra，
  `[project].dependencies` 仍逐字只有 `certifi>=2024.2.2`）。
  ⚠️ **`d69b335` 不带 `Approved-By` trailer（带的是 `Co-Authored-By`）—— 已核过，不影响免停**：
  免停条件是三选一，`[resolved]` 行与 D-25 各自独立成立，且 `DECISIONS.md` 是红线 3。
  前置② 同样已答（`STATE.md:450` 逐字「不算数，它是上游模板残留」；该文件 `:1-9` 人已加抬头「权威性归 D-25」）。
  ⇒ **Phase 1 停机分支 4 今天不触发 ⇒ 这份 plan 具备「可执行契约」⇒ 转 `active`。**

  **对前八轮其余结论的复核（逐条实读，全部仍成立，无一需改）**：
  `ls -d tests/*/` 仍是那八个目录 = `gates.yml:597` 的 `COVERED`（`H1` 预测仍成立）·
  **`gates.yml` 自第 6 轮起仍一行未动**，§0.6 那张对照表逐锚点复核仍准
  （`:597` `COVERED` · `:567` `pip install pytest certifi` · `:646` ruff 七个目录 · `:640`「作用域三个目录」·
  `:579`「这几个目录由 loop 写在红线外」· `:528-530` 零 skip 断言 · `:321`「配上之后它走答案面」·
  `:293`「把判据调整到迁就环境」·「判据自身的判据」仍为 `:528` / `:592` 两处）·
  `project-context.md:52` 仍是**三个**目录、`gates.yml:646` 仍是**七个** ⇒ **交接项 (5a)(5b) 仍成立** ·
  `check_expected_red.py` 判定面仍写死 `tests/gates` · `module-boundaries.md` 现存最末编号节仍是 **§7.22**（`:3820`，全文 4129 行）
  ⇒ **§7.23 仍是正确的下一个编号** · `02-WBS.md:89` 逐字仍是 P1.8b 那一行 ·
  `DECISIONS.md` `## 3. 重开记录` 仍逐字「（暂无）」⇒ **零 `R-x`**。
  ⚠️ **§1.9 四条开工基线本轮全部实跑，四条均 exit 0 且与本文件所记逐字吻合**：
  `门禁 28 项：预期红 0，绿 28，跳过 0` · `801 passed, 6 skipped` · `456 passed, 13 skipped` · `All checks passed!`
  ⇒ **`d69b335` 那次 `pyproject.toml` 改动没有动到任何判据**（另核：`tests/` 与 `tools/` 对 `optional-dependencies` 零命中）。

  **本轮新提 7 条（3 Blocker + 4 Major），全部已就地修完**：

  | # | 级别 | 新发现 | 改在哪 |
  |---|---|---|---|
  | 1 | **Blocker** | **免停出处已存在，而全文仍写着「不存在」。** front matter 的 `> Review Hold:`、§0.5 整节、Phase 1 停机分支 4、`D-d-0` / `D-d-2` 的执行项与 Exit Criteria，**五处一致地要求执行者停机**。照旧文走 ⇒ 一份人已经解锁的 plan 会在 Phase 1 第一条裁定上自我停机 | front matter 换成 `> Plan Status: active` + `> Review Hold Released:`（三处出处逐条列出）· **§0.5 整节重写**成「答案与出处」并把前八轮那两条误读防线原样保存、另加第三条（「命中数不是判据」）· 停机分支 4 加 `✅ 已满足` 段并保留「被 revert 就重新触发」的回退 · `D-d-0` / `D-d-2` 改成 `constrained` 档（记录裁定 + 出处 + 残余风险）· Phase 1 Exit Criteria 同步 |
  | 2 | **Blocker** | **Phase 3 那条 `Add pyproject.toml` 要做的事人已经做完了。** 实读 `d69b335`：`[project.optional-dependencies]` 已在仓里。照旧文走只有两种结局：**写出第二个同名 TOML 表 ⇒ 解析报错**，或发现「已经有了」**而这件在范围内的活无处存证**（撞 Minimum Rule 10） | 该项由 **`Add` 改成 `Proof`**：三条只读复核命令（`grep` / `tomllib` 读出两个键 / `git diff --name-only … -- pyproject.toml` 无输出），**一个字节不改该文件**；Phase 3 `Targets` 里那一格标注为「只读复核」；新增一条 Exit Criteria |
  | 3 | **Blocker** | **D-25 压给 loop 的第 ③ 条硬约束，本 plan 一处都没接。** D-25「未决」栏与 `STATE.md:428` ③ 逐字：「CI 装 chromium 会显著拉长 `gates-l2-live`……**由 loop 在 plan 里给方案并实测，不要默认塞进现有 job 就完事**」，而旧交接项 (2) 逐字就是「在 `gates-l2-live` 里装 `ui` extra 并 `playwright install --with-deps chromium`」—— **正是被点名禁止的那一种**。这是**新的在范围内的活**，不是 follow-up | Phase 3 **新增一条 `Proof`**：(a) `--dry-run`（本轮实读该命令可用、exit 0）· (b) 用临时 `PLAYWRIGHT_BROWSERS_PATH` **冷装计时 + 量体积**，跑完清理，**不许污染 `~/Library/Caches/ms-playwright`**（那是 `H2` 的判定面），拿不到网络就记 `verification scope limited` **不许拿缓存秒数冒充冷装** · (c) 折成**三个方案各带一句代价**，**选哪个归人**。交接项 (2) 整条改写 · §10 verification 九→**十一**条 · Phase 3 新增 Exit Criteria · §11 第一条补一句 |
  | 4 | **Major** | **§1.5 那张实读表里「没有任何 `optional-dependencies` 段」今天是假的**，而这一格正是 `D-d-2` 的立论依据 | 该行整格改准（旧文划掉），并写清**旧亏没消掉、只是换了位置**：`ui` extra **不含 `pytest-playwright`**（⇒ 本机那份仍是「碰巧装着」，与 `D-d-3` ⑥ 互相印证）、**不含浏览器二进制**（⇒ 第 3 条那件实测） |
  | 5 | **Major** | **三个 Phase 的 `Item Types:` 自报比例全部与实数不符**：Phase 1 写「4/6 是 `Decision`」实为 **5/7** · Phase 2 写「5/6 是 `Add`」实为 **3/6** · Phase 3 写「5/7 是 `Proof`」实为 **4/9**。且**三者都不足**指南 Minimum Rule 7 的 80% 阈值 ⇒ 本就不该作 Phase 级统一声明。**与本文件已挡过三处的同族计数不一致是第四处** | 三处全改成「逐项标注为准」+ 实数（Phase 3 经本轮两处改动后为 **6/10 `Proof`**），并写明为何不作 Phase 级声明 |
  | 6 | **Major** | **四处 Exit Criteria 把日志文件写死成 `docs/logs/2026/08-25.md`**，而起草日已过、今天是 `2026-08-26`（`docs/logs/2026/` 实读最末是 `08-25.md`）。照旧文走就是把执行当天的进度回写进起草日的文件，撞指南 When Executing 第 9 条 | 四处（Phase 1/2/3 Exit Criteria + §10 relevant docs）改成 `docs/logs/2026/<执行当天>.md`，并写明跨天的 Phase 各自入自己那天 |
  | 7 | **Major** | **§0 那六条重取基线里没有一条重取「免停出处还在不在」**。本 plan 转 `active` 的全部理由建在三处出处上，而 §0 逐条重取的是行号、目录、驱动、AI 变量 —— **唯独不重取这三处**。一旦被 revert，执行者按 §0 走**看不见** | §0 第 4 条扩成三件：原驱动探针 + **(a)** `grep -n -A6 'optional-dependencies' pyproject.toml` + **(b)** 按 `D-25` / `[resolved]` 字面重取两处出处（**不认本文件写的行号**）；`D-d-0` / `D-d-2` / 停机分支 4 三处均写明「都不在了 ⇒ 停机分支 4 重新触发」 |

  ⚠️ **本轮复核了四件「不该改」**：**Minimum Rule 4 不该拆**（与前八轮同结论：四块共享同一条闭合判据）·
  **Anti-Slacking 禁用词全文零命中**（`optional` 的命中逐处实读，全是 TOML 键名与 §11 的 `Classification` 取值）·
  **`D-d-3` ①–⑥ 一个字不改** —— 它正是 D-25 硬约束 ② 的实现（「UI 门禁跑不起来必须红，不许 skip」）·
  **§1.4b 的 (A)(B) 两条命令一个字不改** —— `ui` extra 落地不影响它们的语义（extra 里没有 `pytest-playwright`，
  而 (A) 的 `-p no:playwright` 与 (B) 的遮蔽模块各自证的仍是原来那两件事）。

  ⚠️ **本轮的 `verification scope limited`，照实写**：**活栈、浏览器、docker 本轮一概未起**（评审轮不做活体取证）
  ⇒ `H2b`–`H11` 那批探针**全部仍是预测值**，本轮一格都没落实际值。
  新增的那条冷装计时**本轮只实读了 `--dry-run` 可用（exit 0）与它打印的安装位置/下载 URL，没有真跑冷装** ——
  **秒数与体积必须由 Phase 3 执行期实测**，本文件不预填任何数字。

- **第 9 轮收敛结论：转 `active`。** 九轮共 **50** 条（第 9 轮 3 Blocker + 4 Major）已全部改进本文件。
  **挡了八轮的那件事已经结束**：`D-d-2` 的免停出处（人已批准、且逐字点名浏览器驱动的具体出处）
  **今天在仓里存在且被本轮三处独立实读确认**，Phase 1 停机分支 4 **不触发**
  ⇒ 满足指南 `Plan Status Flow` 对 `active` 的定义（「独立评审已收敛成**可执行**契约、**实现可以开始**」）。
  ⚠️ **`active` 只解锁「可以开始」，不解锁任何一条红线** —— 三个 Phase 的归人写法、§10 六条红线自证、
  §11 四条 deferred 的「归人」归属，**本轮一个字未松**。
  ⚠️ **前八轮记在这里的那笔账仍然有效，而且本轮又兑现了一次**：
  ① 停得越久，plan 记的活事实越烂 —— 本轮 7 条里有 **4 条（第 1、2、4、6 条）**的成因就是「仓库/日历动了、plan 没跟上」；
  ② **一份从未被执行过的 plan，它写死的每一条「可执行验证」都只是一句没跑过的话** ——
  本轮新增的冷装计时也还只是一句没跑过的话，`H2b`–`H11` 十格探针今天仍然一格都没落实际值。
  ⇒ **§0 那六条重取基线不是形式，是这份 plan 能不能用的前提；越早执行，要重取的东西越少。**


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
      `docs/logs/2026/<执行当天>.md`（⚠️ 第 9 轮改准，不再写死 `08-25.md`） · `docs/evidence/p1-desk-sidebar/`）；
      对 `docs/design/agents-and-roles.md` §9 风险档表 **`No owner-doc update required`**（理由见 §4）
- [ ] verification has run —— 至少这**十一**条（⚠️ 第 8 轮把 §1.4b 那条拆成 (A)(B)，八→九；
      ⚠️ **第 9 轮再加两条，九→十一**：`pyproject.toml` 的 `ui` extra 只读复核 · 装 chromium 的冷装计时），
      命令原文 + 退出码入 `## Closure`：
      `python3 tools/gates/check_expected_red.py` ·
      `python3 -m pytest tests/unit -q` ·
      `python3 -m pytest tests/contracts tests/tools tests/routing tests/context -q` ·
      `ruff check agenerp tests/unit tests/ui tests/contracts tests/tools tests/routing tests/context tests/experiments` ·
      `AGENERP_LIVE=1 … python3 -m pytest -m live tests/ui/test_sidebar.py -q -rs` ·
      **(A) `python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright`**（§1.4b，
      **必须 exit 0、零 `error`**；⚠️ **不断言全 `skipped`** —— 本机装着驱动时它会真跑，那是合法的，
      第 8 轮实跑证伪了旧文那条期望）·
      **(B) `PYTHONPATH=/tmp/agenerp-nodriver python3 -m pytest tests/unit/test_desk_sidebar_body.py -q -p no:playwright -rs`**
      （先按 §1.4b 建好那个只含一行 `raise ImportError` 的遮蔽模块；**必须 exit 0、全 `skipped`、零 `error`**
      —— **这一条才是**无驱动 runner 上 `unit-and-contracts` 不被弄红的实证）·
      **`python3 -c "import tomllib,pathlib;d=tomllib.loads(pathlib.Path('pyproject.toml').read_text());print(d['project']['dependencies'],d['project']['optional-dependencies'])"`**
      （第 9 轮新增；⇒ `dependencies` 仍逐字只有 `certifi>=2024.2.2`、`optional-dependencies` 含 `ui = ["playwright>=1.47"]`，
      **且 `git diff --name-only <基线sha>..HEAD -- pyproject.toml` 无输出** —— 本 plan 对它只读）·
      **`PLAYWRIGHT_BROWSERS_PATH=/tmp/agenerp-pw-cold /usr/bin/time -p python3 -m playwright install chromium`**
      （第 9 轮新增，D-25 逐字压给 loop 的实测；墙钟秒数 + `du -sh` 体积入 `## Closure`，跑完 `rm -rf`；
      ⚠️ **不许污染 `~/Library/Caches/ms-playwright`**；拿不到网络 ⇒ 逐字记 `verification scope limited`）·
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
      ⚠️ **第 8 轮实跑提醒：这条 grep 在本文件上会命中 1 行，而那一行就是本行自己**（它把命令原文写在了文件里）。
      ⇒ **判法是「除本行之外为空」**，别把这个自指命中当成一个真的 `completed` Phase 去查半天。
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
  ⚠️ **第 9 轮补：交接项 (2) 已按 D-25 改成「三个方案 + 实测数」，不是一句「装上去」** ——
  **本 plan 负责把数测出来、把方案摆出来；选哪个、以及一切落在 `.github/workflows/**` 的动作，全部归人。**
- Successor Required: `yes`，**归人**。重开事件：**人下一次推送 `main` 看到第 ⑦ 步红的那一刻**
  （交接文字已在 Phase 3 写死，含可直接照做的一行修法）。
- ⚠️ **这不是「顺手没做」，是「做了就越线」。** 本 plan 明知它会红仍然落目录，理由写在 §1.4 与 `D-d-1`。

### `proxy_read_timeout 300` 在一次**真实长解释**上的行为 · 以及**真 nginx 504 的渲染**

- Classification: `watch-only residual`
- ⚠️ **第 6 轮独立评审整条改写，理由必须写在前面（这是本轮的头号 Blocker）**：
  原文的重开事件逐字是「~~第一次在配了 AI 变量的活栈上跑一次完整解释的那一刻~~」，
  而 §5 / R8 / `H7b` **(乙) 支**判定「执行者的 shell 里很可能正好配着」⇒
  **那一刻就发生在本 plan 自己的执行期内。** 一条**被自己触发**的重开事件不成立；
  原文那句「~~造一次真超时要 AI 变量与约 10 万 token~~」也与 §5「(乙) 支就要烧掉约 11 万 token」正面矛盾。
  ⇒ **按 `H7b` 两支重新裁定如下。**
- Why Not Blocking Closure（**分两支，逐支写死**）：
  **共同的一半**：**真 nginx 502 本 plan 拿得到**（`H8c`，借 `H10` 的停服动作）；
  **真 nginx 504（墙钟 > 300 秒被反代掐断）两支都拿不到** ——
  面板在**真 504** 上渲染成什么样，本 plan 之后**只有打桩证据（`H8` 的 504 那格），没有活体证据**。
  **(甲) 支**（`AGENERP_LLM_*` 数出来是 0）：服务恒 503，**不产生任何真解释请求** ⇒ 与原文同，全条未触及。
  **(乙) 支**（数出来非 0）：本 plan **会产生一次**真解释请求（约 11 万 token、约 50 秒）。
  ⚠️ **它给出的是一个数据点，不是这条的答案**：**50 秒 ≪ 300 秒 ⇒ 那一次根本碰不到上限**。
  ⇒ **(乙) 支下必须把「那一次的墙钟秒数」逐字记进证据文件**，并**逐字写明
  「本轮未触及 `proxy_read_timeout 300` 的上限，该上限仍未验证」** ——
  **不许**把「一次 50 秒的解释正常返回了」写成「反代超时已验证 / §7.21 那条已关掉」。
  §7.21 记着这条从未被验证过，**本 plan 两支都没有把它关掉，也不假装关掉了**。
- Successor Required: `yes`，**归人**（工作项 11 预算 `2/2` 满，拆行只有人能做）。
  **重开事件（改写后，本 plan 触发不了它）**：**第一次出现一次墙钟 > `proxy_read_timeout`（今天是 300 秒）的解释请求**
  —— 无论它是真实长解释自然发生的，还是人把该值临时调小造出来的。
  那一次要么被反代掐断回 504、要么正常返回，**两种结果都直接回答「面板在真 504 上长什么样」**。
  ⚠️ **「跑了一次配着 AI 变量的完整解释」不再是重开事件** —— 本 plan (乙) 支就会做那件事，
  而它已被上面证明**回答不了这个问题**。

### 「Agent 答得对不对」在侧边栏这条链上的验证

- Classification: `out-of-scope improvement`
- Why Not Blocking Closure: 那是 P1.4 的结果面（工作项 6），本 plan 的结果面是**渲染与传输**（Non-Goals 4）。
  两者失败模式不同：前者是「蒙对/答错」，后者是「界面空白/请求没带身份」。
- Successor Required: `no`（在本 mission 内）。重开事件：**人在 `02-WBS.md` 为「侧边栏端到端答题」拆出新行**时。

### `D-d-4` 若改了键位 ⇒ 与 WBS 第 89 行「⌘K」字面的偏差

- Classification: `watch-only residual`
- Why Not Blocking Closure: 表规 6 逐字「可改的是字符串，不可改的是形状」，但**改 `02-WBS.md` 是红线 5**。
- Successor Required: `yes`，**归人**。重开事件：**`H3` 实测判定 `Cmd/Ctrl+K` 已被 Desk 原生占用**的那一刻
  （未触发则本条自然消解，收口时照实写「未触发」）。

## Closure

<待收口时填：Status Note · Closure Audit Evidence（独立审计者 + 命令原文 + 退出码 + sha）· Follow-up>
