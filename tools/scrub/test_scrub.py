"""Tests for the fixture scrubber."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from tools.scrub.scrub_fixtures import (
    SENTINEL_MAC,
    SENTINEL_PIN,
    SENTINEL_SERIAL,
    SENTINEL_UTC,
    scrub_file,
    scrub_tree,
)


def test_zone_names_replaced_by_id(tmp_path: Path):
    xml = b'<status><zones><zone id="1"><name>tv room</name></zone>' \
          b'<zone id="2"><name>master bedroom</name></zone></zones></status>'
    f = tmp_path / "t.xml"
    f.write_bytes(xml)
    n = scrub_file(f)
    assert n == 2
    tree = etree.fromstring(f.read_bytes())
    names = [e.text for e in tree.iter("name")]
    assert names == ["Zone 1", "Zone 2"]


def test_timestamps_normalized(tmp_path: Path):
    xml = b'<root><localTime>2026-04-18T00:34:38-05:01</localTime>' \
          b'<utc>2026-04-18T04:35:30Z</utc>' \
          b'<timestamp>2026-04-17T13:29:00Z</timestamp></root>'
    f = tmp_path / "t.xml"
    f.write_bytes(xml)
    scrub_file(f)
    tree = etree.fromstring(f.read_bytes())
    for tag in ("localTime", "utc", "timestamp"):
        assert tree.findtext(tag) == SENTINEL_UTC


def test_serial_replaced(tmp_path: Path):
    xml = b'<system><serial>1234A56789</serial></system>'
    f = tmp_path / "t.xml"
    f.write_bytes(xml)
    scrub_file(f)
    assert etree.fromstring(f.read_bytes()).findtext("serial") == SENTINEL_SERIAL


def test_pin_and_mac_replaced(tmp_path: Path):
    xml = b'<profile><pin>C00D8F96</pin><routerMac>F23883459DB2</routerMac></profile>'
    f = tmp_path / "t.xml"
    f.write_bytes(xml)
    n = scrub_file(f)
    assert n == 2
    tree = etree.fromstring(f.read_bytes())
    assert tree.findtext("pin") == SENTINEL_PIN
    assert tree.findtext("routerMac") == SENTINEL_MAC


def test_idempotent(tmp_path: Path):
    xml = b'<root><localTime>2026-04-18T00:34:38-05:01</localTime></root>'
    f = tmp_path / "t.xml"
    f.write_bytes(xml)
    assert scrub_file(f) == 1
    assert scrub_file(f) == 0  # second run finds nothing to change


def test_preserves_structure_and_non_targeted_text(tmp_path: Path):
    xml = (
        b'<status><mode>cool</mode><oat>72</oat>'
        b'<zones><zone id="1"><name>tv room</name><rt>74.5</rt></zone></zones>'
        b'</status>'
    )
    f = tmp_path / "t.xml"
    f.write_bytes(xml)
    scrub_file(f)
    tree = etree.fromstring(f.read_bytes())
    assert tree.findtext("mode") == "cool"
    assert tree.findtext("oat") == "72"
    assert tree.find(".//zone/rt").text == "74.5"
    assert tree.find(".//zone/name").text == "Zone 1"


def test_non_xml_file_untouched(tmp_path: Path):
    f = tmp_path / "Alive.xml"
    f.write_bytes(b"alive")
    assert scrub_file(f) == 0
    assert f.read_bytes() == b"alive"


def test_tree_function_counts_replacements():
    xml = b'<s><zone id="1"><name>kitchen</name></zone><utc>2026-01-01</utc></s>'
    tree = etree.fromstring(xml)
    assert scrub_tree(tree) == 2
