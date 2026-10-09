"""The gff3-validate command.

Exit codes: 0 no errors, 1 errors found, 2 usage error or unreadable input.
"""

import argparse
import sys

from gff3_validator import __version__
from gff3_validator.engine import DEFAULT_MAX_FINDINGS, Validator
from gff3_validator.reader import InputError
from gff3_validator.report import to_json, to_text


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gff3-validate",
        description="Validate a GFF3 file (pre-release: only the rules marked "
        "implemented in docs/rules.md are checked).",
    )
    parser.add_argument("input", help="GFF3 file, plain or gzip/BGZF; - for stdin")
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", help="report format"
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
        help="genome for biology checks (planned; accepted but not used yet)",
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
    args = build_parser().parse_args(argv)
    mode = "require" if args.require_header else "skip" if args.no_header else "auto"
    validator = Validator(
        header_mode=mode, genome=args.genome, max_findings=args.max_findings
    )
    try:
        report = validator.validate(args.input, name=args.input)
    except InputError as error:
        print(f"gff3-validate: {error}; validation incomplete", file=sys.stderr)
        return 2
    output = to_json(report) if args.format == "json" else to_text(report)
    sys.stdout.write(output)
    return 0 if report.valid else 1
