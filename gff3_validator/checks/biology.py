"""Biology rules BIO-001 to BIO-011; they run only with ``--genome``.

- BIO-001, BIO-002, BIO-003 (seqids and lengths against the genome) are
  judged at the end of the file from what :class:`Structure` already keeps per
  seqid and per ``##sequence-region``.
- BIO-010 (strand of a child against its Parent) is checked on each line
  with the Parent's strand from :class:`Structure`; for a Parent not defined
  yet, the first line and count per child strand are kept per Parent ID.
- BIO-004 to BIO-009 need all segments of a CDS. A CDS is all CDS lines with
  one ID or, for lines without ID, with one Parent list. Its segments
  (coordinates, phase and line: four integers per line in an ``array``), the
  exons of each Parent (two integers per exon and Parent) and the recoded
  codons of each CDS are kept until the next ``###`` or the end of the file,
  then judged and dropped. Memory is therefore O(CDS and exon lines between
  two ``###``): about 40 bytes per CDS line and 20 bytes per exon and Parent,
  plus about 300 bytes per CDS and per transcript with exons. A file without
  ``###`` keeps them all to the end.
- The CDS is read from the genome in blocks of at most
  :data:`gff3_validator.genome.BLOCK` bases and scanned codon by codon with a
  regular expression, so a long CDS is never held in memory as a whole.

Translation exceptions (SO-Ontologies#658, question 17, pending SO): a codon
covered by a ``recoded_codon`` feature (or a subtype) whose Parent is the CDS,
or by a ``transl_except`` position on the CDS, is exempt from BIO-006 to
BIO-009. A recoded codon may be split over several lines sharing one ID.
"""

import re
from array import array
from collections import Counter
from typing import Dict, Iterator, List, Optional, Tuple

from gff3_validator.checks.attributes import decode
from gff3_validator.checks.structure import Structure, show_id
from gff3_validator.checks.syntax import CDS_TYPES
from gff3_validator.codons import CodonTable
from gff3_validator.genome import BLOCK, Genome, reverse_complement

EXON_TYPES = ("exon", "SO:0000147")
# recoded_codon and its is_a descendants (SO:0000145 > SO:0000883 >
# SO:0000884, SO:0000885). To be replaced by the SO layer's subtype lookup.
RECODED_TYPES = frozenset(
    (
        "recoded_codon",
        "SO:0000145",
        "stop_codon_read_through",
        "SO:0000883",
        "stop_codon_redefined_as_pyrrolysine",
        "SO:0000884",
        "stop_codon_redefined_as_selenocysteine",
        "SO:0000885",
    )
)
STRANDED = ("+", "-")
ACGT = re.compile(b"[ACGT]{3}")
# transl_except=(pos:213..215,aa:Sec) or (pos:complement(join(5..6,9)),aa:...)
TRANSL_EXCEPT = re.compile(r"pos:(.*?),\s*aa:")
RANGE = re.compile(r"([0-9]+)(?:\.\.([0-9]+))?")

# (rule id, line or None, message)
Problem = Tuple[str, object, str]


class Chain:
    """The lines of one CDS seen since the last ``###``."""

    __slots__ = ("name", "seqid", "strand", "parents", "segments", "mixed")

    def __init__(self, name, seqid, strand, parents):
        self.name = name
        self.seqid = seqid
        self.strand = strand
        self.parents = parents
        self.segments = array("q")  # start, end, phase (-1 if invalid), line
        self.mixed = False


class Biology:
    def __init__(self, genome: Genome, table: CodonTable, structure: Structure):
        self.genome = genome
        self.table = table
        self.structure = structure
        self.chains: Dict[str, Chain] = {}
        self.exons: Dict[str, array] = {}
        self.recoded: Dict[str, array] = {}
        # Parent ID not defined yet -> {child strand: [first line, count]}.
        self.pending_strands: Dict[str, Dict[str, list]] = {}
        self.skipped: Counter = Counter()
        self.checked = 0

    # -- per line -------------------------------------------------------

    def feature(
        self, line, seqid, type_, strand, phase, coordinates, attributes
    ) -> Iterator[Problem]:
        parents = attributes.parents
        if strand in STRANDED:
            for parent in parents:
                yield from self._strand(line, type_, strand, parent)
        if coordinates is None:
            return
        start, end = coordinates
        if type_ in EXON_TYPES:
            for parent in parents:
                self._interval(self.exons, parent, start, end)
        elif type_ in RECODED_TYPES:
            for parent in parents:
                self._interval(self.recoded, "I" + parent, start, end)
        elif type_ in CDS_TYPES:
            self._cds(line, seqid, strand, phase, start, end, attributes)

    def _strand(self, line, type_, strand, parent):
        other = self.structure.strand_of(parent)
        if other is None:
            known = self.pending_strands.setdefault(parent, {})
            entry = known.get(strand)
            if entry is None:
                known[strand] = [line, 1]
            else:
                entry[1] += 1
        elif other in STRANDED and other != strand:
            yield (
                "BIO-010",
                line,
                f"{show_id(type_)} is on strand {strand} but its Parent "
                f"{show_id(parent)} is on strand {other}",
            )

    @staticmethod
    def _interval(store, key, start, end):
        found = store.get(key)
        if found is None:
            found = store[key] = array("q")
        found.append(start)
        found.append(end)

    def _cds(self, line, seqid, strand, phase, start, end, attributes):
        identifier = attributes.id
        parents = tuple(attributes.parents)
        if identifier is not None:
            key, name = "I" + identifier, f"CDS {show_id(identifier)}"
        elif parents:
            key = "P" + ",".join(parents)
            name = f"CDS of {show_id(','.join(parents))}"
        else:
            key, name = f"L{line}", f"CDS at line {line}"
        chain = self.chains.get(key)
        if chain is None:
            chain = self.chains[key] = Chain(name, seqid, strand, parents)
        elif chain.seqid != seqid or chain.strand != strand:
            chain.mixed = True  # GFF-STR-002 reports it
        chain.segments.extend(
            (start, end, int(phase) if phase in ("0", "1", "2") else -1, line)
        )
        legacy = attributes.tags.get("transl_except")
        if legacy:
            for match in TRANSL_EXCEPT.finditer(decode(legacy)):
                for low, high in RANGE.findall(match.group(1)):
                    self._interval(self.recoded, key, int(low), int(high or low))

    # -- ### and end of file --------------------------------------------

    def flush(self) -> Iterator[Problem]:
        """Judge every CDS seen since the last ``###`` and forget them."""
        for key, chain in self.chains.items():
            yield from self._judge(chain, self.recoded.get(key, ()))
        self.chains.clear()
        self.exons.clear()
        self.recoded.clear()

    def finish(self) -> Iterator[Problem]:
        yield from self.flush()
        for parent, known in self.pending_strands.items():
            other = self.structure.strand_of(parent)
            if other not in STRANDED:
                continue  # undefined Parent (GFF-STR-004) or no strand
            for strand, (line, count) in known.items():
                if strand != other:
                    more = f" (and {count - 1} more lines)" if count > 1 else ""
                    yield (
                        "BIO-010",
                        line,
                        f"feature is on strand {strand} but its Parent "
                        f"{show_id(parent)} is on strand {other}{more}",
                    )
        self.pending_strands.clear()
        yield from self._sequences()
        reasons = self.skip_reasons()
        if reasons:
            yield (
                "BIO-011",
                None,
                "some biology checks were not run: " + "; ".join(reasons),
            )

    def skip_reasons(self) -> List[str]:
        return [f"{count} {reason}" for reason, count in self.skipped.items()]

    # -- seqids and lengths ----------------------------------------------

    def _sequences(self):
        structure, genome = self.structure, self.genome
        seqids = {seqid: s.first_line for seqid, s in structure.sequences.items()}
        for seqid, (_, _, line) in structure.regions.items():
            seqids.setdefault(seqid, line)
        missing = []
        for seqid, first_line in seqids.items():
            name = genome.resolve(seqid, decode(seqid))
            if name is None:
                missing.append((seqid, first_line))
                continue
            length = genome.length(name)
            sequence = structure.sequences.get(seqid)
            circular = sequence is not None and sequence.circular
            if sequence is not None:
                if circular:
                    beyond, line = sequence.max_start, sequence.max_start_line
                    what = "starts at"
                else:
                    beyond, line = sequence.max_end, sequence.max_end_line
                    what = "ends at"
                if beyond > length:
                    yield (
                        "BIO-002",
                        line,
                        f"feature {what} {beyond}, beyond the {length} bases of "
                        f"{show_id(seqid)} in the genome (the furthest feature "
                        "on that sequence is reported)",
                    )
            region = structure.regions.get(seqid)
            if region is not None and region[1] > length and not circular:
                yield (
                    "BIO-003",
                    region[2],
                    f"##sequence-region of {show_id(seqid)} ends at {region[1]}, "
                    f"but the sequence has {length} bases in the genome",
                )
        if missing and len(missing) == len(seqids):
            example = next(iter(genome.records))
            yield (
                "BIO-001",
                missing[0][1],
                f"none of the {len(seqids)} seqids (for example "
                f"{show_id(missing[0][0])}) is in the genome, whose first "
                f"sequence is {show_id(example)}: is it the genome the "
                "annotation was made on?",
            )
            return
        for seqid, line in missing:
            yield ("BIO-001", line, f"seqid {show_id(seqid)} is not in the genome")

    # -- one CDS ----------------------------------------------------------

    def _judge(self, chain: Chain, recoded) -> Iterator[Problem]:
        values = chain.segments
        segments = [tuple(values[i : i + 4]) for i in range(0, len(values), 4)]
        yield from self._within_exons(chain, segments)
        if chain.mixed:
            self.skipped["CDS with lines on different seqids or strands"] += 1
            return
        if chain.strand not in STRANDED:
            self.skipped["CDS on strand '.' or '?'"] += 1
            return
        if any(segment[2] < 0 for segment in segments):
            self.skipped["CDS with a missing or invalid phase"] += 1
            return
        if chain.strand == "+":
            segments.sort()
        else:
            segments.sort(key=lambda segment: -segment[1])
        consistent = True
        for previous, segment in zip(segments, segments[1:]):
            length = previous[1] - previous[0] + 1
            expected = (3 - ((length - previous[2]) % 3)) % 3
            if segment[2] != expected:
                consistent = False
                yield (
                    "BIO-004",
                    segment[3],
                    f"{chain.name}: phase {segment[2]}, but the previous segment "
                    f"(line {previous[3]}, {length} bases, phase {previous[2]}) "
                    f"gives phase {expected}",
                )
        coding = Coding(chain, segments, recoded)
        remainder = coding.length % 3
        if (
            coding.length > 0
            and remainder
            and not coding.covered(coding.length - remainder, remainder)
        ):
            yield (
                "BIO-009",
                segments[-1][3],
                f"{chain.name}: coding length {coding.length} (segment lengths "
                f"minus the first phase) is not a multiple of three",
            )
        name = self.genome.resolve(chain.seqid, decode(chain.seqid))
        if name is None:
            self.skipped["CDS on seqids not in the genome"] += 1
            return
        length = self.genome.length(name)
        if any(segment[1] > length for segment in segments):
            self.skipped["CDS beyond the end of their genome sequence"] += 1
            return
        if coding.length < 3:
            return
        self.checked += 1
        scan = coding.scan(self.genome, name, self.table)
        table = f"translation table {self.table.id}"
        first = scan.first
        if (
            segments[0][2] == 0
            and ACGT.fullmatch(first)
            and first not in self.table.starts
            and not coding.covered(0, 3)
        ):
            where, line = coding.where(0)
            yield (
                "BIO-006",
                line,
                f"{chain.name} starts with {first.decode()} at {where}, not a "
                f"start codon under {table}",
            )
        if not consistent:
            self.skipped["CDS with inconsistent phases (stop codons not checked)"] += 1
            return
        if scan.internal:
            position, codon = scan.first_internal
            where, line = coding.where(position)
            more = scan.internal - 1
            yield (
                "BIO-008",
                line,
                f"{chain.name} has an in-frame stop codon {codon.decode()} at "
                f"{where} (codon {position // 3 + 1} of {coding.length // 3}) "
                f"under {table}"
                + (f", and {more} more before its end" if more else ""),
            )
        last = scan.last
        if (
            remainder == 0
            and ACGT.fullmatch(last)
            and last not in self.table.stops
            and not coding.covered(coding.length - 3, 3)
        ):
            where, line = coding.where(coding.length - 3)
            yield (
                "BIO-007",
                line,
                f"{chain.name} ends with {last.decode()} at {where}, not a stop "
                f"codon under {table}",
            )

    def _within_exons(self, chain, segments):
        for parent in chain.parents:
            exons = self.exons.get(parent)
            if not exons:
                continue
            pairs = list(zip(exons[::2], exons[1::2]))
            for start, end, _, line in segments:
                if not any(low <= start and end <= high for low, high in pairs):
                    yield (
                        "BIO-005",
                        line,
                        f"{chain.name} segment {start}..{end} is not within an "
                        f"exon of its Parent {show_id(parent)}",
                    )


class Scan:
    __slots__ = ("first", "last", "internal", "first_internal")


class Coding:
    """The coding sequence of one CDS: its segments from 5' to 3'.

    Positions are 0-based offsets into the coding sequence, which starts after
    the first segment's phase.
    """

    def __init__(self, chain, segments, recoded):
        self.strand = chain.strand
        self.seqid = chain.seqid
        self.segments = segments
        self.phase = segments[0][2]
        self.length = sum(end - start + 1 for start, end, _, _ in segments)
        self.length -= self.phase
        self.recoded = list(zip(recoded[::2], recoded[1::2])) if recoded else []

    def genomic(self, position) -> Tuple[Optional[int], Optional[int]]:
        """(1-based genomic coordinate, line) of a coding position."""
        offset = position + self.phase
        for start, end, _, line in self.segments:
            size = end - start + 1
            if offset < size:
                return (start + offset if self.strand == "+" else end - offset), line
            offset -= size
        return None, None

    def where(self, position):
        coordinate, line = self.genomic(position)
        return f"{self.seqid}:{coordinate}", line

    def covered(self, position, count) -> bool:
        """Whether ``count`` bases from ``position`` lie in recoded codons."""
        if not self.recoded:
            return False
        for index in range(position, position + count):
            coordinate, _ = self.genomic(index)
            if coordinate is None or not any(
                low <= coordinate <= high for low, high in self.recoded
            ):
                return False
        return True

    def chunks(self, genome, name) -> Iterator[bytes]:
        """The coding strand from 5' to 3', in pieces of at most BLOCK bases."""
        for start, end, _, _ in self.segments:
            if self.strand == "+":
                position = start - 1
                while position < end:
                    upto = min(position + BLOCK, end)
                    yield genome.fetch(name, position, upto)
                    position = upto
            else:
                position = end
                while position > start - 1:
                    low = max(position - BLOCK, start - 1)
                    yield reverse_complement(genome.fetch(name, low, position))
                    position = low

    def scan(self, genome, name, table: CodonTable) -> Scan:
        """Find the first and last codon and the in-frame stops before the end.

        A stop codon covered by a recoded codon is not counted.
        """
        result = Scan()
        result.first = result.last = b""
        result.internal = 0
        result.first_internal = None
        skip = self.phase
        carry = b""
        offset = 0  # coding position of ``carry``
        pending: Optional[Tuple[int, bytes]] = None
        no_stop = table.no_stop.match
        last_position = -1
        for chunk in self.chunks(genome, name):
            if skip:
                drop = min(skip, len(chunk))
                chunk, skip = chunk[drop:], skip - drop
            data = carry + chunk
            size = len(data) - len(data) % 3
            if size:
                if not result.first:
                    result.first = data[:3]
                position = 0
                while position < size:
                    stop = no_stop(data, position, size).end()
                    if stop >= size:
                        break
                    if not self.covered(offset + stop, 3):
                        if pending is not None:
                            result.internal += 1
                            if result.first_internal is None:
                                result.first_internal = pending
                        pending = (offset + stop, data[stop : stop + 3])
                    position = stop + 3
                result.last = data[size - 3 : size]
                last_position = offset + size - 3
            carry = data[size:]
            offset += size
        if pending is not None and pending[0] != last_position:
            result.internal += 1
            if result.first_internal is None:
                result.first_internal = pending
        return result
