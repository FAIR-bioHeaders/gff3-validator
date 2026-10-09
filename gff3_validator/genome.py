"""Random access to the genome FASTA given with ``--genome`` (biology rules).

The genome is never loaded into memory. Opening it reads it once, line by
line, and builds an index like samtools faidx (.fai): for each record its
name, length, the byte offset of its first base, the number of bases per line
and the number of bytes per line (bases plus the line ending). Slices are
then read on demand with ``seek``, in blocks of ``BLOCK`` bases, and the last
``CACHE_BLOCKS`` blocks are kept in a small LRU cache (about 2 MiB).

Plain FASTA is read in place. Gzip and BGZF input (detected from the magic
bytes, not the file name) is first decompressed to an anonymous temporary file
in the temporary directory (``TMPDIR``), which needs as much free disk space
as the uncompressed genome and is removed when the genome is closed (on
POSIX it has no name at all). Memory is O(number of records).

Leading lines starting with ``;`` (the FASTA comment convention, used for
example by a FAIR-bioHeaders ``;~`` header) are skipped. A FASTA file that
cannot be indexed reliably (sequence before the first ``>``, an empty or
duplicate name, lines of different lengths inside a record, characters that
are not sequence letters) raises :class:`GenomeError`.
"""

import gzip
import shutil
import tempfile
import zlib
from collections import OrderedDict
from typing import Dict, NamedTuple, Optional

from gff3_validator.reader import GZIP_MAGIC, InputError

BLOCK = 1 << 16  # bases per cached block
CACHE_BLOCKS = 32
SPOOL_CHUNK = 1 << 20
LINE_PIECE = 1 << 20
# Bytes allowed in sequence lines: IUPAC letters (any case), "*" and "-".
SEQUENCE_BYTES = bytes(
    sorted(set(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz*-"))
)
COMPLEMENT = bytes.maketrans(
    b"ACGTURYKMBDHVNacgturykmbdhvn", b"TGCAAYRMKVHDBNtgcaayrmkvhdbn"
)


class GenomeError(InputError):
    """The genome FASTA cannot be used; the biology checks cannot run."""


class Record(NamedTuple):
    length: int
    offset: int  # byte offset of the first base
    line_bases: int
    line_width: int  # bytes per line, including the line ending


def reverse_complement(sequence: bytes) -> bytes:
    return sequence.translate(COMPLEMENT)[::-1]


def _show(raw: bytes, limit=40):
    text = raw.decode("utf-8", errors="replace").encode("unicode_escape")
    text = text.decode("ascii")
    return f'"{text[: limit - 3] + "..." if len(text) > limit else text}"'


class Genome:
    """An indexed genome FASTA. Use as a context manager or call ``close``."""

    def __init__(self, path):
        if path == "-" or hasattr(path, "read"):
            raise GenomeError(
                "the genome cannot be read from standard input; give a FASTA "
                "file path with --genome"
            )
        self.path = str(path)
        self.records: Dict[str, Record] = {}
        self.spooled = False
        self._cache: "OrderedDict[tuple, bytes]" = OrderedDict()
        try:
            handle = open(path, "rb")
        except OSError as error:
            raise GenomeError(
                f"cannot open genome {self.path}: {error.strerror}"
            ) from error
        try:
            if handle.read(2) == GZIP_MAGIC:
                handle = self._spool(handle)
            handle.seek(0)
            self._file = handle
            self._index()
        except BaseException:
            handle.close()
            raise

    # -- opening --------------------------------------------------------

    def _spool(self, compressed):
        """Decompress gzip/BGZF input to an anonymous temporary file."""
        compressed.seek(0)
        try:
            spool = tempfile.TemporaryFile(prefix="gff3-validator-genome-")
        except OSError as error:
            compressed.close()
            raise GenomeError(
                f"cannot create a temporary file for the decompressed genome: "
                f"{error.strerror}"
            ) from error
        try:
            with compressed, gzip.GzipFile(fileobj=compressed, mode="rb") as data:
                shutil.copyfileobj(data, spool, SPOOL_CHUNK)
        except (EOFError, zlib.error, gzip.BadGzipFile) as error:
            spool.close()
            raise GenomeError(
                f"genome {self.path} is truncated or not valid gzip: {error}"
            ) from error
        except OSError as error:
            spool.close()
            raise GenomeError(
                f"cannot decompress genome {self.path} to the temporary "
                f"directory (needs as much free space as the uncompressed "
                f"genome; set TMPDIR): {error}"
            ) from error
        self.spooled = True
        return spool

    def _fail(self, number, message):
        raise GenomeError(f"genome {self.path} line {number}: {message}")

    def _lines(self):
        """Yield ``(number, start, head, width, bases, bad)`` for each line.

        Lines are read in pieces of at most ``LINE_PIECE`` bytes, so a genome
        with a whole chromosome on one line does not need that line in memory.
        ``head`` is the first piece without the line ending, ``width`` the
        line's length in bytes with its ending, ``bases`` its length without
        it and ``bad`` the first byte that is not a sequence letter (or b"").
        """
        read = self._file.readline
        number = position = 0
        while True:
            raw = read(LINE_PIECE)
            if not raw:
                return
            number += 1
            start = position
            head = raw.rstrip(b"\r\n")
            width, bases = len(raw), len(head)
            bad = head.translate(None, SEQUENCE_BYTES)[:1]
            while not raw.endswith(b"\n"):
                raw = read(LINE_PIECE)
                if not raw:
                    break
                piece = raw.rstrip(b"\r\n")
                width += len(raw)
                bases += len(piece)
                if not bad:
                    bad = piece.translate(None, SEQUENCE_BYTES)[:1]
            position += width
            yield number, start, head, width, bases, bad

    def _index(self):
        records = self.records
        name: Optional[str] = None
        length = offset = line_bases = line_width = 0
        ended = 0  # line number of a short or blank line ending the record
        for number, start, head, width, bases, bad in self._lines():
            if head.startswith(b">"):
                if name is not None:
                    records[name] = Record(length, offset, line_bases, line_width)
                fields = head[1:].split(None, 1)
                if not fields:
                    self._fail(number, "a '>' line has no sequence name")
                try:
                    name = fields[0].decode("utf-8")
                except UnicodeDecodeError:
                    self._fail(number, "the sequence name is not UTF-8")
                if name in records:
                    self._fail(number, f"duplicate sequence name {_show(fields[0])}")
                length = line_bases = line_width = ended = 0
                offset = start + width
                continue
            if name is None:
                if not head.strip() or head.startswith(b";"):
                    continue  # comment or FAIR-bioHeaders header line
                self._fail(number, "sequence data before the first '>' line")
            if not bases:
                if not ended:
                    ended = number
                continue
            if head.startswith(b";"):
                self._fail(
                    number,
                    "';' comment lines are accepted only before the first record",
                )
            if bad:
                self._fail(
                    number, f"character {_show(bad)} in sequence {_show(name.encode())}"
                )
            if ended:
                self._fail(
                    number,
                    f"sequence {_show(name.encode())} continues after a shorter "
                    f"or blank line (line {ended}); all lines of a record except "
                    "the last must have the same length",
                )
            if line_bases == 0:
                line_bases, line_width = bases, width
                offset = start
            elif bases > line_bases:
                self._fail(
                    number,
                    f"line has {bases} bases, more than the {line_bases} of "
                    f"the first line of sequence {_show(name.encode())}; all "
                    "lines of a record except the last must have the same length",
                )
            elif bases < line_bases:
                ended = number
            elif width != line_width and width != bases:
                self._fail(number, "line endings change inside the record")
            length += bases
        if name is not None:
            records[name] = Record(length, offset, line_bases, line_width)
        if not records:
            raise GenomeError(f"genome {self.path} has no FASTA records ('>' lines)")

    # -- access ---------------------------------------------------------

    def resolve(self, seqid: str, decoded: Optional[str] = None) -> Optional[str]:
        """The genome name for ``seqid`` (or its percent-decoded form)."""
        if seqid in self.records:
            return seqid
        if decoded is not None and decoded in self.records:
            return decoded
        return None

    def length(self, name: str) -> int:
        return self.records[name].length

    def fetch(self, name: str, start: int, end: int) -> bytes:
        """Bases ``start`` to ``end`` (0-based, end exclusive), upper case."""
        record = self.records[name]
        if not 0 <= start <= end <= record.length:
            raise ValueError(f"{start}..{end} is outside {name}")
        parts = []
        position = start
        while position < end:
            block = position // BLOCK
            data = self._block(name, record, block)
            low = position - block * BLOCK
            high = min(end - block * BLOCK, len(data))
            parts.append(data[low:high])
            position = block * BLOCK + high
        return b"".join(parts)

    def _block(self, name, record, block):
        key = (name, block)
        data = self._cache.get(key)
        if data is not None:
            self._cache.move_to_end(key)
            return data
        start = block * BLOCK
        end = min(start + BLOCK, record.length)
        bases, width = record.line_bases, record.line_width
        first = record.offset + (start // bases) * width + start % bases
        last = record.offset + ((end - 1) // bases) * width + (end - 1) % bases
        self._file.seek(first)
        raw = self._file.read(last - first + 1)
        data = raw.translate(None, b"\r\n").upper()
        if len(data) != end - start:
            raise GenomeError(f"genome {self.path} changed while it was being read")
        self._cache[key] = data
        if len(self._cache) > CACHE_BLOCKS:
            self._cache.popitem(last=False)
        return data

    def close(self):
        self._cache.clear()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
