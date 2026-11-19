"""The feature-layer index (issue #31): the six outcomes and what they may not do.

The tests are written against the contract in docs/feature-index.md, and
`tests/fixtures/features/outcomes.json` is that contract in machine-readable
form: every case there is asserted here, and the same file is what another
implementation is scored against.
"""

import gzip
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from gff3_validator import load_catalogue, validate
from gff3_validator.features import (
    FEATURE_ROW_FIELDS,
    NOT_SCORED_OUTCOMES,
    OUTCOME_ABSENT_LAYER,
    OUTCOME_DUPLICATE_ROW,
    OUTCOME_FOUND,
    OUTCOME_MALFORMED_LAYER,
    OUTCOME_NON_GENE_TARGET,
    OUTCOME_NOT_FOUND,
    OUTCOMES,
    SCORED_OUTCOMES,
    FeatureRow,
    build_feature_index,
    is_gene_row_type,
    resolve_feature_id,
)

FIXTURES = Path(__file__).parent / "fixtures" / "features"
OUTCOMES_FILE = FIXTURES / "outcomes.json"
CONTRACT = json.loads(OUTCOMES_FILE.read_text(encoding="utf-8"))
CATALOGUE = load_catalogue()


def case_ids():
    return [f"{case['fixture']}#{case['feature_id']}" for case in CONTRACT["cases"]]


def index_of(name):
    """Index a fixture, and fail loudly if it is not the file the case names.

    An absent-layer assertion on a mistyped path would pass for the wrong
    reason, which is the one way this file could certify nothing and look green.
    """
    path = FIXTURES / name
    assert path.is_file(), f"{name} is not a fixture"
    return build_feature_index(path)


# -- the vocabulary itself --------------------------------------------------


def test_the_six_outcomes_are_the_whole_vocabulary():
    assert CONTRACT["vocabulary"] == list(OUTCOMES)
    assert tuple(CONTRACT["scored"]) == SCORED_OUTCOMES
    assert tuple(CONTRACT["never_scored"]) == NOT_SCORED_OUTCOMES
    # The two halves partition the vocabulary: no outcome is both, none is neither.
    assert set(SCORED_OUTCOMES) | set(NOT_SCORED_OUTCOMES) == set(OUTCOMES)
    assert not set(SCORED_OUTCOMES) & set(NOT_SCORED_OUTCOMES)


# -- every case in the contract --------------------------------------------


@pytest.mark.parametrize("case_id", case_ids())
def test_fixture_case_reports_the_contracted_outcome(case_id):
    case = next(
        candidate
        for candidate in CONTRACT["cases"]
        if f"{candidate['fixture']}#{candidate['feature_id']}" == case_id
    )
    match = index_of(case["fixture"]).resolve(case["feature_id"])
    assert match.outcome == case["outcome"], match.message
    assert match.scored == (case["outcome"] in SCORED_OUTCOMES)
    assert match.passes == (case["outcome"] == OUTCOME_FOUND)
    if case.get("never_scored"):
        assert case["outcome"] in NOT_SCORED_OUTCOMES
        assert not match.scored and not match.passes


def test_the_six_outcomes_are_reachable_and_mutually_distinct():
    """Each of the six is reported, and no two collapse onto one another."""
    reported = {match["outcome"] for match in CONTRACT["cases"] + CONTRACT["synthetic"]}
    assert reported == set(OUTCOMES)


# -- the load-bearing property ---------------------------------------------


NOT_SCORED_CASES = [
    case for case in CONTRACT["cases"] if case["outcome"] in NOT_SCORED_OUTCOMES
]


@pytest.mark.parametrize(
    "case", NOT_SCORED_CASES, ids=[case["fixture"] for case in NOT_SCORED_CASES]
)
def test_a_layer_that_cannot_answer_never_scores_either_way(case):
    match = index_of(case["fixture"]).resolve(case["feature_id"])
    assert match.outcome == case["outcome"]
    # Not a pass...
    assert match.passes is False
    assert match.outcome != OUTCOME_FOUND
    # ...and not one of the rejections a consumer acts on either.
    assert match.scored is False
    assert match.outcome not in SCORED_OUTCOMES
    assert match.rows == ()
    assert match.to_dict()["scored"] is False


def test_a_matching_gene_row_in_a_malformed_layer_is_neither_certified_nor_indicted():
    """The sharp case: the row K4 wants is there, and the layer still answers nothing."""
    index = index_of("malformed_layer.gff3")
    assert [row.id for row in index.rows] == ["gene:G1"]  # the match is visibly present
    assert index.problems == [
        "line 4: a feature row holds nine tab-separated fields, this line holds 5"
    ]
    match = index.resolve("gene:G1")
    assert match.outcome == OUTCOME_MALFORMED_LAYER
    assert not match.scored and not match.passes
    # The same target on the same rows, with the defect removed, is a pass:
    # the difference the consumer must carry is the unreadable line, not the ID.
    repaired = index_of("positive.gff3").resolve("gene:G1")
    assert repaired.outcome == OUTCOME_FOUND


def test_absent_and_malformed_are_distinct_outcomes_with_distinct_reasons():
    absent = index_of("absent_layer.gff3")
    malformed = index_of("malformed_layer.gff3")
    assert absent.state == "absent" and malformed.state == "malformed"
    assert absent.resolve("gene:G1").outcome == OUTCOME_ABSENT_LAYER
    assert malformed.resolve("gene:G1").outcome == OUTCOME_MALFORMED_LAYER
    # A reason that names the input, so "I could not see it" is never
    # mistaken for "it is not there".
    assert absent.reason.startswith("the input holds no feature rows")
    assert "nine-field" in malformed.reason


def test_a_layer_of_rows_without_identifiers_is_not_an_absent_layer():
    index = index_of("rows_without_id.gff3")
    assert index.state == "indexed" and index.usable
    assert index.feature_rows == 2 and len(index.rows) == 2
    assert index.id_rows == 0 and index.rows_without_id == 2
    match = index.resolve("gene:G1")
    assert match.outcome == OUTCOME_NOT_FOUND  # answered, not unanswered
    assert match.scored


# -- inputs that are not files ---------------------------------------------


def test_a_path_that_does_not_exist_is_an_absent_layer(tmp_path):
    missing = tmp_path / "never_written.gff3"
    index = build_feature_index(missing)
    assert index.state == "absent"
    assert index.reason.startswith("the feature layer could not be read: cannot open")
    assert "No such file or directory" in index.reason
    match = index.resolve("gene:G1")
    assert match.outcome == OUTCOME_ABSENT_LAYER
    assert not match.scored and not match.passes


def test_an_empty_input_is_an_absent_layer():
    index = build_feature_index(io.BytesIO(b""))
    assert index.state == "absent"
    assert index.reason == "the input holds no feature rows"


def test_a_truncated_gzip_stream_is_an_absent_layer(tmp_path):
    path = tmp_path / "truncated.gff3.gz"
    body = (FIXTURES / "positive.gff3").read_bytes() * 200
    packed = gzip.compress(body)
    assert len(packed) > 100
    path.write_bytes(packed[: len(packed) // 2])
    index = build_feature_index(path)
    assert index.state == "absent"
    assert "could not be read" in index.reason
    match = index.resolve("gene:G1")
    assert match.outcome == OUTCOME_ABSENT_LAYER
    assert not match.scored and not match.passes


def test_a_stream_is_indexed_the_same_way_as_a_file():
    text = (FIXTURES / "positive.gff3").read_bytes()
    from_path = build_feature_index(FIXTURES / "positive.gff3")
    from_stream = build_feature_index(io.BytesIO(text))
    assert [row.to_dict() for row in from_stream.rows] == [
        row.to_dict() for row in from_path.rows
    ]
    assert from_stream.state == from_path.state == "indexed"


def test_gzip_input_is_indexed_like_the_plain_file(tmp_path):
    plain = build_feature_index(FIXTURES / "positive.gff3")
    packed = tmp_path / "positive.gff3.gz"
    packed.write_bytes(gzip.compress((FIXTURES / "positive.gff3").read_bytes()))
    index = build_feature_index(packed)
    assert [row.id for row in index.rows] == [row.id for row in plain.rows]
    assert index.resolve("gene:G1").outcome == OUTCOME_FOUND


def test_the_negative_control_is_only_meaningful_on_a_case_sensitive_filesystem(
    tmp_path,
):
    """APFS folds `layer.gff3` onto `Layer.gff3`; Linux does not.

    A missing-layer test written against a path that the filesystem quietly
    resolves is a control that never runs. On a case-insensitive filesystem this
    skips with a reason instead of passing; on CI (ubuntu, ext4) it runs.
    """
    written = tmp_path / "Layer.gff3"
    written.write_bytes((FIXTURES / "positive.gff3").read_bytes())
    assert build_feature_index(written).usable
    variant = tmp_path / "layer.gff3"
    if variant.exists():
        pytest.skip(
            "this filesystem is case-insensitive, so the differently cased path "
            "opens the same file; the absent-layer control runs on Linux CI"
        )
    index = build_feature_index(variant)
    assert index.state == "absent"
    assert index.resolve("gene:G1").outcome == OUTCOME_ABSENT_LAYER
    # Not-found would be the wrong answer here: the rows exist one character away.
    assert index.resolve("gene:G1").outcome != OUTCOME_NOT_FOUND


# -- K4's predicate --------------------------------------------------------


def test_found_needs_exactly_one_row_and_it_must_be_a_gene_row():
    assert index_of("positive.gff3").resolve("gene:G1").passes
    assert index_of("duplicate_row.gff3").resolve("gene:G1").outcome == (
        OUTCOME_DUPLICATE_ROW
    )
    assert index_of("non_gene_target.gff3").resolve("rna:R1").outcome == (
        OUTCOME_NON_GENE_TARGET
    )


def test_the_gene_row_type_is_a_literal_test_not_an_ontology_lookup():
    assert is_gene_row_type("gene")
    assert is_gene_row_type("SO:0000704")
    assert not is_gene_row_type("Gene")  # column 3 is case sensitive
    assert not is_gene_row_type("protein_coding_gene")  # narrower than gene
    assert not is_gene_row_type("mRNA")
    assert index_of("accession_type.gff3").resolve("gene:G1").outcome == OUTCOME_FOUND


def test_encoded_record_id_matches_literal_row():
    """Decoded on both sides, so the header's spelling cannot decide the verdict.

    The alternative semantics — decode the file side, look the raw `featureId`
    up — is exercised here as the counterfactual: the as-written value of the row
    is `gene:A%2CB`, so a raw lookup of `gene:A,B` would find nothing and report
    `not-found`. This index reports `found`.
    """
    index = index_of("percent_encoded_target.gff3")
    (row,) = index.rows
    assert row.raw_id == "gene:A%2CB"
    assert row.id == "gene:A,B"
    assert row.raw_id != row.id
    assert row.raw_id not in (None, "gene:A,B")  # what a raw lookup would key on
    assert [candidate.raw_id for candidate in index.rows_for("gene:A,B")] == [
        "gene:A%2CB"
    ]
    assert index.resolve("gene:A,B").outcome == OUTCOME_FOUND
    assert index.resolve("gene:A%2CB").outcome == OUTCOME_FOUND


def test_decoding_collapses_two_spellings_of_one_identifier():
    index = index_of("escape_case_collision.gff3")
    assert [row.id for row in index.rows] == ["gene:C;B", "gene:C;B"]
    assert index.resolve("gene:C%3BB").outcome == OUTCOME_DUPLICATE_ROW
    # The file is valid GFF3: one feature may occupy disjunct intervals. This is
    # a verdict about the pointer, not about the annotation.
    assert validate(FIXTURES / "escape_case_collision.gff3").valid


def test_a_malformed_escape_is_left_as_written_on_both_sides():
    index = index_of("invalid_escape.gff3")
    assert index.resolve("gene:bad%2zz").outcome == OUTCOME_FOUND
    assert index.resolve("gene:bad%zz").outcome == OUTCOME_NOT_FOUND


def test_only_one_id_tag_per_row_is_addressable_and_the_first_wins():
    """A finding to report: the JavaScript resolver indexes both tags."""
    index = index_of("repeated_id_tag.gff3")
    assert [row.raw_id for row in index.rows] == ["gene:A"]
    assert index.resolve("gene:A").outcome == OUTCOME_FOUND
    assert index.resolve("gene:B").outcome == OUTCOME_NOT_FOUND


def test_an_empty_id_is_not_an_identifier():
    """A finding to report: the JavaScript resolver indexes an empty identifier."""
    index = index_of("empty_id.gff3")
    assert index.rows[0].raw_id == "" and index.rows[0].id is None
    assert index.resolve("").outcome == OUTCOME_NOT_FOUND


def test_the_index_stops_at_fasta_and_sees_nothing_after_it():
    index = index_of("after_fasta.gff3")
    assert [row.id for row in index.rows] == ["gene:BEFORE"]
    assert index.resolve("gene:AFTER").outcome == OUTCOME_NOT_FOUND
    assert index.resolve("gene:BEFORE").outcome == OUTCOME_FOUND


def test_crlf_cr_and_mixed_line_endings_do_not_change_the_index():
    baseline = [row.to_dict() for row in index_of("positive.gff3").rows]
    for name in ("positive_cr.gff3", "positive_crlf.gff3", "positive_mixed.gff3"):
        index = index_of(name)
        assert index.state == "indexed" and index.usable
        assert index.feature_rows == 2 and len(index.rows) == 2
        assert [row.to_dict() for row in index.rows] == baseline
        assert index.resolve("gene:G1").outcome == OUTCOME_FOUND
        assert index.resolve("rna:R1").outcome == OUTCOME_NON_GENE_TARGET
        assert index.resolve("gene:NOPE").outcome == OUTCOME_NOT_FOUND
        # Loud-vs-quiet distinction (#38 item 2): a file with rows under CR/CRLF/mixed
        # must never be confusable with an absent layer, and validating it must pass G1.
        assert index.resolve("gene:G1").outcome != OUTCOME_ABSENT_LAYER
        report = validate(FIXTURES / name)
        assert report.valid and report.lines == 4


def test_a_non_string_target_is_a_programming_error_not_an_outcome():
    index = index_of("positive.gff3")
    for bad in (None, 7, ["gene:G1"]):
        with pytest.raises(ValueError):
            index.resolve(bad)


def test_the_rows_carry_the_columns_a_consumer_needs():
    index = index_of("positive.gff3")
    gene, rna = index.rows
    assert isinstance(gene, FeatureRow)
    assert (gene.seqid, gene.type, gene.start, gene.end, gene.strand) == (
        "ctg1",
        "gene",
        101,
        900,
        "+",
    )
    assert (gene.id, gene.raw_id, gene.parents, gene.has_id, gene.is_gene) == (
        "gene:G1",
        "gene:G1",
        (),
        True,
        True,
    )
    assert rna.parents == ("gene:G1",) and rna.is_gene is False
    assert set(gene.to_dict()) == set(FEATURE_ROW_FIELDS)
    # Coordinates are carried, not judged: a non-numeric column is None.
    malformed = index_of("malformed_layer.gff3")
    assert malformed.rows[0].start == 101


def test_one_call_helper_matches_the_two_step_form():
    assert (
        resolve_feature_id(FIXTURES / "positive.gff3", "gene:G1").outcome
        == OUTCOME_FOUND
    )


# -- what the index must not touch -----------------------------------------


def test_indexing_changes_no_rule_verdict_and_adds_no_rule_id():
    before = {rule.id: (rule.level, rule.status, rule.title) for rule in CATALOGUE}
    for path in sorted(FIXTURES.glob("*.gff3")):
        build_feature_index(path).resolve("gene:G1")
    after = {
        rule.id: (rule.level, rule.status, rule.title) for rule in load_catalogue()
    }
    assert before == after
    # And a validation run is unaffected by an index run on the same input.
    first = validate(FIXTURES / "malformed_layer.gff3")
    build_feature_index(FIXTURES / "malformed_layer.gff3")
    second = validate(FIXTURES / "malformed_layer.gff3")
    assert [f.to_dict() for f in first.findings] == [
        f.to_dict() for f in second.findings
    ]
    assert first.counts == second.counts


def test_the_index_reads_no_header_and_needs_no_toolkit():
    """No header parsing: `#~` lines are comments, and the toolkit stays out of it."""
    source = (
        "##gff-version 3\n"
        "#~schema: https://example.invalid/should-not-be-read\n"
        "#~annotation: not parsed by this module\n"
        "ctg1\t.\tgene\t1\t10\t.\t+\t.\tID=gene:G1\n"
    )
    index = build_feature_index(io.BytesIO(source.encode("utf-8")))
    assert [row.id for row in index.rows] == ["gene:G1"]
    assert index.feature_rows == 1
    script = (
        "import sys\n"
        "import gff3_validator.features\n"
        "print('bioheaders' in sys.modules)\n"
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == b"False"


def test_the_index_never_writes_to_the_input():
    path = FIXTURES / "positive.gff3"
    before = path.read_bytes()
    build_feature_index(path)
    assert path.read_bytes() == before


# -- cross-implementation agreement (issue #31, acceptance 4; issue #37) ---

# After FAIR-bioHeaders-Tools-JavaScript#21 (8fd467dab0e8) and gff3-validator#38,
# all 24 fixture cases in outcomes.json agree between this index and src/features.js.
KNOWN_JAVASCRIPT_DIVERGENCES = set()

AGREEMENT = (
    Path(__file__).resolve().parents[1] / "scripts" / "feature_index_agreement.py"
)
JAVASCRIPT = Path(os.environ.get("GFF3_VALIDATOR_JS_FEATURES", "")).expanduser()


@pytest.mark.skipif(
    not JAVASCRIPT.is_file(),
    reason="needs a FAIR-bioHeaders-Tools-JavaScript checkout: set "
    "GFF3_VALIDATOR_JS_FEATURES=src/features.js",
)
def test_the_javascript_resolver_agrees_except_for_the_published_findings():
    result = subprocess.run(
        [sys.executable, str(AGREEMENT), "--js", str(JAVASCRIPT), "--json", "--strict"],
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode()
    report = json.loads(result.stdout)
    assert report["js_sha256"], "the JavaScript resolver was not read"
    assert len([row for row in report["rows"] if row["agree"] is not None]) == len(
        CONTRACT["cases"]
    )
    assert set(report["findings"]) == KNOWN_JAVASCRIPT_DIVERGENCES
    # Both never-scored outcomes (malformed-layer and absent-layer) are derived from
    # the two unscoreable layer states on both sides, never a pass or a rejection.
    derived_never_scored = {
        row["outcome"]
        for row in report["rows"]
        if row["js_verdict"] in ("unchecked", "not-checked")
    }
    assert derived_never_scored == set(CONTRACT["never_scored"])
    for row in report["rows"]:
        if row["outcome"] == OUTCOME_MALFORMED_LAYER:
            assert row["js_verdict"] == "unchecked", row
        elif row["outcome"] == OUTCOME_ABSENT_LAYER:
            assert row["js_verdict"] == "not-checked", row
        if row["agree"]:
            # Identical outcomes carry identical scoring on both sides.
            assert (row["js_verdict"] == "pass") == (row["outcome"] == OUTCOME_FOUND)
