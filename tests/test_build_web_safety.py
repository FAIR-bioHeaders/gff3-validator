# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Output safety for the developer web builder; all deletions use synthetic roots."""

import importlib.util
import subprocess
from pathlib import Path
from unittest import mock

import pytest

MODULE = Path(__file__).resolve().parents[1] / "scripts/build_web.py"
spec = importlib.util.spec_from_file_location("build_web_safety", MODULE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


@pytest.fixture
def checkout(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / "docs/keep.md").write_text("tracked source")
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "docs"], check=True)
    monkeypatch.setattr(builder, "ROOT", root)
    return root


@pytest.mark.parametrize("which", ["root", "ancestor", "tracked", "metadata"])
def test_protected_output_is_refused_before_build_or_delete(checkout, which):
    target = {
        "root": checkout,
        "ancestor": checkout.parent,
        "tracked": checkout / "docs",
        "metadata": checkout / ".git/objects",
    }[which]
    with (
        mock.patch.object(builder.shutil, "rmtree") as remove,
        mock.patch.object(builder, "build_wheel") as wheel,
    ):
        with pytest.raises(ValueError):
            builder.build(target)
        remove.assert_not_called()
        wheel.assert_not_called()
    assert (checkout / "docs/keep.md").read_text() == "tracked source"


def test_other_worktree_marker_is_refused(checkout):
    target = checkout.parent / "other"
    target.mkdir()
    (target / ".git").write_text("gitdir: /private/worktree/metadata\n")
    sentinel = target / "keep"
    sentinel.write_text("other work")
    with mock.patch.object(builder.shutil, "rmtree") as remove:
        with pytest.raises(ValueError, match="another repository or worktree"):
            builder.build(target)
        remove.assert_not_called()
    assert sentinel.read_text() == "other work"


def test_symlink_output_is_refused_before_resolution(checkout):
    target = checkout.parent / "user-work"
    target.mkdir()
    (target / "keep").write_text("keep")
    link = checkout.parent / "site-link"
    link.symlink_to(target, target_is_directory=True)
    with mock.patch.object(builder.shutil, "rmtree") as remove:
        with pytest.raises(ValueError, match="symlink"):
            builder.build(link)
        remove.assert_not_called()
    assert (target / "keep").read_text() == "keep"


def test_unknown_tracking_state_fails_closed(checkout):
    target = checkout / "scratch"
    target.mkdir()
    (target / "keep").write_text("keep")
    with mock.patch.object(builder.subprocess, "run", side_effect=OSError("no git")):
        with mock.patch.object(builder.shutil, "rmtree") as remove:
            with pytest.raises(ValueError, match="cannot establish"):
                builder.build(target)
            remove.assert_not_called()
    assert (target / "keep").read_text() == "keep"


def test_untracked_scratch_is_replaced_without_harming_sources(checkout):
    target = checkout / "scratch[1]"
    target.mkdir()
    (target / "disposable").write_text("old output")
    wheel = checkout.parent / "gff3_validator-test.whl"
    wheel.write_bytes(b"synthetic wheel payload")
    builder.build(target, wheel)
    assert not (target / "disposable").exists()
    assert (target / "index.html").is_file()
    assert (target / wheel.name).read_bytes() == wheel.read_bytes()
    assert (checkout / "docs/keep.md").read_text() == "tracked source"


def test_cli_reports_unsafe_output_without_building(checkout, capsys):
    with mock.patch.object(builder.shutil, "rmtree") as remove:
        assert builder.main(["--out", str(checkout)]) == 1
        remove.assert_not_called()
    assert "this checkout or its ancestor" in capsys.readouterr().err


def test_literal_brackets_in_tracked_output_are_not_treated_as_a_glob(checkout):
    target = checkout / "notes[1]"
    target.mkdir()
    (target / "keep").write_text("tracked bracket source")
    subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(checkout), "add", "notes[1]"],
        check=True,
    )
    with mock.patch.object(builder.shutil, "rmtree") as remove:
        with pytest.raises(ValueError, match="tracked source"):
            builder.build(target)
        remove.assert_not_called()
    assert (target / "keep").read_text() == "tracked bracket source"


def load_generator():
    generator_spec = importlib.util.spec_from_file_location(
        "make_conformance_safety", MODULE.parent / "make_conformance.py"
    )
    generator = importlib.util.module_from_spec(generator_spec)
    generator_spec.loader.exec_module(generator)
    return generator


def test_conformance_generator_refuses_source_root_before_removing_profiles(checkout):
    generator = load_generator()
    with (
        mock.patch.object(generator, "ROOT", checkout),
        mock.patch.object(generator.shutil, "rmtree") as remove,
    ):
        with pytest.raises(ValueError, match="this checkout or its ancestor"):
            generator.write(checkout)
        remove.assert_not_called()
    assert (checkout / "docs/keep.md").read_text() == "tracked source"


def test_conformance_generator_refuses_another_checkout(checkout):
    generator = load_generator()
    target = checkout.parent / "another"
    target.mkdir()
    (target / ".git").write_text("gitdir: /private/worktree/metadata\n")
    with (
        mock.patch.object(generator, "ROOT", checkout),
        mock.patch.object(generator.shutil, "rmtree") as remove,
    ):
        with pytest.raises(ValueError, match="another repository or worktree"):
            generator.write(target)
        remove.assert_not_called()


def test_conformance_generator_allows_designated_generated_tree(checkout):
    generator = load_generator()
    output = checkout / "conformance"
    output.mkdir()
    (output / "manifest.json").write_text("old generated manifest")
    subprocess.run(["git", "-C", str(checkout), "add", "conformance"], check=True)
    with mock.patch.object(generator, "ROOT", checkout):
        generator.write(output)
    assert (output / "manifest.json").read_text().startswith("{")
    assert (checkout / "docs/keep.md").read_text() == "tracked source"


@pytest.mark.parametrize("kind", ["symlink", "worktree"])
def test_conformance_generated_subdirectory_cannot_point_at_user_work(checkout, kind):
    generator = load_generator()
    output = checkout / "scratch"
    output.mkdir()
    target = output / "profiles"
    if kind == "symlink":
        user_work = checkout.parent / "user-work"
        user_work.mkdir()
        (user_work / "keep").write_text("user work")
        target.symlink_to(user_work, target_is_directory=True)
    else:
        target.mkdir()
        (target / ".git").write_text("gitdir: /private/worktree/metadata\n")
        (target / "keep").write_text("user work")
        user_work = target
    with (
        mock.patch.object(generator, "ROOT", checkout),
        mock.patch.object(generator.shutil, "rmtree") as remove,
    ):
        with pytest.raises(ValueError, match="symlink or repository"):
            generator.write(output)
        remove.assert_not_called()
    assert (user_work / "keep").read_text() == "user work"
