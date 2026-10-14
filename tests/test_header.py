"""FHGFF3 header rules HDR-004 to HDR-010 with the real FAIR-bioHeaders toolkit.

FAIR-bioHeaders-Specification spec 007 (contracts/validator.md). Every test here is marked
``headers``: it runs only when the toolkit with FHGFF3 support is installed.
"""

import io
import json
from pathlib import Path

import pytest

from gff3_validator import load_catalogue, validate

pytestmark = pytest.mark.headers

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "conformance"
CASES = {
    case["id"]: case
    for case in json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))[
        "cases"
    ]
}
GENOME_FHR = SUITE / "genomes" / "genome.fhr.fa"
PLAIN_GENOME = SUITE / "genomes" / "genome.fa"


def rules(report, layer_rules=None):
    found = [finding.rule for finding in report.findings]
    return found if layer_rules is None else [r for r in found if r in layer_rules]


def case_bytes(name):
    return (SUITE / CASES[name]["file"]).read_bytes()


def write(tmp_path, name, data):
    path = tmp_path / name
    path.write_bytes(data)
    return path


def test_header_rules_are_implemented():
    catalogue = load_catalogue()
    for number in range(4, 11):
        rule = catalogue[f"HDR-{number:03d}"]
        assert rule.status == "implemented"
        assert rule.layer == "fhgff3"
    assert catalogue["HDR-010"].level == "warning"


def test_valid_header_with_matching_genome():
    report = validate(
        SUITE / CASES["fhgff3-header-valid"]["file"], genome=str(GENOME_FHR)
    )
    assert rules(report) == []
    assert report.valid
    assert not any(item["layer"] == "fhgff3" for item in report.skipped)


def test_genome_without_an_fhr_header_is_not_checked(tmp_path):
    path = write(tmp_path, "a.gff3", case_bytes("fhgff3-header-valid"))
    report = validate(path, genome=str(PLAIN_GENOME))
    assert "HDR-009" not in rules(report)
    notes = [item["reason"] for item in report.skipped if item["layer"] == "fhgff3"]
    assert any(note.startswith("HDR-009 not checked") for note in notes)


def test_stale_genome_is_an_error_but_the_file_itself_is_consistent():
    report = validate(
        SUITE / CASES["hdr-009-stale-genome"]["file"], genome=str(GENOME_FHR)
    )
    assert rules(report) == ["HDR-009"]
    assert "HDR-005" not in rules(report)


def test_header_results_and_feature_results_are_separate(tmp_path):
    # A valid header does not make a broken feature valid ...
    data = case_bytes("fhgff3-header-valid").replace(b"\t+\t", b"\t*\t")
    report = validate(write(tmp_path, "bad-feature.gff3", data))
    found = rules(report)
    assert "HDR-005" in found  # the feature bytes changed after the checksum
    assert any(rule.startswith("GFF-") for rule in found)
    # ... and a broken header adds no feature finding.
    report = validate(SUITE / CASES["hdr-008-no-genome-link"]["file"])
    assert rules(report) == ["HDR-008"]


def test_plain_gff3_has_no_header_findings():
    report = validate(SUITE / CASES["canonical-gene"]["file"])
    assert [r for r in rules(report) if r.startswith("HDR-")] == []


def test_require_header_passes_with_a_valid_header():
    report = validate(
        SUITE / CASES["fhgff3-header-valid"]["file"], header_mode="require"
    )
    assert rules(report) == []


def test_no_header_mode_skips_the_checks():
    report = validate(
        SUITE / CASES["hdr-008-no-genome-link"]["file"], header_mode="skip"
    )
    assert rules(report) == ["HDR-003"]


def test_streams_cannot_be_checked():
    data = case_bytes("hdr-008-no-genome-link")
    report = validate(io.BytesIO(data))
    assert rules(report) == ["HDR-002"]
    assert "file on disk" in report.findings[0].message


def test_directive_warning_is_not_an_error():
    report = validate(SUITE / CASES["hdr-010-species-disagrees"]["file"])
    assert rules(report) == ["HDR-010"]
    assert report.valid
    assert "taxonomy ID 10090" in report.findings[0].message


@pytest.mark.parametrize(
    "name, rule",
    [
        ("hdr-004-header-after-feature", "HDR-004"),
        ("hdr-005-checksum-mismatch", "HDR-005"),
        ("hdr-006-duplicate-key", "HDR-006"),
        ("hdr-007-schema-error", "HDR-007"),
        ("hdr-008-no-genome-link", "HDR-008"),
    ],
)
def test_each_header_rule(name, rule):
    report = validate(SUITE / CASES[name]["file"])
    assert rules(report) == [rule]
    assert not report.valid


def test_unsupported_schema_version_is_reported_not_substituted():
    """FAIR-bioHeaders-Specification rule V4 (docs/SCHEMA-VERSIONS.md): no other schema is used."""
    report = validate(SUITE / CASES["hdr-007-unsupported-schema-version"]["file"])
    assert rules(report) == ["HDR-007"]
    message = next(f.message for f in report.findings if f.rule == "HDR-007")
    assert "unsupported schema version" in message
    assert "https://w3id.org/fair-bioheaders/fhgff3/v0.0.0" in message
    notes = [item["reason"] for item in report.skipped if item["layer"] == "fhgff3"]
    assert any(note.startswith("HDR-008 not checked") for note in notes)


def test_release_urls_select_the_same_schema(tmp_path):
    """V1-V3: the raw-main, raw tag and w3id forms of FHGFF3 are all FHGFF3."""
    from bioheaders.gff3 import header_report

    data = case_bytes("fhgff3-header-valid")
    w3id = b"https://w3id.org/fair-bioheaders/fhgff3/v0.4.0"
    assert w3id in data
    # Raw URLs under either name of the specification repository
    # (FAIR-bioHeaders-Specification#108).
    values = [w3id + b"/"]
    for repository in (b"FHR-Specification", b"FAIR-bioHeaders-Specification"):
        raw = b"https://raw.githubusercontent.com/FAIR-bioHeaders/" + repository + b"/"
        values += [raw + b"v0.4.0/fhgff3.json", raw + b"main/fhgff3.json"]
    for value in values:
        path = write(tmp_path, "a.gff3", data.replace(w3id, value))
        report = header_report(str(path))
        assert report["header_type"] == "FHGFF3"
        assert report["schema"]["ok"] is True, report["schema"]
