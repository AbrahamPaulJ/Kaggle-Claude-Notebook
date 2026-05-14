#!/data/data/com.termux/files/usr/bin/bash
set -e

echo "Installing Claude Code..."
npm install -g @anthropic-ai/claude-code@2.1.112 --silent

export CLAUDE_CODE_DISABLE_UPDATES=1


termux-wake-lock

pkill -f notebook_ui.py 2>/dev/null || true
sleep 1

cd /data/data/com.termux/files/home/Kaggle-Claude-Notebook
nohup python3 notebook_ui.py > ~/kaggle-ui.log 2>&1 &
sleep 2

echo ""
echo "Server running — Android will not kill it"
echo "Logs: tail -f ~/kaggle-ui.log"
echo "Stop: kill \$(lsof -ti:5000)"
echo ""
termux-open-url http://localhost:5000
