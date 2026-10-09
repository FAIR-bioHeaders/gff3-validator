"""Check the GFF3 conformance suite and score a validator against it.

Standard library only. Without options it checks the suite itself: the files
are what scripts/make_conformance.py generates (byte for byte), and the
manifest is consistent (every file exists, an invalid case has exactly one
error rule, a valid case has none, and in this repository every implemented
catalogue rule has a case).

Then, optionally, it runs a validator over every case and prints a table:

    # gff3-validator's JSON report: compares every finding (rule, level, line)
    python scripts/check_conformance.py --gff3-validate gff3-validate

    # any other tool: compares only the exit status (valid: 0, invalid: not 0)
    python scripts/check_conformance.py --command 'gt gff3validator {file}'

In the generic mode ``{file}`` is replaced by the case file and ``{genome}``,
if present, by the genome FASTA; cases that need a genome are skipped when the
command has no ``{genome}``, and cases with validator options (FHGFF3 header
modes) are always skipped. ``--status spec`` scores only the cases the GFF3
1.26 text settles. The exit status is 1 if any check or case fails.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "conformance"
GENERATOR = ROOT / "scripts" / "make_conformance.py"
CATALOGUE = ROOT / "rules" / "catalogue.yaml"
GENERATED = ("valid", "invalid", "genomes")
OPTIONS = {"require_header": "--require-header", "no_header": "--no-header"}


# -- the suite itself ------------------------------------------------------


def generated_files(directory):
    files = {}
    for name in GENERATED:
        for path in sorted((directory / name).rglob("*")):
            if path.is_file():
                files[path.relative_to(directory).as_posix()] = path.read_bytes()
    manifest = directory / "manifest.json"
    if manifest.is_file():
        files["manifest.json"] = manifest.read_bytes()
    return files


def check_up_to_date(suite):
    """Regenerate the suite in a temporary directory and compare bytes."""
    with tempfile.TemporaryDirectory() as temporary:
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--output", temporary],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            return [f"generator failed: {result.stderr.strip()}"]
        expected = generated_files(Path(temporary))
    actual = generated_files(suite)
    problems = [f"{name}: missing" for name in sorted(expected.keys() - actual.keys())]
    problems += [
        f"{name}: not produced by the generator"
        for name in sorted(actual.keys() - expected.keys())
    ]
    problems += [
        f"{name}: differs from the generator output (rerun make_conformance.py)"
        for name in sorted(expected.keys() & actual.keys())
        if expected[name] != actual[name]
    ]
    return problems


def implemented_rules():
    """Implemented rule ids from rules/catalogue.yaml, or None if unavailable."""
    try:
        import yaml
    except ImportError:
        return None
    if not CATALOGUE.is_file():
        return None
    data = yaml.safe_load(CATALOGUE.read_text(encoding="utf-8"))
    return {rule["id"] for rule in data["rules"] if rule["status"] == "implemented"}


def check_manifest(suite, manifest):
    problems = []
    statuses = set(manifest["statuses"])
    seen = set()
    for case in manifest["cases"]:
        name = case["id"]
        if name in seen:
            problems.append(f"{name}: duplicate id")
        seen.add(name)
        for key in ("file", "genome"):
            if key in case and not (suite / case[key]).is_file():
                problems.append(f"{name}: {key} {case[key]} is missing")
        if case["status"] not in statuses:
            problems.append(f"{name}: unknown status {case['status']}")
        if (case["status"] == "proposed") != ("open_question" in case):
            problems.append(f"{name}: open_question goes with status proposed")
        errors = {x["rule"] for x in case["findings"] if x["level"] == "error"}
        if case["expected"] == "invalid" and errors != {case["rule"]}:
            problems.append(f"{name}: an invalid case has exactly its rule as error")
        if case["expected"] == "valid" and errors:
            problems.append(f"{name}: a valid case has error findings")
        if case["file"].split("/")[0] != case["expected"]:
            problems.append(f"{name}: file is not in {case['expected']}/")
    implemented = implemented_rules()
    if implemented is not None:
        covered = {case["rule"] for case in manifest["cases"]}
        for rule in sorted(implemented - covered):
            problems.append(f"implemented rule {rule} has no case")
    return problems


# -- running validators ----------------------------------------------------


def run(command, timeout):
    try:
        return subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, errors="replace"
        )
    except subprocess.TimeoutExpired:
        return None


def finding_key(finding):
    return (finding["rule"], finding["level"], finding["line"])


def show(findings):
    return ", ".join(
        f"{rule}/{level}@{'-' if line is None else line}"
        for rule, level, line in sorted(findings, key=lambda x: (x[0], x[2] or 0))
    )


def score_json(suite, case, base, timeout):
    """gff3-validator adapter: exit status and every (rule, level, line)."""
    command = list(base) + ["--format", "json"]
    if "genome" in case:
        command += ["--genome", str(suite / case["genome"])]
    for option, value in case.get("options", {}).items():
        if value:
            command.append(OPTIONS[option])
    command.append(str(suite / case["file"]))
    result = run(command, timeout)
    if result is None:
        return "fail", "?", "timed out"
    if result.returncode not in (0, 1):
        return "fail", "?", f"exit {result.returncode}: {result.stderr.strip()[:200]}"
    got = "valid" if result.returncode == 0 else "invalid"
    try:
        report = json.loads(result.stdout)
    except ValueError:
        return "fail", got, "output is not JSON"
    expected = Counter(finding_key(x) for x in case["findings"])
    actual = Counter(finding_key(x) for x in report["findings"])
    details = []
    if got != case["expected"]:
        details.append(f"exit {result.returncode}")
    if actual != expected:
        missing, extra = expected - actual, actual - expected
        if missing:
            details.append("missing " + show(missing.elements()))
        if extra:
            details.append("unexpected " + show(extra.elements()))
    return ("fail" if details else "pass"), got, "; ".join(details)


def score_exit(suite, case, template, timeout):
    """Generic adapter: only the exit status (0 valid, anything else invalid)."""
    if case.get("options"):
        return "skip", "", "needs validator options"
    if "genome" in case and "{genome}" not in template:
        return "skip", "", "needs a genome ({genome} not in the command)"
    values = {"file": str(suite / case["file"])}
    if "genome" in case:
        values["genome"] = str(suite / case["genome"])
    command = [part.format(**values) for part in shlex.split(template)]
    if "genome" not in case:
        command = [part for part in command if "{genome}" not in part]
    result = run(command, timeout)
    if result is None:
        return "fail", "?", "timed out"
    got = "valid" if result.returncode == 0 else "invalid"
    detail = ""
    if got == "valid" and case["expected"] == "invalid":
        detail = "accepted (exit 0)"
    elif got != case["expected"]:
        lines = (result.stderr + result.stdout).strip().splitlines()
        errors = [line for line in lines if "error" in line.lower()]
        detail = (errors or lines or [f"exit {result.returncode}"])[0]
        detail = detail.replace(str(suite / case["file"]), "FILE")
        detail = detail.replace(command[0], Path(command[0]).name)[:160]
    return ("pass" if got == case["expected"] else "fail"), got, detail


def table(rows, markdown):
    header = ("case", "status", "expected", "got", "result", "detail")
    if markdown:
        lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
        for row in rows:
            cells = [str(cell).replace("|", "\\|") for cell in row]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)
    widths = [max(len(str(row[i])) for row in rows + [header]) for i in range(5)]
    lines = []
    for row in [header] + rows:
        cells = [str(cell).ljust(widths[i]) for i, cell in enumerate(row[:5])]
        lines.append("  ".join(cells + [str(row[5])]).rstrip())
    return "\n".join(lines)


def summary(rows):
    by_status = {}
    for row in rows:
        by_status.setdefault(row[1], Counter())[row[4]] += 1
    total = Counter(row[4] for row in rows)
    parts = [
        f"{status}: {counts['pass']}/{counts['pass'] + counts['fail']} passed"
        + (f", {counts['skip']} skipped" if counts["skip"] else "")
        for status, counts in sorted(by_status.items())
    ]
    scored = total["pass"] + total["fail"]
    return (
        f"{total['pass']}/{scored} cases passed, {total['fail']} failed, "
        f"{total['skip']} skipped ({'; '.join(parts)})"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Check the GFF3 conformance suite and score a validator."
    )
    parser.add_argument("--suite", default=str(SUITE), help="conformance directory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--gff3-validate",
        metavar="COMMAND",
        help="gff3-validator command (for example 'gff3-validate' or "
        "'poetry run gff3-validate'); compares the JSON findings",
    )
    mode.add_argument(
        "--command",
        metavar="TEMPLATE",
        help="any validator, with {file} (and optionally {genome}); compares "
        "the exit status only",
    )
    parser.add_argument(
        "--status",
        action="append",
        help="score only cases with this status (repeatable): spec, proposed, "
        "extension:fhgff3, extension:insdc",
    )
    parser.add_argument(
        "--skip-compressed", action="store_true", help="skip gzip and BGZF cases"
    )
    parser.add_argument(
        "--no-suite-check",
        action="store_true",
        help="do not regenerate the suite or check the manifest",
    )
    parser.add_argument("--markdown", action="store_true", help="Markdown table")
    parser.add_argument("--timeout", type=float, default=60, help="seconds per case")
    parser.add_argument(
        "--jobs",
        type=int,
        default=os.cpu_count() or 1,
        help="cases run in parallel (default: number of CPUs)",
    )
    args = parser.parse_args(argv)

    suite = Path(args.suite)
    manifest = json.loads((suite / "manifest.json").read_text(encoding="utf-8"))
    failed = False
    if not args.no_suite_check:
        problems = []
        if suite.resolve() == SUITE.resolve():
            problems += check_up_to_date(suite)
        problems += check_manifest(suite, manifest)
        for problem in problems:
            print(f"suite: {problem}", file=sys.stderr)
        cases = manifest["cases"]
        print(
            f"suite: {len(cases)} cases, {len(manifest['rules'])} rules"
            + (": OK" if not problems else f": {len(problems)} problems"),
            file=sys.stderr,
        )
        failed = bool(problems)

    if not (args.gff3_validate or args.command):
        return 1 if failed else 0
    cases = [
        case
        for case in manifest["cases"]
        if not args.status or case["status"] in args.status
    ]

    def score(case):
        if args.skip_compressed and case.get("compression"):
            return "skip", "", "compressed"
        if args.gff3_validate:
            base = shlex.split(args.gff3_validate)
            return score_json(suite, case, base, args.timeout)
        return score_exit(suite, case, args.command, args.timeout)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        results = list(pool.map(score, cases))
    rows = [
        (case["id"], case["status"], case["expected"], got, outcome, detail)
        for case, (outcome, got, detail) in zip(cases, results)
    ]
    print(table(rows, args.markdown))
    print()
    print(summary(rows))
    if any(row[4] == "fail" for row in rows):
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.exit(main())
