"""Export captured traffic rows to a fixture-friendly directory tree.

Reads from `/v1/debug/capture/*` on a running addon and writes each
entry's request and response bodies to disk, organized by direction
and HTTP method, with a filename carrying the row id + path so the
ordering and provenance survive curation.

Typical workflow:
  1. POST /v1/debug/capture/start           (on the addon)
  2. (live traffic accumulates)
  3. python export_capture.py --base-url http://192.168.1.233:3001 \
                              --out-dir addon/tests/fixtures/thermostat/live_20260424
  4. POST /v1/debug/capture/stop            (when done)
  5. Hand-curate: copy/rename the interesting bodies into the fixture
     set that replaces the 0000TEST0000 synthetic anchors.

Stdlib-only (urllib + json + base64) so the script runs on whichever
machine the operator happens to be at without a venv. Base URL
defaults to the dev laptop's localhost:3001 — override with
`--base-url` for the HA box.

Output layout:
  {out-dir}/
    southbound/
      POST_systems_{serial}_status_0001.xml            (request body)
      POST_systems_{serial}_status_0001.response.xml   (response body)
      POST_systems_{serial}_0002.xml
      ...
    northbound/
      GET_v1_state_0042.response.json
      PATCH_v1_zones_1_0043.request.json
      PATCH_v1_zones_1_0043.response.json
      ...
    carrier_out/
      (empty until Carrier passthrough lands + emits capture rows)
    _index.tsv                                         (id\tts\tmethod\tpath\tstatus)

Response bodies carry `.response.{ext}`; request bodies drop the
middle component (matching the symmetric shape). Ext is picked from
the content-type suffix so .xml/.json/.bin are visually obvious.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


def _http_get(url: str) -> dict | list:
    """Fetch a JSON response. 3xx/4xx/5xx raise — the script stops
    rather than silently skip rows."""
    req = urllib.request.Request(url, headers={"accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def _ext_for(content_type: str | None, encoding: str | None) -> str:
    """Pick a file extension. Text-ish content gets a visible suffix so
    `ls` is readable; base64-wrapped binary falls to .bin."""
    if encoding == "base64":
        return "bin"
    if not content_type:
        return "txt"
    ct = content_type.lower().split(";", 1)[0].strip()
    if ct == "application/json":
        return "json"
    if ct in ("application/xml", "text/xml"):
        return "xml"
    if ct == "application/x-www-form-urlencoded":
        return "form"
    if ct.startswith("text/"):
        return "txt"
    return "bin"


def _sanitize_path(path: str) -> str:
    """Turn a URL path into a filename fragment. Collapse leading slash,
    swap remaining slashes for underscores, strip query-unsafe chars."""
    p = path.lstrip("/")
    out = []
    for ch in p:
        if ch == "/":
            out.append("_")
        elif ch.isalnum() or ch in ("_", "-", "."):
            out.append(ch)
        else:
            out.append("_")
    return "".join(out) or "root"


def _decode(body: str | None, encoding: str | None) -> bytes | None:
    if body is None:
        return None
    if encoding == "base64":
        return base64.b64decode(body)
    return body.encode("utf-8")


def export(base_url: str, out_dir: Path, since_id: int | None, page_size: int) -> int:
    """Drive the pagination loop. Returns the count of entries written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("southbound", "northbound", "carrier_out"):
        (out_dir / sub).mkdir(exist_ok=True)

    index_rows: list[str] = []
    written = 0
    cursor: int | None = since_id

    while True:
        params: dict[str, str | int] = {"limit": page_size}
        if cursor is not None:
            params["sinceId"] = cursor
        url = (
            f"{base_url.rstrip('/')}/v1/debug/capture/entries?"
            + urllib.parse.urlencode(params)
        )
        page = _http_get(url)
        assert isinstance(page, list)
        if not page:
            break

        for meta in page:
            entry_url = (
                f"{base_url.rstrip('/')}/v1/debug/capture/entries/{meta['id']}"
            )
            full = _http_get(entry_url)
            assert isinstance(full, dict)
            _write_entry(full, out_dir)
            index_rows.append(
                "\t".join(
                    [
                        str(full["id"]),
                        full["capturedAt"],
                        full["direction"],
                        full["method"],
                        full["path"] + (("?" + full["query"]) if full.get("query") else ""),
                        str(full["statusCode"]),
                        str(full["reqBytes"]),
                        str(full["respBytes"]),
                    ]
                )
            )
            written += 1
            cursor = full["id"]

        if len(page) < page_size:
            break

    (out_dir / "_index.tsv").write_text(
        "id\tcapturedAt\tdirection\tmethod\tpath\tstatus\treqBytes\trespBytes\n"
        + "\n".join(index_rows)
        + ("\n" if index_rows else ""),
        encoding="utf-8",
    )
    return written


def _write_entry(full: dict, out_dir: Path) -> None:
    direction = full["direction"]
    method = full["method"]
    path = _sanitize_path(full["path"])
    eid = f"{full['id']:06d}"
    base = out_dir / direction / f"{method}_{path}_{eid}"

    req_bytes = _decode(full.get("reqBody"), full.get("reqBodyEncoding"))
    if req_bytes is not None:
        ext = _ext_for(full.get("reqContentType"), full.get("reqBodyEncoding"))
        base.with_suffix(f".request.{ext}").write_bytes(req_bytes)

    resp_bytes = _decode(full.get("respBody"), full.get("respBodyEncoding"))
    if resp_bytes is not None:
        ext = _ext_for(full.get("respContentType"), full.get("respBodyEncoding"))
        base.with_suffix(f".response.{ext}").write_bytes(resp_bytes)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Export captured traffic rows to a fixture-friendly tree. "
            "Assumes capture is already enabled on the target addon."
        ),
    )
    p.add_argument(
        "--base-url",
        default="http://localhost:3001",
        help="Addon base URL (default: http://localhost:3001)",
    )
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path(f"captures/live_{datetime.utcnow():%Y%m%d_%H%M%S}"),
        help="Destination directory (created if missing). "
             "Default: captures/live_{utcnow}/",
    )
    p.add_argument(
        "--since-id",
        type=int,
        default=None,
        help="Only export entries with id > since-id (resume a prior run)",
    )
    p.add_argument(
        "--page-size",
        type=int,
        default=500,
        help="Entries per listing page (max 1000 server-side; default 500)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    try:
        count = export(args.base_url, args.out_dir, args.since_id, args.page_size)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} from {args.base_url}: {e.reason}", file=sys.stderr)
        return 2
    except urllib.error.URLError as e:
        print(f"connection failed: {e.reason}", file=sys.stderr)
        return 2
    print(f"exported {count} entries to {args.out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
