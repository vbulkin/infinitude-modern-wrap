#!/bin/sh

OPTIONS_FILE="/data/options.json"

# Parse options — try jq first, fall back to grep
if command -v jq >/dev/null 2>&1 && [ -f "$OPTIONS_FILE" ]; then
  PASS_REQS=$(jq -r '.pass_reqs // empty' "$OPTIONS_FILE" 2>/dev/null)
  SERIAL_TTY=$(jq -r '.serial_tty // empty' "$OPTIONS_FILE" 2>/dev/null)
else
  PASS_REQS=$(grep -o '"pass_reqs"\s*:\s*[0-9]*' "$OPTIONS_FILE" 2>/dev/null | grep -o '[0-9]*')
  SERIAL_TTY=$(grep -o '"serial_tty"\s*:\s*"[^"]*"' "$OPTIONS_FILE" 2>/dev/null | cut -d'"' -f4)
fi
PASS_REQS=${PASS_REQS:-300}

echo "[INFO] Starting Infinitude (pass_reqs=${PASS_REQS}, serial_tty=${SERIAL_TTY:-none})"

mkdir -p /data/infinitude/state

export APP_SECRET="${APP_SECRET:-infinitude}"
export PASS_REQS="${PASS_REQS}"
export MODE="Production"

cd /infinitude

exec ./infinitude daemon \
    -l "http://*:3000" \
    --state /data/infinitude/state \
    ${SERIAL_TTY:+--serial_tty "$SERIAL_TTY"}
