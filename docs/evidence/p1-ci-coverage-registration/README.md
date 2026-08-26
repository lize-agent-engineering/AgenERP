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

## 3 · 判据的活性证明（变异自查 N1–N10）

见 §4。
