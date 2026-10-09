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


@pytest.mark.skipif(not ENABLED, reason="set GFF3_VALIDATOR_PERFORMANCE_TEST=1")
def test_large_file_runtime_and_memory(tmp_path):
    path = tmp_path / "synthetic.gff3"
    genes = max(1, LINES // LINES_PER_GENE)
    write_synthetic(path, genes)
    size = path.stat().st_size
    code = (
        "import resource, sys, time\n"
        "from gff3_validator import validate\n"
        "start = time.perf_counter()\n"
        "report = validate(sys.argv[1])\n"
        "elapsed = time.perf_counter() - start\n"
        "peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
        "print(report.lines, report.counts['error'], len(report.findings), "
        "f'{elapsed:.1f}', peak)\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", code, str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        path.unlink()
    lines, errors, findings, elapsed, peak = result.stdout.split()
    peak_mib = int(peak) / 1024  # ru_maxrss is in KiB on Linux
    if sys.platform == "darwin":
        peak_mib /= 1024  # bytes on macOS
    print(
        f"\n{int(lines):,} lines ({size / 2**20:.0f} MiB, {genes:,} genes, "
        f"{genes * LINES_PER_GENE:,} features): {elapsed} s, peak RSS "
        f"{peak_mib:.0f} MiB; {errors} errors"
    )
    assert int(errors) == 0 and int(findings) == 0
