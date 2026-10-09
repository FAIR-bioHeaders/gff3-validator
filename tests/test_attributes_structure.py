"""Edge cases of the attribute, directive and structure rules."""

import io

import pytest

from gff3_validator import validate
from gff3_validator.checks import structure
from gff3_validator.checks.attributes import parse_attributes
from gff3_validator.checks.structure import find_cycles


def run(*lines, max_findings=10000):
    text = "##gff-version 3\n" + "".join(
        line.replace("|", "\t") + "\n" for line in lines
    )
    return validate(io.BytesIO(text.encode("utf-8")), max_findings=max_findings)


def ids(report):
    return sorted(finding.rule for finding in report.findings)


def attribute_rules(text, start=None, end=None):
    _, problems = parse_attributes(text, start, end)
    return sorted(rule for rule, _ in problems)


# -- attributes ---------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        ".",
        "ID=g1;Name=EDEN",
        "ID=g1;Note=",  # empty value: question 4, not reported
        "Parent=a,b;Alias=x,y;Note=one,two",
        "Dbxref=EMBL:AA816246,GO:GO:0001;Ontology_term=GO:0046703",
        "Is_circular=true",
        "Is_circular=false",
        "Derives_from=a,b",  # question 5: not reported
        "gene_biotype=a,b",
        "Note=a%3Bb%2Cc%3Dd%26e%25f%09g",
        "Target=EST%20A 1 21 +;Gap=M8 D3 M6 I1 M6",
        "Target=EST23 21 1",  # start > end: not reported until SO answers
        "Target=EST23  1   21",  # runs of spaces accepted
    ],
)
def test_attributes_accepted(text):
    assert attribute_rules(text, 1, 23) == []


@pytest.mark.parametrize(
    "text, rules",
    [
        ("ID", ["GFF-ATT-001"]),
        ("ID=g1;Name", ["GFF-ATT-001"]),
        ("=x", ["GFF-ATT-002"]),
        ("ID=g1;", ["GFF-ATT-003"]),
        (";ID=g1", ["GFF-ATT-003"]),
        ("ID=a;ID=b", ["GFF-ATT-004"]),
        ("Note=a&b", ["GFF-ATT-005"]),
        ("no,te=a", ["GFF-ATT-005"]),
        ("ID=a,b", ["GFF-ATT-006"]),
        ("Gap=M1,M2;Target=x 1 3", ["GFF-ATT-006", "GFF-ATT-011"]),
        ("Is_pseudo=true", ["GFF-ATT-007"]),
        ("PARENT=t1", ["GFF-ATT-008"]),
        ("derives_from=t1", ["GFF-ATT-008"]),
        ('Note="text"', ["GFF-ATT-009"]),
        ("Target=EST23", ["GFF-ATT-010"]),
        ("Target=EST 23 1 21", ["GFF-ATT-010"]),
        ("Target=EST23 1 x", ["GFF-ATT-010"]),
        ("Target=EST23 0 21", ["GFF-ATT-010"]),
        ("Target=EST23 1 21 .", ["GFF-ATT-010"]),
        ("Target=EST23 1 21;Gap=m8 d3", ["GFF-ATT-011"]),
        ("Target=EST23 1 21;Gap=M0", ["GFF-ATT-011"]),
        ("Gap=M23", ["GFF-ATT-012"]),
        ("Target=EST23 1 21;Gap=M23", ["GFF-ATT-013"]),
        ("Dbxref=:123", ["GFF-ATT-014"]),
        ("Ontology_term=GO:", ["GFF-ATT-014"]),
        ("Is_circular=1", ["GFF-ATT-016"]),
        ("Name=EDEN%2D1", ["GFF-SYN-009"]),
        ("Name=caf%C3%A9", ["GFF-SYN-009"]),
    ],
)
def test_attributes_rejected(text, rules):
    assert attribute_rules(text, 1, 23) == rules


def test_protein_gap_with_frameshifts():
    # The specification's frameshift examples: 3 x (M + D) + F - R bases.
    assert attribute_rules("Target=p 1 10;Gap=M3 I1 M2 F1 M4", 100, 127) == []
    assert attribute_rules("Target=p 1 10;Gap=M3 I1 M2 R1 M4", 100, 125) == []
    assert attribute_rules("Target=p 1 10;Gap=M3 I1 M2 R1 M4", 100, 127) == [
        "GFF-ATT-013"
    ]


def test_gap_lengths_skipped_without_coordinates():
    assert attribute_rules("Target=EST23 1 21;Gap=M23") == []


def test_ids_and_references_are_percent_decoded():
    attributes, _ = parse_attributes("ID=a%2Cb;Parent=p%3B1,p2;Derives_from=d%201")
    assert attributes.id == "a,b"
    assert attributes.parents == ["p;1", "p2"]
    assert attributes.derives_from == ["d 1"]


# -- syntax rules on whole lines -------------------------------------------


def test_crlf_line_endings_are_not_reported():
    data = b"##gff-version 3\r\nctg1\t.\tgene\t1\t90\t.\t+\t.\tID=g1\r\n"
    data += b"ctg1\t.\tmRNA\t1\t90\t.\t+\t.\tID=t1;Parent=g1\r\n"
    assert ids(validate(io.BytesIO(data))) == []


def test_lone_carriage_return_is_a_control_character():
    report = run("ctg1|.|gene|1|90|.|+|.|ID=g1;Note=a\rb")
    assert [(f.rule, f.field) for f in report.findings] == [("GFF-SYN-005", 9)]


@pytest.mark.parametrize(
    "seqid, rules",
    [
        ("chr%231", []),  # "#" is outside the seqid set: escaping is required
        ("chr%41", ["GFF-SYN-009"]),  # "A" is inside it
        ("chr%2", ["GFF-SYN-008"]),
        ("chr 1", ["GFF-SYN-010"]),
    ],
)
def test_seqid_encoding(seqid, rules):
    assert ids(run(f"{seqid}|.|gene|1|90|.|+|.|ID=g1")) == rules


def test_over_encoding_in_other_columns():
    report = run("ctg1|my%20tool|gene|1|90|.|+|.|ID=g1")
    assert [(f.rule, f.field) for f in report.findings] == [("GFF-SYN-009", 2)]


def test_summarised_rules_are_reported_once_with_a_count():
    report = run(*[f"ctg1|.|gene|1|90|.|+|.|ID=g{n};" for n in range(5)])
    (finding,) = report.findings
    assert (finding.rule, finding.line) == ("GFF-ATT-003", 2)
    assert "4 more" in finding.message


def test_summarised_rules_do_not_crowd_out_errors():
    lines = [f"ctg1|.|gene|1|90|.|+|.|ID=g{n};" for n in range(20)]
    report = run(*lines, "ctg1|.|gene|1|90|.|+|.|ID=x;Parent=missing", max_findings=1)
    assert [f.rule for f in report.findings] == ["GFF-STR-004"]
    assert report.truncated == 1


# -- directives -----------------------------------------------------------


@pytest.mark.parametrize(
    "directive",
    [
        "##sequence-region ctg1 1",
        "##sequence-region ctg1 a 100",
        "##sequence-region ctg1 0 100",
        "##sequence-region ctg1 100 1",
        "##sequence-region",
    ],
)
def test_bad_sequence_region(directive):
    assert ids(run(directive)) == ["GFF-DIR-001"]


def test_sequence_region_not_starting_at_1_is_accepted():
    assert ids(run("##sequence-region ctg1 50 100", "ctg1|.|gene|50|90|.|+|.|.")) == []


def test_identical_repeated_sequence_region_is_reported():
    report = run("##sequence-region ctg1 1 100", "##sequence-region ctg1 1 100")
    assert ids(report) == ["GFF-DIR-002"]
    assert "same bounds" in report.findings[0].message


@pytest.mark.parametrize(
    "directive, rules",
    [
        (
            "##species http://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=6239",
            [],
        ),
        (
            "##species https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi"
            "?name=Caenorhabditis+elegans",
            [],
        ),
        ("##species NCBITaxon:6239", ["GFF-DIR-007"]),
        ("##species", ["GFF-DIR-007"]),
        ("##genome-build NCBI B36", []),
        ("##genome-build", ["GFF-DIR-008"]),
        ("##attribute-ontology http://example.org/a.obo", ["GFF-DIR-009"]),
        ("##source-ontology", ["GFF-DIR-009"]),
        ("##date 2026-10-08", ["GFF-DIR-010"]),
        ("####", ["GFF-DIR-010"]),
        ("###", []),
        ("### ", []),
    ],
)
def test_directives(directive, rules):
    assert ids(run(directive)) == rules


def test_fasta_section():
    report = run(
        "ctg1|.|gene|1|8|.|+|.|ID=g1",
        "##FASTA",
        "ACGT",
        ">ctg1 description",
        "ACGT",
        "",
        "# comment",
        "ACGT",
        ">",
        "AC",
        ">ctg1",
        "AC",
        "###",
        ">last",
    )
    found = [(f.rule, f.line) for f in report.findings]
    assert found == [
        ("GFF-DIR-006", 4),  # sequence before the first header
        ("GFF-DIR-006", 10),  # header without id
        ("GFF-DIR-006", 12),  # repeated id
        ("GFF-DIR-004", 14),  # directive
        ("GFF-DIR-006", 15),  # last record has no sequence
    ]


def test_fasta_ids_match_decoded_seqids():
    report = run("chr%231|.|gene|1|4|.|+|.|ID=g1", "##FASTA", ">chr#1", "ACGT")
    assert ids(report) == []


# -- IDs and references -----------------------------------------------------


def test_forward_references_resolve_at_end_of_file():
    report = run(
        "ctg1|.|exon|1|90|.|+|.|Parent=t1",
        "ctg1|.|polypeptide|1|90|.|+|.|Derives_from=t1",
        "ctg1|.|mRNA|1|90|.|+|.|ID=t1",
    )
    assert ids(report) == []


def test_unresolved_reference_reported_once_per_id_with_count():
    report = run(*["ctg1|.|exon|1|90|.|+|.|Parent=t9"] * 3)
    (finding,) = report.findings
    assert (finding.rule, finding.line) == ("GFF-STR-004", 2)
    assert "2 more lines" in finding.message


def test_reference_to_earlier_id_after_resolution_point_is_accepted():
    # Question 9: only references that cross ### forwards are reported.
    report = run(
        "ctg1|.|gene|1|90|.|+|.|ID=g1",
        "###",
        "ctg1|.|mRNA|1|90|.|+|.|ID=t1;Parent=g1",
        "###",
        "ctg1|.|CDS|1|30|.|+|0|ID=c1;Parent=t1",
        "###",
        "ctg1|.|CDS|61|90|.|+|0|ID=c1;Parent=t1",
    )
    assert ids(report) == []


def test_derives_from_crossing_resolution_point():
    report = run(
        "ctg1|.|polypeptide|1|90|.|+|.|Derives_from=c1",
        "###",
        "ctg1|.|CDS|1|90|.|+|0|ID=c1",
    )
    assert [(f.rule, f.line) for f in report.findings] == [("GFF-DIR-003", 2)]


def test_discontinuous_feature_with_identical_lines_is_valid():
    report = run(
        "ctg1|.|mRNA|1|90|.|+|.|ID=t1",
        "ctg1|.|cDNA_match|1|30|.|+|.|ID=m1;Parent=t1",
        "ctg1|.|cDNA_match|61|90|.|+|.|ID=m1;Parent=t1",
    )
    assert ids(report) == []


def test_seqid_change_is_str002():
    report = run("chr1|.|CDS|1|30|.|+|0|ID=c1", "chr2|.|CDS|61|90|.|+|0|ID=c1")
    assert ids(report) == ["GFF-STR-002"]
    assert "seqid" in report.findings[0].message


def test_ids_compared_after_decoding():
    report = run(
        "ctg1|.|gene|1|90|.|+|.|ID=g%2C1", "ctg1|.|mRNA|1|90|.|+|.|ID=t1;Parent=g%2C1"
    )
    assert ids(report) == []
    report = run("ctg1|.|gene|1|90|.|+|.|ID=g%41", "ctg1|.|mRNA|1|90|.|+|.|ID=gA")
    assert "GFF-STR-001" in ids(report)


def test_self_parent_is_a_cycle():
    assert ids(run("ctg1|.|gene|1|90|.|+|.|ID=a;Parent=a")) == ["GFF-STR-006"]


def test_cycle_through_a_later_line_of_a_discontinuous_feature():
    report = run(
        "ctg1|.|mRNA|1|90|.|+|.|ID=a",
        "ctg1|.|CDS|1|30|.|+|0|ID=b;Parent=a",
        "ctg1|.|mRNA|1|90|.|+|.|ID=a;Parent=b",
    )
    assert ids(report) == ["GFF-STR-003", "GFF-STR-006"]


def test_long_cycle_has_no_recursion_limit():
    size = 20000
    lines = [
        f"ctg1|.|gene|1|90|.|+|.|ID=n{i};Parent=n{(i + 1) % size}" for i in range(size)
    ]
    report = run(*lines)
    (finding,) = report.findings
    assert finding.rule == "GFF-STR-006"
    assert f"({size} features)" in finding.message


def test_find_cycles_reports_each_cycle():
    graph = {0: [1], 1: [0], 2: [3], 3: [4], 4: [2], 5: [0]}
    cycles = list(find_cycles(6, lambda n: graph[n], iter(range(6))))
    assert sorted(sorted(c) for c in cycles) == [[0, 1], [2, 3, 4]]


# -- bounds -----------------------------------------------------------------


def test_features_before_the_sequence_region_are_checked():
    report = run(
        "ctg1|.|gene|1|150|.|+|.|ID=g1",
        "##sequence-region ctg1 10 100",
    )
    assert [(f.rule, f.line) for f in report.findings] == [
        ("GFF-STR-008", 2),
        ("GFF-STR-008", 2),
    ]


def test_start_before_region_start():
    report = run("##sequence-region ctg1 10 100", "ctg1|.|gene|5|50|.|+|.|ID=g1")
    assert [(f.rule, f.line) for f in report.findings] == [("GFF-STR-008", 3)]


def test_later_is_circular_exempts_earlier_features():
    report = run(
        "##sequence-region J02448 1 6407",
        "J02448|.|CDS|6006|7238|.|+|0|ID=geneII",
        "J02448|.|region|1|6407|.|+|.|ID=J02448;Is_circular=true",
        "J02448|.|gene|6500|6600|.|+|.|ID=g2",
    )
    assert [(f.rule, f.line) for f in report.findings] == [("GFF-STR-008", 5)]


def test_many_features_beyond_the_region_are_counted(monkeypatch):
    monkeypatch.setattr(structure, "MAX_DEFERRED", 2)
    report = run(
        "##sequence-region ctg1 1 100",
        *[f"ctg1|.|gene|90|{100 + n}|.|+|.|ID=g{n}" for n in range(1, 6)],
    )
    assert [f.line for f in report.findings] == [3, 4, None]
    assert "3 more features" in report.findings[-1].message


def test_circular_sequence_in_fasta_checks_start():
    report = run(
        "ctg1|.|region|1|4|.|+|.|ID=ctg1;Is_circular=true",
        "ctg1|.|gene|3|6|.|+|.|ID=g1",
        "##FASTA",
        ">ctg1",
        "ACGT",
    )
    assert ids(report) == []


def test_undefined_seqid_is_not_bounds_checked():
    report = run("##sequence-region ctg1 1 100", ".|.|gene|1|90|.|+|.|ID=g1")
    assert ids(report) == []
