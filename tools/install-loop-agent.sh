#!/usr/bin/env bash
# 把监督器装成 launchd 用户代理：开机自启 + 崩溃重拉。
#
# 用法：
#   tools/install-loop-agent.sh install <todo-id> [mission]
#   tools/install-loop-agent.sh uninstall
#   tools/install-loop-agent.sh status
#
# 两个刻意的选择：
#   · KeepAlive 只在 Crashed 时重拉。监督器撞停机条件是**正常退出（0）**，
#     不能被 launchd 拉起来——那等于绕过停机闸。只有真崩溃才重来。
#   · PATH 写死绝对路径。launchd 的环境几乎是空的，继承不到登录 shell 的 PATH，
#     不写死就会在开机自启时找不到 node / claude / loopx。
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.agenerp.loop"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOOPX_DEFAULT="$HOME/Library/Python/3.12/bin/loopx"

case "${1:-status}" in
  install)
    TODO="${2:?用法: tools/install-loop-agent.sh install <todo-id> [mission]}"
    MISSION="${3:-p0-foundation}"
    mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/_tmp"
    cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$ROOT/tools/loop-supervisor.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
  <!-- 只在崩溃时重拉：撞停机条件是正常退出，重拉等于绕过停机闸 -->
  <key>KeepAlive</key>
  <dict><key>Crashed</key><true/></dict>
  <key>ThrottleInterval</key><integer>120</integer>
  <key>StandardOutPath</key><string>$ROOT/_tmp/supervisor.log</string>
  <key>StandardErrorPath</key><string>$ROOT/_tmp/supervisor.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:$HOME/Library/Python/3.12/bin:/Library/Frameworks/Python.framework/Versions/3.12/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>HOME</key><string>$HOME</string>
    <key>AGENERP_MISSION</key><string>$MISSION</string>
    <key>AGENERP_TODO</key><string>$TODO</string>
    <key>LOOPX_BIN</key><string>$LOOPX_DEFAULT</string>
  </dict>
</dict>
</plist>
PLIST_EOF
    plutil -lint "$PLIST" >/dev/null || { echo "plist 语法不合法"; exit 1; }
    launchctl unload "$PLIST" 2>/dev/null
    launchctl load "$PLIST" && echo "已装载 $LABEL（mission=$MISSION todo=$TODO）"
    echo "日志：$ROOT/_tmp/supervisor.log"
    echo "停止：tools/install-loop-agent.sh uninstall"
    ;;
  uninstall)
    launchctl unload "$PLIST" 2>/dev/null && echo "已卸载 $LABEL" || echo "本来就没装载"
    rm -f "$PLIST"
    ;;
  status)
    if launchctl list | grep -q "$LABEL"; then
      echo "已装载："; launchctl list | grep "$LABEL"
    else
      echo "未装载"
    fi
    [ -f "$ROOT/.mission-halt.json" ] && { echo "--- 停机记录（监督器会拒绝继续）---"; cat "$ROOT/.mission-halt.json"; }
    exit 0
    ;;
  *) echo "用法: tools/install-loop-agent.sh {install <todo-id> [mission]|uninstall|status}"; exit 1 ;;
esac
