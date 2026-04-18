#!/bin/bash
# start-nanoclaw.sh — Start NanoClaw without systemd
# To stop: kill \$(cat /share/nanoclaw/nanoclaw.pid)

set -euo pipefail

cd "/share/nanoclaw"

# Stop existing instance if running
if [ -f "/share/nanoclaw/nanoclaw.pid" ]; then
  OLD_PID=$(cat "/share/nanoclaw/nanoclaw.pid" 2>/dev/null || echo "")
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing NanoClaw (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 2
  fi
fi

echo "Starting NanoClaw..."
nohup "/usr/bin/node" "/share/nanoclaw/dist/index.js" \
  >> "/share/nanoclaw/logs/nanoclaw.log" \
  2>> "/share/nanoclaw/logs/nanoclaw.error.log" &

echo $! > "/share/nanoclaw/nanoclaw.pid"
echo "NanoClaw started (PID $!)"
echo "Logs: tail -f /share/nanoclaw/logs/nanoclaw.log"
