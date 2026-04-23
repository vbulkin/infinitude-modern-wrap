#!/usr/bin/env sh
set -e

exec uvicorn infinitude_proxy.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-3000}" \
    --log-level "${LOG_LEVEL:-info}" \
    --log-config /opt/infinitude-proxy/log_config.yaml
