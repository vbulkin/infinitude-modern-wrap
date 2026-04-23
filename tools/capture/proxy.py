"""Thermostat ↔ Infinitude capture-and-forward proxy.

Sits inline between a Carrier/Bryant thermostat and an upstream
Infinitude instance. Records every request + response pair to disk as
replay fixtures for the Phase 3 southbound protocol tests, then
forwards transparently so the thermostat sees unchanged behavior.

Usage
-----

    pip install -e addon/[dev]           # shares the addon's venv
    export CAPTURE_UPSTREAM=http://<legacy-infinitude-host>:3000
    export CAPTURE_DIR=./captures
    python tools/capture/proxy.py --port 3001

Then point the thermostat (or your DNS override) at this proxy's
port. Each request produces three files:

    captures/<iso-ts>_<seq>.meta.json       # method, path, headers, status, timing
    captures/<iso-ts>_<seq>.request.<ext>   # raw request body (.xml or .bin)
    captures/<iso-ts>_<seq>.response.<ext>  # raw response body

Multi-file layout (rather than one JSON blob) keeps XML human-readable
and gives `git diff` a fair chance on captured bodies.

NOTE: this proxy only sees the thermostat-to-Infinitude leg. Carrier
cloud passthrough traffic flows from Infinitude outbound and is NOT
captured here. That requires a second proxy inserted at Infinitude's
upstream side (e.g. a mitmproxy-style tool that Infinitude is
configured to route api.ing.carrier.com through).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request, Response


def _upstream_url() -> str:
    url = os.environ.get("CAPTURE_UPSTREAM")
    if not url:
        print("error: set CAPTURE_UPSTREAM to the existing Infinitude base URL", file=sys.stderr)
        sys.exit(2)
    return url.rstrip("/")


def _capture_dir() -> Path:
    d = Path(os.environ.get("CAPTURE_DIR", "./captures")).resolve()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ext_for(content_type: str | None, body: bytes) -> str:
    if content_type and "xml" in content_type.lower():
        return "xml"
    if content_type and "json" in content_type.lower():
        return "json"
    if body[:1] == b"<":
        return "xml"
    return "bin"


def _safe_path_slug(path: str) -> str:
    slug = path.strip("/").replace("/", "_") or "root"
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in slug)[:80]


def create_app(
    *,
    upstream: str | None = None,
    capture_dir: Path | None = None,
    client: httpx.AsyncClient | None = None,
) -> FastAPI:
    upstream = (upstream or _upstream_url()).rstrip("/")
    capture_dir = capture_dir or _capture_dir()
    seq = 0
    seq_lock = asyncio.Lock()
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30.0)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            if owns_client:
                await client.aclose()

    app = FastAPI(title="Infinitude Capture Proxy", lifespan=lifespan)

    @app.api_route(
        "/{full_path:path}",
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
    )
    async def catch_all(full_path: str, request: Request) -> Response:
        nonlocal seq
        async with seq_lock:
            seq += 1
            n = seq

        started = datetime.now(timezone.utc)
        body = await request.body()
        hop_by_hop = {"host", "content-length", "connection", "transfer-encoding"}
        fwd_headers = {k: v for k, v in request.headers.items() if k.lower() not in hop_by_hop}

        target = f"{upstream}/{full_path}"
        try:
            upstream_resp = await client.request(
                request.method,
                target,
                params=request.query_params,
                content=body,
                headers=fwd_headers,
            )
            resp_status = upstream_resp.status_code
            resp_body = upstream_resp.content
            resp_headers = dict(upstream_resp.headers)
            upstream_error: str | None = None
        except httpx.HTTPError as exc:
            resp_status = 502
            resp_body = f"capture proxy: upstream error: {exc}".encode()
            resp_headers = {"content-type": "text/plain"}
            upstream_error = str(exc)

        finished = datetime.now(timezone.utc)
        duration_ms = int((finished - started).total_seconds() * 1000)

        ts = started.strftime("%Y%m%dT%H%M%S.%f")[:-3] + "Z"
        base = f"{ts}_{n:04d}_{request.method}_{_safe_path_slug(full_path)}"
        req_ext = _ext_for(request.headers.get("content-type"), body)
        resp_ext = _ext_for(resp_headers.get("content-type"), resp_body)

        (capture_dir / f"{base}.request.{req_ext}").write_bytes(body)
        (capture_dir / f"{base}.response.{resp_ext}").write_bytes(resp_body)

        meta: dict[str, Any] = {
            "id": base,
            "timestamp": ts,
            "duration_ms": duration_ms,
            "upstream_url": target,
            "upstream_error": upstream_error,
            "request": {
                "method": request.method,
                "path": f"/{full_path}",
                "query": dict(request.query_params),
                "headers": dict(request.headers),
                "body_bytes": len(body),
                "body_file": f"{base}.request.{req_ext}",
            },
            "response": {
                "status": resp_status,
                "headers": resp_headers,
                "body_bytes": len(resp_body),
                "body_file": f"{base}.response.{resp_ext}",
            },
        }
        (capture_dir / f"{base}.meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        print(
            f"[{ts}] #{n:04d} {request.method} /{full_path} -> {resp_status} "
            f"({len(body)}B req, {len(resp_body)}B resp, {duration_ms}ms)",
            flush=True,
        )

        passthrough_headers = {
            k: v for k, v in resp_headers.items()
            if k.lower() not in hop_by_hop
        }
        return Response(
            content=resp_body,
            status_code=resp_status,
            headers=passthrough_headers,
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Infinitude capture proxy")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()
    uvicorn.run(create_app(), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
