# 故意写坏的行业包（判据夹具）

这里的包**都是坏的，且必须一直是坏的**：它们是 `python3 -m agenerp.packs validate`
四种处置（plan §6 H6）里 ②③ 两种的固定输入。

- `missing-test-case/` —— 第二条规则没有 `test_case`。验收原文是「无 `test_case` 的规则即失败」，
  期望退出码 **4**（装载失败），且消息指名到那条 `rule_id`。
- `failing-test-case/` —— 规则形状合法、`test_case` 也在，但**测例跑不过**（`expect_quantity` 与实际对不上）。
  期望退出码 **5**，且消息带期望与实测。

⚠️ **不放进 `industry-packs/`**：产品制品目录里不许躺着故意写坏的包 —— 那是给人看的行业包，
不是判据的输入。判据用 CLI 的 `--packs-dir` 指到这里。

⚠️ 这两份是**静态**夹具，只覆盖「某一条规则坏了」的一个位置。H3 要求的
「逐条变异、含最后一条」由 `test_industry_pack.py` 从真包**派生**到 `tmp_path` 完成 ——
只测第一条挡不住「只校验第一条就返回」的假实现。
