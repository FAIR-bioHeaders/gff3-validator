"""Execution failures must not satisfy an invalid conformance vector."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "checker", Path(__file__).resolve().parents[1] / "scripts/check_conformance.py"
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


@pytest.mark.parametrize("tail", ["--genome {genome}", "--genome={genome}", "{genome}"])
def test_optional_genome_removed_before_formatting(monkeypatch, tmp_path, tail):
    calls = []

    def run(command, timeout):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(checker, "run", run)
    case = {"file": "a.gff3", "expected": "valid"}
    assert (
        checker.score_exit(tmp_path, case, "validator {file} " + tail, 1)[0] == "pass"
    )
    assert calls == [["validator", str(tmp_path / "a.gff3")]]
    case["genome"] = "a.fa"
    assert (
        checker.score_exit(tmp_path, case, "validator {file} " + tail, 1)[0] == "pass"
    )
    assert str(tmp_path / "a.fa") in " ".join(calls[-1])


@pytest.mark.parametrize(
    "code,stderr,allowed,outcome",
    [
        (1, "invalid GFF3", (1,), "pass"),
        (2, "invalid GFF3", (2,), "pass"),
        (2, "failed", (1,), "fail"),
        (-9, "", (1,), "fail"),
        (127, "not found", (127,), "fail"),
        (126, "permission denied", (126,), "fail"),
        (1, "Traceback (most recent call last):\nRuntimeError", (1,), "fail"),
    ],
)
def test_execution_status_contract(
    monkeypatch, tmp_path, code, stderr, allowed, outcome
):
    monkeypatch.setattr(
        checker, "run", lambda *_: subprocess.CompletedProcess([], code, "", stderr)
    )
    case = {"file": "a.gff3", "expected": "invalid"}
    assert (
        checker.score_exit(tmp_path, case, "validator {file}", 1, allowed)[0] == outcome
    )


@pytest.mark.parametrize("module", [False, True])
def test_generator_entrypoints_without_pythonpath(tmp_path, module):
    import os
    import sys

    root = Path(__file__).resolve().parents[1]
    command = [sys.executable]
    command += (
        ["-m", "scripts.make_conformance"]
        if module
        else ["scripts/make_conformance.py"]
    )
    command += ["--output", str(tmp_path / "generated")]
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        command, cwd=root, env=environment, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "generated/manifest.json").is_file()
