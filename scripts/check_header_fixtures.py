"""Check historical structural and supported-contract fixtures through an installed CLI.

No dependency or fixture is modified. Run each mode in its own package environment:
--mode unavailable for a core-only install, --mode checked with the declared headers
extra. The historical file is not a complete FHGFF3 instance. The companion uses
immutable v0.4.0, supported by the declared fair-bioheaders >=0.7,<0.9 range;
this is not a claim of support for the family's newer v0.6.0 release.
"""

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "tests/fixtures/valid/fhgff3_header.gff3"
COMPANION = ROOT / "conformance/valid/fhgff3-header-valid.gff3"
HISTORICAL_SHA256 = "28f74236779c3572536cad46f97f14dac64e15a6f70d600b45909785b7a3a1ac"


def check(command, mode):
    if hashlib.sha256(HISTORICAL.read_bytes()).hexdigest() != HISTORICAL_SHA256:
        raise ValueError("historical structural fixture bytes changed")
    rows = []
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory(prefix="validator-header-fixtures-") as work:
        for name, fixture, skip in (
            ("historical", HISTORICAL, False),
            ("supported-v0.4.0", COMPANION, False),
            ("explicit-skip", HISTORICAL, True),
        ):
            args = command + ["--format", "json"]
            if skip:
                args.append("--no-header")
            result = subprocess.run(
                args + [str(fixture)],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
                env=environment,
            )
            if result.returncode not in (0, 1):
                raise ValueError(
                    f"{name}: incomplete command, exit {result.returncode}: {result.stderr}"
                )
            report = json.loads(result.stdout)
            hdr = {
                f["rule"] for f in report["findings"] if f["rule"].startswith("HDR-")
            }
            notes = [x["reason"] for x in report["skipped"] if x["layer"] == "fhgff3"]
            if skip:
                expected, code = {"HDR-003"}, 0
            elif mode == "unavailable":
                expected, code = {"HDR-002"}, 0
            elif name == "historical":
                expected, code = {"HDR-005", "HDR-007"}, 1
            else:
                expected, code = set(), 0
            if hdr != expected or result.returncode != code:
                raise ValueError(
                    f"{name}: expected {sorted(expected)} / exit {code}, got {sorted(hdr)} / exit {result.returncode}"
                )
            if report.get("valid") != (code == 0):
                raise ValueError(
                    f"{name}: JSON validity disagrees with the expected exit"
                )
            if mode == "checked" and name == "supported-v0.4.0" and notes:
                raise ValueError(
                    f"{name}: companion header checks were not performed: {notes}"
                )
            if skip or mode == "unavailable":
                if not notes:
                    raise ValueError(
                        f"{name}: unperformed header checks have no reason"
                    )
                status = "not-run"
            else:
                status = "rejected" if hdr else "checked"
            rows.append(
                {
                    "fixture": name,
                    "header_checks": status,
                    "rules": sorted(hdr),
                    "not_checked": notes,
                }
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gff3-validate", required=True)
    parser.add_argument("--mode", choices=("checked", "unavailable"), required=True)
    args = parser.parse_args()
    try:
        rows = check(shlex.split(args.gff3_validate), args.mode)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"header fixtures: {error}\n")
    print(json.dumps({"mode": args.mode, "checks": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
