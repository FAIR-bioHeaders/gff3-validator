"""The gff3-validate command.

Exit codes: 0 no errors, 1 errors found, 2 usage error or unreadable input.
"""

import argparse
import sys

from gff3_validator import __version__, codons
from gff3_validator.engine import DEFAULT_MAX_FINDINGS, Validator
from gff3_validator.reader import InputError
from gff3_validator.report import to_html, to_json, to_sarif, to_text

FORMATS = {"text": to_text, "json": to_json, "html": to_html, "sarif": to_sarif}


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gff3-validate",
        description="Validate a GFF3 file (pre-release: only the rules marked "
        "implemented in docs/rules.md are checked).",
    )
    parser.add_argument("input", help="GFF3 file, plain or gzip/BGZF; - for stdin")
    parser.add_argument(
        "--format",
        choices=tuple(FORMATS),
        default="text",
        help="report format: text, JSON, a self-contained HTML page or SARIF 2.1.0",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--require-header",
        action="store_true",
        help="require a FAIR-bioHeaders (FHGFF3) header",
    )
    group.add_argument(
        "--no-header", action="store_true", help="skip FAIR-bioHeaders header checks"
    )
    parser.add_argument(
        "--genome",
        metavar="FASTA",
        help="genome FASTA (plain or gzip/BGZF, not stdin) for the biology "
        "checks; gzip input is decompressed to a temporary file in TMPDIR",
    )
    parser.add_argument(
        "--translation-table",
        type=int,
        metavar="N",
        choices=sorted(codons.TABLES),
        help=f"NCBI translation table for start, stop and internal stop codons "
        f"(default {codons.DEFAULT_TABLE}; use 11 for bacteria, archaea and "
        f"plastids); one of {', '.join(map(str, sorted(codons.TABLES)))}",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=DEFAULT_MAX_FINDINGS,
        metavar="N",
        help=f"report at most N findings (default {DEFAULT_MAX_FINDINGS}); "
        "counts stay complete",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.translation_table is not None and not args.genome:
        parser.error("--translation-table needs --genome")
    mode = "require" if args.require_header else "skip" if args.no_header else "auto"
    validator = Validator(
        header_mode=mode,
        genome=args.genome,
        max_findings=args.max_findings,
        translation_table=args.translation_table or codons.DEFAULT_TABLE,
    )
    try:
        report = validator.validate(args.input, name=args.input)
    except InputError as error:
        print(f"gff3-validate: {error}; validation incomplete", file=sys.stderr)
        return 2
    sys.stdout.write(FORMATS[args.format](report))
    return 0 if report.valid else 1
