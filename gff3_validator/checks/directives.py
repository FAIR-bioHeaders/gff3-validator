"""Directive rules (GFF-DIR-001, -004 to -010) and the ##FASTA section.

GFF-DIR-002 (one ##sequence-region per seqid) and GFF-DIR-003 (###) need
state and are in :mod:`gff3_validator.checks.structure`.
"""

import re
from typing import List, Optional, Tuple

from gff3_validator.checks.syntax import INTEGER, show

KNOWN = frozenset(
    (
        "gff-version",
        "sequence-region",
        "feature-ontology",
        "attribute-ontology",
        "source-ontology",
        "species",
        "genome-build",
        "FASTA",
    )
)
ONTOLOGY = frozenset(("feature-ontology", "attribute-ontology", "source-ontology"))
# The two "preferred" forms in Other Syntax: ##species (https also accepted).
SPECIES = re.compile(
    r"https?://www\.ncbi\.nlm\.nih\.gov/Taxonomy/Browser/wwwtax\.cgi\?"
    r"(id=[0-9]+|name=[^\s&]+)"
)

# (rule id, message)
Problem = Tuple[str, str]


def split_directive(line):
    """Return ``(name, arguments)`` for a line starting with "##"."""
    words = line[2:].split()
    return (words[0], words[1:]) if words else ("", [])


def sequence_region(arguments) -> Tuple[Optional[str], Optional[tuple]]:
    """Check ``##sequence-region seqid start end`` (GFF-DIR-001).

    Returns ``(problem message or None, (seqid, start, end) or None)``.
    """
    if len(arguments) != 3:
        return (
            f"has {len(arguments)} fields, expected 'seqid start end'",
            None,
        )
    seqid, start, end = arguments
    if not (INTEGER.fullmatch(start) and INTEGER.fullmatch(end)):
        return "start and end are not whole numbers", None
    first, last = int(start), int(end)
    if first < 1:
        return f"start is {first}; coordinates are 1-based", None
    if first > last:
        return f"start {first} is greater than end {last}", None
    return None, (seqid, first, last)


def check_directive(name, arguments) -> List[Problem]:
    """Rules that need only the directive line itself."""
    if name == "species":
        value = " ".join(arguments)
        if not SPECIES.fullmatch(value):
            return [
                (
                    "GFF-DIR-007",
                    f"##species {show(value)} is not an NCBI Taxonomy browser URL "
                    "(the preferred format)",
                )
            ]
    elif name == "genome-build":
        if len(arguments) < 2:
            return [
                (
                    "GFF-DIR-008",
                    f"##genome-build gives {len(arguments)} of the 2 values "
                    "(source and build name)",
                )
            ]
    elif name in ONTOLOGY:
        uri = show(" ".join(arguments)) if arguments else "no URI"
        return [
            (
                "GFF-DIR-009",
                f"##{name} names {uri}; ontologies are not fetched during "
                "validation",
            )
        ]
    elif name not in KNOWN:
        return [
            ("GFF-DIR-010", f"directive {show('##' + name)} is not defined by GFF3")
        ]
    return []


class FastaSection:
    """Read the FASTA records after ##FASTA without keeping sequences.

    Only the record ids (the first word after ">", question for GFF-DIR-006)
    and their lengths are kept.
    """

    def __init__(self, record):
        self.record = record  # called with (id, length) for each record
        self.name = None
        self.header_line = 0
        self.length = 0
        self.has_sequence = False
        self.seen = {}
        self.orphan_reported = False

    def line(self, number, text) -> List[Tuple[str, Optional[int], str]]:
        if text.startswith(">"):
            problems = self._close()
            words = text[1:].split(None, 1)
            name = words[0] if words else ""
            self.header_line = number
            self.length = 0
            self.has_sequence = False
            if not name:
                self.name = None
                problems.append(("GFF-DIR-006", number, "FASTA header has no id"))
            elif name in self.seen:
                self.name = None
                problems.append(
                    (
                        "GFF-DIR-006",
                        number,
                        f"FASTA id {show(name)} is repeated (first at line "
                        f"{self.seen[name]})",
                    )
                )
            else:
                self.name = name
                self.seen[name] = number
            return problems
        if "\t" in text:
            return [("GFF-DIR-004", number, "feature line after ##FASTA")]
        if text.startswith("##"):
            return [("GFF-DIR-004", number, "directive after ##FASTA")]
        stripped = text.strip()
        if stripped == "" or text.startswith("#"):
            return []  # Blank and comment lines: question for GFF-DIR-004.
        if self.header_line == 0:
            if self.orphan_reported:
                return []
            self.orphan_reported = True
            return [
                ("GFF-DIR-006", number, "sequence line before the first FASTA header")
            ]
        self.has_sequence = True
        self.length += len(stripped)
        return []

    def _close(self):
        problems = []
        if self.header_line and not self.has_sequence:
            problems.append(
                ("GFF-DIR-006", self.header_line, "FASTA record has no sequence")
            )
        if self.name is not None:
            self.record(self.name, self.length)
            self.name = None
        return problems

    def finish(self):
        return self._close()
