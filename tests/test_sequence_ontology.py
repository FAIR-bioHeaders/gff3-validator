"""The SO layer: the bundled release, the OBO parser and rules SO-001 to SO-009."""

import gzip
import hashlib
import io
import json
from importlib import resources

import pytest

from gff3_validator import cli, load_catalogue, validate
from gff3_validator.checks.biology import EXON_TYPES, RECODED_TYPES
from gff3_validator.checks.sequence_ontology import CDS, EXON, RECODED_CODON
from gff3_validator.checks.syntax import CDS_TYPES
from gff3_validator.ontology import (
    Ontology,
    OntologyError,
    derived_bytes,
    load_ontology,
    parse_obo,
)
from gff3_validator.report import to_html, to_json, to_sarif, to_text

SO = load_ontology()
TINY = """format-version: 1.2
data-version: test-1
date: 01:02:2026 10:00
subsetdef: SOFA "SO feature annotation"

[Term]
id: SO:0000110
name: sequence_feature
subset: SOFA

[Term]
id: SO:0000704
name: gene
subset: SOFA
synonym: "INSDC_feature:gene" EXACT []
is_a: SO:0000110 ! sequence_feature

[Term]
id: SO:0000673
name: transcript
synonym: "a \\"quoted\\" name" EXACT []
synonym: "transcript_related" RELATED []
is_a: SO:0000110 ! sequence_feature
relationship: member_of SO:0000704 ! gene

[Term]
id: SO:0000147
name: exon
is_a: SO:0000110 {source="x"} ! sequence_feature
relationship: part_of SO:0000673 ! transcript

[Term]
id: SO:0000001
name: old_term
is_obsolete: true
replaced_by: SO:0000704

[Typedef]
id: part_of
name: part_of
is_transitive: true
"""


def run(*lines, **options):
    text = "##gff-version 3\n" + "".join(
        line.replace("|", "\t") + "\n" for line in lines
    )
    return validate(io.BytesIO(text.encode("utf-8")), **options)


def found(report):
    return sorted((f.rule, f.line) for f in report.findings)


# -- the bundled release -------------------------------------------------------


def test_bundled_release_is_recorded_and_matches_the_catalogue():
    release = json.loads(
        resources.files("gff3_validator")
        .joinpath("data", "so-release.json")
        .read_text(encoding="utf-8")
    )
    data = resources.files("gff3_validator").joinpath("data", "so.json.gz").read_bytes()
    assert hashlib.sha256(data).hexdigest() == release["derived_sha256"]
    assert release["source"].startswith(
        "https://raw.githubusercontent.com/The-Sequence-Ontology/SO-Ontologies/"
    )
    assert len(release["sha256"]) == 64 and release["commit"] in release["source"]
    assert SO.release["data_version"] == release["data_version"]
    assert len(SO.terms) == release["terms"]
    title = load_catalogue().sources["so"]["title"]
    assert f"data-version {release['data_version']}" in title
    assert release["commit"][:7] in title


def test_derived_file_is_deterministic():
    data = resources.files("gff3_validator").joinpath("data", "so.json.gz")
    assert derived_bytes(SO.terms) == data.read_bytes()


def test_well_known_terms():
    for name, accession in (
        ("gene", "SO:0000704"),
        ("mRNA", "SO:0000234"),
        ("exon", "SO:0000147"),
        ("CDS", "SO:0000316"),
    ):
        assert SO.exact(name) == accession
        assert SO.exact(accession) == accession
        assert SO.in_subset(accession)
        assert SO.is_a(accession, "SO:0000110")


# -- the OBO parser and --so ---------------------------------------------------


def test_parse_obo():
    header, terms = parse_obo(TINY.splitlines())
    assert header["data-version"] == "test-1"
    assert set(terms) == {
        "SO:0000110",
        "SO:0000704",
        "SO:0000673",
        "SO:0000147",
        "SO:0000001",
    }
    assert terms["SO:0000147"]["is_a"] == ["SO:0000110"]
    assert terms["SO:0000147"]["part_of"] == ["SO:0000673"]
    assert terms["SO:0000673"]["member_of"] == ["SO:0000704"]
    assert terms["SO:0000673"]["synonyms"] == ['a "quoted" name']
    assert terms["SO:0000001"]["obsolete"] is True
    assert terms["SO:0000001"]["replaced_by"] == ["SO:0000704"]
    assert "part_of" not in terms  # the [Typedef] is skipped


def test_parse_obo_rejects_empty_and_nameless():
    with pytest.raises(OntologyError):
        parse_obo(["format-version: 1.2"])
    with pytest.raises(OntologyError):
        parse_obo(["[Term]", "id: SO:0000001"])


def test_so_option_uses_another_release(tmp_path):
    path = tmp_path / "so.obo.gz"
    path.write_bytes(gzip.compress(TINY.encode()))
    report = run(
        "ctg1|.|gene|1|90|.|+|.|ID=g1",
        "ctg1|.|transcript|1|90|.|+|.|ID=t1;Parent=g1",
        "ctg1|.|exon|1|90|.|+|.|Parent=g1",
        "ctg1|.|mRNA|1|90|.|+|.|ID=t2;Parent=g1",
        so=str(path),
    )
    assert found(report) == [("SO-001", 5), ("SO-009", 3), ("SO-009", 4)]
    assert report.ontology["data_version"] == "test-1"
    assert report.ontology["bundled"] is False
    assert report.ontology["source"] == str(path)
    (unknown,) = [f for f in report.findings if f.rule == "SO-001"]
    assert "so.obo data-version test-1 (--so)" in unknown.message


def test_cli_so_option(tmp_path, capsys):
    obo = tmp_path / "so.obo"
    obo.write_text(TINY, encoding="utf-8")
    gff = tmp_path / "a.gff3"
    gff.write_text("##gff-version 3\nctg1\t.\tgene\t1\t9\t.\t+\t.\tID=g1\n")
    assert cli.main(["--so", str(obo), str(gff)]) == 0
    assert "Sequence Ontology: so.obo data-version test-1" in capsys.readouterr().out
    assert cli.main(["--so", str(tmp_path / "missing.obo"), str(gff)]) == 2
    assert "--so: cannot read" in capsys.readouterr().err
    bad = tmp_path / "bad.obo"
    bad.write_bytes(b"\xff\xfe")
    assert cli.main(["--so", str(bad), str(gff)]) == 2


# -- the subtype lookups that replace the hard-coded names -----------------------


def test_subtype_lookups_keep_the_hard_coded_names():
    cds, exon, recoded = (SO.type_names(x) for x in (CDS, EXON, RECODED_CODON))
    assert CDS_TYPES <= cds and EXON_TYPES <= exon
    # recoded_codon has exactly the three subtypes that were listed by name.
    assert recoded == RECODED_TYPES
    assert {"CDS_predicted", "edited_CDS", "SO:1001254"} <= cds
    assert {"coding_exon", "interior_exon"} <= exon
    assert not cds & exon and not cds & recoded and not exon & recoded


def test_hard_coded_names_still_work_with_a_release_without_them(tmp_path):
    path = tmp_path / "so.obo"
    path.write_text(TINY, encoding="utf-8")
    report = run("ctg1|.|CDS|1|90|.|+|.|ID=c1", so=str(path))
    assert ("GFF-SYN-019", 2) in found(report)


def test_cds_subtype_needs_a_phase_but_case_variant_does_not():
    report = run(
        "ctg1|.|CDS_predicted|1|90|.|+|.|ID=c1",
        "ctg1|.|cds|1|90|.|+|.|ID=c2",
    )
    assert found(report) == [("GFF-SYN-019", 2), ("SO-005", 3), ("SO-009", 2)]


# -- type rules --------------------------------------------------------------------


@pytest.mark.parametrize(
    "type_, rule",
    [
        ("protein_coding_gene_model", "SO-001"),
        ("SO:9999999", "SO-001"),
        ("lnc_RNA", "SO-001"),
        ("SO:704", "SO-002"),
        ("so:0000704", "SO-002"),
        ("coding_sequence_variant", "SO-003"),
        ("RNA_polymerase_promoter", "SO-004"),
        ("five_prime_utr", "SO-005"),
        ("five prime UTR", "SO-005"),
        ("protein_coding_gene", "SO-009"),
    ],
)
def test_type_rules(type_, rule):
    report = run(f"ctg1|.|{type_}|1|90|.|+|.|ID=x1")
    assert [f.rule for f in report.findings] == [rule]


@pytest.mark.parametrize("type_", ["gene", "SO:0000704", "sequence_feature", "SNV"])
def test_good_types(type_):
    assert run(f"ctg1|.|{type_}|1|90|.|+|.|ID=x1").findings == []


def test_percent_encoded_type_is_decoded():
    report = run("ctg1|.|five%20prime%20UTR|1|90|.|+|.|ID=x1")
    assert sorted(f.rule for f in report.findings) == ["GFF-SYN-009", "SO-005"]


def test_messages_name_the_release_and_suggest():
    (unknown,) = run("ctg1|.|lnc_RNA|1|90|.|+|.|ID=x1").findings
    assert "so.obo data-version 2026-08-07 (bundled)" in unknown.message
    assert '"lncRNA"' in unknown.message
    (obsolete,) = run("ctg1|.|RNA_polymerase_promoter|1|90|.|+|.|ID=p").findings
    assert 'replaced by "promoter" (SO:0000167)' in obsolete.message
    (variant,) = run("ctg1|.|five_prime_utr|1|90|.|+|.|ID=u").findings
    assert '"five_prime_UTR" (SO:0000204)' in variant.message


def test_undefined_type_is_only_syn012():
    assert [f.rule for f in run("ctg1|.|.|1|90|.|+|.|ID=x").findings] == ["GFF-SYN-012"]


def test_type_findings_are_summarised_per_type():
    lines = [f"ctg1|.|made_up|{i}|{i + 9}|.|+|.|ID=x{i}" for i in range(1, 50)]
    lines.append("ctg1|.|other_made_up|1|9|.|+|.|ID=y")
    report = run(*lines)
    assert found(report) == [("SO-001", 2), ("SO-001", 51)]
    assert "(and 48 more lines like this)" in report.findings[0].message


def test_ontology_term_values():
    report = run(
        "ctg1|.|gene|1|90|.|+|.|ID=g1;Ontology_term=SO:9999999,GO:0046703",
        "ctg1|.|gene|1|90|.|+|.|ID=g2;Ontology_term=SO:704,SO:0000704",
        "ctg1|.|gene|1|90|.|+|.|ID=g3;Ontology_term=SO:1000069",  # obsolete
    )
    assert found(report) == [("SO-008", 2), ("SO-008", 3)]


# -- Parent relationships (SO-006) -------------------------------------------------


@pytest.mark.parametrize(
    "child, parent",
    [
        ("mRNA", "gene"),
        ("exon", "mRNA"),
        ("exon", "gene"),  # NOTE 2: transitivity
        ("CDS", "mRNA"),
        ("five_prime_UTR", "transcript"),
        ("mRNA", "protein_coding_gene"),  # is_a inheritance on the parent side
        ("ncRNA", "ncRNA_gene"),
        ("match_part", "cDNA_match"),
        ("pseudogenic_transcript", "pseudogene"),
        ("stop_codon_redefined_as_selenocysteine", "CDS"),
    ],
)
def test_part_of_allowed(child, parent):
    assert SO.part_of(SO.exact(child), SO.exact(parent))


@pytest.mark.parametrize(
    "child, parent",
    [("gene", "mRNA"), ("mRNA", "exon"), ("gene", "gene"), ("CDS", "exon")],
)
def test_part_of_not_allowed(child, parent):
    assert not SO.part_of(SO.exact(child), SO.exact(parent))


def test_parent_rule_with_forward_reference_and_summary():
    report = run(
        "ctg1|.|mRNA|1|90|.|+|.|ID=t1;Parent=e1",
        "ctg1|.|mRNA|1|90|.|+|.|ID=t2;Parent=e1",
        "ctg1|.|exon|1|90|.|+|.|ID=e1",
        "ctg1|.|mRNA|1|90|.|+|.|ID=t3;Parent=e1",
    )
    assert found(report) == [("SO-006", 2)]
    assert "(and 2 more lines like this)" in report.findings[0].message


def test_parent_rule_skips_unresolved_types():
    report = run(
        "ctg1|.|made_up|1|90|.|+|.|ID=a",
        "ctg1|.|gene|1|90|.|+|.|ID=g;Parent=a",
        "ctg1|.|RNA_polymerase_promoter|1|90|.|+|.|ID=p;Parent=g",
    )
    assert found(report) == [("SO-001", 2), ("SO-004", 4)]


def test_synonym_types_are_resolved_for_parents():
    report = run(
        "ctg1|.|gene|1|90|.|+|.|ID=g",
        "ctg1|.|protein_coding_transcript|1|90|.|+|.|ID=t;Parent=g",
        "ctg1|.|exon|1|90|.|+|.|Parent=t",
    )
    assert found(report) == [("SO-005", 3)]


# -- phase on other features (GFF-SYN-020) ------------------------------------------


def test_phase_on_other_features():
    report = run(
        "ctg1|.|start_codon|1|3|.|+|0|ID=s1",
        "ctg1|.|start_codon|7|9|.|+|0|ID=s2",
        "ctg1|.|edited_CDS|1|90|.|+|0|ID=c1",
        "ctg1|.|made_up|1|90|.|+|0|ID=m1",
    )
    assert found(report) == [("GFF-SYN-020", 2), ("SO-001", 5), ("SO-009", 4)]


# -- BIO-010 along part_of relations only (question 18) -------------------------------


def test_strand_checked_only_along_part_of(tmp_path):
    from pathlib import Path

    genome = Path(__file__).parent / "fixtures" / "biology" / "genome.fa"
    report = run(
        "chr1|.|gene|1|90|.|+|.|ID=g1",
        "chr1|.|mRNA|1|90|.|-|.|ID=t1;Parent=g1",  # part of the gene: BIO-010
        "chr1|.|gene|1|90|.|-|.|ID=g2;Parent=g1",  # not part_of: SO-006 only
        "chr1|.|made_up|1|90|.|-|.|ID=x1;Parent=g1",  # unresolved: BIO-010
        "chr1|.|exon|1|90|.|+|.|Parent=t9",  # forward, part_of: BIO-010
        "chr1|.|gene|1|90|.|+|.|ID=g9;Parent=t9",  # forward, not part_of
        "chr1|.|mRNA|1|90|.|-|.|ID=t9",
        genome=genome,
    )
    rules = [(f.rule, f.line) for f in report.findings if f.rule != "BIO-011"]
    assert sorted(rules) == [
        ("BIO-010", 3),
        ("BIO-010", 5),
        ("BIO-010", 6),
        ("SO-001", 5),
        ("SO-006", 4),
        ("SO-006", 7),
    ]


# -- reports name the release ----------------------------------------------------------


def test_every_report_names_the_release():
    report = run("ctg1|.|gene|1|90|.|+|.|ID=g1")
    version = SO.release["data_version"]
    assert json.loads(to_json(report))["sequence_ontology"]["data_version"] == version
    assert f"Sequence Ontology: so.obo data-version {version} (bundled)" in (
        to_text(report)
    )
    assert f"so.obo data-version {version} (bundled)" in to_html(report)
    driver = json.loads(to_sarif(report))["runs"][0]["tool"]["driver"]
    assert driver["properties"]["sequenceOntology"]["data_version"] == version


def test_feature_ontology_directive_names_the_release():
    report = run("##feature-ontology http://example.org/so.obo")
    (finding,) = report.findings
    assert finding.rule == "GFF-DIR-009"
    assert "types are checked against Sequence Ontology so.obo" in finding.message


def test_lookups_are_memoized():
    ontology = Ontology(SO.terms, SO.release)
    gene, exon = ontology.exact("gene"), ontology.exact("exon")
    assert ontology.part_of(exon, gene)
    assert (exon, gene) in ontology._part_of
    assert ontology.ancestors(exon) is ontology.ancestors(exon)
