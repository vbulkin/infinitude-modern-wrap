"""Tests for the export_capture.py curation script.

Focus: the pure-function logic (extension picking, path sanitization,
body decode, entry-to-file layout). HTTP pagination is urllib doing
the obvious thing and isn't worth a live-server fixture.
"""

from __future__ import annotations

import base64
import sys
from pathlib import Path

import pytest

# The script lives in addon/scripts/ which isn't on sys.path by default.
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import export_capture as ec  # noqa: E402


def test_sanitize_path_strips_leading_slash_and_swaps_separators():
    assert ec._sanitize_path("/systems/2013W000855/status") == "systems_2013W000855_status"
    assert ec._sanitize_path("/v1/zones/1/hold") == "v1_zones_1_hold"


def test_sanitize_path_replaces_unsafe_characters():
    assert ec._sanitize_path("/weird path with spaces!") == "weird_path_with_spaces_"
    assert ec._sanitize_path("") == "root"
    assert ec._sanitize_path("/") == "root"


def test_ext_for_textual_content_types():
    assert ec._ext_for("application/json", "utf-8") == "json"
    assert ec._ext_for("application/xml", "utf-8") == "xml"
    assert ec._ext_for("text/xml; charset=utf-8", "utf-8") == "xml"
    assert ec._ext_for("text/plain", "utf-8") == "txt"
    assert ec._ext_for("application/x-www-form-urlencoded", "utf-8") == "form"


def test_ext_for_base64_falls_to_bin():
    """Once the body is base64-wrapped, the extension signals "raw bytes"
    regardless of content-type — keeps `ls` honest about what's inside."""
    assert ec._ext_for("image/png", "base64") == "bin"
    assert ec._ext_for(None, "base64") == "bin"


def test_decode_handles_utf8_and_base64():
    assert ec._decode("hello", "utf-8") == b"hello"
    assert ec._decode(base64.b64encode(b"\x00\x01\x02").decode(), "base64") == b"\x00\x01\x02"
    assert ec._decode(None, None) is None


def test_write_entry_places_request_and_response_under_direction(tmp_path: Path):
    """The on-disk layout is the contract humans will curate against —
    this is the test that pins it."""
    full = {
        "id": 42,
        "capturedAt": "2026-04-24T12:00:00Z",
        "direction": "southbound",
        "method": "POST",
        "path": "/systems/2013W000855/status",
        "query": None,
        "statusCode": 200,
        "reqContentType": "application/x-www-form-urlencoded",
        "reqBytes": 14,
        "reqBody": "data=<status/>",
        "reqBodyEncoding": "utf-8",
        "respContentType": "application/xml",
        "respBytes": 42,
        "respBody": "<?xml version='1.0'?><status/>",
        "respBodyEncoding": "utf-8",
        "durationMs": 3,
    }
    (tmp_path / "southbound").mkdir()

    ec._write_entry(full, tmp_path)

    req = tmp_path / "southbound" / "POST_systems_2013W000855_status_000042.request.form"
    resp = tmp_path / "southbound" / "POST_systems_2013W000855_status_000042.response.xml"
    assert req.exists()
    assert req.read_bytes() == b"data=<status/>"
    assert resp.exists()
    assert resp.read_text().startswith("<?xml")


def test_write_entry_zero_padded_id_for_lexical_sort(tmp_path: Path):
    """Ids zero-pad to 6 digits so `ls` orders captures by arrival even
    though filenames also carry method/path prefixes."""
    (tmp_path / "northbound").mkdir()
    full = {
        "id": 3,
        "direction": "northbound",
        "method": "GET",
        "path": "/v1/state",
        "query": None,
        "reqContentType": None,
        "reqBody": None,
        "reqBodyEncoding": None,
        "respContentType": "application/json",
        "respBody": "{}",
        "respBodyEncoding": "utf-8",
    }
    ec._write_entry(full, tmp_path)
    assert (tmp_path / "northbound" / "GET_v1_state_000003.response.json").exists()


def test_write_entry_skips_missing_bodies(tmp_path: Path):
    """An entry with no request body (a GET) shouldn't create an empty
    .request file — it should just emit the response."""
    (tmp_path / "northbound").mkdir()
    full = {
        "id": 1,
        "direction": "northbound",
        "method": "GET",
        "path": "/v1/healthz",
        "query": None,
        "reqContentType": None,
        "reqBody": None,
        "reqBodyEncoding": None,
        "respContentType": "application/json",
        "respBody": '{"status":"healthy"}',
        "respBodyEncoding": "utf-8",
    }
    ec._write_entry(full, tmp_path)
    nb = tmp_path / "northbound"
    assert not any(p.name.endswith(".request.json") for p in nb.iterdir())
    assert (nb / "GET_v1_healthz_000001.response.json").exists()
