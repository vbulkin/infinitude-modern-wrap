"""Smoke tests — every scaffolded route must return schema-valid JSON."""

from __future__ import annotations

from fastapi.testclient import TestClient

from infinitude_proxy.main import app
from infinitude_proxy.models import Health, RuntimeConfig, Version

client = TestClient(app)


def test_healthz_returns_valid_health():
    r = client.get("/v1/healthz")
    assert r.status_code == 200
    Health.model_validate(r.json())


def test_version_returns_valid_version():
    r = client.get("/v1/version")
    assert r.status_code == 200
    v = Version.model_validate(r.json())
    assert v.api == "v1"


def test_config_returns_valid_runtime_config():
    r = client.get("/v1/config")
    assert r.status_code == 200
    RuntimeConfig.model_validate(r.json())


def test_state_returns_503_when_thermostat_has_not_reported():
    r = client.get("/v1/state")
    assert r.status_code == 503
    body = r.json()
    assert body["error"]["code"] == "upstream_unavailable"
    assert "not reported" in body["error"]["message"].lower()


def test_openapi_includes_v1_paths():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for p in ("/v1/healthz", "/v1/version", "/v1/config", "/v1/state"):
        assert p in paths, f"missing {p}"


def test_swagger_ui_uses_relative_openapi_url():
    """`/docs` must reference `./openapi.json` (relative), not `/openapi.json`
    (absolute). Under HA Supervisor ingress the addon is mounted at
    `/api/hassio_ingress/<token>/`, and an absolute reference 404s
    because the host root doesn't proxy `/openapi.json`. A relative
    URL resolves against the current page so both ingress and direct
    port access work."""
    r = client.get("/docs")
    assert r.status_code == 200
    body = r.text
    assert "./openapi.json" in body
    # Make sure we didn't accidentally also embed the absolute form
    # (the default FastAPI Swagger HTML uses '/openapi.json' verbatim).
    assert "'/openapi.json'" not in body
    assert '"/openapi.json"' not in body
