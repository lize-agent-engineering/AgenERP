/**
 * GATE_VERIFY —— 独立判定步（方案 C 补丁 P2）
 *
 * 由引擎自身 spawn 子进程复跑 mission.commands，**以退出码判定**。
 * AI 不参与该判定：BUILD_VERIFY 那一步若谎报 pass，这里立刻打脸。
 *
 * 判定顺序（任一失败即整体 fail，短路返回）：
 *   0. 写保护：git diff 触及 tests/gates/** → 立即 fail（写保护第 1 层，见 REF:GATE-PROTECT）
 *   1. mission.commands.lint
 *   2. mission.commands.typecheck
 *   3. mission.commands.test
 *   4. mission.commands.build
 *
 * 返回 { marker: "pass"|"fail", text }。失败时 text 带真实输出（截断），
 * 由引擎 append 进下一轮 prompt —— 让模型看见真实报错，而不是自己想象的报错。
 */
import { spawnSync } from "node:child_process";

const MAX_OUTPUT = 4000; // 单条命令回灌进 prompt 的输出上限，防止把上下文撑爆
const PROTECTED = ["tests/gates/"];

function run(cmd, cwd) {
  const started = Date.now();
  const r = spawnSync(cmd, { cwd, shell: true, encoding: "utf8", timeout: 30 * 60 * 1000 });
  const out = `${r.stdout || ""}${r.stderr || ""}`;
  return {
    cmd,
    code: r.status === null ? 124 : r.status, // null = 被超时/信号杀掉
    ms: Date.now() - started,
    output: out.length > MAX_OUTPUT ? `…（前略）\n${out.slice(-MAX_OUTPUT)}` : out,
  };
}

function protectedFilesTouched(cwd) {
  const r = spawnSync("git", ["diff", "--name-only", "HEAD"], { cwd, encoding: "utf8" });
  if (r.status !== 0) return [];
  return (r.stdout || "")
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l && PROTECTED.some((p) => l.startsWith(p)));
}

export default function gateVerify(delegates, flowVars) {
  const cwd = delegates?.config?.projectRoot || process.cwd();
  const commands = delegates?.config?.mission?.commands || {};

  const fail = (reason, details) => {
    flowVars?.set?.("GATE_VERIFY_RESULT", "FAIL");
    flowVars?.set?.("GATE_VERIFY_DETAILS", reason);
    return { marker: "fail", text: `GATE_VERIFY FAILED — ${reason}\n${details}` };
  };

  // 0. 写保护：改裁判即失败，且不再往下跑
  const touched = protectedFilesTouched(cwd);
  if (touched.length) {
    return fail(
      "本轮改动触及门禁测试（tests/gates/**）",
      [
        "被改动的文件：",
        ...touched.map((f) => `  - ${f}`),
        "",
        "门禁是裁判，loop 不得修改（AGENTS.md 红线 1）。",
        "请 `git checkout -- tests/gates/` 撤销这些改动后重来。",
        "判据确实需要改时，走 needs-human 五步由人处置，不要自行修改。",
      ].join("\n"),
    );
  }

  // 1-4. 逐条复跑，短路
  const order = ["lint", "typecheck", "test", "build"];
  const ran = [];
  for (const key of order) {
    const cmd = commands[key];
    if (!cmd) continue;
    const r = run(cmd, cwd);
    ran.push(r);
    if (r.code !== 0) {
      return fail(
        `${key} 失败（exit ${r.code}）`,
        [
          `命令：${r.cmd}`,
          `退出码：${r.code}${r.code === 124 ? "（超时或被信号终止）" : ""}`,
          `耗时：${(r.ms / 1000).toFixed(1)}s`,
          "",
          "真实输出：",
          r.output || "（无输出）",
          "",
          `已通过：${ran.slice(0, -1).map((x) => x.cmd).join(" | ") || "（无）"}`,
        ].join("\n"),
      );
    }
  }

  if (!ran.length) {
    return fail(
      "mission.commands 里一条可执行命令都没有",
      "至少配置 commands.test。没有命令就没有判据，等于没有门禁。",
    );
  }

  flowVars?.set?.("GATE_VERIFY_RESULT", "PASS");
  flowVars?.set?.("GATE_VERIFY_DETAILS", "");
  return {
    marker: "pass",
    text: [
      "GATE_VERIFY PASSED —— 以下命令由引擎独立复跑，均退出码 0：",
      ...ran.map((r) => `  ✓ ${r.cmd}  (exit 0, ${(r.ms / 1000).toFixed(1)}s)`),
    ].join("\n"),
  };
}
