#!/bin/sh

OPTIONS_FILE="/data/options.json"

PASS_REQS=$(grep -o '"pass_reqs":[^,}]*' "$OPTIONS_FILE" | grep -o '[0-9]*')
SERIAL_TTY=$(grep -o '"serial_tty":"[^"]*"' "$OPTIONS_FILE" | cut -d'"' -f4)
PASS_REQS=${PASS_REQS:-1020}

echo "[INFO] Starting Infinitude (pass_reqs=${PASS_REQS})"

mkdir -p /data/infinitude/state

export APP_SECRET="${APP_SECRET:-infinitude}"
export PASS_REQS="${PASS_REQS}"
export MODE="Production"

cd /infinitude

exec ./infinitude daemon \
    -l "http://*:3000" \
    --state /data/infinitude/state \
    ${SERIAL_TTY:+--serial_tty "$SERIAL_TTY"}
