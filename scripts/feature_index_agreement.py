r"""Run this feature index and the JavaScript resolver over the same fixtures.

Issue #31 acceptance 4: the agreement table that
`FAIR-bioHeaders-Tools-JavaScript` and `FAIR-bioHeaders-Tools-Julia` can cite,
produced from `tests/fixtures/features/outcomes.json` (the contract) and the
fixtures beside it.

    # both sides
    python scripts/feature_index_agreement.py \
        --js ../FAIR-bioHeaders-Tools-JavaScript/src/features.js

    # this side only (what CI can do without a sibling checkout)
    python scripts/feature_index_agreement.py

    # markdown, for docs/feature-index.md
    python scripts/feature_index_agreement.py --js PATH --markdown

    # exit 1 if the two sides disagree
    python scripts/feature_index_agreement.py --js PATH --strict

The JavaScript column is `indexGff3FeatureRows` and `isGeneRowType` read from the
file you point at — its SHA-256 is printed, so the table carries provenance —
plus the K4 predicate of `src/fhgm.js`: the block that turns a resolved layer
into `pass` / `reject` / `unchecked`. That predicate is transcribed here rather
than imported because `src/fhgm.js` pulls in `ajv` and a header to import at all;
read the two side by side when reviewing (`src/fhgm.js`, the `if (recordErrors
.length === 0)` block, at the commit whose id the table records).

A disagreement is a finding to report, not something to fix by editing one side.
Nothing here writes to the sibling checkout, and no network access is used.
"""

import argparse
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gff3_validator.features import build_feature_index  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "features"
CONTRACT = json.loads((FIXTURES / "outcomes.json").read_text(encoding="utf-8"))

# The outcome -> verdict words each implementation reports for it. In
# FAIR-bioHeaders-Tools-JavaScript (after PR #21, commit 8fd467dab0e8),
# indexGff3FeatureRows counts nine-field feature rows (featureRows) independently
# of ID-carrying rows, and src/fhgm.js maps a readable, trustworthy layer with
# featureRows === 0 to state: 'none' -> "not-checked" (absent-layer), while
# rows_without_id (featureRows > 0, rows.length === 0) scores as "reject"
# (not-found). See docs/feature-index.md, "Cross-implementation agreement".
JS_VERDICT = {
    "found": "pass",
    "not-found": "reject",
    "duplicate-row": "reject",
    "non-gene-target": "reject",
    "malformed-layer": "unchecked",
    "absent-layer": "not-checked",
}

JS_DRIVER = """
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const features = await import(pathToFileURL(process.argv[2]).href);
const verdicts = __VERDICTS__;
const cases = JSON.parse(readFileSync(0, 'utf8'));

// decodeFeatureId, as src/fhgm.js writes it: a malformed escape stays as written.
function decodeFeatureId(value) {
  try {
    return decodeURIComponent(value.replace(/\\+/g, '%2B'));
  } catch {
    return value;
  }
}

const out = [];
for (const one of cases) {
  const bytes = new Uint8Array(readFileSync(one.fixture));
  const indexed = features.indexGff3FeatureRows(bytes);
  let outcome;
  if (indexed.problems.length > 0) {
    outcome = 'malformed-layer';
  } else if (indexed.featureRows === 0) {
    outcome = 'absent-layer';
  } else {
    const wanted = decodeFeatureId(one.feature_id);
    const types = indexed.rows
      .filter((row) => decodeFeatureId(row.id) === wanted)
      .map((row) => row.type);
    if (types.length === 0) outcome = 'not-found';
    else if (types.length > 1) outcome = 'duplicate-row';
    else if (features.isGeneRowType(types[0])) outcome = 'found';
    else outcome = 'non-gene-target';
  }
  out.push({
    case: one.case,
    js_outcome: outcome,
    js_verdict: verdicts[outcome],
    rows_seen: indexed.rows.length,
    feature_rows: indexed.featureRows,
    problems: indexed.problems.length,
  });
}
console.log(JSON.stringify(out));
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_js(js_path, cases):
    node = shutil.which("node")
    if node is None:
        raise SystemExit("node is not installed; run without --js for one side only")
    payload = json.dumps(
        [
            {
                "case": case_key(case),
                "fixture": str(FIXTURES / case["fixture"]),
                "feature_id": case["feature_id"],
            }
            for case in cases
        ]
    ).encode("utf-8")
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", delete=False, encoding="utf-8"
    ) as handle:
        handle.write(JS_DRIVER.replace("__VERDICTS__", json.dumps(JS_VERDICT)))
        driver = Path(handle.name)
    try:
        result = subprocess.run(
            [node, str(driver), str(js_path)], input=payload, capture_output=True
        )
    finally:
        driver.unlink()
    if result.returncode != 0:
        raise SystemExit(f"the JavaScript resolver failed: {result.stderr.decode()}")
    return {item["case"]: item for item in json.loads(result.stdout.decode("utf-8"))}


def case_key(case):
    return f"{case['fixture']}#{case['feature_id']}"


def case_key_of(row):
    return f"{row['fixture']}#{row['feature_id']}"


def rows(js_rows):
    out = []
    for case in CONTRACT["cases"]:
        outcome = (
            build_feature_index(FIXTURES / case["fixture"])
            .resolve(case["feature_id"])
            .outcome
        )
        js = js_rows.get(case_key(case))
        out.append(
            {
                "fixture": case["fixture"],
                "feature_id": case["feature_id"],
                "outcome": outcome,
                "why": case.get("why", ""),
                "js_verdict": js["js_verdict"] if js else "-",
                "js_outcome": js["js_outcome"] if js else "-",
                "agree": None if js is None else js["js_outcome"] == outcome,
            }
        )
    return out


def extra_probes(js_supplied):
    """Behaviours the fixtures cannot express as a file, reported beside it."""
    probes = []
    missing = build_feature_index(FIXTURES / "no_such_fixture.gff3")
    probes.append(
        (
            "a path that does not exist",
            missing.resolve("gene:G1").outcome,
            "not comparable at the index boundary: src/features.js is handed "
            "content, not a path, so an unreadable file never reaches it",
        )
    )
    packed = gzip.compress((FIXTURES / "positive.gff3").read_bytes())
    index = build_feature_index(io.BytesIO(packed))
    probes.append(
        (
            "a gzip-compressed layer",
            index.resolve("gene:G1").outcome,
            (
                "src/features.js refuses bytes that still carry the gzip magic and "
                "reports them as a layer problem (its note: a gzip stream scanned as "
                "text would be confidently wrong); this index reads gzip and BGZF "
                "through the validator's own reader, so the same bytes are a usable "
                "layer. Both answers decline to guess, which is the property that "
                "matters."
                if js_supplied
                else "not run (JavaScript side not supplied)"
            ),
        )
    )
    return probes


def markdown_table(result):
    lines = [
        "| fixture | featureId | this index | `src/features.js` verdict | "
        "that verdict in this vocabulary | agreement |",
        "|---|---|---|---|---|---|",
    ]
    for row in result:
        lines.append(
            "| `{fixture}` | `{feature_id}` | `{outcome}` | {js_verdict} | "
            "`{js_outcome}` | {mark} |".format(
                mark="same" if row["agree"] else "**DIFFERS**", **row
            )
        )
    return "\n".join(lines)


def single_side_table(result):
    lines = [
        "| fixture | featureId | gff3-validator |",
        "|---|---|---|",
    ]
    lines += [
        "| `{fixture}` | `{feature_id}` | `{outcome}` |".format(**row) for row in result
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Score the feature-index fixtures with this index, and "
        "optionally with the JavaScript resolver, and print the agreement table."
    )
    parser.add_argument(
        "--js",
        metavar="PATH",
        help="path to a FAIR-bioHeaders-Tools-JavaScript src/features.js (read only)",
    )
    parser.add_argument(
        "--markdown", action="store_true", help="emit the markdown table"
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the table as JSON (for tests)"
    )
    parser.add_argument(
        "--strict", action="store_true", help="exit 1 when the two sides disagree"
    )
    args = parser.parse_args(argv)

    js_path = Path(args.js).expanduser().resolve() if args.js else None
    if js_path and not js_path.is_file():
        raise SystemExit(f"--js: not a file: {js_path}")
    js_rows = run_js(js_path, CONTRACT["cases"]) if js_path else {}
    result = rows(js_rows)
    findings = [row for row in result if row["agree"] is False]

    if args.json:
        print(
            json.dumps(
                {
                    "js": None if js_path is None else str(js_path),
                    "js_sha256": None if js_path is None else digest(js_path),
                    "rows": result,
                    "findings": [case_key_of(row) for row in findings],
                },
                indent=2,
            )
        )
        return 1 if (args.strict and findings) else 0
    if args.markdown:
        print(markdown_table(result) if js_path else single_side_table(result))
        return 1 if (args.strict and findings) else 0

    width = max(len(row["fixture"]) for row in result)
    for row in result:
        tail = (
            f" js={row['js_outcome']:<15} {'same' if row['agree'] else 'DIFFERS'}"
            if js_path
            else ""
        )
        print(
            f"{row['fixture']:<{width}}  {row['feature_id']!r:<20} "
            f"validator={row['outcome']:<15}{tail}"
        )
    if js_path:
        print(
            f"\n{len(result) - len(findings)}/{len(result)} cases agree, "
            f"{len(findings)} findings"
        )
        for row in findings:
            print(f"  finding: {row['fixture']} {row['feature_id']!r} -- {row['why']}")
        print(f"\nfeatures.js: {js_path}\n  sha256 {digest(js_path)}")
    else:
        print("\nJavaScript side not run (pass --js PATH); findings unknown")
    print("\nbeside the fixtures:")
    for name, outcome, note in extra_probes(bool(js_path)):
        print(f"  {name}: validator reports {outcome}\n    {note}")
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
