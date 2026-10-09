"""The conformance suite (conformance/) is up to date and the engine passes it.

CI also runs scripts/check_conformance.py against the installed CLI; this
test runs the same comparison in-process so that it is quick locally.
"""

import importlib.util
import json
from collections import Counter
from pathlib import Path

import pytest

from gff3_validator import validate

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "conformance"
MANIFEST = json.loads((SUITE / "manifest.json").read_text(encoding="utf-8"))
HEADER_MODES = {"require_header": "require", "no_header": "skip"}


def load_checker():
    path = ROOT / "scripts" / "check_conformance.py"
    spec = importlib.util.spec_from_file_location("check_conformance", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_suite_is_up_to_date_and_consistent():
    checker = load_checker()
    assert checker.check_up_to_date(SUITE) == []
    assert checker.check_manifest(SUITE, MANIFEST) == []


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda case: case["id"])
def test_engine_passes_case(case):
    options = {}
    if "genome" in case:
        options["genome"] = str(SUITE / case["genome"])
    for option, value in case.get("options", {}).items():
        if value:
            options["header_mode"] = HEADER_MODES[option]
    report = validate(SUITE / case["file"], **options)
    actual = Counter((x.rule, x.level, x.line) for x in report.findings)
    expected = Counter((x["rule"], x["level"], x["line"]) for x in case["findings"])
    assert actual == expected
    assert report.valid == (case["expected"] == "valid")
