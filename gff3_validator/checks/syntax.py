"""Per-line syntax rules for GFF3 directives and feature columns 1 to 8.

These rules keep no state between feature lines, so memory does not grow
with the file.
"""

import re
from typing import Iterator, Tuple

COLUMN_NAMES = (
    "seqid",
    "source",
    "type",
    "start",
    "end",
    "score",
    "strand",
    "phase",
    "attributes",
)
VERSION = re.compile(r"##gff-version[ \t]+3(\.[0-9]+){0,2}[ \t\r]*")
INTEGER = re.compile(r"[0-9]+")
FLOAT = re.compile(r"[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?")
STRANDS = ("+", "-", ".", "?")
PHASES = ("0", "1", "2", ".")
CDS_TYPES = ("CDS", "SO:0000316")

# (rule id, field number or None, message)
Problem = Tuple[str, object, str]


def show(value, limit=60):
    """Quote an untrusted value for a message: escaped and shortened."""
    text = value.encode("unicode_escape").decode("ascii")
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return f'"{text}"'


def is_version_line(line):
    return VERSION.fullmatch(line) is not None


def check_feature(line) -> Iterator[Problem]:
    """Check one feature line (not blank, comment, directive or FASTA)."""
    fields = line.split("\t")
    if len(fields) != 9:
        hint = (
            "; the line has no tabs, so columns may be separated by spaces"
            if len(fields) == 1
            else ""
        )
        yield (
            "GFF-SYN-003",
            None,
            f"found {len(fields)} tab-separated columns, expected 9{hint}",
        )
        return
    for number, value in enumerate(fields, start=1):
        if value == "":
            yield (
                "GFF-SYN-004",
                number,
                f"column {number} ({COLUMN_NAMES[number - 1]}) is empty",
            )
    seqid, source, type_, start, end, score, strand, phase, attributes = fields

    coordinates = []
    for number, value in ((4, start), (5, end)):
        if value == "":
            continue
        if INTEGER.fullmatch(value):
            coordinates.append(int(value))
        else:
            yield (
                "GFF-SYN-013",
                number,
                f"{COLUMN_NAMES[number - 1]} {show(value)} is not a whole number",
            )
    if len(coordinates) == 2:
        first, last = coordinates
        if first < 1:
            yield ("GFF-SYN-014", 4, f"start is {first}; coordinates are 1-based")
        elif first > last:
            yield ("GFF-SYN-015", 5, f"start {first} is greater than end {last}")

    if score not in ("", ".") and not FLOAT.fullmatch(score):
        yield ("GFF-SYN-016", 6, f"score {show(score)} is not a number or '.'")
    if strand != "" and strand not in STRANDS:
        yield ("GFF-SYN-017", 7, f"strand {show(strand)} is not +, -, . or ?")
    if phase != "" and phase not in PHASES:
        yield ("GFF-SYN-018", 8, f"phase {show(phase)} is not 0, 1, 2 or '.'")
    elif phase == "." and type_ in CDS_TYPES:
        yield ("GFF-SYN-019", 8, f"{type_} feature has no phase ('.')")
