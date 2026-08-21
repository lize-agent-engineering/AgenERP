# tests/gates —— 门禁测试（裁判）

**这个目录里的文件，loop 一律不得修改。** 改断言、加 `skip`/`xfail`、放松 fixture、删文件、改名——
任意一种都视为改裁判，`git diff` 触及本路径即**立即停机**（见 `AGENTS.md` 红线 1、CI `gates-untouched` job）。

## 这些测试现在应该是红的

它们是**先写判据、后写实现**的产物：判据来自 `docs/backlog/implementation-roadmap.md` 的阶段验收，
逐条翻译成可执行断言。实现还不存在，所以现在全红——**这一步的正确结果就是失败**。

绿灯的唯一合法来源是：实现真的做出来了。

## 判据出处

| 测试 | 判据来源 |
|---|---|
| `test_snapshot_diff_structured` | roadmap P0 验收「能对同一站点打两次快照并输出结构化 diff」 |
| `test_normalizer_idempotent` | roadmap P0 定制包规范化器；Spike 06 打脸点：什么都不改重新导出也会产生 diff |
| `test_customization_roundtrip_delete` | roadmap P0 验收「新增字段 → 导出 → `git diff` 干净 → 从包删除 → apply → 字段真的消失」 |
| `test_zero_dep_boot` | roadmap P0 验收「空环境变量下 `docker compose up` 成功」+ 首页显示「AI 能力未配置」 |

## 要改判据怎么办

判据被实测推翻时，走 `docs/masterplan/01-EXECUTION-MODEL.md` §2 的 needs-human 五步，由**人**改，
并在 roadmap 里追加一行写清是什么实测推翻了它。**不要在这里静悄悄改。**

## 预期红名单在哪

在 `tools/gates/expected-red.txt`，**不在本目录**。分清两件事：
本目录的测试代码是**裁判**，红线保护，一个字不许改；那份名单只是
「哪些裁判现在预期是红的」的**账本**，实现到位时 loop 应当在同一提交里划掉对应行。
账本只能变短，变长需 `Gates-Change-Approved-By:` 人工批准（CI 棘轮 job 盯着）。
