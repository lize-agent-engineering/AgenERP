# 洞察 Agent 归因的首次活端点实跑（P1.5 第 2 个 plan，2026-08-25）

本目录是 plan
[`2026-08-25-0225-2-insight-attribution-live-run.md`](../../plans/p1-insight/2026-08-25-0225-2-insight-attribution-live-run.md)
Phase 2 的落盘证据。归因本体在 `agenerp/insight/`（本 plan **一行未改**），
实验设施在 `tools/experiments/p1_insight_live/run.py`。

## 复跑

```bash
set -a; . ./.env; . ~/.config/agenerp/secrets.env; set +a
export AGENERP_SITE=frontend AGENERP_SITE_URL=http://127.0.0.1:18080
export AGENERP_ADMIN_PASSWORD=<本地 compose 的 Administrator 口令>
export AGENERP_LLM_BASE_URL="$DASHSCOPE_BASE_URL" \
       AGENERP_LLM_API_KEY="$DASHSCOPE_API_KEY" \
       AGENERP_LLM_MODEL=qwen3.6-plus
python3 -m tools.experiments.p1_insight_live.run --inspect-only   # 零 LLM、零 token
python3 -m tools.experiments.p1_insight_live.run                  # 一次完整归因
```

**凭据一个字节不在本目录里。** 脚本落盘前扫一遍 `credential_scan.scanned` 列的那几个变量，
扫到就拒绝落盘并非零退出；**跳过的短值照实记在 `credential_scan.skipped_too_short`**
（本机 `AGENERP_ADMIN_PASSWORD` 只有 5 个字符，扫它会在任何含 `Administrator` 的证据上误报）。

## 文件

| 文件 | 内容 |
|---|---|
| `live-run-01.json` | 第 1 跑（`2026-08-24T21:17:50Z` UTC）。25 次模型调用，`stopped = max-turns` |
| `live-run-02.json` | **原样复跑**（`2026-08-24T21:20:39Z` UTC）。22 次模型调用，`stopped = tool-call-runaway` |

两份文件的键集合相同（`run` / `at` / `pack` / `site` / `model` / `inspection` /
`attributions` / `checks` / `requests` / `credential_scan` / `elapsed_seconds` / `notes`），
形状由 `tests/unit/test_insight_live_harness.py` 钉住。

## 这一跑证明了什么，没证明什么

**证明了（结构化事实，`checks` 六项两跑全绿，脚本 exit 0）**：

- 巡检 → 归因这条链在**真站点 + 真模型**上走得通，一次都没有跑飞、没有越权、没有写；
- 命中记录**逐字未被改写**（`hits_unchanged`，两处各记一遍）；
- **账本条数 == `chat()` 被调次数**（两个数来自不同采集面）；三项 usage 全部 > 0；
  `total_matches_endpoint` 逐条为真；
- 取证轨迹**非空且工具调用可枚举**；
- 站点侧**零白名单外请求**（`requests.denied` 空、`other_verbs` 空）。

**没有证明（照实写死，不得被下游读成已验证）**：

- ❌ **归因文本的质量。** 两跑的 `answer` 都是**空文本** —— 模型自始至终没交出答案
  （`accepted = false`）。本目录里**没有一段归因文本**。
- ❌ **判定器在归因题族上的表现。** `attributions[].judge` 两跑都是
  `ok=false` + `JudgingError: 待判的答案是空文本`。**没有观测到任何跨题族标签。**
- ❌ **稳定性 / 分布。** 两跑不是采样计划，是「超了先原样复跑一次」这条裁判规则的产物。

## 为什么没有答案：一个实测定位的活缺陷

`doc.links` 对 `Item/HRD-PACK-5K` **必然 HTTP 500**：`scan_links` 会遍历所有指向 `Item` 的
Link 字段宿主，其中 `Quick Stock Balance` 在本站点上是 **Single DocType**（`issingle = 1`，
没有实体表），`GET /api/resource/Quick Stock Balance` 直接回
`pymysql.err.ProgrammingError: ('DocType', 'Quick Stock Balance')`。
而 L1 门禁要的正是「对 `HRD-PACK-5K` 调过 `doc.links`」——**这条证据在本站点上取不到**，
循环因此只能一直取证到轮数 / 工具调用上限。

登记在 [`docs/bugs/03-doc-links-dies-on-single-doctypes.md`](../../bugs/03-doc-links-dies-on-single-doctypes.md)
与 `docs/masterplan/STATE.md` §3 的 needs-human 队列。**本 plan 不改它**（plan §3 Non-Goal 2 / D1）。

## verification scope limited

本目录的两跑**只在本机、只跑了两次、CI 完全没有覆盖**（活栈 + 真 key 都不在 runner 上）。
它们证明的是「这条链在这台机器的这个站点上今天走得通」，不是任何一般性结论。
