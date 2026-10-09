"""Column 9 (attributes) rules: GFF-ATT-001 to GFF-ATT-016.

These rules look at one line at a time. :func:`parse_attributes` returns the
attributes it could read, so that the structure rules can use ID, Parent,
Derives_from and Is_circular without parsing the column twice.
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import unquote

from gff3_validator.checks.syntax import ENCODABLE, encoded_outside, show

# GFF3 1.26, Column 9: tags with predefined meanings.
RESERVED = (
    "ID",
    "Name",
    "Alias",
    "Parent",
    "Target",
    "Gap",
    "Derives_from",
    "Note",
    "Dbxref",
    "Ontology_term",
    "Is_circular",
)
RESERVED_BY_LOWER = {tag.lower(): tag for tag in RESERVED}
# "In addition to Parent, the Alias, Note, Dbxref and Ontology_term attributes
# can have multiple values."
MULTI_VALUED = frozenset(("Parent", "Alias", "Note", "Dbxref", "Ontology_term"))
# Reserved tags whose commas are checked by GFF-ATT-006. Derives_from is left
# out until SO answers question 5 (docs/questions-for-SO.md).
SINGLE_VALUED = frozenset(("ID", "Name", "Target", "Gap", "Is_circular"))
XREF_TAGS = ("Dbxref", "Ontology_term")
GAP_OPERATION = re.compile(r"([MIDFR])([0-9]+)")
DIGITS = re.compile(r"[0-9]+")

# Characters that GFF3 says are percent-encoded; "no other characters may be
# encoded" (GFF-SYN-009). In column 9 also the reserved characters ; = & ,.
ENCODABLE_COLUMN9 = ENCODABLE | {ord(";"), ord("="), ord("&"), ord(",")}

# (rule id, message); all attribute problems are in column 9.
Problem = Tuple[str, str]


def decode(value):
    """Percent-decode a value (UTF-8); text without "%" is returned as is."""
    return unquote(value) if "%" in value else value


class Attributes:
    """The attributes of one feature line, as far as they could be read.

    ``tags`` maps each tag (first occurrence) to its raw value. The decoded
    values used by the structure rules are in ``id``, ``parents`` and
    ``derives_from``.
    """

    __slots__ = ("tags", "id", "parents", "derives_from", "circular", "target")

    def __init__(self):
        self.tags: Dict[str, str] = {}
        self.id: Optional[str] = None
        self.parents: List[str] = []
        self.derives_from: List[str] = []
        self.circular = False
        self.target = None  # (start, end) when Target is well formed


def parse_attributes(text, start=None, end=None):
    """Check column 9 and return ``(attributes, problems)``.

    ``start`` and ``end`` are the feature coordinates when they are valid; they
    are needed for the Gap length check (GFF-ATT-013).
    """
    attributes = Attributes()
    problems: List[Problem] = []
    if text == ".":
        return attributes, problems
    parts = text.split(";")
    tags = attributes.tags
    for position, part in enumerate(parts):
        if part == "":
            if position == len(parts) - 1:
                if position:
                    problems.append(("GFF-ATT-003", "column 9 ends with ';'"))
            else:
                problems.append(("GFF-ATT-003", "empty attribute pair (';;')"))
            continue
        tag, equals, value = part.partition("=")
        if not equals:
            problems.append(
                ("GFF-ATT-001", f"{show(part)} is not a tag=value pair (no '=')")
            )
            continue
        if tag == "":
            problems.append(("GFF-ATT-002", f"{show(part)} has an empty tag"))
            continue
        bad = [c for c in "=&," if c in tag] + [c for c in "=&" if c in value]
        if bad:
            shown = " and ".join(f"'{c}'" for c in dict.fromkeys(bad))
            problems.append(
                (
                    "GFF-ATT-005",
                    f"unescaped {shown} in {show(part)}; reserved characters in "
                    "column 9 are percent-encoded",
                )
            )
        if tag in tags:
            problems.append(
                ("GFF-ATT-004", f"tag {show(tag)} appears more than once on the line")
            )
            continue
        tags[tag] = value
        if tag not in RESERVED:
            reserved = RESERVED_BY_LOWER.get(tag.lower())
            if reserved is not None:
                problems.append(
                    (
                        "GFF-ATT-008",
                        f"tag {show(tag)} is not the reserved tag {reserved} "
                        "(tags are case sensitive)",
                    )
                )
            elif tag[0].isupper():
                problems.append(
                    (
                        "GFF-ATT-007",
                        f"tag {show(tag)} begins with an upper-case letter but is "
                        "not a reserved tag",
                    )
                )
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            problems.append(("GFF-ATT-009", f"value of {tag} is quoted"))
        encoded = encoded_outside(value, ENCODABLE_COLUMN9) if "%" in value else None
        if encoded and not (tag == "Target" and encoded == "%20"):
            problems.append(
                (
                    "GFF-SYN-009",
                    f"{encoded} in the value of {show(tag)} encodes a character "
                    "that is written literally",
                )
            )
    _check_reserved(attributes, problems, start, end)
    return attributes, problems


def _check_reserved(attributes, problems, start, end):
    tags = attributes.tags
    for tag in SINGLE_VALUED:
        value = tags.get(tag)
        if value is not None and "," in value:
            problems.append(
                (
                    "GFF-ATT-006",
                    f"{tag} has one value; escape the comma in {show(value)} as %2C",
                )
            )
    if "ID" in tags and tags["ID"]:
        attributes.id = decode(tags["ID"])
    if "Parent" in tags:
        attributes.parents = [decode(v) for v in tags["Parent"].split(",") if v]
    if "Derives_from" in tags:
        # Commas are read as separators here, so that Derives_from=a,b is not
        # reported as an unresolved reference while question 5 is open.
        attributes.derives_from = [
            decode(v) for v in tags["Derives_from"].split(",") if v
        ]
    for tag in XREF_TAGS:
        for value in tags.get(tag, "").split(","):
            if value == "":
                continue
            dbtag, colon, identifier = value.partition(":")
            if not colon or not dbtag or not identifier:
                problems.append(
                    (
                        "GFF-ATT-014",
                        f"{tag} value {show(value)} is not of the form DBTAG:ID",
                    )
                )
    circular = tags.get("Is_circular")
    if circular is not None:
        if circular == "true":
            attributes.circular = True
        elif circular != "false":
            problems.append(
                ("GFF-ATT-016", f'Is_circular is {show(circular)}, not "true"')
            )
    target = tags.get("Target")
    if target is not None:
        attributes.target = _check_target(target, problems)
    gap = tags.get("Gap")
    if gap:
        operations = _check_gap(gap, problems)
        if target is None:
            problems.append(("GFF-ATT-012", "Gap is given without a Target"))
        elif operations and attributes.target and start is not None:
            _check_gap_lengths(operations, start, end, attributes.target, problems)


def _check_target(value, problems):
    fields = [field for field in value.split(" ") if field]
    problem = None
    if len(fields) not in (3, 4):
        problem = (
            f"has {len(fields)} space-separated fields, expected "
            "target_id start end [strand]"
        )
        if len(fields) == 1 and "+" in value:
            problem += " ('+' does not stand for a space)"
        elif len(fields) > 4:
            problem += " (spaces in target_id are escaped as %20)"
    elif not (DIGITS.fullmatch(fields[1]) and DIGITS.fullmatch(fields[2])):
        problem = "start and end are not whole numbers"
    elif int(fields[1]) < 1 or int(fields[2]) < 1:
        problem = "start and end are 1-based (at least 1)"
    elif len(fields) == 4 and fields[3] not in ("+", "-"):
        problem = f"strand {show(fields[3])} is not + or -"
    if problem:
        problems.append(("GFF-ATT-010", f"Target {show(value)} {problem}"))
        return None
    return int(fields[1]), int(fields[2])


def _check_gap(value, problems):
    operations = []
    for token in value.split(" "):
        if token == "":
            continue
        match = GAP_OPERATION.fullmatch(token)
        if not match or int(match.group(2)) == 0:
            problems.append(
                (
                    "GFF-ATT-011",
                    f"Gap operation {show(token)} is not a code M, I, D, F or R "
                    "followed by a positive length",
                )
            )
            return None
        operations.append((match.group(1), int(match.group(2))))
    return operations


def _check_gap_lengths(operations, start, end, target, problems):
    totals = {"M": 0, "I": 0, "D": 0, "F": 0, "R": 0}
    for code, length in operations:
        totals[code] += length
    reference = end - start + 1
    target_length = abs(target[1] - target[0]) + 1
    m, i, d, f, r = (totals[c] for c in "MIDFR")
    nucleotide = f == 0 and r == 0 and m + d == reference and m + i == target_length
    protein = 3 * (m + d) + f - r == reference and m + i == target_length
    if not (nucleotide or protein):
        problems.append(
            (
                "GFF-ATT-013",
                f"Gap describes a reference of {m + d} (or {3 * (m + d) + f - r} "
                f"bases for a protein target) and a target of {m + i}, but the "
                f"feature is {reference} bases and the Target {target_length} long",
            )
        )
