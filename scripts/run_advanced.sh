#!/usr/bin/env bash
set -euo pipefail
PORT="${1:-8592}"
mkdir -p .run
if [[ -f ".run/streamlit.$PORT.pid" ]]; then
  kill "$(cat .run/streamlit.$PORT.pid)" 2>/dev/null || true
  rm -f ".run/streamlit.$PORT.pid"
fi
streamlit run app_advanced.py --server.address 127.0.0.1 --server.port "$PORT" --server.headless true \
  > ".run/streamlit.$PORT.log" 2>&1 &
echo $! > ".run/streamlit.$PORT.pid"
echo "Advanced app running: http://127.0.0.1:$PORT"

