"""The catalogue is well formed and the generated files are in sync."""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from gff3_validator.rules import catalogue_problems, load_catalogue

ROOT = Path(__file__).resolve().parent.parent


def test_packaged_catalogue_loads():
    catalogue = load_catalogue()
    assert catalogue.version.endswith("-draft")
    assert len(catalogue.rules) > 50


def test_source_and_packaged_copy_are_identical():
    source = ROOT / "rules" / "catalogue.yaml"
    packaged = ROOT / "gff3_validator" / "catalogue.yaml"
    assert source.read_bytes() == packaged.read_bytes()


def test_generated_files_in_sync():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "render_rules.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_every_rule_awaits_or_records_review():
    for rule in load_catalogue():
        assert rule.review == "pending-SO"


def test_reference_urls_are_pinned():
    catalogue = load_catalogue()
    assert "/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/" in (
        catalogue.sources["gff3"]["url"]
    )


@pytest.mark.parametrize(
    "change, message",
    [
        ({"level": "fatal"}, "level must be one of"),
        ({"id": "GFF-001"}, "id does not match"),
        ({"colour": "red"}, "unknown field"),
        ({"reference": {"source": "nowhere", "section": "x"}}, "unknown reference"),
    ],
)
def test_catalogue_problems_detected(change, message):
    data = yaml.safe_load((ROOT / "rules" / "catalogue.yaml").read_text("utf-8"))
    data["rules"][0].update(change)
    assert any(message in problem for problem in catalogue_problems(data))


def test_duplicate_ids_detected():
    data = yaml.safe_load((ROOT / "rules" / "catalogue.yaml").read_text("utf-8"))
    data["rules"].append(dict(data["rules"][0]))
    assert any("duplicate id" in problem for problem in catalogue_problems(data))
