"""Run gff3-validate (in process) for the cases of the web parity test.

Usage: python web/test/cli_reports.py CASES.json > RESULTS.json

CASES.json is a list of {"id", "args"} where args are command-line
arguments ending with the input path. For each case the result holds the exit
code and the json, sarif and html outputs, keyed by id.
"""

import contextlib
import io
import json
import sys

from gff3_validator.cli import main


def run(args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = main(args)
        except SystemExit as exit:
            code = exit.code
    return code, out.getvalue()


def cli_reports(cases):
    results = {}
    for case in cases:
        entry = {}
        for fmt in ("json", "sarif", "html"):
            code, output = run(["--format", fmt] + case["args"])
            entry["exit"] = code
            entry[fmt] = output
        results[case["id"]] = entry
    return results


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as handle:
        json.dump(cli_reports(json.load(handle)), sys.stdout)
