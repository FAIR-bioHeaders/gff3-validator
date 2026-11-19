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


def iter_lines(source, on_invalid_utf8=None):
    """Yield ``(line_number, text)`` for each line of ``source``.

    A line ends at LF, at CRLF, or at a CR that is not followed by LF (FORMAT
    R1). Text is decoded as UTF-8 with the line feed removed. Carriage returns
    are kept on the yielded line (so both CRLF and lone-CR lines end with
    ``"\\r"``, which callers strip as the line terminator). Invalid bytes are
    replaced by U+FFFD and ``on_invalid_utf8(line_number)`` is called, if
    given (GFF-SYN-006).
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
            if raw.endswith(b"\n"):
                raw = raw[:-1]
            # Split at any lone CR (a CR not followed by the line's terminating LF).
            parts = raw.split(b"\r")
            for index, piece in enumerate(parts):
                # If the chunk ended with \r (before the stripped \n, i.e. CRLF,
                # or at EOF with a trailing \r), the final empty piece after \r
                # is the terminator of the preceding piece, not a new empty line.
                if index == len(parts) - 1 and piece == b"" and index > 0:
                    break
                if index < len(parts) - 1:
                    piece = piece + b"\r"
                number += 1
                try:
                    text = piece.decode("utf-8")
                except UnicodeDecodeError:
                    text = piece.decode("utf-8", errors="replace")
                    if on_invalid_utf8 is not None:
                        on_invalid_utf8(number)
                yield number, text
    finally:
        if owned is not None:
            owned.close()
