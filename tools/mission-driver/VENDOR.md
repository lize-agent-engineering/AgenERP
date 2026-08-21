# Vendored fork · mission-driver

| | |
|---|---|
| 上游 | https://github.com/entropy-cloud/attractor-guided-engineering-template （MIT） |
| 钉死于 | `58f7df70bd365591e1bbba7add77b977d907c4fb`（2026-08-17） |
| vendor 日期 | 2026-08-20 |
| 引擎版本 | package.json `1.1.0` |

## 为什么 vendor 而不是 submodule

方案 C 裁决「fork + 钉死版本，同时向上游提 PR」。vendor 让本地补丁可见、可 diff、可被 CI 审，
不需要开发者多记一条 submodule 命令。代价是同步上游要手工——**只在有明确收益时同步**。

## 本仓打的补丁（改动上游文件时必须在此登记）

| # | 文件 | 改法 | 是否提上游 |
|---|---|---|---|
| P1 | `src/flow-loader.js` | `SCRIPT_REGISTRY` 可从 mission.json 的 `scripts` 字段扩展 | **是**（通用改动） |
| P3 | `flows/plan-execution.json` | `BUILD_VERIFY` 之后插入 `GATE_VERIFY` 独立判定步 | 否（项目侧策略） |
| P5 | `src/config.js` · `src/main.js` | 新增 `--driver codex`（跨模型对照用）：AGENTS.md 原生加载故不下发人格，prompt 走 stdin | 可考虑（driver 层通用） |
| P4 | `src/config.js` · `src/runner.js` · `agents/build.claude.md` · `agents/claude-loop.settings.json` | 新增 `--driver claude`（D-3）：settings 关 hooks/自带技能，persona 经 `--append-system-prompt` 显式下发 | 可考虑（driver 层通用） |

（P2 是项目侧新增文件 `tools/gates/gate-verify.mjs`，不改上游。）

查看本仓相对上游的全部改动：`git log --oneline -- tools/mission-driver/`

## 上游自带的测试失败（**不是我们打坏的**）

vendor 当天在**未打补丁的原始克隆**上跑 `node --test test/*.test.js`，结果 621 pass / 2 fail：

- `WI4 mission-check CLI — Case D: pathToFileURL normalization anchor`
- `FlowEngine — null marker soft-lands via onMaxRetries instead of hard-failing`

打完 P1/P3 后本仓失败集合与之**逐条相同**。以后同步上游或改引擎时，用这两条当基线：
失败集合一旦多出第三条，就是我们弄坏的。

比对方法：
```
node --test --test-reporter=tap test/*.test.js | grep '^not ok'
```

## vendor 边界

引擎的测试引用了上游 `tools/` 下的兄弟文件，只 vendor `tools/mission-driver/` 会漏。
本仓一并带上：`tools/check-doc-references.mjs`、`tools/check-oversized-code-files.mjs`。
