"""Opt-in performance test on a large synthetic GFF3 file.

Run with ``GFF3_VALIDATOR_PERFORMANCE_TEST=1 poetry run pytest -s
tests/test_performance.py``. ``GFF3_VALIDATOR_PERFORMANCE_LINES`` sets the
approximate number of feature lines (default 2,000,000). The file is written
to pytest's temporary directory and deleted afterwards. Runtime and peak
resident memory of a separate Python process running the validator are
printed.
"""

import os
import subprocess
import sys

import pytest

ENABLED = os.environ.get("GFF3_VALIDATOR_PERFORMANCE_TEST") == "1"
LINES = int(os.environ.get("GFF3_VALIDATOR_PERFORMANCE_LINES", "2000000"))
# Per gene: gene, two mRNAs, each with five exons and four CDS segments.
LINES_PER_GENE = 1 + 2 * (1 + 5 + 4)


def write_synthetic(path, genes):
    """Write ``genes`` canonical genes on 25 sequences; every feature has an ID."""
    per_sequence = -(-genes // 25)
    with open(path, "w", encoding="utf-8") as out:
        out.write("##gff-version 3\n")
        for chromosome in range(25):
            out.write(f"##sequence-region chr{chromosome} 1 {per_sequence * 10000}\n")
        for number in range(genes):
            seqid = f"chr{number // per_sequence}"
            base = (number % per_sequence) * 10000
            gene = f"gene{number:07d}"
            rows = [
                (seqid, "gene", base + 1, base + 9000, ".", f"ID={gene};Name=G{number}")
            ]
            for isoform in (1, 2):
                mrna = f"{gene}.t{isoform}"
                rows.append(
                    (
                        seqid,
                        "mRNA",
                        base + 1,
                        base + 9000,
                        ".",
                        f"ID={mrna};Parent={gene}",
                    )
                )
                for exon in range(5):
                    start = base + 1 + exon * 1800
                    rows.append(
                        (
                            seqid,
                            "exon",
                            start,
                            start + 899,
                            ".",
                            f"ID={mrna}.e{exon};Parent={mrna}",
                        )
                    )
                for cds in range(4):
                    start = base + 1 + cds * 1800 + 100
                    rows.append(
                        (
                            seqid,
                            "CDS",
                            start,
                            start + 799,
                            "0",
                            f"ID={mrna}.cds;Parent={mrna}",
                        )
                    )
            for seqid_, type_, start, end, phase, attributes in rows:
                out.write(
                    f"{seqid_}\tsynthetic\t{type_}\t{start}\t{end}\t.\t+\t{phase}\t"
                    f"{attributes}\n"
                )
            out.write("###\n")


def measure(path, genome=None):
    """Validate ``path`` in a new process; return its numbers."""
    code = (
        "import resource, sys, time\n"
        "from gff3_validator import validate\n"
        "start = time.perf_counter()\n"
        "report = validate(sys.argv[1], genome=sys.argv[2] or None)\n"
        "elapsed = time.perf_counter() - start\n"
        "peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "print(report.lines, report.counts['error'], len(report.findings), "
        "f'{elapsed:.1f}', peak)\n"
        "for finding in report.findings[:5]:\n"
        "    print(finding.rule, finding.line, finding.message, file=sys.stderr)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(path), str(genome or "")],
        capture_output=True,
        text=True,
        check=True,
    )
    lines, errors, findings, elapsed, peak = result.stdout.split()
    peak_mib = int(peak) / 1024  # ru_maxrss is in KiB on Linux
    if sys.platform == "darwin":
        peak_mib /= 1024  # bytes on macOS
    return int(lines), int(errors), int(findings), elapsed, peak_mib, result.stderr


@pytest.mark.skipif(not ENABLED, reason="set GFF3_VALIDATOR_PERFORMANCE_TEST=1")
def test_large_file_runtime_and_memory(tmp_path):
    path = tmp_path / "synthetic.gff3"
    genes = max(1, LINES // LINES_PER_GENE)
    write_synthetic(path, genes)
    size = path.stat().st_size
    try:
        lines, errors, findings, elapsed, peak_mib, _ = measure(path)
    finally:
        path.unlink()
    print(
        f"\n{lines:,} lines ({size / 2**20:.0f} MiB, {genes:,} genes, "
        f"{genes * LINES_PER_GENE:,} features): {elapsed} s, peak RSS "
        f"{peak_mib:.0f} MiB; {errors} errors"
    )
    assert errors == 0 and findings == 0


# -- with --genome -----------------------------------------------------------

GENOME_LINES = int(os.environ.get("GFF3_VALIDATOR_PERFORMANCE_GENOME_LINES", "500000"))
GENE_SPAN = 10000
BACKGROUND = b"GCCGGCGGCCCG"  # no A or T: no stop codon in any frame, either strand
COMPLEMENT = bytes.maketrans(b"ACGT", b"TGCA")


def gene_layout():
    """Exons and CDS segments of one plus-strand gene, relative to its start.

    Four CDS segments of 800, 800, 800 and 798 bases (phases 0, 1, 2, 0)
    make 1066 codons, starting with ATG and ending with TAA.
    """
    exons = [(1 + k * 1800, 900 + k * 1800) for k in range(5)]
    cds = [(101 + k * 1800, 900 + k * 1800) for k in range(4)]
    cds[-1] = (cds[-1][0], cds[-1][1] - 2)
    phases, phase = [], 0
    for start, end in cds:
        phases.append(phase)
        phase = (3 - ((end - start + 1 - phase) % 3)) % 3
    sequence = bytearray((BACKGROUND * (GENE_SPAN // len(BACKGROUND) + 1))[:GENE_SPAN])
    sequence[cds[0][0] - 1 : cds[0][0] + 2] = b"ATG"
    sequence[cds[-1][1] - 3 : cds[-1][1]] = b"TAA"
    return exons, list(zip(cds, phases)), bytes(sequence)


def write_synthetic_with_genome(gff3_path, fasta_path, genes):
    """Canonical genes, alternating strands, on 25 sequences, and their genome.

    Every CDS translates without a problem, so a run has no findings.
    """
    exons, cds, plus = gene_layout()
    minus = plus.translate(COMPLEMENT)[::-1]

    def place(start, end, strand, base):
        if strand == "+":
            return base + start, base + end
        return base + GENE_SPAN + 1 - end, base + GENE_SPAN + 1 - start

    per_sequence = -(-genes // 25)
    with open(gff3_path, "w", encoding="utf-8") as out, open(fasta_path, "wb") as fa:
        out.write("##gff-version 3\n")
        for chromosome in range(25):
            count = max(0, min(per_sequence, genes - chromosome * per_sequence))
            sequence = b"".join(plus if n % 2 == 0 else minus for n in range(count))
            sequence = sequence or BACKGROUND
            out.write(f"##sequence-region chr{chromosome} 1 {len(sequence)}\n")
            fa.write(f">chr{chromosome}\n".encode())
            for offset in range(0, len(sequence), 60 * 100000):
                piece = sequence[offset : offset + 60 * 100000]
                fa.write(
                    b"\n".join(piece[i : i + 60] for i in range(0, len(piece), 60))
                    + b"\n"
                )
        for number in range(genes):
            seqid = f"chr{number // per_sequence}"
            base = (number % per_sequence) * GENE_SPAN
            strand = "+" if (number % per_sequence) % 2 == 0 else "-"
            gene = f"gene{number:07d}"
            rows = [("gene", 1, GENE_SPAN, ".", f"ID={gene}")]
            for isoform in (1, 2):
                mrna = f"{gene}.t{isoform}"
                rows.append(("mRNA", 1, GENE_SPAN, ".", f"ID={mrna};Parent={gene}"))
                for k, (start, end) in enumerate(exons):
                    rows.append(
                        ("exon", start, end, ".", f"ID={mrna}.e{k};Parent={mrna}")
                    )
                for (start, end), phase in cds:
                    rows.append(
                        ("CDS", start, end, phase, f"ID={mrna}.cds;Parent={mrna}")
                    )
            for type_, start, end, phase, attributes in rows:
                start, end = place(start, end, strand, base)
                out.write(
                    f"{seqid}\tsynthetic\t{type_}\t{start}\t{end}\t.\t{strand}\t"
                    f"{phase}\t{attributes}\n"
                )
            out.write("###\n")


@pytest.mark.skipif(not ENABLED, reason="set GFF3_VALIDATOR_PERFORMANCE_TEST=1")
def test_large_file_with_genome_runtime_and_memory(tmp_path):
    """``GFF3_VALIDATOR_PERFORMANCE_GENOME_LINES`` sets the size (default
    500,000 lines; the genome has 10 kb per gene, about 240 MB by default)."""
    path = tmp_path / "synthetic.gff3"
    fasta = tmp_path / "synthetic.fa"
    genes = max(1, GENOME_LINES // LINES_PER_GENE)
    try:
        write_synthetic_with_genome(path, fasta, genes)
        sizes = path.stat().st_size, fasta.stat().st_size
        lines, errors, findings, elapsed, peak_mib, stderr = measure(path, fasta)
    finally:
        for item in (path, fasta):
            if item.exists():
                item.unlink()
    print(
        f"\n{lines:,} lines ({sizes[0] / 2**20:.0f} MiB, {genes:,} genes, "
        f"{2 * genes:,} CDS) with a {sizes[1] / 2**20:.0f} MiB genome: "
        f"{elapsed} s, peak RSS {peak_mib:.0f} MiB; {errors} errors"
    )
    assert errors == 0 and findings == 0, stderr
