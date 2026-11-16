"""Historical core structure is not optional-header acceptance (#33)."""

import hashlib
from pathlib import Path

import pytest

from gff3_validator import header, validate

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "tests/fixtures/valid/fhgff3_header.gff3"
COMPANION = ROOT / "conformance/valid/fhgff3-header-valid.gff3"
REAL_UNAVAILABLE_REASON = header.unavailable_reason


def hdr_rules(report):
    return {x.rule for x in report.findings if x.rule.startswith("HDR-")}


def test_structural_fixture_preserved_and_disabled_check_visible():
    assert hashlib.sha256(HISTORICAL.read_bytes()).hexdigest() == (
        "28f74236779c3572536cad46f97f14dac64e15a6f70d600b45909785b7a3a1ac"
    )
    report = validate(HISTORICAL)
    assert report.valid  # Core structure only; not a FHGFF3 conformance verdict.
    assert hdr_rules(report) == {"HDR-002"}
    assert any(
        x["layer"] == "fhgff3" and "intentionally disabled" in x["reason"]
        for x in report.skipped
    )


@pytest.mark.headers
def test_historical_fixture_is_not_a_complete_header():
    report = validate(HISTORICAL)
    assert not report.valid
    assert hdr_rules(report) == {"HDR-005", "HDR-007"}


@pytest.mark.headers
def test_supported_release_companion_really_checks_header(monkeypatch):
    calls = []
    real = header.check

    def checked(*args, **kwargs):
        calls.append(args[0])
        return real(*args, **kwargs)

    monkeypatch.setattr(header, "check", checked)
    report = validate(COMPANION)
    assert report.valid
    assert hdr_rules(report) == set()
    assert calls == [str(COMPANION)]
    assert b"https://w3id.org/fair-bioheaders/fhgff3/v0.4.0" in COMPANION.read_bytes()
    assert not any(x["layer"] == "fhgff3" for x in report.skipped)


@pytest.mark.parametrize("version", [None, "0.5.0"])
def test_unavailable_checks_report_reason_instead_of_acceptance(monkeypatch, version):
    monkeypatch.setattr(header, "toolkit_supports_fhgff3", lambda: False)
    monkeypatch.setattr(header, "toolkit_version", lambda: version)
    monkeypatch.setattr(header, "unavailable_reason", REAL_UNAVAILABLE_REASON)
    report = validate(COMPANION)
    assert hdr_rules(report) == {"HDR-002"}
    notes = [x["reason"] for x in report.skipped if x["layer"] == "fhgff3"]
    assert notes and ("not installed" if version is None else version) in notes[0]


def test_installed_probe_refuses_a_silent_unperformed_header_check(monkeypatch):
    import importlib.util
    import json
    import subprocess

    spec = importlib.util.spec_from_file_location(
        "check_header_fixtures", ROOT / "scripts/check_header_fixtures.py"
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)

    def silent(*args, **kwargs):
        report = {"valid": True, "findings": [{"rule": "HDR-002"}], "skipped": []}
        return subprocess.CompletedProcess(args, 0, json.dumps(report), "")

    monkeypatch.setattr(checker.subprocess, "run", silent)
    with pytest.raises(ValueError, match="unperformed header checks have no reason"):
        checker.check(["unused-command"], "unavailable")


def test_installed_probe_refuses_unperformed_companion(monkeypatch):
    import importlib.util
    import json
    import subprocess

    spec = importlib.util.spec_from_file_location(
        "check_header_fixtures", ROOT / "scripts/check_header_fixtures.py"
    )
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)

    def unchecked(args, **kwargs):
        historical = args[-1] == str(HISTORICAL)
        report = {
            "valid": not historical,
            "findings": (
                [{"rule": r} for r in ("HDR-005", "HDR-007")] if historical else []
            ),
            "skipped": (
                [] if historical else [{"layer": "fhgff3", "reason": "disabled"}]
            ),
        }
        return subprocess.CompletedProcess(
            args, int(historical), json.dumps(report), ""
        )

    monkeypatch.setattr(checker.subprocess, "run", unchecked)
    with pytest.raises(ValueError, match="companion header checks were not performed"):
        checker.check(["unused-command"], "checked")
