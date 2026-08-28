# 分支清理留档 · 2026-08-28

> 人要求：「只保留 main、p1、p2、以及未来的 p3 等，保持清晰的分支线」。
> **删之前逐个验过零损失**，方法与证据见下。恢复命令：`git branch <名> <sha>`。

## 判定方法

- `git branch --merged main` 只看**祖先关系**，会把「做了实验又 revert」的分支判成未并入 —— 不够。
- `git diff main <branch>` 也不对：这些分支停在 08-22/23（P0 期），
  差异里那 10 万行「删除」其实是 **main 后来新增的**，不是分支独有的工作。
- 用 `git cherry -v main <branch>`：逐条判「等价补丁在不在 main 里」。
- 对 cherry 报「main 里没有」的，**再逐条查内容是否真的落在 main**
  （补丁 ID 匹配不上 ≠ 内容不在 —— rebase/squash 之后 ID 就变了）。

## 逐条核对结论

| 分支 | cherry 判定 | 内容复核 | 结论 |
|---|---|---|---|
| `ci/1206-1-verdict-guard-proof` | 全有等价补丁 | — | 删 |
| `ci/0120-1-unit-contracts-land` | 全有等价补丁 | — | 删 |
| `ci/0337-2-docs` | 全有等价补丁 | — | 删 |
| `ci/0337-2-land` | 全有等价补丁 | — | 删 |
| `ci/1206-2-l2-live-land` | 全有等价补丁 | — | 删 |
| `ci/2325-2-seed-land` | 全有等价补丁 | — | 删 |
| `ci/0120-1-unit-contracts` | 4 条「没有」 | **全是 EXPERIMENT + 对应 Revert 成对，净效果为零** | 删 |
| `ci/0337-2-experiments` | 8 条「没有」 | **全是 experiment，末条「最终 revert…名单复原到 main 基线」** | 删 |
| `ci/0337-1-seed-lint-coverage` | 5 条「没有」 | 3 条是 MUTATION+Revert 成对；那 1 条真实的两个 job **在 main**（`gates.yml:643 seed-selfverify` · `:663 lint`）| 删 |
| `ci/2325-2-seed-chain-on-ci` | 2 条「没有」 | `gates-l2-seed` job **在 main**（`gates.yml:491`）| 删 |
| `ci/0027-2-l2-full-live-gate` | 1 条「没有」 | 「零孤儿列」修复**在 main**（`snapshot.py:342` 逐字在；`git diff main c6a9269 -- oob.py snapshot.py` **为空**）| 删 |
| `p1-insight` | 9 条「没有」 | **真有独有工作**（样板公司重构 · 站点重建 · 外协四步链 · CP9 复盘）| **保留** |

## 删除前的 SHA（恢复用）

```
git branch ci/0027-2-l2-full-live-gate      c6a92697d78414d788c4178da20b859afac911e7
git branch ci/0120-1-unit-contracts         17c7dff52c37d60fceee8a1f2c3eb5c6f5523d3d
git branch ci/0120-1-unit-contracts-land    622bc4e16410ec131f8f927ac2e35f98410ecb0a
git branch ci/0337-1-seed-lint-coverage     b089fb55ef97a745cdb03580f5251809472afe5a
git branch ci/0337-2-docs                   07a26ba36b7d2f423fe63157bb6e132b7defb8c1
git branch ci/0337-2-experiments            e62aafae024073cfff41ee00b261241a31ddcdca
git branch ci/0337-2-land                   f756f504fa0ed09390bf43e27ca35a4feaa2fb08
git branch ci/1206-1-verdict-guard-proof    050eedf01bd309b5f57c23a00e0a2c8d6ea4a113
git branch ci/1206-2-l2-live-land           a22247225220297ed38efd3fd6d1a61c43553ea4
git branch ci/2325-2-seed-chain-on-ci       d6ed11d51b4aa35d145f8b79ae0ec25f145323fd
git branch ci/2325-2-seed-land              5fec32301d8f484ab39f8389cc11f622ab5b1629
```

## 保留下来的分支线

- `main` —— 主线
- `p1-insight` —— P1（⚠️ **有 9 条 main 里没有的提交**，与 main 已分叉）
- `p2-views` —— P2（本轮工作）

## worktree

```
/Users/lize/Claude/Projects/AgenERP           eb82f19 [main]
/Users/lize/Claude/Projects/AgenERP-p2-views  2eb6a38 [p2-views]
```
