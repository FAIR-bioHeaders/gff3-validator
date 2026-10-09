"""The installed gff3-validate command: input forms, formats, options, exit codes."""

import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "valid" / "canonical_gene.gff3"
INVALID = FIXTURES / "invalid" / "syn019_cds_no_phase.gff3"
HEADER = FIXTURES / "valid" / "fhgff3_header.gff3"


def command():
    found = shutil.which("gff3-validate")
    return [found] if found else [sys.executable, "-m", "gff3_validator"]


def run(*args, stdin=None, cwd=None):
    return subprocess.run(
        command() + [str(arg) for arg in args],
        input=stdin,
        capture_output=True,
        cwd=cwd,
    )


def findings(result):
    return [item["rule"] for item in json.loads(result.stdout)["findings"]]


def test_valid_file_exits_0(tmp_path):
    result = run(VALID, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert b"no errors" in result.stdout
    assert b"not checked: so" in result.stdout


def test_invalid_file_exits_1_with_rule_line_and_fix():
    result = run(INVALID)
    assert result.returncode == 1
    text = result.stdout.decode()
    assert f"{INVALID}:6 (column 8): error GFF-SYN-019:" in text
    assert "fix: Give the phase" in text


def test_json_report():
    result = run("--format", "json", INVALID)
    report = json.loads(result.stdout)
    assert report["valid"] is False
    assert report["counts"]["error"] == 1
    (finding,) = report["findings"]
    assert finding == {
        "rule": "GFF-SYN-019",
        "level": "error",
        "line": 6,
        "field": 8,
        "message": "CDS feature has no phase ('.')",
        "fix": finding["fix"],
    }
    assert report["catalogue_version"].endswith("-draft")


def test_gzip_and_bgzf_style_input(tmp_path):
    data = INVALID.read_bytes()
    plain = tmp_path / "x.gff3.gz"
    plain.write_bytes(gzip.compress(data))
    # Multi-member gzip, as BGZF writes, and no .gz suffix.
    members = tmp_path / "members.gff3"
    middle = data.index(b"ctg1\t.\tCDS")
    members.write_bytes(gzip.compress(data[:middle]) + gzip.compress(data[middle:]))
    for path in (plain, members):
        result = run("--format", "json", path)
        assert result.returncode == 1
        assert findings(result) == ["GFF-SYN-019"]


def test_stdin():
    result = run("--format", "json", "-", stdin=INVALID.read_bytes())
    assert result.returncode == 1
    assert findings(result) == ["GFF-SYN-019"]


def test_truncated_gzip_exits_2(tmp_path):
    path = tmp_path / "x.gff3.gz"
    path.write_bytes(gzip.compress(VALID.read_bytes() * 50)[:-40])
    result = run(path)
    assert result.returncode == 2
    assert b"validation incomplete" in result.stderr
    assert result.stdout == b""


def test_missing_file_exits_2(tmp_path):
    result = run(tmp_path / "absent.gff3")
    assert result.returncode == 2
    assert b"cannot open" in result.stderr


@pytest.mark.parametrize("args", [[], ["--format", "xml", VALID]])
def test_usage_errors_exit_2(args):
    assert run(*args).returncode == 2


def test_header_flags_are_exclusive():
    assert run("--require-header", "--no-header", VALID).returncode == 2


def test_require_header_on_plain_file():
    result = run("--format", "json", "--require-header", VALID)
    assert result.returncode == 1
    assert findings(result) == ["HDR-001"]


def test_header_present_is_reported_not_validated():
    result = run("--format", "json", HEADER)
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert findings(result) == ["HDR-002"]
    assert report["header_lines"] == 3
    assert any(item["layer"] == "fhgff3" for item in report["skipped"])
    assert run("--require-header", HEADER).returncode == 0


def test_no_header_skips_header_checks():
    result = run("--format", "json", "--no-header", HEADER)
    assert result.returncode == 0
    assert findings(result) == ["HDR-003"]


def test_genome_option_runs_biology_checks():
    genome = FIXTURES / "biology" / "genome.fa"
    result = run("--format", "json", "--genome", genome, VALID)
    assert result.returncode == 1
    report = json.loads(result.stdout)
    # canonical_gene.gff3 is on ctg123, which the test genome does not have:
    # its codons are not checked, but coding lengths still are (BIO-009).
    assert sorted(item["rule"] for item in report["findings"]) == [
        "BIO-001",
        "BIO-009",
        "BIO-009",
        "BIO-011",
    ]
    (biology,) = [item for item in report["skipped"] if item["layer"] == "biology"]
    assert biology["reason"] == "partial: 4 CDS on seqids not in the genome"
    result = run("--format", "json", "--genome", "missing.fa", VALID)
    assert result.returncode == 2
    assert b"cannot open genome missing.fa" in result.stderr


def test_version():
    result = run("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == b"0.0.1.dev0"
