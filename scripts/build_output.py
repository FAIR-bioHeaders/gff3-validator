# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Guard dedicated disposable developer build outputs against source/Git overlap."""

import subprocess
from pathlib import Path


def safe_output(out, root, allowed_tracked=()):
    """Refuse source/Git overlaps before any destructive build operation."""
    out = Path(out)
    if out.is_symlink():
        raise ValueError("output must not be a symlink")
    out = out.resolve()
    root = Path(root).resolve()
    if out == root or out in root.parents:
        raise ValueError("output is this checkout or its ancestor")
    if ".git" in out.parts:
        raise ValueError("output is Git metadata")
    if (out / ".git").exists():
        raise ValueError("output is another repository or worktree")
    if out.is_relative_to(root) and out not in {
        Path(p).absolute() for p in allowed_tracked
    }:
        try:
            tracked = subprocess.run(
                [
                    "git",
                    "--literal-pathspecs",
                    "ls-files",
                    "-z",
                    "--",
                    out.relative_to(root).as_posix(),
                ],
                cwd=root,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise ValueError(
                "cannot establish that output contains no tracked source"
            ) from error
        if tracked.stdout:
            raise ValueError("output contains tracked source files")
    return out
