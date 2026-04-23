"""Smoke test for the capture proxy."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from tools.capture import proxy as proxy_mod


def test_capture_writes_request_response_and_meta(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/xml"},
            content=b"<status><pingRate>12</pingRate></status>",
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    app = proxy_mod.create_app(
        upstream="http://upstream.test",
        capture_dir=tmp_path,
        client=mock_client,
    )

    with TestClient(app) as tc:
        r = tc.post(
            "/systems/1234A56789/status",
            content=b"<status><version>1.37</version></status>",
            headers={"content-type": "application/xml"},
        )

    assert r.status_code == 200
    assert r.content == b"<status><pingRate>12</pingRate></status>"

    metas = sorted(Path(tmp_path).glob("*.meta.json"))
    assert len(metas) == 1, f"expected 1 meta, got {list(tmp_path.iterdir())}"
    meta = json.loads(metas[0].read_text())
    assert meta["request"]["method"] == "POST"
    assert meta["request"]["path"] == "/systems/1234A56789/status"
    assert meta["response"]["status"] == 200

    req_xml = (tmp_path / meta["request"]["body_file"]).read_bytes()
    resp_xml = (tmp_path / meta["response"]["body_file"]).read_bytes()
    assert b"<version>1.37</version>" in req_xml
    assert b"<pingRate>12</pingRate>" in resp_xml
