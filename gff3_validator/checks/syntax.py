"""Per-line syntax rules for GFF3 directives and feature columns 1 to 8.

These rules keep no state between feature lines, so memory does not grow
with the file.
"""

import re
from typing import Iterator, List, Tuple

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
# CDS by label and accession. The engine passes the SO layer's set (CDS and
# its is_a subtypes, question 6), which always includes these two.
CDS_TYPES = frozenset(("CDS", "SO:0000316"))
# Control characters other than tab (tab separates columns), GFF-SYN-005.
CONTROL = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
BAD_PERCENT = re.compile(r"%(?![0-9A-Fa-f]{2})")
PERCENT = re.compile(r"%([0-9A-Fa-f]{2})")
# Whitespace that is not a control character (those are GFF-SYN-005).
SPACE = re.compile(r"[^\S\x00-\x1f\x7f]")
# GFF-SYN-007 heuristic: whitespace then "#" in column 9.
COMMENT = re.compile(r"\s#")
# Octets that may be percent-encoded in any column (GFF-SYN-009).
ENCODABLE = frozenset([*range(0x00, 0x20), 0x7F, 0x25])
# Column 1: characters outside [a-zA-Z0-9.:^*$@!+_?-|] must be escaped, so
# encoding them is allowed (the list is read literally, question 3).
SEQID_PLAIN = frozenset(
    map(
        ord,
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:^*$@!+_?-|",
    )
)

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


def check_feature(line, cds_types=CDS_TYPES) -> Iterator[Problem]:
    """Check one feature line (not blank, comment, directive or FASTA)."""
    fields = line.split("\t")
    yield from check_columns(fields, line, cds_types)


def encoded_inside(value, octets):
    """Return the first percent-encoded octet in ``value`` that is in ``octets``."""
    for match in PERCENT.finditer(value):
        if int(match.group(1), 16) in octets:
            return match.group(0)
    return None


def encoded_outside(value, octets):
    """Return the first percent-encoded octet in ``value`` not in ``octets``."""
    for match in PERCENT.finditer(value):
        if int(match.group(1), 16) not in octets:
            return match.group(0)
    return None


def check_encoding(fields, line) -> List[Problem]:
    """GFF-SYN-005, -008 and -009 (columns 1 to 8; column 9 is checked for
    over-encoding by the attribute rules, which know the reserved tags)."""
    problems = []
    if CONTROL.search(line):
        for number, value in enumerate(fields, start=1):
            match = CONTROL.search(value)
            if match:
                problems.append(
                    (
                        "GFF-SYN-005",
                        number,
                        f"unescaped control character "
                        f"{show(match.group(0))} in column {number}",
                    )
                )
    if "%" in line:
        for number, value in enumerate(fields, start=1):
            if "%" not in value:
                continue
            match = BAD_PERCENT.search(value)
            if match:
                problems.append(
                    (
                        "GFF-SYN-008",
                        number,
                        f"'%' in {show(value)} is not followed by two hexadecimal "
                        "digits",
                    )
                )
            if number == 9:
                continue
            # In column 1 encoding is required outside the seqid set, so only
            # encoding a character inside it is reported.
            encoded = (
                encoded_inside(value, SEQID_PLAIN)
                if number == 1
                else encoded_outside(value, ENCODABLE)
            )
            if encoded:
                problems.append(
                    (
                        "GFF-SYN-009",
                        number,
                        f"{encoded} in column {number} encodes a character that "
                        "is written literally",
                    )
                )
    return problems


def check_columns(fields, line, cds_types=CDS_TYPES) -> Iterator[Problem]:
    """Check the columns of a feature line split on tabs.

    ``cds_types`` are the column 3 values that need a phase (GFF-SYN-019).
    """
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
    yield from check_encoding(fields, line)
    if SPACE.search(seqid):
        yield ("GFF-SYN-010", 1, f"seqid {show(seqid)} contains unescaped whitespace")
    if type_ == ".":
        yield ("GFF-SYN-012", 3, "type is undefined ('.')")

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
    elif phase == "." and type_ in cds_types:
        yield ("GFF-SYN-019", 8, f"{type_} feature has no phase ('.')")
    if "#" in attributes and COMMENT.search(attributes):
        yield (
            "GFF-SYN-007",
            9,
            "column 9 contains ' #', possibly an end-of-line comment",
        )


def coordinates(start, end):
    """Return ``(start, end)`` as integers when both are valid, else None."""
    if INTEGER.fullmatch(start) and INTEGER.fullmatch(end):
        first, last = int(start), int(end)
        if 1 <= first <= last:
            return first, last
    return None
