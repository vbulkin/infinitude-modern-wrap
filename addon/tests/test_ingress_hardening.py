"""Southbound ingress hardening — body-size ceiling, hardened XML
parser, and the no-500-to-the-thermostat exception contract.

Beta-readiness cluster: the thermostat is the only legitimate southbound
client, but the port is reachable by anything on the LAN. A malformed,
oversized, or hostile body must never crash the request (a 5xx desyncs
the directive channel and the firmware retry-storms) and must never let
lxml expand an entity bomb or fetch an external resource.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from infinitude_proxy.main import create_app
from infinitude_proxy.parser import (
    SouthboundParseError,
    _fromstring,
    parse_telemetry,
)
from infinitude_proxy.southbound import MAX_SOUTHBOUND_BODY_BYTES
from infinitude_proxy.state_store import StateStore


def _client() -> TestClient:
    return TestClient(create_app(store=StateStore()))


# ── Hardened parser (unit) ────────────────────────────────────────────────


def test_fromstring_normalizes_syntax_error_to_southbound_parse_error():
    with pytest.raises(SouthboundParseError):
        _fromstring(b"<status><not-closed>")


def test_parse_telemetry_raises_typed_error_on_garbage():
    with pytest.raises(SouthboundParseError):
        parse_telemetry(b"this is not xml at all")


def test_hardened_parser_does_not_expand_entity_bomb():
    """billion-laughs: with resolve_entities=False the references are
    never expanded, so the parse stays cheap and the multiplied payload
    never materializes."""
    bomb = (
        b'<?xml version="1.0"?>'
        b'<!DOCTYPE lolz [<!ENTITY lol "lololololol">'
        b'<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
        b'<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">]>'
        b'<status>&lol3;</status>'
    )
    root = _fromstring(bomb)
    # The dangerous expansion never happened.
    assert b"lololol" not in etree.tostring(root)


def test_hardened_parser_blocks_external_entity(tmp_path):
    """XXE: an external entity must not be fetched/inlined (no_network +
    load_dtd off + resolve_entities off)."""
    secret = tmp_path / "secret.txt"
    secret.write_text("TOPSECRET")
    payload = (
        '<?xml version="1.0"?>'
        f'<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file://{secret.as_posix()}">]>'
        "<status>&xxe;</status>"
    ).encode()
    # Either acceptable: the parser rejects the external-entity DTD
    # outright, or it parses but never inlines the file contents. What
    # must NOT happen is the secret leaking into the tree.
    try:
        root = _fromstring(payload)
    except SouthboundParseError:
        return
    assert b"TOPSECRET" not in etree.tostring(root)


# ── No 500 to the thermostat ──────────────────────────────────────────────


def test_malformed_telemetry_returns_clean_directive():
    """The status path must answer a valid CLEAN-cadence directive even
    on a garbage body, never a 5xx."""
    client = _client()
    resp = client.post(
        "/systems/0000TEST0000/status",
        content=b"<<<not telemetry>>>",
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 200
    assert b"<configHasChanges>false</configHasChanges>" in resp.content
    assert b"<pingRate>12</pingRate>" in resp.content


def test_malformed_config_post_discarded_not_500():
    client = _client()
    resp = client.post(
        "/systems/0000TEST0000",
        content=b"<system><config>truncated",
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 200


def test_malformed_idu_status_post_discarded_not_500():
    client = _client()
    resp = client.post(
        "/systems/0000TEST0000/idu_status",
        content=b"not even close to xml",
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 200


# ── Body-size ceiling ─────────────────────────────────────────────────────


def test_oversized_body_rejected_413():
    client = _client()
    big = b"A" * (MAX_SOUTHBOUND_BODY_BYTES + 1)
    resp = client.post(
        "/systems/0000TEST0000/status",
        content=big,
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "payload_too_large"


def test_body_at_cap_not_rejected_for_size():
    """A body exactly at the cap is not rejected *for size* — it parses
    (and, being non-XML filler here, is discarded with a 200, proving the
    size gate let it through to the parser rather than 413-ing it)."""
    client = _client()
    at_cap = b"A" * MAX_SOUTHBOUND_BODY_BYTES
    resp = client.post(
        "/systems/0000TEST0000/idu_status",
        content=at_cap,
        headers={"content-type": "application/xml"},
    )
    assert resp.status_code == 200


# ── Northbound still gets a typed 500 ─────────────────────────────────────


def test_northbound_unexpected_error_returns_typed_500(monkeypatch):
    store = StateStore()
    app = create_app(store=store)
    # raise_server_exceptions=False so the handler's response is returned
    # rather than the original exception being re-raised into the test.
    client = TestClient(app, raise_server_exceptions=False)

    def boom():
        raise RuntimeError("kaboom")

    monkeypatch.setattr(store, "get_config", boom)
    resp = client.get("/v1/state")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "internal_error"
