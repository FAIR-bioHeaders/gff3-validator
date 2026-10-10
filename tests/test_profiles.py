"""Repository and community profiles (FHR-Specification #51 and #70): loading,
the AgBioData rules, and how profile findings are reported apart from the core
findings."""

import importlib.util
import io
import json
from collections import Counter
from pathlib import Path

import jsonschema
import pytest
import yaml

from gff3_validator import Validator, validate, web
from gff3_validator.cli import main
from gff3_validator.profiles import (
    ProfileError,
    builtin_ids,
    list_profiles,
    load_profile,
    parse_profile,
    profile_problems,
)
from gff3_validator.report import to_html, to_json, to_sarif_dict, to_text

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "conformance"
MANIFEST = json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))
GENOME = SUITE / "genomes" / "genome.fa"
SOURCE = ROOT / "profiles" / "agbiodata.yaml"
AGB = load_profile("agbiodata")
V = "##gff-version 3"
SARIF_SCHEMA = json.loads(
    (ROOT / "tests" / "schemas" / "sarif-schema-2.1.0.json").read_text("utf-8")
)


def run(text, profile="agbiodata", **options):
    data = text if isinstance(text, bytes) else text.encode()
    return Validator(profile=profile, **options).validate(io.BytesIO(data), name="t")


def profile_rules(report):
    return [finding.rule for finding in report.profile.findings]


def lines(*rows):
    return "\n".join(rows) + "\n"


def feature(text):
    """A feature line written with spaces between the first eight columns."""
    return "\t".join(text.split(None, 8))


# -- the profile file -----------------------------------------------------------


def test_shipped_profiles():
    assert builtin_ids() == ["agbiodata"]
    assert [profile.id for profile in list_profiles()] == ["agbiodata"]


def test_packaged_copy_is_the_source():
    packaged = ROOT / "gff3_validator" / "profiles" / "agbiodata.yaml"
    assert packaged.read_bytes() == SOURCE.read_bytes()


def test_agbiodata_metadata_pins_its_source():
    source = AGB.source
    assert source["license"] == "CC0-1.0"
    assert source["commit"] == "32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8"
    assert f"/blob/{source['commit']}/Recommendations.md" in source["url"]
    assert source["date"] == "2021-12-29"
    assert "not reviewed" in AGB.review
    assert {rule.id for rule in AGB.implemented()} == {
        f"AGB-{n:03d}" for n in range(1, 14)
    }
    assert set(AGB.levels) == {"SO-001", "BIO-008"}
    assert all(change.level == "error" for change in AGB.levels.values())
    assert len(AGB.guidance) >= 15


def test_every_rule_and_guidance_cites_a_section():
    for rule in AGB:
        assert rule.reference["section"] and rule.reference["anchor"]
    for item in AGB.guidance:
        assert item.reference["section"]


def test_conformance_manifest_agrees_with_the_profile():
    entry = MANIFEST["profiles"]["agbiodata"]
    assert entry["name"] == AGB.name
    assert entry["version"] == AGB.version
    assert entry["source"] == AGB.source["url"]
    assert entry["license"] == AGB.source["license"]
    assert entry["rules"] == AGB.docs


def data():
    return yaml.safe_load(SOURCE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "change, message",
    [
        (lambda d: d["levels"][0].update(level="info"), "can only raise"),
        (lambda d: d["levels"][0].update(rule="GFF-SYN-011"), "not implemented"),
        (lambda d: d["levels"][0].update(rule="XYZ-001"), "not a catalogue rule"),
        (lambda d: d.update(checks="os"), "not a checks module"),
        (lambda d: d["rules"][0].update(id="NCBI-001"), "id does not match"),
        (lambda d: d["rules"][0].update(level="fatal"), "level must be"),
        (lambda d: d["rules"][0].update(colour="red"), "unknown field"),
        (lambda d: d["rules"].append(dict(d["rules"][0])), "duplicate id"),
        (lambda d: d.pop("source"), "missing 'source'"),
        (lambda d: d["source"].pop("license"), "missing 'license'"),
        (lambda d: d["guidance"][0].update(covered_by=["NOPE-1"]), "unknown"),
    ],
)
def test_profile_problems_detected(change, message):
    from gff3_validator import load_catalogue

    profile = data()
    change(profile)
    problems = profile_problems(profile, load_catalogue())
    assert any(message in problem for problem in problems), problems


def test_implemented_rule_needs_a_checker():
    profile = data()
    profile.pop("checks")
    assert any(
        "has no checks" in problem for problem in profile_problems(profile)
    ), "a rule marked implemented needs code"
    profile = data()
    profile["rules"].append(dict(profile["rules"][0], id="AGB-099"))
    with pytest.raises(ValueError, match="AGB-099 is implemented"):
        parse_profile(yaml.safe_dump(profile))


def test_profile_from_a_path_that_only_raises_levels(tmp_path):
    path = tmp_path / "strict.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "profile_format": 1,
                "id": "strict",
                "name": "Strict example",
                "version": "1",
                "description": "Raises one warning.",
                "review": "an example",
                "source": {
                    "title": "t",
                    "url": "https://example.org",
                    "license": "CC0",
                },
                "prefix": "STR",
                "rules": [],
                "levels": [
                    {
                        "rule": "GFF-ATT-007",
                        "level": "error",
                        "reference": {"section": "s"},
                        "reason": "r",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    report = run(lines(V, feature("ctg1 . gene 1 90 . + . ID=g1;Colour=red")), path)
    assert [f.rule for f in report.findings] == ["GFF-ATT-007"]
    assert report.valid and report.compliant is False
    (finding,) = report.profile.findings
    assert (finding.rule, finding.level, finding.core_level) == (
        "GFF-ATT-007",
        "error",
        "warning",
    )


def test_unknown_or_broken_profile(tmp_path):
    with pytest.raises(ProfileError, match="unknown profile 'ncbi'"):
        load_profile("ncbi")
    broken = tmp_path / "broken.yaml"
    broken.write_text("id: [", encoding="utf-8")
    with pytest.raises(ProfileError, match="broken.yaml"):
        load_profile(broken)
    with pytest.raises(ProfileError, match="cannot read"):
        load_profile(tmp_path / "missing.yaml")


# -- each AgBioData rule: the documented example fires, the valid one does not --

EXTRA_VALID = {
    "AGB-006": feature("ctg1 . CDS 1 90 . + 0 ID=c1;Parent=t1"),
}


@pytest.mark.parametrize("rule", list(AGB), ids=lambda rule: rule.id)
def test_rule_example_and_valid(rule):
    bad = run(lines(V, rule.example))
    assert rule.id in profile_rules(bad)
    good = rule.valid or EXTRA_VALID[rule.id]
    assert rule.id not in profile_rules(run(lines(V, good)))


@pytest.mark.parametrize(
    "rule, rows",
    [
        # AGB-001 and AGB-002: Ontology_term with a GO term gets both.
        ("AGB-002", [feature("ctg1 . gene 1 90 . + . ID=g1;Ontology_term=GO:1")]),
        # AGB-003: a child before its parent is compared at the end.
        (
            "AGB-003",
            [
                feature("ctg1 . mRNA 1 95 . + . ID=t1;Parent=g1"),
                feature("ctg1 . gene 1 90 . + . ID=g1"),
            ],
        ),
        # AGB-003: a child on another seqid than its parent.
        (
            "AGB-003",
            [
                feature("ctg1 . gene 1 90 . + . ID=g1"),
                feature("ctg2 . mRNA 1 90 . + . ID=t1;Parent=g1"),
            ],
        ),
        ("AGB-008", [feature("ctg1 . gene 1 90 . + . ID=g1;so_term_name=no_such")]),
        ("AGB-009", [feature("ctg1 . match 1 90 . + . ID=m;Target=E1 1 90 + ")]),
        ("AGB-010", ["##attribute-ontology https://example.org/a.obo"]),
        ("AGB-011", ["##species human"]),
        ("AGB-012", ['##score name="x";min=a;max=1;best=lower']),
        ("AGB-012", ['##Score name="x";min=0;max=1;best=best']),
        ("AGB-012", ["##Score just text"]),
    ],
)
def test_more_non_compliant_cases(rule, rows):
    assert rule in profile_rules(run(lines(V, *rows)))


@pytest.mark.parametrize(
    "rule, rows",
    [
        # Discontinuous parent: its extent is all of its lines.
        (
            "AGB-003",
            [
                feature("ctg1 . gene 1 40 . + . ID=g1"),
                feature("ctg1 . gene 60 90 . + . ID=g1"),
                feature("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
            ],
        ),
        # A parent defined earlier is not a forward reference.
        (
            "AGB-004",
            [
                feature("ctg1 . gene 1 90 . + . ID=g1"),
                feature("ctg1 . mRNA 1 90 . + . ID=t1;Parent=g1"),
            ],
        ),
        ("AGB-007", [feature("ctg1 . match_part 1 90 . + . ID=m1")]),
        ("AGB-008", [feature("ctg1 . gene 1 90 . + . ID=g1;so_term_name=SO:0001217")]),
        ("AGB-009", [feature("ctg1 . match 1 90 . + . ID=m;Target=EST%2023 1 90")]),
        ("AGB-010", ["##source-ontology https://purl.obolibrary.org/obo/so.obo"]),
        ("AGB-012", ["##score name=x; min=-1.5 ;max=2e3; best=higher"]),
    ],
)
def test_more_compliant_cases(rule, rows):
    assert rule not in profile_rules(run(lines(V, *rows)))


def test_summarised_rules_are_reported_once_with_a_count():
    rows = [feature(f"ctg1 . exon {n} {n + 9} . + . ID=e{n}") for n in (1, 20, 40)]
    report = run(lines(V, *rows))
    (finding,) = [f for f in report.profile.findings if f.rule == "AGB-007"]
    assert finding.line == 2
    assert "(and 2 more like this in the file)" in finding.message
    assert report.profile.counts["warning"] == 1


# -- raised core levels -----------------------------------------------------------


def test_so_001_is_a_core_warning_and_a_profile_error():
    report = run(lines(V, feature("ctg1 . gene_model 1 90 . + . ID=g1")))
    assert [(f.rule, f.level) for f in report.findings] == [("SO-001", "warning")]
    assert report.valid is True
    assert report.compliant is False
    (finding,) = report.profile.findings
    assert (finding.rule, finding.level, finding.core_level) == (
        "SO-001",
        "error",
        "warning",
    )


def test_bio_008_needs_the_genome():
    text = SUITE / "profiles/agbiodata/noncompliant/bio-008-raised-to-error.gff3"
    without = validate(text, profile="agbiodata")
    assert without.compliant is True
    assert any("BIO-008 (raised to error)" in r for r in without.profile.skipped)
    with_genome = validate(text, profile="agbiodata", genome=str(GENOME))
    assert with_genome.compliant is False
    assert profile_rules(with_genome) == ["BIO-008"]
    assert not with_genome.profile.skipped


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda case: case["id"])
def test_profile_never_changes_core_results(case):
    if case.get("options"):
        pytest.skip("header options")
    options = {"genome": str(SUITE / case["genome"])} if "genome" in case else {}
    plain = validate(SUITE / case["file"], **options)
    profiled = validate(SUITE / case["file"], profile="agbiodata", **options)
    assert profiled.findings == plain.findings
    assert profiled.counts == plain.counts
    assert profiled.valid == plain.valid
    assert plain.profile is None and plain.compliant is None
    plain_json = json.loads(to_json(plain))
    profiled_json = json.loads(to_json(profiled))
    assert plain_json.pop("profile") is None
    profiled_json.pop("profile")
    assert profiled_json == plain_json


# -- reports ------------------------------------------------------------------------

CASE = SUITE / "profiles/agbiodata/noncompliant/agb-009-target-spaces.gff3"


def test_json_has_profile_metadata_and_findings():
    report = json.loads(to_json(validate(CASE, profile="agbiodata")))
    assert report["valid"] is True
    profile = report["profile"]
    assert profile["id"] == "agbiodata"
    assert profile["version"] == AGB.version
    assert profile["source"]["url"] == AGB.source["url"]
    assert profile["source"]["license"] == "CC0-1.0"
    assert profile["source"]["commit"].startswith("32c8a38")
    assert profile["compliant"] is False
    assert profile["counts"] == {"error": 1, "warning": 0, "info": 0}
    (finding,) = profile["findings"]
    assert finding["rule"] == "AGB-009" and finding["core_level"] is None
    assert set(finding) == {
        "rule",
        "level",
        "line",
        "field",
        "message",
        "fix",
        "core_level",
    }


def test_text_labels_profile_findings_and_keeps_the_core_verdict():
    report = Validator(profile="agbiodata").validate(CASE, name="a.gff3")
    text = to_text(report)
    assert "a.gff3:2 (column 9): AgBioData profile error AGB-009:" in text
    assert (
        "a.gff3: no errors (0 errors, 0 warnings, 0 notes; 2 lines); "
        "AgBioData profile: 1 errors, 0 warnings, 0 notes (not compliant)"
    ) in text
    assert "profile: AgBioData GFF3 recommendations 0.1.0-draft (" in text
    assert "commit 32c8a38, 2021-12-29, CC0-1.0" in text
    raised = run(lines(V, feature("ctg1 . gene_model 1 90 . + . ID=g1")))
    assert "AgBioData profile error SO-001 (core level warning):" in to_text(raised)


def test_html_has_a_separate_profile_section():
    report = validate(CASE, profile="agbiodata")
    page = to_html(report)
    assert '<section aria-labelledby="profile-title">' in page
    assert "AgBioData profile findings (1)" in page
    assert "not compliant" in page
    assert "Profile findings do not change whether the file is valid GFF3" in page
    assert "docs/profiles/agbiodata.md#agb-009" in page
    assert AGB.source["url"] in page
    assert '<p class="verdict bad" role="status">' in page
    assert "profile-title" not in to_html(validate(CASE))


def test_html_escapes_profile_messages():
    hostile = lines(V, feature("ctg1 . <b>x</b> 1 90 . + . ID=g1"))
    report = run(hostile)
    assert profile_rules(report) == ["SO-001"]
    section = to_html(report).split('aria-labelledby="profile-title"', 1)[1]
    assert "&lt;b&gt;x&lt;/b&gt;" in section
    assert "<b>x" not in section


def test_sarif_profile_is_a_tool_extension_and_schema_valid():
    report = run(lines(V, feature("ctg1 . gene_model 1 90 . + . ID=g1"), "##species x"))
    log = to_sarif_dict(report)
    validator = jsonschema.Draft4Validator(
        SARIF_SCHEMA, format_checker=jsonschema.FormatChecker()
    )
    errors = sorted(validator.iter_errors(log), key=str)
    assert not errors, errors[:3]
    run_ = log["runs"][0]
    (extension,) = run_["tool"]["extensions"]
    assert extension["name"] == "agbiodata"
    assert extension["version"] == AGB.version
    ids = [rule["id"] for rule in extension["rules"]]
    assert "AGB-001" in ids and "SO-001" in ids
    profile_results = [r for r in run_["results"] if "rule" in r]
    assert {r["ruleId"] for r in profile_results} == {"SO-001", "AGB-011"}
    for result in profile_results:
        assert result["rule"]["toolComponent"] == {"name": "agbiodata", "index": 0}
        assert extension["rules"][result["rule"]["index"]]["id"] == result["ruleId"]
        assert result["properties"]["profile"] == "agbiodata"
    core = [r for r in run_["results"] if "rule" not in r]
    assert {r["ruleId"] for r in core} == {"SO-001", "GFF-DIR-007"}
    assert run_["properties"]["profile"]["compliant"] is False
    assert run_["properties"]["profile"]["source"]["license"] == "CC0-1.0"
    assert "extensions" not in to_sarif_dict(validate(CASE))["runs"][0]["tool"]


# -- command line and web page ---------------------------------------------------


def test_cli_exit_status_follows_profile_compliance(capsys):
    compliant = SUITE / "profiles/agbiodata/compliant/agb-001-ontology-term.gff3"
    assert main(["--profile", "agbiodata", str(compliant)]) == 0
    assert main(["--profile", "agbiodata", str(CASE)]) == 1
    assert main([str(CASE)]) == 0
    capsys.readouterr()


def test_cli_profile_path_list_and_errors(capsys, tmp_path):
    assert main(["--profile", str(SOURCE), str(CASE)]) == 1
    capsys.readouterr()
    assert main(["--list-profiles"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("agbiodata\t0.1.0-draft\tAgBioData GFF3 recommendations")
    assert "CC0-1.0" in out
    assert main(["--profile", "nope", str(CASE)]) == 2
    assert "unknown profile" in capsys.readouterr().err
    with pytest.raises(SystemExit) as stop:
        main([])
    assert stop.value.code == 2


def test_web_run_matches_the_cli_with_a_profile():
    data = CASE.read_bytes()

    def read_at(offset, length):
        return data[offset : offset + length]

    stream = web.open_callback(len(data), read_at)
    result = web.run(stream, str(CASE), profile="agbiodata")
    expected = Validator(profile="agbiodata").validate(CASE, name=str(CASE))
    assert result["json"] == to_json(expected)
    assert result["valid"] is True and result["compliant"] is False
    assert "AgBioData profile" in result["summary"]
    assert web.profiles() == [
        {"id": "agbiodata", "name": AGB.name, "version": AGB.version}
    ]
    plain = web.run(web.open_callback(len(data), read_at), "x")
    assert plain["compliant"] is None
    bad = web.run(web.open_callback(len(data), read_at), "x", profile="nope")
    assert bad["ok"] is False and "unknown profile" in bad["error"]


# -- conformance profile cases, in process -----------------------------------------


def load_checker():
    path = ROOT / "scripts" / "check_conformance.py"
    spec = importlib.util.spec_from_file_location("check_conformance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_profile_rule_has_a_conformance_case():
    checker = load_checker()
    covered = {case["rule"] for case in MANIFEST["profile_cases"]}
    assert checker.profile_rules()["agbiodata"] <= covered


@pytest.mark.parametrize("case", MANIFEST["profile_cases"], ids=lambda case: case["id"])
def test_engine_passes_profile_case(case):
    options = {"profile": case["profile"]}
    if "genome" in case:
        options["genome"] = str(SUITE / case["genome"])
    report = validate(SUITE / case["file"], **options)
    key = Counter
    assert key((x.rule, x.level, x.line) for x in report.findings) == key(
        (x["rule"], x["level"], x["line"]) for x in case["findings"]
    )
    assert key((x.rule, x.level, x.line) for x in report.profile.findings) == key(
        (x["rule"], x["level"], x["line"]) for x in case["profile_findings"]
    )
    assert report.valid
    assert report.compliant == (case["expected_profile"] == "compliant")
