# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Guard disposable developer build outputs against physical source/Git overlap."""

import os
import subprocess
import unicodedata
from pathlib import Path


def _same_file(first, second):
    try:
        return first.samefile(second)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise ValueError("cannot establish output filesystem identity") from error


def safe_output(out, root, allowed_tracked=()):
    """Refuse overlaps, including case aliases on case-insensitive filesystems."""
    out = Path(out)
    if out.is_symlink():
        raise ValueError("output must not be a symlink")
    out = out.resolve()
    root = Path(root).resolve()
    if (
        out == root
        or out in root.parents
        or any(_same_file(out, ancestor) for ancestor in (root, *root.parents))
    ):
        raise ValueError("output is this checkout or its ancestor")
    if any(part.casefold() == ".git" for part in out.parts):
        raise ValueError("output is Git metadata")
    if out.is_dir():
        try:
            metadata = any(p.name.casefold() == ".git" for p in out.iterdir())
        except OSError as error:
            raise ValueError("cannot establish output repository identity") from error
        if metadata:
            raise ValueError("output is another repository or worktree")
    # resolve() does not canonicalise spelling on every case-insensitive FS.
    # Find the physical checkout anchor through the actual output's ancestors.
    anchor = next(
        (ancestor for ancestor in (out, *out.parents) if _same_file(ancestor, root)),
        None,
    )
    allowed = any(
        not Path(candidate).is_symlink()
        and (
            out == Path(candidate).absolute()
            or _same_file(out, Path(candidate).absolute())
        )
        for candidate in allowed_tracked
    )
    if anchor is not None and not allowed:
        relative = tuple(
            unicodedata.normalize("NFC", part).casefold()
            for part in out.relative_to(anchor).parts
        )
        try:
            tracked = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=root,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as error:
            raise ValueError(
                "cannot establish that output contains no tracked source"
            ) from error
        for entry in tracked.stdout.split(b"\0"):
            if not entry:
                continue
            parts = tuple(
                unicodedata.normalize("NFC", part).casefold()
                for part in Path(os.fsdecode(entry)).parts
            )
            if parts[: len(relative)] == relative:
                raise ValueError("output contains tracked source files")
    return out
