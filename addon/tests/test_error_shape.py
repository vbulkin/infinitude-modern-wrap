"""Spec-compliant error envelope — `{ error: { code, message, details? } }`.

FastAPI's default is `{ "detail": ... }`; the openapi spec's `Error`
schema is the envelope tested here. These cases check that both
HTTPException paths (404 "not received yet", 404 "zone not found")
and pydantic RequestValidationError paths (422 body failed validation)
produce the spec shape.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import ValidationError

from infinitude_proxy.errors import (
    _code_for,
    _error_body,
    validation_exception_handler,
)
from infinitude_proxy.main import create_app
from infinitude_proxy.models import ErrorResponse
from infinitude_proxy.state_store import StateStore

FIXTURES = Path(__file__).parent / "fixtures" / "thermostat"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _client() -> TestClient:
    return TestClient(create_app(store=StateStore()))


# ── Code mapper ───────────────────────────────────────────────────────

def test_code_for_maps_known_statuses():
    assert _code_for(404) == "not_found"
    assert _code_for(422) == "validation_error"
    assert _code_for(409) == "conflict"
    assert _code_for(502) == "upstream_error"


def test_code_for_falls_through_to_http_prefix():
    # Unmapped status → `http_{status}` so the code is still well-typed.
    assert _code_for(418) == "http_418"


def test_error_body_omits_empty_details():
    assert _error_body("not_found", "x") == {
        "error": {"code": "not_found", "message": "x"}
    }
    assert "details" not in _error_body("not_found", "x")["error"]


# ── HTTPException — 404 paths ─────────────────────────────────────────

def test_404_no_config_uses_spec_envelope():
    client = _client()
    resp = client.get("/v1/system")
    assert resp.status_code == 404
    body = resp.json()
    ErrorResponse.model_validate(body)  # schema compliance
    assert body["error"]["code"] == "not_found"
    assert "no config received yet" in body["error"]["message"]


def test_404_unknown_zone_uses_spec_envelope():
    client = _client()
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.get("/v1/zones/99")
    assert resp.status_code == 404
    body = resp.json()
    ErrorResponse.model_validate(body)
    assert body["error"]["code"] == "not_found"
    assert "99" in body["error"]["message"]


def test_no_default_detail_key():
    """Regression guard: FastAPI's default shape is `{"detail": ...}`.
    After registering our handler, that key must not be in error bodies
    or clients will try to read it and find None."""
    client = _client()
    resp = client.get("/v1/system")
    body = resp.json()
    assert "detail" not in body
    assert "error" in body


# ── Validation — 422 paths ────────────────────────────────────────────

def test_422_invalid_body_uses_spec_envelope_with_details():
    client = _client()
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    # Invalid hold activity — pydantic will 422.
    resp = client.put("/v1/zones/1/hold", json={"activity": "bogus"})
    assert resp.status_code == 422
    body = resp.json()
    ErrorResponse.model_validate(body)
    assert body["error"]["code"] == "validation_error"
    assert isinstance(body["error"]["details"], list)
    assert len(body["error"]["details"]) >= 1
    d = body["error"]["details"][0]
    assert d["path"].startswith("/body")
    assert d["issue"]


def test_422_extra_field_uses_spec_envelope():
    client = _client()
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system", json={"mode": "heat", "bogus": 1})
    assert resp.status_code == 422
    body = resp.json()
    ErrorResponse.model_validate(body)
    assert body["error"]["code"] == "validation_error"


def test_422_empty_patch_body_uses_spec_envelope():
    """Slice 4/5 semantic: empty PATCH body → 422 raised via HTTPException,
    so this goes through the HTTPException handler rather than pydantic."""
    client = _client()
    client.post(
        "/systems/0000TEST0000",
        content=_read("boot_01_system_config.xml"),
        headers={"content-type": "application/xml"},
    )
    resp = client.patch("/v1/system", json={})
    assert resp.status_code == 422
    body = resp.json()
    ErrorResponse.model_validate(body)
    assert body["error"]["code"] == "validation_error"


# ── Handler internals ─────────────────────────────────────────────────

async def test_validation_handler_paths_are_json_pointers():
    """Each detail.path is a slash-joined loc tuple — matches the
    JSON-pointer-ish shape the spec's Error.details describes."""
    from infinitude_proxy.models import ZoneHoldRequest
    try:
        ZoneHoldRequest(activity="bogus")
    except ValidationError as ve:
        # Wrap in a RequestValidationError-shaped object for the handler.
        class _E:
            def errors(self):
                # Pydantic errors have a loc tuple; prepend 'body' to
                # mimic the FastAPI request-body path our endpoint
                # handler sees in production.
                return [
                    {"loc": ("body",) + tuple(e["loc"]), "msg": e["msg"]}
                    for e in ve.errors()
                ]

        resp = await validation_exception_handler(None, _E())  # type: ignore[arg-type]
        import json
        body = json.loads(resp.body.decode())
        for d in body["error"]["details"]:
            assert d["path"].startswith("/body")
