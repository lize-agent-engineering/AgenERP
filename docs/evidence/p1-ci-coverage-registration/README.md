# p1-ci-coverage-registration —— 「哪些测试目录被谁复跑得到」的实测证据

> 来源 plan：`docs/plans/p1-insight/2026-08-26-2213-1-ci-coverage-registration-drift.md`
> 落点节：`docs/architecture/module-boundaries.md` **§7.26**（登记表本体，单一真相源）
> 判据：`tests/unit/test_ci_coverage_registration.py`
> 起点 sha：`bc7f13f` · 全程离线（零 docker / 零网络 / 零凭据 / 零 LLM 调用 / 零 token 成本）

⚠️ **本目录只记「谁复跑得到哪个目录」这一件事。**
不记 live 面的 job 在测什么、不记 `check_expected_red.py` 的判定域、不记条数、不记断言质量。

---

## 1 · Phase 1 实测：四张来源逐条读出来（2026-08-26）

**五条全是「读」，一个字节都没写。** 收尾复核见本文件 §5。

### ① `tests/` 下的目录集合

```
$ ls -d tests/*/ | xargs -n1 basename | sort
context
contracts
experiments
fixtures
gates
routing
tools
ui
unit

$ ls -d tests/*/ | wc -l
       9
```

⇒ **九个目录**。§7.26 表的数据行数必须逐字等于 `9`。

### ② `.github/workflows/gates.yml` 的 `unit-and-contracts` job（job 键 `:586`，下一个 job `seed-selfverify` 在 `:643`）

```
$ awk 'NR>=586 && NR<=642 {printf "%d:%s\n", NR, $0}' .github/workflows/gates.yml \
    | grep -E "name: [①-⑦]|run: python3 -m pytest|if:|continue-on-error"
603:      - name: ① 单测（tests/unit）
604:        run: python3 -m pytest tests/unit -q
606:      - name: ② 契约测试（tests/contracts）
607:        run: python3 -m pytest tests/contracts -q
614:      - name: ③ 工具执行层（tests/tools）
615:        run: python3 -m pytest tests/tools -q
617:      - name: ④ 模型路由（tests/routing）
618:        run: python3 -m pytest tests/routing -q
620:      - name: ⑤ 上下文层（tests/context）
621:        run: python3 -m pytest tests/context -q
623:      - name: ⑥ 实验设施（tests/experiments）
624:        run: python3 -m pytest tests/experiments -q
628:      - name: ⑦ 没有测试目录被漏在 CI 之外
```

⚠️ **`if:` 与 `continue-on-error:` 在 `586–642` 这个区间里零命中**（上面那条 `grep` 的模式里含这两个词，
输出里一行都没有）⇒ **六条步骤没有一条被条件或软失败削弱，job 本身也不带 `if:`**。
对照：同一份文件里两种写法都**实际存在**（`:211` `if: always()` · `:367-368` `if: failure()` + `continue-on-error: true`），
所以「本仓不用这两个词」不是理由 —— 是实测出来它们没落在这个 job 上。

第 ⑦ 步 `:628` 不是「跑某个目录」的步骤，是**目录集合的元判据**，见 ⑤。

### ③ `lint` job（job 键 `:663`）那条 `run:` 行的 ruff 参数

```
$ grep -n "ruff check agenerp" .github/workflows/gates.yml
682:        run: ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui
```

⇒ **八个 `tests/` 目录**：`unit contracts tools routing context experiments ui` —— 七个，加 `agenerp` 一个包目录。
**不在里面的两个**：`tests/gates`（`pyproject.toml` 的 `[tool.ruff] exclude` 排除它，理由是免得 lint 逼着去改裁判）·
`tests/fixtures`。

⚠️ **必须读 `run:` 行，不许读 `name:` 行**：`:681` 的 `name:` 逐字是
`ruff check（agenerp + tests/ 全部非门禁目录）`，一个首匹配解析器会从它里面读出 `['tests/']`。

### ④ `missions/p1-insight.json` 的 `commands.test`

```
$ python3 -c "import json;print(json.load(open('missions/p1-insight.json'))['commands']['test'])"
python3 tools/gates/check_expected_red.py && python3 -m pytest tests/unit -q
```

⇒ **只有 `tests/unit` 一个目录**。`GATE_VERIFY` 复跑不到其余八个。

### ⑤ `gates.yml:631` 的 `COVERED` 字面值

```
$ sed -n '631p' .github/workflows/gates.yml
          COVERED="contracts context experiments fixtures gates routing tools ui unit"
```

⇒ **九项，与 ① 的实扫集合逐字相等**（含 `ui`）⇒ 今天推送时 **第 ⑦ 步不红**。

### 收尾自证：五条都是读

```
$ git diff --name-only -- .github/ missions/
（无输出）
```

---

## 2 · Phase 1 的裁定：纳管口径 = `tests/` 下的**目录**，不是文件

- **备选 (A) 按文件纳管**（先例 `tests/routing/test_routing_guard_registration.py` 的口径）—— **否决**：
  表会退化成全量测试清单（`tests/unit` 一个目录就 60+ 个文件），第 2/3 列没法逐行写实。
- **备选 (B) 只纳管今天有缺口的目录** —— **否决**：那样「新增了目录却忘了登记」不会红，
  而那正是 `gates.yml:628` 第 ⑦ 步在 CI 侧防的事，登记表没理由比 CI 松。
- **选定 (C) 全目录纳管。**

**残余风险照实记**：`tests/fixtures` 是数据目录、没有 `def test_*`，它在表里也占一行，
第 2/3 列写「本 job 里不跑 / —」、第 4 列写「不在」—— **这是事实，不是缺口**，不许读成「有个目录漏了」。

---

---

## 3 · 判据的活性证明：变异自查 N1–N10（**十条全部在 `/tmp` 的整仓副本上施加**）

**硬约束与它的兑现**：每条变异都在 `cp`（实际用 `tar` 管道，排除 `.git`）到 `/tmp/agenerp-mut` 的整仓副本上施加，
施加后在副本上复跑判据，**然后丢弃整份副本重新拷贝**（比逐条复原更难出错）。
**活仓工作树全程除 `docs/plans/p1-insight/2026-08-26-2213-*.md` 两个文件外零改动** ——
不许「反正会复原」就在活仓施加：那一步一旦中断，仓里就留着一个被改松的门禁面或一份被改假的 owner doc。

**副本上的基线**：`python3 -m pytest tests/unit/test_ci_coverage_registration.py -q` → **exit 0 · `8 passed`**
（七条断言、八个 `def test_` —— ② 的两个方向分开写死）。

### 3.1 逐条：预测**先写死**（写在 plan 的 Phase 3 变异表里），再施加

| # | 变异 | 预测 | **实测** | 吻合 |
|---|---|---|---|---|
| N1 | 删掉表里 `context` 那一行 | 红 · 断言① | **exit 1 · `3 failed`** —— ① · ②b · ③ | ✅ ①如预测（另见 3.2 ①） |
| N2 | 表里 `routing` 改成 `routinq` | 红 · ①②③ 三条同时红，⑦ 不红 | **exit 1 · `4 failed`** —— ① · **②a** · **②b** · ③，**⑦ 未红** | ✅（② 两个方向都红 = 断言②红） |
| N3 | 整表删空 | 红 · **仅断言⑤** | 首跑 **`8 failed`（不符）** → 补解析器 → 复跑 **exit 1 · `1 failed`（仅 `test_05`）** | ⚠️ **首跑不符，见 3.3** |
| N4 | 副本 `gates.yml` 删掉第 ⑤ 步 | 红 · **②a**，单点红 | **exit 1 · `1 failed`** —— `test_02a` | ✅ |
| N5 | 副本 `ruff check` 参数删掉 `tests/context` | 红 · 断言③ | **exit 1 · `1 failed`** —— `test_03` | ✅ |
| N6 | 副本 `commands.test` 加进 `tests/context` | 红 · 断言④ | **exit 1 · `1 failed`** —— `test_04` | ✅ |
| N7 | 副本把第 ⑤ 步**整条挪进 `gates-l2-live`** | 红 · **②a**，单点红 | **exit 1 · `1 failed`** —— `test_02a` | ✅ |
| **N7b** | N7 **+ 去掉 job 边界约束** | **转绿** ⇒ 边界活性证明之一 | **exit 0 · `8 passed`** | ✅ |
| N8 | 副本在 `gates-l2-live` 里**插入** `- run: python3 -m pytest tests/fixtures -q` | **必须保持绿** | **exit 0 · `8 passed`** | ✅ |
| **N8b** | N8 **+ 去掉 job 边界约束** | **转红在②b** ⇒ 边界活性证明之二 | **exit 1 · `2 failed`** —— **②a** · **②b** | ✅ ②b如预测（另见 3.2 ②） |
| N9a | 副本给第 ⑤ 步加 `continue-on-error: true` | 红 · 断言⑦ | **exit 1 · `1 failed`** —— `test_07` | ✅ |
| N9b | 副本给第 ⑤ 步加 `if: false` | 红 · 断言⑦ | **exit 1 · `1 failed`** —— `test_07` | ✅ |
| N9c | 副本给 `unit-and-contracts` **job 级**加 `if: github.event_name == 'schedule'` | 红 · 断言⑦ | **exit 1 · `1 failed`** —— `test_07` | ✅ |
| N10 | 副本在 `unit-and-contracts` 里**插入** `- run: python3 -m pytest tests/fixtures/x.py -q` | **必须保持绿** | **exit 0 · `8 passed`** | ✅ |
| **N10b** | N10 **+ 去掉「裸目录」约束** | **转红在②b** ⇒ ②b 的活性证明 | **exit 1 · `2 failed`** —— **②a** · **②b** | ✅ ②b如预测（另见 3.2 ②） |

⇒ **两条 must-stay-green（N8 / N10）都真的保持绿**，且**各自的约束一去掉就转红** ——
「两条形状约束互为替身、去掉哪一条基线都还是绿」这件事在本条上**不成立**，两条各有一对变异证明其活性。

### 3.2 三处「红得比预测多」，逐条说清成因，**不粉饰**

① **N1 多红了 ②b 与 ③**：删掉 `context` 行，同时破坏了三件事 ——
目录集合少一项（①）· CI 里第 ⑤ 步找不到对应行（②b）· 第 4 列的「在」集合少一项（③）。
预测只写了 ①，是**预测写窄了**，不是判据失灵。**判据在这里比预测更严，不是更松。**

② **N8b / N10b 多红了 ②a**：去掉约束之后，`tests/fixtures` 变成一条「CI 里有的步骤」，
于是 ②a 那句「表说『本 job 里不跑』的必须真的没有」也当场为假。**②b 如预测转红，②a 是同因的第二个方向。**

③ **N2 的 ② 在两个方向上都红**：plan 的预测按**断言编号**写（「①②③ 三条同时红」），
而 ②a / ②b 是同一条断言的两个方向，各占一个 `def test_` ⇒ `4 failed`。**这是计数口径差，不是行为差。**

**共同点：三处都是「实测比预测红得更多」。** 按 plan 的口径，需要当场处置的是**打不红**的那种不符
（「不许把打不红的那条从表里删掉」）——**本轮没有出现打不红的变异**。

### 3.3 ⚠️ N3 首跑与预测**不符**，逐字记，并记下当场怎么补的

- **预测**：整表删空 → **仅断言⑤红**（其余六条各自对空表短路返回）。
- **首跑实测**：**`8 failed`** —— 八条**全红**，且都红在同一个地方：`_table_rows()` 的
  「行必须是六列」上。
- **根因（复跑确认，不是猜的）**：解析器只用了**起始**标记 `<!-- machine-read: ci-coverage -->`，
  从它往下找**第一张表**。表被删空之后，往下第一张表变成了 **§7.26.2 那张四列表**（「今天仍在别处重复登记同一事实的位置」），
  于是先红在列数上，**存活守卫⑤从未被触发**。
  ⚠️ **成对标记本来就是为这件事加的，解析器却只用了它的一半** —— 照实记。
- **当场处置**（不是把 N3 从表里删掉）：在闭合标记 `<!-- /machine-read: ci-coverage -->` 处**截断扫描**，
  并对「闭合标记缺失」单独给一条断言。commit `a52a5d7`。
- **复跑**：**exit 1 · `1 failed`（仅 `test_05_table_is_not_empty`）** ⇒ 与预测吻合。
  **N1–N10 全表在修复后重跑，无一条回归。**

### 3.4 失败文案实样（`D2` 的唯一缓解，必须逐字点到「改哪个文件的哪一列」）

**N4**（CI 里删掉第 ⑤ 步）：

```
E  AssertionError: `tests/context`：表说它在 `unit-and-contracts` 的第 ⑤ 步，而该 job 里**没有任何一条**裸目录 `pytest tests/context` 步骤。
E      仓里实际跑到的目录：['contracts', 'experiments', 'routing', 'tools', 'unit']
E    该改的是 docs/architecture/module-boundaries.md §7.26 的 <!-- machine-read: ci-coverage --> 那张表 的第 2 列（改成 `本 job 里不跑`），或确认 .github/workflows/gates.yml 是不是被人正当改过（那属红线 2，只能改表跟上）。
```

**N9a**（第 ⑤ 步加 `continue-on-error: true`）：

```
E  AssertionError: `tests/context`：第 ⑤ 步被条件或软失败削弱了 ——「跑了」不等于「拦得住」。
E      仓里实际：['continue-on-error: true']（步骤名逐字 '⑤ 上下文层（tests/context）'）
E      表的第 3 列说：'否'
E    该改的是 docs/architecture/module-boundaries.md §7.26 的 <!-- machine-read: ci-coverage --> 那张表 的第 3 列 —— 若确是人正当改的，第 3 列必须逐字写出那个条件。
```

⇒ 四要素俱全：**哪一行 · 表说什么 · 仓里实际是什么 · 该改哪个文件的哪一列**。

---

## 4 · 改准之前的原文，逐字留痕（本节只留痕，不做判断）

### 4.1 `docs/architecture/module-boundaries.md` §7.7 末节（`:483-490`）

```
#### 判据缺口，如实记在这里

`tests/context` **不在** `missions/p1-insight.json` 的 `commands.test` 里，
也不在 `.github/workflows/gates.yml` 的 `unit-and-contracts` / `lint` 任何一个 job 的作用域里
（那两个 job 的作用域是 `tests/unit` `tests/contracts`）。因此 **`GATE_VERIFY` 与 CI 都复跑不到本层的主判据**。
`missions/**` 与 `.github/workflows/**` 都在红线内，loop 无权自己补。
代偿控制：变异自查（plan Phase 3 的 M1–M8）+ 独立关闭审计 + STATE §3 的 needs-human 行。
**不得因为本层测试自己是绿的就说「已被门禁覆盖」。**
```

### 4.2 `docs/architecture/model-management.md` §12.5（`:373-386`）

```
⚠️ **判定面缺口，照实记，不假装没有。**
`tests/routing` 既**不在** `missions/p1-insight.json` 的 `commands.test` 里，
也**不在** `.github/workflows/gates.yml` 的任何 job 里（`unit-and-contracts` 的作用域是
`tests/unit` `tests/contracts`，`lint` 的是 `agenerp tests/unit tests/contracts`）。
`tests/tools` 是同形态的第一条缺口，`tests/routing` 是第二条。
两者都要人来接（`missions/**` 与 `.github/workflows/**` 都在红线内，loop 不得动），
已在 `STATE.md` §3 追加 needs-human。
**在人接进去之前，不得声称 CI 覆盖了 `tests/routing`。**
本层现有的代偿控制只有三条：本节的同构判据、`test_router.py` 的降级反测、
以及 P1.1 收口时跑过的 M1–M5 假实现变异自查（结果表在 plan 的 Phase 3 记录里）。

⚠️ **`pyproject.toml` 没有声明 `dependencies`**，`certifi` 至今是一个未声明的依赖。
本层用惰性 import 与两道反测把它挡在"被 CI import 到"的路径之外，
**这不等于依赖问题解决了** —— 真正解决要和"把 `tests/routing` 接进 CI"一起做，同属人的活。
```

### 4.3 `docs/architecture/module-boundaries.md` §7.23.6（改准前，实读 `:4429-4448`）

```
#### 7.23.6 CI 覆盖面：本节落地后**三处零覆盖**，全部归人（红线 2）

**照实说，不粉饰**：`tests/ui/` 落地之后

1. `gates.yml:597` 第 ⑦ 步「没有测试目录被漏在 CI 之外」**会红** —— 它的名字逐字叫「判据自身的判据」，
   **红正是它的目的**。本仓已有四个同形态先例（`tests/tools` / `tests/routing` / `tests/context` / `tests/experiments`）。
2. **新门禁在 CI 上零覆盖**：`tools/gates/check_expected_red.py` 的判定面写死 `"tests/gates"`，
   而 `gates-l2-live` 只有一条判定步就是跑它 ⇒ `tests/ui/test_sidebar.py` **不会被任何 job 跑到一次**。
   **「把 `ui` 加进 `COVERED` 就好了」是错的** —— 那只让第 ⑦ 步不红。
3. **`tests/ui` 在 CI 上零 lint 覆盖**：`gates.yml:646` 的 ruff 参数是七个目录的**字面量**
   （本机会被真扫，因为 `[tool.ruff]` 的 `exclude` 只排除 `tests/gates`）。

⇒ 六件人要做的事逐件写在交付 plan 的 Phase 3 交接项与 `STATE.md` §3。
**六件全部落在 `.github/workflows/**` 里 ⇒ 红线 2，本节与本 plan 一个字节都不碰。**

⚠️ **`project-context.md:52` 的 lint 作用域由本 plan 就地改准**（它不在任何红线内），
让交接项有真相源可照抄。**但改完之后漂移并没有消除**：`gates.yml:640` 那句注释逐字写的是
「**作用域三个目录**逐字照抄……」，改完之后「三个目录」**仍然是错的**；
且真相源变成**八个**目录而 `:646` 是**七个**，两边**仍然不等**。**这两处残余都在红线 2，交人，不假装修好了。**
```

### 4.4 `docs/context/project-context.md:52` 的 ⚠️ 注解 —— **只留本 plan 要删的那几段**

（该行其余部分：`ruff` 命令本体、2026-08-23 追加段、`F401` 变异实测、规则集边界 —— **一个字不动，故不留痕**）

```
① `gates.yml` 那句注释逐字写的是「**作用域三个目录**逐字照抄本行」，改完之后「三个目录」**仍然是错的**；
② 本行现在是**八个**目录（新增 `tests/ui`）而 `lint` job 是**七个** —— 两边**仍然不等**。
**残余的两处都落在 `.github/workflows/**` 里 ⇒ 红线 2，plan 一个字节都不碰，逐字交人**
但**在 CI 上是零 lint 覆盖**，直到人把它加进 `lint` job。
```

⚠️ 逐字命中 **4/4** 段。

---

## 5 · 收尾补扫：十二关键词 × 四个目录，逐条判词

```
$ grep -rn "commands.test\|unit-and-contracts\|复跑不到\|未声明\|dependencies\|零覆盖\|COVERED\|ruff\|任何 job\|不会被任何\|会红\|仍然不等" \
    docs/architecture/ docs/backlog/ docs/context/ docs/design/ | wc -l
170
```

⚠️ **它仍然是关键词扫描，不是全文逐行复核，并且已经漏过两次** ——
起草期按三个词扫漏了 B2 第 4 处；扩到五个词之后**仍然命不中** B2 第 6 处（`awk` 机械证明该区间零命中）。
**不许写成「扫完就没有了」。** 边界见 plan 的 `D4`，其中包含第 8 轮追加的那一条：
**本 plan 自己引用过的每一处位置，都必须被显式判过「它今天是真是假」。**

**判词是集合不是单选**，三分口径：**`成立`**（内容与行号都对）·
**`行号漂移`**（引文内容仍能逐字找到，只是行号变了）· **`已过期`**（内容本身已被证伪）。
**只有集合里含 `已过期` 的才进本 plan 的改准范围**；判 `行号漂移` 的**留在原地**
（改行号不是本 plan 的结果面，且行号会随任何一次编辑再漂）。

### 5.1 逐条判词

| 位置 | 逐字 | 判词 | 处置 |
|---|---|---|---|
| `module-boundaries.md:4417`（§7.23.5） | 「`unit-and-contracts` 只装 `pytest certifi`，`gates.yml:567`」 | **`行号漂移`**（内容成立：`:601` 逐字 `pip install pytest certifi`；`:567` → `:601`） | **留在原地** |
| `system-baseline.md:1623-1626`（§14.10「验证范围」） | 隔离 A/B 三条命令，含 `ruff check agenerp tests/unit tests/contracts` | **`成立`** —— 它是**当日 A/B 实测的命令记录**，不含对当期判定面的断言 | 无（§14.10 已由本 plan 加时点限定，见 §6） |
| `docs/backlog/tools-dir-has-no-static-check-coverage.md:18` | 事实 4 取证列「`gates.yml:426` 的判据 step 逐字是 `ruff check agenerp tests/unit tests/contracts`」 | **`已过期` + `行号漂移`**（今天 `:682`、八个目录）。⚠️ **结论本身仍成立**：ruff 参数至今不含 `tools/` | **进改准范围**。形态 = **自带日期的事实账本** ⇒ 用 `:4270` 那一档口径：**不改写上表一个字**，追加一句时点限定 + 指向 §7.26 的指针 |
| `docs/backlog/gates-and-tools-leak-env-across-directories.md:37-39` | 「CI 从不触发它：`gates.yml:570-584` 把四个目录逐目录分开跑……这两个目录从未进过同一个 pytest 进程」 | **`成立` + `行号漂移`**（结论今天仍真；`:570-584` → `:603-624`。它列了四个目录、未声称穷举，`context` / `experiments` 亦逐目录分开跑，不改变结论） | **留在原地** |
| 同上 `:40` | 「`check_expected_red.py` → `门禁 28 项：预期红 0，绿 28，跳过 0`，exit 0」 | **`成立`**（数字是**当日观测**，文件头逐字钉死「2026-08-26 在 `main` @ `f3ff580` 上实跑」；今天是 **29 项**、仍 exit 0 ⇒ **结论未变**） | 无 |
| `docs/backlog/p0-foundation-roadmap.md:93 :100 :101 :103 :104 :142` | 各含 `ruff check agenerp tests/unit tests/contracts` / `commands.test 仍然没有…` / `GATE_VERIFY 与 CI 都复跑不到…` | **`成立`** —— 每一行都自带「**2026-08-23 追加**」并逐字声明「上面所有既有行一个字未改」⇒ 它们是**按 plan 分节的交付账本**，记的是当日事实，不是当期断言 | 无 |
| `docs/backlog/needs-human-expected-red-handoff.md:69 :141 :145 :152` | `commands.test` 的复跑机制 · 当时的引文块 | **`成立`**（`:69` 描述 `gate-verify.mjs` 的机制，今天仍真；其余是带引号的历史裁定记录） | 无 |
| `docs/backlog/00-roadmap-authoring-guide.md:21 :92` | 英文 `dependencies`（工作项依赖，非 `pyproject`） | **`成立`**（关键词误命中） | 无 |
| `docs/context/project-context.md:52` | 见 §4.4 | **`已过期`** | 已在本轮就地改准（B2 第 7 处） |
| `docs/architecture/model-management.md` §12.5 · `module-boundaries.md` §7.7 / §7.23.6 / `:4270` · `system-baseline.md` §14.7 / §14.10 · `roadmap:41` / `:108-109` | 见 §4 与 B2 表 | **`已过期`** | 已在本轮按各自口径处置（见 §6） |

### 5.2 `docs/design/` 零命中

```
$ grep -rn "…十二关键词…" docs/design/ | wc -l
0
```

⇒ 该目录不含同形态登记文字。**这一条是「扫过了、没有」，不是「没扫」。**

---

## 6 · 逐处处置清单（**两种口径分开，不许互相套用**）

**判断依据逐字是：该段是不是一份带时点的账本 / 交付记录 / 探针快照。**

### 6.1 断言性散文 —— **就地删被证伪的从句 + 加指针，重述零个事实**

| 位置 | 删掉的从句 | 保留的（一个字不动） |
|---|---|---|
| `module-boundaries.md` §7.7 `:485-488` | 「也不在 `unit-and-contracts` / `lint` 任何一个 job 的作用域里」·「`.github/workflows/**` 也在红线内」·「都在红线内」 | 「`tests/context` 不在 `commands.test` 里 ⇒ `GATE_VERIFY` 复跑不到」·「代偿控制：……」一行 ·「**不得因为本层测试自己是绿的就说「已被门禁覆盖」**」 |
| `model-management.md` §12.5 `:373-386` | 「不在任何 job 里」·「都在红线内」·「在人接进去之前」·「只有三条」·「`pyproject.toml` 没有声明 `dependencies`」·「真正解决要和把 `tests/routing` 接进 CI 一起做」 | `:374`「不在 `commands.test` 里」· `:379`「已在 `STATE.md` §3 追加 needs-human」· `:385`「惰性 import + 两道反测」——**判「真」的三句** |
| `module-boundaries.md` §7.23.6 | 「会红」·「不会被任何 job 跑到一次」·「零 lint 覆盖 / 七个目录」·「本节与本 plan 一个字节都不碰」·「三个目录仍然是错的 / 两边仍然不等」 | 「六件全部落在 `.github/workflows/**` ⇒ 红线 2，归人」**这一条今天仍然成立，逐字保留** |
| `docs/context/project-context.md:52` | ⚠️ 注解里被 `f795e47` 证伪的四段 | `ruff` 命令本体（`lint` job 要照抄的真相源）· 2026-08-23 追加段 · `F401` 变异实测 · 规则集边界 —— **一个字不动** |

⚠️ **`:378` / `:488` 那句「`missions/**` 与 `.github/workflows/**` 都在红线内」在两处各错一次，同一处置**：
收窄到 `missions/**` 一侧 + 把「在红线内」改成「在 `ai-autonomy-policy.md` 的 Protected Areas 里标 `blocked`」。
**`AGENTS.md` 的七条红线实读无 `missions/**`。** ⚠️ **不动 `:489`**（「代偿控制：……」那一行）——
它与 §7.6a `:331` 同句式、**都没有「只有」**，不是封闭计数；有「只有三条」的只是 `model-management.md:381`。

### 6.2 带时点的账本 / 交付记录 / 探针快照 —— **一个字不改写，只加时点限定 + 指针**

| 位置 | 是什么 | 追加的内容 | `git diff --numstat` 删除列 |
|---|---|---|---|
| `module-boundaries.md:4275`（§7.23.1 探针 `H1`） | 执行期探针快照 | 「该值为 2026-08-25 的观测；当期真值见 §7.26」 | **0** |
| `system-baseline.md` §14.7 `:1016-1017` | plan `2026-08-23-0337-1` 交付记录 | 时点限定 + 指针；**并逐字指出「一个字不加不减」这条口径本身仍然成立** | **0** |
| `system-baseline.md` §14.10 `:1587-1589` | plan `2026-08-23-0859-2` 交付记录 | 时点限定 + 指针；**并逐字指出本节结论没有失效**（`tests/gates` 至今不在 ruff 作用域内） | **0** |
| `roadmap:41` | 引擎回写的账本行 | 一条纯指针 + 证据路径，**紧贴假话之后** | 已有字**零改动**（逐字核过：追加 233 字符） |
| `roadmap:108` / `:109` | 同上 | 各一条纯指针 | 已有字**零改动**（追加 205 / 171 字符） |
| `docs/backlog/tools-dir-has-no-static-check-coverage.md` | 自带日期的事实账本 | 时点限定 + 指针（补扫查出，见 §5.1） | **0** |

⚠️ **`roadmap` 那三处的残余风险照实记（plan 的 `D5`）**：该文件由引擎在 closure 审计后回写，
追加句只能紧贴假话之后，**挡不住整行被后续追加淹没**；而该行已有的假话仍在原地。
**不接受「把假话直接删掉」这种缓解** —— 那是引擎回写的账本行。

---

## 7 · 收尾复跑（**与起草期 B5 逐条同一条命令**）

| 命令 | 退出码 | 输出 |
|---|---|---|
| `python3 tools/gates/check_expected_red.py` | **0** | `判定模式：default` · `门禁 29 项：预期红 0，绿 29，跳过 0` ⇒ **本 plan 不新增门禁** |
| `python3 -m pytest tests/unit tests/tools -q` | **0** | `928 passed, 29 skipped`（基线 `920`，**只增不减**，+8 = 新判据的八个 `def test_`） |
| `python3 -m pytest tests/contracts tests/routing tests/context -q` | **0** | `386 passed, 1 skipped`（与基线逐字相同） |
| `ruff check agenerp tests/unit tests/contracts tests/tools tests/routing tests/context tests/experiments tests/ui` | **0** | `All checks passed!` |

**红线自证**（`BASE = bc7f13f`）：

```
$ git diff --name-only bc7f13f -- tests/gates/ .github/workflows/ docs/masterplan/DECISIONS.md docs/masterplan/02-WBS.md
（无输出）                                    ← 红线 1 / 2 / 3 / 5

$ git diff --name-only bc7f13f -- missions/ agenerp/ tests/routing/ tests/context/ tests/tools/ \
    tests/contracts/ docker-compose.yml industry-packs/ pyproject.toml
（无输出）                                    ← 本 plan 自设的围栏，**不是红线**

$ git diff --numstat bc7f13f -- docs/masterplan/STATE.md
13	0	docs/masterplan/STATE.md              ← 删除列为 0（红线 5 的追加口径）
```

⚠️ **`missions/**` 列在围栏而不是红线**：`AGENTS.md` 的七条红线里没有它，
禁令出处是 `docs/context/ai-autonomy-policy.md:87` 的 Protected Areas（标 `blocked`）。**两者不许混为一谈。**
项目名 / 包名 / 命名空间未改（红线 4）· 全程未对 `${XM_PATH}` 发起任何读写（红线 6）· 未生成运行时 Server Script（红线 7）。

⚠️ **verification scope limited** —— 未跑整仓 `pytest tests -q -m "not live"`（**已知基线即红**，
见 `docs/backlog/gates-and-tools-leak-env-across-directories.md`）· 未起 docker 栈 · 未跑任何 `-m live` ·
**未经 CI 服务端复跑**。
