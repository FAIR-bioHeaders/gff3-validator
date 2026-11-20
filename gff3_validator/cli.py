"""The gff3-validate command.

Exit codes: 0 no errors, 1 errors found (core errors, or with --profile also
profile errors), 2 usage error or unreadable input.

The feature-index modes (--list-features, --feature-id) inspect the feature
layer below the header and run no validation, so their exit status answers a
different question: 0 found / usable, 1 a scored outcome that is not a pass,
2 no verdict (absent or malformed layer, unreadable input, usage error). See
docs/feature-index.md.
"""

import argparse
import json
import sys

from gff3_validator import __version__, codons
from gff3_validator.engine import DEFAULT_MAX_FINDINGS, Validator
from gff3_validator.features import build_feature_index
from gff3_validator.ontology import OntologyError
from gff3_validator.profiles import ProfileError, list_profiles, load_profile
from gff3_validator.reader import InputError
from gff3_validator.report import to_html, to_json, to_sarif, to_text

FORMATS = {"text": to_text, "json": to_json, "html": to_html, "sarif": to_sarif}
# The inspection modes render the index, not a Report, so they take fewer formats.
INDEX_FORMATS = ("text", "json")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="gff3-validate",
        description="Validate a GFF3 file (pre-release: only the rules marked "
        "implemented in docs/rules.md are checked).",
    )
    parser.add_argument(
        "input", nargs="?", help="GFF3 file, plain or gzip/BGZF; - for stdin"
    )
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
        "--so",
        metavar="OBO",
        help="check types against this so.obo (plain or gzip) instead of the "
        "bundled Sequence Ontology release; every report names the release used",
    )
    parser.add_argument(
        "--profile",
        metavar="ID",
        help="also check a repository or community profile: the id of a shipped "
        "profile (see --list-profiles) or the path of a profile YAML file; "
        "profile findings are reported separately and do not change whether the "
        "file is valid GFF3, but profile errors make the exit status 1",
    )
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="list the shipped profiles and exit",
    )
    parser.add_argument(
        "--max-findings",
        type=int,
        default=DEFAULT_MAX_FINDINGS,
        metavar="N",
        help=f"report at most N findings (default {DEFAULT_MAX_FINDINGS}); "
        "counts stay complete",
    )
    inspection = parser.add_mutually_exclusive_group()
    inspection.add_argument(
        "--list-features",
        action="store_true",
        help="inspect the feature layer (the rows below the header) instead of "
        "validating: enumerate its feature rows and say whether it can be "
        "trusted at all; exit 0 when it can, 2 when it cannot",
    )
    inspection.add_argument(
        "--feature-id",
        metavar="ID",
        help="resolve one featureId against the feature layer, as FHGM K4 "
        "defines it: exactly one local row carrying this ID (percent-decoded on "
        "both sides), and that row a gene row. Runs no validation. Exit 0 when "
        "it resolves, 1 when it does not, 2 when the layer gives no verdict "
        "(absent-layer or malformed-layer)",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.list_profiles:
        for profile in list_profiles():
            print(f"{profile.id}\t{profile.version}\t{profile.name}")
            print(f"\tsource: {profile.source['url']} ({profile.source['license']})")
            print(f"\t{profile.review}")
        return 0
    if args.input is None:
        parser.error("the input file is required")
    inspecting = args.list_features or args.feature_id is not None
    if inspecting:
        unusable = [
            name
            for name, value in (
                ("--genome", args.genome),
                ("--translation-table", args.translation_table),
                ("--so", args.so),
                ("--profile", args.profile),
                ("--require-header", args.require_header),
                ("--no-header", args.no_header),
            )
            if value
        ]
        if unusable:
            parser.error(
                "the feature-index modes read no validation input: "
                + " and ".join(unusable)
                + " would do nothing"
            )
        if args.format not in INDEX_FORMATS:
            parser.error(
                f"--{'list-features' if args.list_features else 'feature-id'} "
                f"formats as {', '.join(INDEX_FORMATS)}, not {args.format}"
            )
        return inspect(args)
    if args.translation_table is not None and not args.genome:
        parser.error("--translation-table needs --genome")
    mode = "require" if args.require_header else "skip" if args.no_header else "auto"
    profile = None
    if args.profile is not None:
        try:
            profile = load_profile(args.profile)
        except ProfileError as error:
            print(f"gff3-validate: --profile: {error}", file=sys.stderr)
            return 2
    try:
        validator = Validator(
            header_mode=mode,
            genome=args.genome,
            max_findings=args.max_findings,
            translation_table=args.translation_table or codons.DEFAULT_TABLE,
            so=args.so,
            profile=profile,
        )
    except OntologyError as error:
        print(f"gff3-validate: --so: {error}", file=sys.stderr)
        return 2
    try:
        report = validator.validate(args.input, name=args.input)
    except InputError as error:
        print(f"gff3-validate: {error}; validation incomplete", file=sys.stderr)
        return 2
    sys.stdout.write(FORMATS[args.format](report))
    return 0 if report.valid and report.compliant is not False else 1


def inspect(args):
    """Run --list-features or --feature-id; see main() for the exit codes."""
    index = build_feature_index(args.input)
    if args.list_features:
        if args.format == "json":
            sys.stdout.write(
                json.dumps(index.to_dict(args.max_findings), indent=2) + "\n"
            )
        else:
            sys.stdout.write(list_features_text(index, args.max_findings))
        return 0 if index.usable else 2
    match = index.resolve(args.feature_id)
    if args.format == "json":
        sys.stdout.write(json.dumps(match.to_dict(), indent=2) + "\n")
    else:
        sys.stdout.write(feature_match_text(match))
    if not match.scored:
        return 2
    return 0 if match.passes else 1


NO_VERDICT = (
    "no verdict: an absent or malformed layer is not scored, so it is never a "
    "pass and never a rejection"
)


def list_features_text(index, max_rows=None):
    """The --list-features text form."""
    lines = [f"{index.source}: feature layer {index.state}"]
    if not index.usable:
        lines.append(f"\t{NO_VERDICT}")
        if index.reason:
            lines.append(f"\treason: {index.reason}")
    lines.append(
        f"feature rows: {index.feature_rows} "
        f"(with ID: {index.id_rows}, without ID: {index.rows_without_id}, "
        f"gene rows: {index.gene_rows})"
    )
    for row in index.rows if max_rows is None else index.rows[:max_rows]:
        lines.append(f"\t{row.describe()}")
    if max_rows is not None and len(index.rows) > max_rows:
        lines.append(f"\t... {len(index.rows) - max_rows} more feature rows")
    for problem in index.problems:
        lines.append(f"\tdefect: {problem}")
    return "".join(line + "\n" for line in lines)


def feature_match_text(match):
    """The --feature-id text form: the outcome, then why."""
    lines = [f"{match.source}: {match.feature_id!r} -> {match.outcome}"]
    lines.append(f"\t{match.message}")
    if not match.scored:
        lines.append(f"\t{NO_VERDICT}")
    return "".join(line + "\n" for line in lines)
