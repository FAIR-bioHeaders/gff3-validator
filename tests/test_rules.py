"""Each implemented rule fires on its fixture and only where the catalogue says."""

import io
from pathlib import Path

import pytest
import yaml

from gff3_validator import load_catalogue, validate
from gff3_validator.checks.syntax import check_feature

FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED = yaml.safe_load((FIXTURES / "expected.yaml").read_text(encoding="utf-8"))
CATALOGUE = load_catalogue()
IMPLEMENTED = {rule.id for rule in CATALOGUE.implemented()}


def rule_ids(report):
    return {finding.rule for finding in report.findings}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_reports_expected_implemented_rules(name):
    expected = set(EXPECTED[name]) & IMPLEMENTED
    report = validate(FIXTURES / name)
    assert rule_ids(report) == expected
    errors = [rule for rule in expected if CATALOGUE[rule].level == "error"]
    assert report.valid == (not errors)


def test_every_fixture_is_listed():
    files = {
        str(path.relative_to(FIXTURES))
        for path in FIXTURES.rglob("*.gff3")
        if path.is_file()
    }
    assert files == set(EXPECTED)


def test_expected_ids_exist_in_catalogue():
    for ids in EXPECTED.values():
        assert set(ids) <= set(CATALOGUE.rules)


def test_every_implemented_rule_has_a_fixture():
    covered = set().union(*(set(ids) for ids in EXPECTED.values()))
    # HDR-001 and HDR-003 depend on options and are tested in test_cli.py.
    assert IMPLEMENTED - covered == {"HDR-001", "HDR-003"}


def line(*columns):
    return "\t".join(columns)


GOOD = ["ctg1", ".", "CDS", "1", "90", ".", "+", "0", "ID=c1"]


def problems(columns):
    return [problem[0] for problem in check_feature(line(*columns))]


def with_column(number, value):
    columns = list(GOOD)
    columns[number - 1] = value
    return columns


def test_good_line_has_no_problems():
    assert problems(GOOD) == []


@pytest.mark.parametrize("value", ["1", "-1.5", ".5", "5.", "1e-10", "1E+10", "0"])
def test_scores_accepted(value):
    assert problems(with_column(6, value)) == []


@pytest.mark.parametrize("value", ["high", "nan", "inf", "0x1p3", "1,5", "e5"])
def test_scores_rejected(value):
    assert problems(with_column(6, value)) == ["GFF-SYN-016"]


@pytest.mark.parametrize("value", ["+", "-", ".", "?"])
def test_strands_accepted(value):
    assert problems(with_column(7, value)) == []


@pytest.mark.parametrize("value", ["1", "plus", "+-", "*"])
def test_strands_rejected(value):
    assert problems(with_column(7, value)) == ["GFF-SYN-017"]


@pytest.mark.parametrize("value", ["+5", "1.0", "1e3", "-1", "one"])
def test_non_integer_coordinates(value):
    assert problems(with_column(4, value)) == ["GFF-SYN-013"]


def test_start_equal_to_end_is_valid():
    assert problems(with_column(5, "1")) == []


def test_end_zero_is_start_after_end():
    assert problems(with_column(5, "0")) == ["GFF-SYN-015"]


def test_phase_required_for_cds_accession():
    columns = with_column(8, ".")
    columns[2] = "SO:0000316"
    assert problems(columns) == ["GFF-SYN-019"]


def test_phase_dot_allowed_for_other_types():
    columns = with_column(8, ".")
    columns[2] = "exon"
    assert problems(columns) == []


def test_bad_phase_on_cds_is_one_finding():
    assert problems(with_column(8, "3")) == ["GFF-SYN-018"]


def test_ten_columns():
    assert problems(GOOD + [""]) == ["GFF-SYN-003"]


def test_empty_columns_reported_individually():
    columns = with_column(2, "")
    columns[5] = ""
    assert problems(columns) == ["GFF-SYN-004", "GFF-SYN-004"]


def test_findings_carry_line_field_and_fix():
    report = validate(FIXTURES / "invalid" / "syn017_bad_strand.gff3")
    (finding,) = report.findings
    assert (finding.rule, finding.level, finding.line, finding.field) == (
        "GFF-SYN-017",
        "error",
        3,
        7,
    )
    assert finding.fix == CATALOGUE["GFF-SYN-017"].fix


def test_version_variants_and_crlf(tmp_path):
    for first in ("##gff-version 3", "##gff-version 3.1.26", "##gff-version 3\r"):
        path = tmp_path / "x.gff3"
        path.write_bytes(first.encode() + b"\n")
        assert rule_ids(validate(path)) == set(), first
    for first in ("##gff-version 2", "##gff-version 3.1.26.1", "﻿##gff-version 3"):
        path.write_bytes(first.encode() + b"\n")
        assert rule_ids(validate(path)) == {"GFF-SYN-001"}, first


def test_empty_input(tmp_path):
    path = tmp_path / "empty.gff3"
    path.write_bytes(b"")
    report = validate(path)
    assert [(f.rule, f.line) for f in report.findings] == [("GFF-SYN-001", None)]


def test_fasta_section_is_not_read_as_features(tmp_path):
    path = tmp_path / "x.gff3"
    path.write_text("##gff-version 3\n>ctg1\nACGT\n", encoding="utf-8")
    assert rule_ids(validate(path)) == {"GFF-DIR-005"}


def test_max_findings_keeps_counts(tmp_path):
    path = tmp_path / "x.gff3"
    path.write_text("##gff-version 3\n" + "bad line\n" * 5, encoding="utf-8")
    report = validate(path, max_findings=2)
    assert len(report.findings) == 2
    assert report.truncated == 3
    assert report.counts["error"] == 5


@pytest.mark.parametrize(
    "rule", [rule for rule in CATALOGUE.implemented() if rule.layer == "core"]
)
def test_catalogue_example_fires_its_rule(rule):
    text = rule.example
    if rule.id != "GFF-SYN-001":
        text = "##gff-version 3\n" + text
    data = text.encode("utf-8").replace(b"\\xe9", b"\xe9") + b"\n"
    assert rule.id in rule_ids(validate(io.BytesIO(data)))


def test_skipped_layers_are_reported():
    report = validate(FIXTURES / "valid" / "canonical_gene.gff3")
    layers = {item["layer"] for item in report.skipped}
    assert {"core", "so", "biology"} <= layers
