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

# Persist state across container restarts: symlink /infinitude/state -> /data/infinitude/state
mkdir -p /data/infinitude/state
rm -rf /infinitude/state
ln -sf /data/infinitude/state /infinitude/state

# Write infinitude.json config (matches upstream entrypoint.sh)
cat > /infinitude/infinitude.json <<EOF
{"app_secret":"${APP_SECRET:-infinitude}","pass_reqs":${PASS_REQS},"serial_tty":"${SERIAL_TTY}","serial_socket":""}
EOF

# Test SSL/HTTPS connectivity at startup — results readable via /api/state/ssl-test.txt
SSL_TEST="/data/infinitude/state/ssl-test.txt"
{
  echo "=== SSL Test $(date) ==="
  perl -MIO::Socket::SSL -e 'print "IO::Socket::SSL: OK v$IO::Socket::SSL::VERSION\n"' 2>&1 || echo "IO::Socket::SSL: MISSING"
  perl -MNet::SSLeay -e 'print "Net::SSLeay: OK v$Net::SSLeay::VERSION\n"' 2>&1 || echo "Net::SSLeay: MISSING"
  curl -sf -o /dev/null -w "HTTPS google.com: HTTP %{http_code}\n" https://www.google.com 2>&1 || echo "HTTPS google.com: FAILED"
  curl -sf -o /dev/null -w "HTTPS Carrier Alive: HTTP %{http_code}\n" https://www.api.eng.bryant.com/Alive 2>&1 || echo "HTTPS Carrier Alive: FAILED"
  echo "=== End ==="
} | tee "$SSL_TEST"

export APP_SECRET="${APP_SECRET:-infinitude}"
export PASS_REQS="${PASS_REQS}"
export MODE="Production"

cd /infinitude

exec ./infinitude daemon \
    -m "$MODE" \
    -l "http://*:3000" \
    ${SERIAL_TTY:+--serial_tty "$SERIAL_TTY"}
