"""Glue for the in-browser page (``web/``), which runs this engine in Pyodide.

The page's Web Worker calls :func:`run` with a :class:`CallbackReader` over
the user's file, so the file is read in slices on demand and never copied
whole into memory (gzip is detected and decompressed by the engine's reader,
as on the command line). It is plain Python with no browser imports, so the
same code runs, and is tested, under CPython and under Pyodide in Node.js.
"""

import io

from gff3_validator import codons
from gff3_validator.engine import DEFAULT_MAX_FINDINGS, Validator
from gff3_validator.reader import InputError
from gff3_validator.report import summary, to_html, to_json, to_sarif, to_text

READ_BLOCK = 1 << 20  # bytes asked of the page per read


class CallbackReader(io.RawIOBase):
    """A read-only binary stream of ``size`` bytes over ``read_at``.

    ``read_at(offset, length)`` returns up to ``length`` bytes starting at
    ``offset`` (bytes, a buffer, or in Pyodide a JavaScript ArrayBuffer or
    typed array). ``progress(done, size)``, if given, is called after each
    read.
    """

    def __init__(self, size, read_at, progress=None):
        super().__init__()
        self.size = int(size)
        self.offset = 0
        self._read_at = read_at
        self._progress = progress

    def readable(self):
        return True

    def readinto(self, buffer):
        view = memoryview(buffer).cast("B")
        wanted = min(len(view), self.size - self.offset)
        if wanted <= 0:
            return 0
        data = self._read_at(self.offset, wanted)
        if hasattr(data, "to_bytes"):  # a Pyodide JsProxy of a JS buffer
            data = data.to_bytes()
        count = len(data)
        if count == 0:
            raise OSError(f"the file ended early, at byte {self.offset}")
        view[:count] = data
        self.offset += count
        if self._progress is not None:
            self._progress(self.offset, self.size)
        return count


def open_callback(size, read_at, progress=None):
    """A buffered stream over :class:`CallbackReader`, read in 1 MiB slices."""
    raw = CallbackReader(size, read_at, progress)
    return io.BufferedReader(raw, buffer_size=READ_BLOCK)


def run(
    source,
    name,
    header_mode="auto",
    genome=None,
    translation_table=None,
    max_findings=DEFAULT_MAX_FINDINGS,
):
    """Validate ``source`` like ``gff3-validate`` and render every report.

    Options mirror the command line: ``header_mode`` is ``auto``,
    ``require`` (``--require-header``) or ``skip`` (``--no-header``);
    ``genome`` is a FASTA path (``--genome``); ``translation_table`` needs a
    genome. Returns a dict with ``ok`` False and an ``error`` message when the
    input cannot be read (the command line exits 2), otherwise ``ok`` True,
    ``valid``, ``counts``, ``summary`` and the ``json``, ``sarif``, ``html``
    and ``text`` reports.
    """
    if translation_table is not None and genome is None:
        return {"ok": False, "error": "a translation table needs a genome FASTA"}
    try:
        validator = Validator(
            header_mode=header_mode,
            genome=genome,
            max_findings=max_findings,
            translation_table=(
                codons.DEFAULT_TABLE
                if translation_table is None
                else int(translation_table)
            ),
        )
        report = validator.validate(source, name=name)
    except (InputError, ValueError) as error:
        return {"ok": False, "error": f"{error}; validation incomplete"}
    return {
        "ok": True,
        "valid": report.valid,
        "counts": dict(report.counts),
        "summary": summary(report),
        "json": to_json(report),
        "sarif": to_sarif(report),
        "html": to_html(report),
        "text": to_text(report),
    }
