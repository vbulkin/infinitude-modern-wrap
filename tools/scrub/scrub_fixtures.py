"""Scrub captured Carrier XML fixtures for safe commit to a public repo.

Replacements (structurally preserved):
  * <name> inside <zone id="N">    → "Zone N"
  * <localTime> / <utc> / <timestamp> texts → fixed sentinel UTC
  * <serial> / <SerialNumber>       → "0000TEST0000"

Idempotent: running twice is a no-op. Operates in-place on files passed in,
or on every *.xml under a directory if --dir is given.

Usage
-----
    python tools/scrub/scrub_fixtures.py --dir addon/tests/fixtures/carrier
    python tools/scrub/scrub_fixtures.py file1.xml file2.xml
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lxml import etree

SENTINEL_UTC = "2026-01-01T12:00:00Z"
SENTINEL_SERIAL = "0000TEST0000"

TIMESTAMP_TAGS = {"localTime", "utc", "timestamp"}
SERIAL_TAGS = {"serial", "SerialNumber", "serialNumber"}


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def scrub_tree(root: etree._Element) -> int:
    """Mutate tree in place; return count of replacements."""
    n = 0
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue  # skip comments, processing instructions
        local = _strip_ns(el.tag)
        if local == "zone":
            zid = el.get("id")
            if zid:
                for child in el:
                    if _strip_ns(child.tag) == "name" and child.text:
                        new = f"Zone {zid}"
                        if child.text != new:
                            child.text = new
                            n += 1
        if local in TIMESTAMP_TAGS and el.text and el.text.strip():
            if el.text != SENTINEL_UTC:
                el.text = SENTINEL_UTC
                n += 1
        if local in SERIAL_TAGS and el.text and el.text.strip():
            if el.text != SENTINEL_SERIAL:
                el.text = SENTINEL_SERIAL
                n += 1
    return n


def scrub_file(path: Path) -> int:
    raw = path.read_bytes()
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.fromstring(raw, parser)
    except etree.XMLSyntaxError:
        return 0  # non-XML file (e.g. Alive plain text), leave as-is
    n = scrub_tree(tree)
    if n == 0:
        return 0
    xml_decl = b'<?xml version="1.0" encoding="UTF-8"?>\n' if raw.startswith(b"<?xml") else b""
    out = xml_decl + etree.tostring(tree, encoding="utf-8")
    path.write_bytes(out)
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrub PII from captured fixtures")
    ap.add_argument("--dir", type=Path, help="Scrub every *.xml in this directory")
    ap.add_argument("files", nargs="*", type=Path)
    args = ap.parse_args()

    files: list[Path] = list(args.files)
    if args.dir:
        files.extend(sorted(args.dir.glob("*.xml")))
    if not files:
        ap.error("provide --dir and/or file paths")

    total = 0
    for f in files:
        if not f.is_file():
            print(f"skip: {f} (not a file)", file=sys.stderr)
            continue
        n = scrub_file(f)
        total += n
        print(f"{f}: {n} replacements")
    print(f"total: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
