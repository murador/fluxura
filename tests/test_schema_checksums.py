"""Verifica l'integrità degli XSD con i checksum registrati."""

import hashlib
from pathlib import Path

SCHEMA_DIR = Path(__file__).parents[1] / "src" / "fluxura" / "schemas" / "fatturapa"


def test_xsd_checksums_match():
    lines = (SCHEMA_DIR / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines()
    expected = dict(reversed(line.split("  ", 1)) for line in lines if line.strip())
    assert expected, "CHECKSUMS.sha256 vuoto"
    for name, digest in expected.items():
        actual = hashlib.sha256((SCHEMA_DIR / name).read_bytes()).hexdigest()
        assert actual == digest, f"{name}: checksum diverso da CHECKSUMS.sha256"
    xsd_files = {p.name for p in SCHEMA_DIR.glob("*.xsd")}
    assert xsd_files == set(expected), "XSD non coperti dai checksum"