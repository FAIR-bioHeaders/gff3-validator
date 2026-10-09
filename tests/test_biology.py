"""Biology rules (BIO-001 to BIO-011), the genome index and translation tables."""

import gzip
import io
import random
import subprocess
import sys
from pathlib import Path

import pytest

from gff3_validator import GenomeError, Validator
from gff3_validator import genome as genome_module
from gff3_validator import validate
from gff3_validator.codons import CODONS, TABLES, table
from gff3_validator.genome import Genome, reverse_complement

FIXTURES = Path(__file__).parent / "fixtures"
BIOLOGY = FIXTURES / "biology"
GENOME = BIOLOGY / "genome.fa"
VALID = BIOLOGY / "valid_genes.gff3"
CANONICAL = FIXTURES / "valid" / "canonical_gene.gff3"


def rules(report):
    return sorted(finding.rule for finding in report.findings)


def fasta(records, width=60, ending=b"\n", header=b""):
    out = header
    for name, sequence in records:
        out += b">" + name + ending
        for start in range(0, len(sequence), width):
            out += sequence[start : start + width] + ending
    return out


def gff3(*rows):
    lines = ["##gff-version 3"] + ["\t".join(row.split()) for row in rows]
    return io.BytesIO(("\n".join(lines) + "\n").encode())


# -- genome FASTA ------------------------------------------------------------


@pytest.mark.parametrize("name", ["genome.fa", "genome.fa.gz", "genome_fhr.fa"])
def test_genome_forms_give_the_same_index_and_report(name):
    with Genome(BIOLOGY / name) as genome:
        assert {key: rec.length for key, rec in genome.records.items()} == {
            "chr1": 300,
            "chr2": 120,
            "chr3": 60,
        }
        assert genome.fetch("chr1", 10, 13) == b"ATG"
        assert genome.spooled == name.endswith(".gz")
    report = validate(VALID, genome=BIOLOGY / name)
    assert rules(report) == []
    assert report.valid


@pytest.mark.parametrize("ending", [b"\n", b"\r\n"])
@pytest.mark.parametrize("compress", [False, True])
def test_fetch_matches_the_sequence(tmp_path, monkeypatch, ending, compress):
    monkeypatch.setattr(genome_module, "BLOCK", 17)
    monkeypatch.setattr(genome_module, "CACHE_BLOCKS", 3)
    generator = random.Random(7)
    records = [
        (f"s{n}".encode(), bytes(generator.choice(b"acgtN") for _ in range(size)))
        for n, size in enumerate((1, 59, 60, 61, 1000))
    ]
    data = fasta(records, width=13, ending=ending)
    path = tmp_path / "g.fa"
    path.write_bytes(gzip.compress(data) if compress else data)
    with Genome(path) as genome:
        for name, sequence in records:
            name = name.decode()
            assert genome.length(name) == len(sequence)
            for _ in range(40):
                start = generator.randrange(len(sequence) + 1)
                end = generator.randrange(start, len(sequence) + 1)
                assert genome.fetch(name, start, end) == sequence[start:end].upper()


def test_genome_with_unwrapped_long_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(genome_module, "LINE_PIECE", 7)
    sequence = b"ACGT" * 50
    path = tmp_path / "g.fa"
    path.write_bytes(b";~ header line longer than seven bytes\n>one\n" + sequence)
    with Genome(path) as genome:
        assert genome.length("one") == 200
        assert genome.fetch("one", 190, 200) == sequence[190:]


def test_reverse_complement():
    assert reverse_complement(b"ATGCNRY") == b"RYNGCAT"


@pytest.mark.parametrize(
    "data, message",
    [
        (b">a\nACGT\nACGTA\n", "more than the 4"),
        (b">a\nACGT\nAC\nACGT\n", "continues after a shorter or blank line"),
        (b">a\nACGT\n\nACGT\n", "continues after a shorter or blank line"),
        (b">a\nACGT\n>a\nACGT\n", 'duplicate sequence name "a"'),
        (b"ACGT\n>a\nACGT\n", "before the first '>'"),
        (b">\nACGT\n", "no sequence name"),
        (b">a\nAC GT\n", "character"),
        (b">a\nACGT\n;note\n", "only before the first record"),
        (b">a\nACGT\r\nACGT\nAC\n", "line endings change"),
        (b";only a comment\n", "no FASTA records"),
        (b"", "no FASTA records"),
    ],
)
def test_malformed_genome_is_an_input_error(tmp_path, data, message):
    path = tmp_path / "g.fa"
    path.write_bytes(data)
    with pytest.raises(GenomeError, match=message):
        validate(VALID, genome=path)


def test_genome_from_stdin_or_missing_or_truncated(tmp_path):
    with pytest.raises(GenomeError, match="standard input"):
        Genome("-")
    with pytest.raises(GenomeError, match="cannot open"):
        Genome(tmp_path / "missing.fa")
    path = tmp_path / "g.fa.gz"
    path.write_bytes(gzip.compress(GENOME.read_bytes())[:-20])
    with pytest.raises(GenomeError, match="truncated"):
        Genome(path)


def test_trailing_blank_lines_are_accepted(tmp_path):
    path = tmp_path / "g.fa"
    path.write_bytes(b">a\nACGT\nAC\n\n>b\nAAA\n\n")
    with Genome(path) as genome:
        assert genome.length("a") == 6
        assert genome.fetch("b", 0, 3) == b"AAA"


# -- translation tables ------------------------------------------------------


@pytest.mark.parametrize("number", sorted(TABLES))
def test_no_stop_pattern_agrees_with_the_table(number):
    code = table(number)
    for codon in CODONS:
        data = codon.encode()
        is_stop = code.no_stop.match(data).end() == 0
        assert is_stop == (data in code.stops), (number, codon)
    assert code.no_stop.match(b"NNNTNA").end() == 6


def test_table_contents():
    assert table(1).stops == {b"TAA", b"TAG", b"TGA"}
    assert table(1).starts == {b"TTG", b"CTG", b"ATG"}
    assert table(2).stops == {b"TAA", b"TAG", b"AGA", b"AGG"}
    assert b"TGA" not in table(4).stops
    assert table(11).starts >= {b"GTG", b"ATT", b"ATG"}
    for number in (27, 28, 31):
        assert number not in TABLES


def test_unknown_table_is_rejected():
    with pytest.raises(ValueError, match="not available"):
        Validator(translation_table=7)


def test_translation_table_changes_start_and_stop(tmp_path):
    # CDS 1..12: GTG CCC TGA AGA; table 1: no start, stop TGA inside.
    path = tmp_path / "g.fa"
    path.write_bytes(fasta([(b"c", b"GTGCCCTGAAGA")]))

    def run(number):
        report = validate(
            gff3("c . CDS 1 12 . + 0 ID=x"), genome=path, translation_table=number
        )
        return rules(report)

    assert run(1) == ["BIO-006", "BIO-007", "BIO-008"]
    assert run(11) == ["BIO-007", "BIO-008"]  # GTG is a start in table 11
    assert run(4) == ["BIO-007"]  # GTG starts, TGA is W, AGA is R
    assert run(2) == []  # GTG starts, TGA is W, AGA is a stop


# -- rules -----------------------------------------------------------------


def test_minus_strand_internal_stop_and_phase(tmp_path):
    # Coding strand ATG CCC TAA CCC TAA, written reverse complemented.
    coding = b"ATGCCCTAACCCTAA"
    path = tmp_path / "g.fa"
    path.write_bytes(fasta([(b"c", b"GG" + reverse_complement(coding) + b"GG")]))
    report = validate(
        gff3("c . CDS 3 9 . - 1 ID=x", "c . CDS 10 17 . - 0 ID=x"), genome=path
    )
    assert rules(report) == ["BIO-008"]
    (finding,) = report.findings
    assert "TAA at c:11 (codon 3 of 5)" in finding.message


def test_recoded_codon_exemptions_are_needed():
    text = VALID.read_text()
    without = [
        line
        for line in text.splitlines()
        if "selenocysteine" not in line and "recoded_codon" not in line
    ]
    data = "\n".join(without).replace("transl_except", "remark") + "\n"
    report = validate(io.BytesIO(data.encode()), genome=GENOME)
    assert rules(report) == ["BIO-008", "BIO-008", "BIO-008"]


def test_unknown_seqids_and_skipped_checks_reported_as_skipped():
    report = validate(gff3("chrZ . CDS 1 30 . + 0 ID=x"), genome=GENOME)
    assert rules(report) == ["BIO-001", "BIO-011"]
    (biology,) = [item for item in report.skipped if item["layer"] == "biology"]
    assert "1 CDS on seqids not in the genome" in biology["reason"]


def test_without_genome_biology_is_not_checked():
    report = validate(BIOLOGY / "bio008_internal_stop.gff3")
    assert rules(report) == []
    (biology,) = [item for item in report.skipped if item["layer"] == "biology"]
    assert "needs --genome" in biology["reason"]


def test_chains_are_judged_at_resolution_points():
    rows = [
        "chr1 . CDS 171 200 . + 0 ID=a",
        "###",
        "chr1 . CDS 171 200 . + 0 ID=b",
    ]
    report = validate(gff3(*rows), genome=GENOME)
    assert [(f.rule, f.line) for f in report.findings] == [
        ("BIO-008", 2),
        ("BIO-008", 4),
    ]


def canonical_genome(path, stop_at=None):
    """A genome on which the GFF3 specification's canonical gene translates.

    The background has no T, so no codon in any frame is a stop; ATG starts
    the three translation starts (1201, 3301, 3391) and TAA ends the CDS that
    end on a complete codon (cds00003 and cds00004, at 7598..7600).
    """
    length = 1497228
    sequence = bytearray((b"GCCAGA" * (length // 6 + 1))[:length])
    for position, codon in ((1201, b"ATGC"), (3301, b"ATGC"), (3391, b"ATGC")):
        sequence[position - 1 : position + 3] = codon
    sequence[7597:7600] = b"TAA"
    if stop_at:
        sequence[stop_at - 1 : stop_at + 2] = b"TAG"
    path.write_bytes(fasta([(b"ctg123", bytes(sequence))]))


def test_canonical_gene_translates(tmp_path):
    path = tmp_path / "ctg123.fa"
    canonical_genome(path)
    report = validate(CANONICAL, genome=path)
    # The specification's cds00001 and cds00002 end one base after a codon
    # boundary (2305 and 1402 coding bases), which BIO-009 notes; their stop
    # codon is therefore not checked. Everything else is consistent.
    assert [(f.rule, f.line) for f in report.findings] == [
        ("BIO-009", 16),
        ("BIO-009", 19),
    ]
    assert report.valid


def test_canonical_gene_with_an_internal_stop(tmp_path):
    path = tmp_path / "ctg123.fa"
    canonical_genome(path, stop_at=5000)  # frame 0 of cds00001 and cds00002
    report = validate(CANONICAL, genome=path)
    assert rules(report) == ["BIO-008", "BIO-008", "BIO-009", "BIO-009"]


# -- command line ----------------------------------------------------------


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "gff3_validator", *map(str, args)],
        capture_output=True,
    )


def test_cli_genome_and_table_options(tmp_path):
    result = run("--genome", GENOME, BIOLOGY / "bio008_internal_stop.gff3")
    assert result.returncode == 0
    assert b"BIO-008" in result.stdout
    result = run("--genome", GENOME, "--translation-table", "11", VALID)
    assert result.returncode == 0, result.stderr
    result = run("--translation-table", "11", VALID)
    assert result.returncode == 2
    assert b"--translation-table needs --genome" in result.stderr
    result = run("--genome", GENOME, "--translation-table", "7", VALID)
    assert result.returncode == 2
    bad = tmp_path / "bad.fa"
    bad.write_bytes(b">a\nACGT\n>a\nACGT\n")
    result = run("--genome", bad, VALID)
    assert result.returncode == 2
    assert b"duplicate sequence name" in result.stderr
    assert b"validation incomplete" in result.stderr
    result = run("--genome", "-", VALID)
    assert result.returncode == 2
    assert b"standard input" in result.stderr
