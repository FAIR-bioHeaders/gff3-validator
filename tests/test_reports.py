"""HTML and SARIF reports: self-contained, escaped, and SARIF 2.1.0 schema-valid."""

import base64
import gzip
import hashlib
import io
import json
from html.parser import HTMLParser
from pathlib import Path

import jsonschema
import pytest
import yaml

from gff3_validator import Validator, load_catalogue, validate, web
from gff3_validator.cli import main
from gff3_validator.report import (
    HTML_SCRIPT,
    HTML_STYLE,
    rule_url,
    to_html,
    to_json,
    to_sarif_dict,
)

FIXTURES = Path(__file__).parent / "fixtures"
GENOME = FIXTURES / "biology" / "genome.fa"
EXPECTED = yaml.safe_load((FIXTURES / "expected.yaml").read_text(encoding="utf-8"))
# Vendored from OASIS (see tests/schemas/NOTICE); never fetched at test time.
SARIF_SCHEMA = json.loads(
    (Path(__file__).parent / "schemas" / "sarif-schema-2.1.0.json").read_text(
        encoding="utf-8"
    )
)
CATALOGUE = load_catalogue()
HOSTILE = (
    "##gff-version 3\n"
    "##<script>alert(1)</script> x\n"
    'ctg1\t.\tgene\t1\t10\t.\t+\t.\tID=<b>&amp;"x\n'
)


def named(data, name):
    return Validator().validate(io.BytesIO(data), name=name)


def fixture_report(name):
    if name.startswith("biology/"):
        return validate(FIXTURES / name, genome=GENOME)
    return validate(FIXTURES / name)


def check_sarif(log):
    validator = jsonschema.Draft4Validator(
        SARIF_SCHEMA, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(log), key=str)
    assert not errors, "\n".join(error.message for error in errors[:5])


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.data = {}
        self._current = None

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self._current = tag

    def handle_data(self, data):
        if self._current in ("style", "script"):
            self.data[self._current] = data

    def handle_endtag(self, tag):
        self._current = None


def parse(text):
    parser = Elements()
    parser.feed(text)
    return parser


# --------------------------------------------------------------------------
# SARIF
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sarif_is_schema_valid_and_matches_findings(name):
    report = fixture_report(name)
    log = to_sarif_dict(report)
    check_sarif(log)
    (run,) = log["runs"]
    rules = run["tool"]["driver"]["rules"]
    assert [rule["id"] for rule in rules] == list(CATALOGUE.rules)
    assert len(run["results"]) == len(report.findings)
    for result, finding in zip(run["results"], report.findings):
        assert result["ruleId"] == finding.rule
        assert rules[result["ruleIndex"]]["id"] == finding.rule
        assert result["level"] == {"error": "error", "warning": "warning"}.get(
            finding.level, "note"
        )
        (location,) = result["locations"]
        physical = location["physicalLocation"]
        assert physical["artifactLocation"]["uri"].endswith(Path(name).name)
        if finding.line is None:
            assert "region" not in physical
        else:
            assert physical["region"] == {"startLine": finding.line}
        assert result.get("properties", {}).get("gff3Column") == finding.field


def test_sarif_rules_carry_catalogue_metadata():
    log = to_sarif_dict(validate(FIXTURES / "valid" / "canonical_gene.gff3"))
    rules = {rule["id"]: rule for rule in log["runs"][0]["tool"]["driver"]["rules"]}
    rule = rules["GFF-SYN-019"]
    assert rule["helpUri"] == rule_url("GFF-SYN-019")
    assert rule["helpUri"].endswith("/docs/rules.md#gff-syn-019")
    assert rule["defaultConfiguration"] == {"level": "error"}
    assert rule["shortDescription"]["text"] == CATALOGUE["GFF-SYN-019"].title
    assert rules["GFF-SYN-007"]["defaultConfiguration"] == {"level": "note"}
    assert log["version"] == "2.1.0"
    notes = log["runs"][0]["invocations"][0]["toolExecutionNotifications"]
    assert any("not checked: so" in note["message"]["text"] for note in notes)


@pytest.mark.parametrize(
    "source, location",
    [
        ("dir/my file.gff3", {"uri": "dir/my%20file.gff3", "uriBaseId": "%SRCROOT%"}),
        ("/data/a.gff3", {"uri": "file:///data/a.gff3"}),
        ("C:\\data\\a.gff3", {"uri": "file:///C:/data/a.gff3"}),
    ],
)
def test_sarif_artifact_uris(source, location):
    report = named(HOSTILE.encode(), source)
    log = to_sarif_dict(report)
    check_sarif(log)
    physical = log["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
    assert physical["artifactLocation"] == location


def test_sarif_for_stdin_and_whole_file_findings():
    report = named(b"", "-")
    log = to_sarif_dict(report)
    check_sarif(log)
    (result,) = log["runs"][0]["results"]
    assert result["ruleId"] == "GFF-SYN-001"
    assert "locations" not in result


def test_sarif_reports_truncation():
    report = validate(
        FIXTURES / "invalid" / "att001_gtf_attributes.gff3", max_findings=0
    )
    log = to_sarif_dict(report)
    check_sarif(log)
    assert log["runs"][0]["results"] == []
    assert log["runs"][0]["properties"]["truncatedFindings"] == report.truncated > 0


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------


def test_html_is_self_contained_and_escaped():
    report = named(HOSTILE.encode(), '<img src=x onerror="1">.gff3')
    text = to_html(report)
    parsed = parse(text)
    tags = [tag for tag, _ in parsed.tags]
    # Only the report's own inline style and script; nothing that loads.
    assert tags.count("script") == 1 and tags.count("style") == 1
    for tag, attrs in parsed.tags:
        assert tag not in ("img", "link", "iframe", "object", "embed")
        assert "src" not in attrs and "srcset" not in attrs
        if "href" in attrs:
            assert tag == "a" and attrs["href"].startswith("https://")
        assert not any(name.startswith("on") for name in attrs)
    assert "<script>alert" not in text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in text
    assert "&lt;img src=x onerror=&quot;1&quot;&gt;.gff3" in text


def test_html_csp_allows_exactly_the_inline_style_and_script():
    text = to_html(validate(FIXTURES / "invalid" / "syn019_cds_no_phase.gff3"))
    parsed = parse(text)
    (csp,) = [
        attrs["content"]
        for tag, attrs in parsed.tags
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"
    ]
    assert parsed.data["style"] == HTML_STYLE
    assert parsed.data["script"] == HTML_SCRIPT
    for directive, body in (("style-src", HTML_STYLE), ("script-src", HTML_SCRIPT)):
        digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
        assert f"{directive} 'sha256-{digest}'" in csp
    assert "default-src 'none'" in csp


def test_html_lists_findings_not_checked_layers_and_sources():
    report = validate(FIXTURES / "valid" / "directives.gff3")
    text = to_html(report)
    parsed = parse(text)
    headers = [attrs for tag, attrs in parsed.tags if tag == "th"]
    assert headers and all(attrs.get("scope") == "col" for attrs in headers)
    keys = {attrs["data-key"] for tag, attrs in parsed.tags if "data-key" in attrs}
    assert keys == {"line", "rule", "level"}
    rows = [attrs for tag, attrs in parsed.tags if tag == "tr" and "data-rule" in attrs]
    assert [row["data-rule"] for row in rows] == [f.rule for f in report.findings]
    links = {attrs["href"] for tag, attrs in parsed.tags if tag == "a"}
    for finding in report.findings:
        assert rule_url(finding.rule) in links
    assert "Not checked" in text
    assert "<strong>so</strong>: partial: these SO rules are planned" in text
    assert "<strong>biology</strong>: not run; needs --genome" in text
    assert report.ontology["source"] in links
    assert "so.obo data-version " in text and report.ontology["sha256"] in text
    assert "Limitations" in text
    assert "no errors" in text


def test_html_without_findings():
    text = to_html(validate(FIXTURES / "valid" / "canonical_gene.gff3"))
    assert "<p>No findings.</p>" in text and 'id="findings"' not in text


# --------------------------------------------------------------------------
# The browser glue (gff3_validator.web), here under CPython
# --------------------------------------------------------------------------


def callback(data, calls=None):
    def read_at(offset, length):
        if calls is not None:
            calls.append((offset, length))
        return data[offset : offset + length]

    return web.open_callback(len(data), read_at)


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_web_glue_matches_the_library(name):
    path = FIXTURES / name
    genome = str(GENOME) if name.startswith("biology/") else None
    result = web.run(callback(path.read_bytes()), path.name, genome=genome)
    expected = json.loads(to_json(fixture_report(name)))
    got = json.loads(result["json"])
    expected.pop("source")
    assert got.pop("source") == path.name
    assert got == expected
    assert result["valid"] == expected["valid"]
    check_sarif(json.loads(result["sarif"]))
    assert result["html"].startswith("<!DOCTYPE html>")


def test_web_glue_reads_gzip_in_slices_and_reports_progress():
    data = (FIXTURES / "valid" / "canonical_gene.gff3").read_bytes() * 2000
    packed = gzip.compress(data)
    calls, progress = [], []
    raw = web.CallbackReader(
        len(packed),
        lambda offset, length: (calls.append(length), packed[offset : offset + length])[
            1
        ],
        lambda done, size: progress.append((done, size)),
    )
    stream = io.BufferedReader(raw, buffer_size=web.READ_BLOCK)
    result = web.run(stream, "big.gff3.gz")
    assert result["ok"]
    assert max(calls) <= web.READ_BLOCK
    assert progress[-1] == (len(packed), len(packed))
    assert json.loads(result["json"])["lines"] == data.count(b"\n")


def test_web_glue_reports_unreadable_input_like_exit_2():
    packed = gzip.compress(
        (FIXTURES / "valid" / "canonical_gene.gff3").read_bytes() * 50
    )
    result = web.run(callback(packed[:-40]), "cut.gff3.gz")
    assert result["ok"] is False
    assert "validation incomplete" in result["error"]
    result = web.run(callback(b"##gff-version 3\n"), "x.gff3", translation_table=11)
    assert result["ok"] is False
    result = web.run(callback(b"##gff-version 3\n"), "x.gff3", genome="/absent.fa")
    assert result["ok"] is False and "cannot open genome" in result["error"]


def finding_rules(result):
    return [finding["rule"] for finding in json.loads(result["json"])["findings"]]


def test_web_glue_options_match_the_cli_options():
    header = (FIXTURES / "valid" / "fhgff3_header.gff3").read_bytes()
    plain = (FIXTURES / "valid" / "canonical_gene.gff3").read_bytes()
    skipped = web.run(callback(header), "h", header_mode="skip")
    assert finding_rules(skipped) == ["HDR-003"]
    required = web.run(callback(plain), "p", header_mode="require")
    assert finding_rules(required) == ["HDR-001"]
    path = FIXTURES / "biology" / "bio008_internal_stop.gff3"
    for number in (1, 4, 11):
        result = web.run(
            callback(path.read_bytes()),
            str(path),
            genome=str(GENOME),
            translation_table=number,
        )
        expected = Validator(genome=str(GENOME), translation_table=number).validate(
            path, name=str(path)
        )
        assert result["json"] == to_json(expected)


@pytest.mark.parametrize("fmt", ["sarif", "html"])
def test_cli_html_and_sarif_formats(fmt, capsys):
    code = main(
        ["--format", fmt, str(FIXTURES / "invalid" / "syn019_cds_no_phase.gff3")]
    )
    assert code == 1
    text = capsys.readouterr().out
    if fmt == "sarif":
        check_sarif(json.loads(text))
    else:
        assert text.startswith("<!DOCTYPE html>") and "GFF-SYN-019" in text
