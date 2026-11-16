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


def test_header_on_stdin_is_reported_not_validated():
    # Header checks re-read the file, so they need a path: on standard input a
    # header is noted (HDR-002) whether or not the toolkit is installed.
    result = run("--format", "json", "-", stdin=HEADER.read_bytes())
    assert result.returncode == 0
    report = json.loads(result.stdout)
    assert findings(result) == ["HDR-002"]
    assert report["header_lines"] == 3
    assert any(item["layer"] == "fhgff3" for item in report["skipped"])
    assert run("--require-header", "-", stdin=HEADER.read_bytes()).returncode == 0


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
    assert result.stdout.strip() == b"0.1.0"


# -- the feature-index modes (issue #31, docs/feature-index.md) ------------

FEATURES = FIXTURES / "features"


def test_list_features_enumerates_the_layer():
    result = run("--list-features", FEATURES / "positive.gff3")
    assert result.returncode == 0, result.stderr
    text = result.stdout.decode()
    assert "feature layer indexed" in text
    assert "feature rows: 2 (with ID: 2, without ID: 0, gene rows: 1)" in text
    assert "ID=gene:G1" in text and "ID=rna:R1" in text


def test_list_features_json_lists_rows_and_problems():
    result = run(
        "--format", "json", "--list-features", FEATURES / "malformed_layer.gff3"
    )
    assert result.returncode == 2, "a layer that cannot answer has no verdict"
    data = json.loads(result.stdout)
    assert data["layer"] == "malformed" and data["usable"] is False
    assert data["problems"][0].startswith("line 4: a feature row holds nine")
    assert [row["id"] for row in data["rows"]] == ["gene:G1"]


def test_feature_id_found_exits_0():
    result = run("--feature-id", "gene:G1", FEATURES / "positive.gff3")
    assert result.returncode == 0, result.stdout
    assert "-> found" in result.stdout.decode()


def test_feature_id_decodes_both_sides():
    # The row writes ID=gene:A%2CB; the decoded pointer is the same identifier.
    assert (
        run(
            "--feature-id", "gene:A,B", FEATURES / "percent_encoded_target.gff3"
        ).returncode
        == 0
    )


@pytest.mark.parametrize(
    "identifier,fixture",
    [
        ("gene:NOPE", "not_found.gff3"),
        ("gene:G1", "duplicate_row.gff3"),
        ("rna:R1", "non_gene_target.gff3"),
    ],
)
def test_scored_non_pass_exits_1(identifier, fixture):
    result = run("--format", "json", "--feature-id", identifier, FEATURES / fixture)
    assert result.returncode == 1
    data = json.loads(result.stdout)
    assert data["scored"] is True and data["passes"] is False
    assert data["outcome"] in ("not-found", "duplicate-row", "non-gene-target")


@pytest.mark.parametrize(
    "identifier,fixture,outcome",
    [
        ("gene:G1", "malformed_layer.gff3", "malformed-layer"),
        ("gene:G1", "implied_fasta.gff3", "malformed-layer"),
        ("gene:G1", "absent_layer.gff3", "absent-layer"),
    ],
)
def test_not_scored_outcomes_exit_2_never_0_never_1(identifier, fixture, outcome):
    result = run("--format", "json", "--feature-id", identifier, FEATURES / fixture)
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["outcome"] == outcome
    assert data["scored"] is False and data["passes"] is False
    assert data["rows"] == []


def test_feature_id_on_a_missing_file_exits_2_as_absent_layer(tmp_path):
    result = run("--format", "json", "--feature-id", "gene:G1", tmp_path / "nope.gff3")
    assert result.returncode == 2, "no layer is neither a pass nor a rejection"
    data = json.loads(result.stdout)
    assert data["outcome"] == "absent-layer" and data["scored"] is False
    assert "cannot open" in data["message"]


def test_feature_id_reads_standard_input():
    result = run(
        "--format",
        "json",
        "--feature-id",
        "gene:G1",
        "-",
        stdin=(FEATURES / "positive.gff3").read_bytes(),
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["outcome"] == "found"


def test_inspection_modes_do_not_validate():
    # str001_duplicate_id.gff3 is invalid GFF3 (GFF-STR-001); the index answers
    # about its rows and reports nothing about its validity.
    invalid = FIXTURES / "invalid" / "str001_duplicate_id.gff3"
    result = run("--format", "json", "--list-features", invalid)
    assert result.returncode == 0
    assert "findings" not in json.loads(result.stdout)
    assert run(invalid).returncode == 1


@pytest.mark.parametrize(
    "args",
    [
        ["--list-features", "--feature-id", "x", VALID],
        ["--list-features", "--genome", "genome.fa", VALID],
        ["--feature-id", "x", "--profile", "agbiodata", VALID],
        ["--feature-id", "x", "--require-header", VALID],
        ["--feature-id", "x", "--no-header", VALID],
        ["--feature-id", "x", "--so", "so.obo", VALID],
        ["--format", "sarif", "--feature-id", "x", VALID],
        ["--format", "html", "--list-features", VALID],
    ],
)
def test_inspection_modes_reject_options_they_do_not_use(args):
    assert run(*args).returncode == 2


def test_feature_id_needs_the_input():
    assert run("--feature-id", "gene:G1").returncode == 2
