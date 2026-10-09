"""Streaming input: plain, gzip/BGZF or stdin, one line at a time."""

import gzip
import io
import sys
import zlib

GZIP_MAGIC = b"\x1f\x8b"


class InputError(Exception):
    """The input could not be read completely; validation is incomplete."""


def open_input(source):
    """Open ``source`` (a path, ``"-"`` for stdin, or a binary stream).

    Returns ``(stream, owned)``, where ``owned`` is the file opened here (to be
    closed by the caller) or None. Gzip and BGZF input (BGZF is multi-member
    gzip) is detected from the magic bytes, not the file name, and decompressed
    on the fly.
    """
    owned = None
    if source == "-":
        stream = sys.stdin.buffer
    elif hasattr(source, "read"):
        stream = source
    else:
        try:
            stream = owned = open(source, "rb")
        except OSError as error:
            raise InputError(f"cannot open {source}: {error.strerror}") from error
    if not hasattr(stream, "peek"):
        stream = io.BufferedReader(stream)
    if stream.peek(2)[:2] == GZIP_MAGIC:
        stream = gzip.GzipFile(fileobj=stream, mode="rb")
    return stream, owned


def iter_lines(source):
    """Yield ``(line_number, text)`` for each line of ``source``.

    Text is decoded as UTF-8 (invalid bytes are replaced; GFF-SYN-006 will
    report them) with the line feed removed. Carriage returns are kept, so
    CRLF input stays visible to the rules.
    """
    stream, owned = open_input(source)
    try:
        number = 0
        while True:
            try:
                raw = stream.readline()
            except (EOFError, OSError, zlib.error) as error:
                raise InputError(
                    f"input is truncated or corrupt after line {number}: {error}"
                ) from error
            if not raw:
                break
            number += 1
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            yield number, raw.decode("utf-8", errors="replace")
    finally:
        if owned is not None:
            owned.close()
