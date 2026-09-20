#!/bin/zsh
# Installs (or reinstalls) the daily launchd job. Run once: zsh launchd/install.sh
set -e
SRC="${0:A:h}/com.lukizhao.gard-radar-mp.plist"
DST="$HOME/Library/LaunchAgents/com.lukizhao.gard-radar-mp.plist"
cp "${0:A:h}/gard-radar-mp-run.sh" "$HOME/.claude/gard-radar-mp-run.sh" && chmod +x "$HOME/.claude/gard-radar-mp-run.sh"
launchctl bootout "gui/$(id -u)/com.lukizhao.gard-radar-mp" 2>/dev/null || true
cp "$SRC" "$DST"
launchctl bootstrap "gui/$(id -u)" "$DST"
launchctl print "gui/$(id -u)/com.lukizhao.gard-radar-mp" | grep -E 'state|program|runs' | head -5
echo "installed: runs daily 07:40, log at ~/.claude/gard-radar-mp.log"
