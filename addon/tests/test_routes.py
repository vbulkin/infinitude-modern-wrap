"""Smoke tests — every scaffolded route must return schema-valid JSON.

Phase 2 coverage. When Phase 3 replaces canned_state with real telemetry,
these tests become contract tests instead.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from infinitude_proxy.main import app
from infinitude_proxy.models import Health, RuntimeConfig, State, Version

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


def test_state_returns_valid_state_with_zones():
    r = client.get("/v1/state")
    assert r.status_code == 200
    s = State.model_validate(r.json())
    assert len(s.zones) >= 1
    assert all(z.id.isdigit() for z in s.zones)


def test_openapi_includes_v1_paths():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for p in ("/v1/healthz", "/v1/version", "/v1/config", "/v1/state"):
        assert p in paths, f"missing {p}"
