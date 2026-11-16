"""The feature layer: a public index of the GFF3 rows below the header.

FHGM **K4** asks one question of a GFF3 file: does this ``featureId`` resolve to
exactly one local ``gene`` row? That is a question about the *feature layer* —
the tab-separated rows under the header — and it is not a catalogue rule, so it
is answered here rather than by a new rule id. See `docs/feature-index.md` for
the contract this module implements and the reasons for each decision.

Three boundaries are the whole design:

* **No header parsing.** The FHGFF3 header (``#~`` lines) belongs to the
  FAIR-bioHeaders toolkit; :mod:`gff3_validator.header` delegates to it. This
  module reads the layer below it and treats every ``#`` line, header included,
  as a comment.
* **No findings.** Nothing here emits a ``Finding``, changes a rule's verdict or
  touches the catalogue. Answering "how many rows carry this ID" is an
  enumeration, not a judgement about whether the file is valid GFF3.
* **An untrustworthy layer is never scored.** ``malformed-layer`` and
  ``absent-layer`` are neither a pass nor a rejection: a consumer that cannot
  see the feature rows must not certify the header that points at them, and must
  not indict it either. ``FeatureMatch.scored`` is ``False`` for both.

Like the rest of the core, this is standard library only and makes no network
requests.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from gff3_validator.checks.attributes import DIGITS, decode, parse_attributes
from gff3_validator.reader import InputError, iter_lines

# The six outcomes of index.resolve(); docs/feature-index.md states each one.
OUTCOME_FOUND = "found"
OUTCOME_NOT_FOUND = "not-found"
OUTCOME_DUPLICATE_ROW = "duplicate-row"
OUTCOME_NON_GENE_TARGET = "non-gene-target"
OUTCOME_MALFORMED_LAYER = "malformed-layer"
OUTCOME_ABSENT_LAYER = "absent-layer"

OUTCOMES = (
    OUTCOME_FOUND,
    OUTCOME_NOT_FOUND,
    OUTCOME_DUPLICATE_ROW,
    OUTCOME_NON_GENE_TARGET,
    OUTCOME_MALFORMED_LAYER,
    OUTCOME_ABSENT_LAYER,
)
# Outcomes that answer K4. A consumer may score these.
SCORED_OUTCOMES = (
    OUTCOME_FOUND,
    OUTCOME_NOT_FOUND,
    OUTCOME_DUPLICATE_ROW,
    OUTCOME_NON_GENE_TARGET,
)
# Outcomes that mean "the index could not answer". A consumer must carry these
# as not-checked: never a pass, never a rejection.
NOT_SCORED_OUTCOMES = (OUTCOME_MALFORMED_LAYER, OUTCOME_ABSENT_LAYER)

# The state of the layer itself: indexed (usable), malformed (rows that cannot
# be read) or absent (no layer to index, or an input that could not be read).
LAYER_INDEXED = "indexed"
LAYER_MALFORMED = "malformed"
LAYER_ABSENT = "absent"
LAYER_STATES = (LAYER_INDEXED, LAYER_MALFORMED, LAYER_ABSENT)

# Sequence bytes are not feature rows (GFF3 1.26, Column 9 / ##FASTA). The line
# has to be exactly this, as in the FHGM authoring checker and the JavaScript
# resolver, so that all three stop at the same place.
FASTA_DIRECTIVE = "##FASTA"
# The two spellings of the gene row type that a model pointer may target. This
# is a literal test of column 3: no ontology is loaded, and a narrower or broader
# term is not a gene row for this purpose.
GENE_ROW_TYPES = ("gene", "SO:0000704")


def is_gene_row_type(type):
    """Whether column 3 of a feature row spells the gene type K4 targets.

    ``gene`` (the SO term name) or ``SO:0000704`` (its accession); anything else,
    including a term that merely relates to a gene, is not a gene row.
    """
    return type in GENE_ROW_TYPES


@dataclass(frozen=True)
class FeatureRow:
    """One feature row of the layer, as far as the index reads it.

    ``id`` is the percent-decoded ``ID=`` value — the form pointers are compared
    in — and ``raw_id`` keeps it as written. ``start`` and ``end`` are integers
    when the columns hold whole numbers and ``None`` otherwise, which is a fact
    carried, not a judgement made: the syntax rules decide whether a coordinate
    is valid.
    """

    line: int
    seqid: str
    source: str
    type: str
    start: Optional[int]
    end: Optional[int]
    score: str
    strand: str
    phase: str
    raw_id: Optional[str] = None
    id: Optional[str] = None
    parents: Tuple[str, ...] = ()

    @property
    def has_id(self):
        """Whether the row carries an ``ID=`` this index can address."""
        return self.id is not None

    @property
    def is_gene(self):
        """Whether this row is a gene row (see :func:`is_gene_row_type`)."""
        return is_gene_row_type(self.type)

    def to_dict(self):
        return {
            "line": self.line,
            "seqid": self.seqid,
            "source": self.source,
            "type": self.type,
            "start": self.start,
            "end": self.end,
            "score": self.score,
            "strand": self.strand,
            "phase": self.phase,
            "raw_id": self.raw_id,
            "id": self.id,
            "parents": list(self.parents),
            "gene": self.is_gene,
        }

    def describe(self):
        """One text line: where the row is, on what, of what type, and its ID."""
        span = "-"
        if self.start is not None:
            span = str(self.start)
            if self.end is not None:
                span += f"-{self.end}"
        identifier = self.raw_id if self.raw_id is not None else "-"
        return (
            f"line {self.line}\t{self.seqid}\t{self.type}\t{span}{self.strand}"
            f"\tID={identifier}"
        )


@dataclass
class FeatureIndex:
    """The feature layer of one input, and what could be said about it.

    ``state`` is ``"indexed"`` when the rows can be trusted, ``"malformed"``
    when some row is not a nine-field feature row and ``"absent"`` when there is
    no layer to index. In the last two cases :meth:`resolve` reports a
    not-scored outcome instead of guessing. ``problems`` lists the rows it could
    not read; ``reason`` says why an absent layer is absent.
    """

    source: str
    state: str = LAYER_ABSENT
    rows: List[FeatureRow] = field(default_factory=list)
    problems: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    feature_rows: int = 0

    @property
    def usable(self):
        """Whether row counts can be trusted, which is whether K4 can be scored."""
        return self.state == LAYER_INDEXED

    @property
    def id_rows(self):
        """The rows a pointer can address: those that carry an ID."""
        return sum(1 for row in self.rows if row.id is not None)

    @property
    def rows_without_id(self):
        return sum(1 for row in self.rows if row.id is None)

    @property
    def gene_rows(self):
        return sum(1 for row in self.rows if row.is_gene)

    def _by_id(self):
        grouped = {}
        for row in self.rows:
            if row.id is not None:
                grouped.setdefault(row.id, []).append(row)
        return grouped

    def rows_for(self, feature_id):
        """The rows carrying ``feature_id``, percent-decoded on both sides.

        Returns an empty list when the layer is not usable, which is not the same
        as "no row carries it": ask :meth:`resolve` for the outcome, not this.
        """
        if not isinstance(feature_id, str):
            raise ValueError("feature_id must be a string")
        if not self.usable:
            return []
        return list(self._by_id().get(decode(feature_id), ()))

    def resolve(self, feature_id) -> "FeatureMatch":
        """Answer the K4 predicate for ``feature_id``."""
        if not isinstance(feature_id, str):
            raise ValueError("feature_id must be a string")
        if self.state == LAYER_ABSENT:
            return FeatureMatch(
                self.source,
                feature_id,
                decode(feature_id),
                OUTCOME_ABSENT_LAYER,
                self.reason or "no feature rows could be read from this input",
                (),
                self,
            )
        if self.state == LAYER_MALFORMED:
            return FeatureMatch(
                self.source,
                feature_id,
                decode(feature_id),
                OUTCOME_MALFORMED_LAYER,
                "the feature layer cannot be trusted: " + "; ".join(self.problems),
                (),
                self,
            )
        candidates = self.rows_for(feature_id)
        identifier = decode(feature_id)
        if not candidates:
            message = f"no local feature row carries the decoded ID {identifier!r}"
            outcome = OUTCOME_NOT_FOUND
        elif len(candidates) > 1:
            where = ", ".join(f"line {row.line} ({row.type})" for row in candidates)
            message = (
                f"{len(candidates)} local feature rows share the decoded ID "
                f"{identifier!r}, so it does not select one row: {where}"
            )
            outcome = OUTCOME_DUPLICATE_ROW
        elif candidates[0].is_gene:
            message = (
                f"one local gene row carries the decoded ID {identifier!r} "
                f"(line {candidates[0].line})"
            )
            outcome = OUTCOME_FOUND
        else:
            message = (
                f"the single local row carrying the decoded ID {identifier!r} is "
                f"of type {candidates[0].type!r} (line {candidates[0].line}), "
                "not a gene row"
            )
            outcome = OUTCOME_NON_GENE_TARGET
        return FeatureMatch(
            self.source,
            feature_id,
            identifier,
            outcome,
            message,
            tuple(candidates),
            self,
        )

    def to_dict(self, max_rows=None):
        shown = self.rows if max_rows is None else self.rows[:max_rows]
        return {
            "source": self.source,
            "layer": self.state,
            "usable": self.usable,
            "feature_rows": self.feature_rows,
            "id_rows": self.id_rows,
            "rows_without_id": self.rows_without_id,
            "gene_rows": self.gene_rows,
            "reason": self.reason,
            "problems": list(self.problems),
            "rows": [row.to_dict() for row in shown],
            "truncated_rows": max(0, len(self.rows) - len(shown)),
        }


@dataclass(frozen=True)
class FeatureMatch:
    """One ``featureId`` resolved against one feature layer.

    ``outcome`` is one of the six in :data:`OUTCOMES`. ``scored`` says whether a
    consumer may act on it, and ``passes`` is true only for ``found``; the two
    not-scored outcomes are neither.
    """

    source: str
    feature_id: str
    decoded_id: str
    outcome: str
    message: str
    rows: Tuple[FeatureRow, ...] = ()
    index: Optional[FeatureIndex] = field(default=None, compare=False, repr=False)

    @property
    def scored(self):
        """Whether this outcome answers K4 (true) or reports that it could not (false)."""
        return self.outcome in SCORED_OUTCOMES

    @property
    def passes(self):
        """K4 satisfied: exactly one local gene row carries the decoded ID."""
        return self.outcome == OUTCOME_FOUND

    def to_dict(self):
        return {
            "source": self.source,
            "layer": None if self.index is None else self.index.state,
            "feature_id": self.feature_id,
            "decoded_id": self.decoded_id,
            "outcome": self.outcome,
            "scored": self.scored,
            "passes": self.passes,
            "message": self.message,
            "rows": [row.to_dict() for row in self.rows],
        }


def build_feature_index(source, name=None) -> FeatureIndex:
    """Index the feature layer of ``source`` (a path, ``"-"`` or a binary stream).

    Never raises for an input it cannot read: an unreadable or empty layer is
    ``absent`` with the reason, so that a consumer gets a not-scored outcome
    rather than an exception it might swallow as a pass.
    """
    index = FeatureIndex(source=str(name or source))
    rows, problems = index.rows, index.problems
    stopped_at_fasta = False
    try:
        for number, line in iter_lines(source):
            if line.endswith("\r"):
                line = line[:-1]
            if line == FASTA_DIRECTIVE:
                stopped_at_fasta = True
                break
            if line.strip() == "" or line.startswith("#"):
                continue
            index.feature_rows += 1
            columns = line.split("\t")
            if len(columns) != 9:
                problems.append(
                    f"line {number}: a feature row holds nine tab-separated "
                    f"fields, this line holds {len(columns)}"
                )
                continue
            # The catalogue's own column-9 reader, so that there is exactly one
            # place that decides how an ID is percent-decoded. Its problems are
            # the rules' business: this index reads facts and reports no findings.
            attributes, _ = parse_attributes(columns[8])
            rows.append(
                FeatureRow(
                    line=number,
                    seqid=columns[0],
                    source=columns[1],
                    type=columns[2],
                    start=_whole(columns[3]),
                    end=_whole(columns[4]),
                    score=columns[5],
                    strand=columns[6],
                    phase=columns[7],
                    raw_id=attributes.tags.get("ID"),
                    id=attributes.id,
                    parents=tuple(attributes.parents),
                )
            )
    except InputError as error:
        # An input that stops midway may have lost rows and may have lost the
        # defect that made them unreadable: no count is trustworthy, so the
        # layer is absent rather than malformed, and nothing is scored.
        index.state = LAYER_ABSENT
        opening = str(error).startswith("cannot open ")
        index.reason = (
            f"the feature layer could not be read: {error}"
            if opening
            else f"the input could not be read completely: {error}"
        )
        rows.clear()
        problems.clear()
        return index
    if problems:
        index.state = LAYER_MALFORMED
        index.reason = (
            f"{len(problems)} line(s) of the feature layer are not nine-field "
            "feature rows"
        )
    elif index.feature_rows:
        # Rows were read, even if none of them carries an ID: the layer is there
        # and a pointer can be answered (as "not-found" for an anonymous layer).
        index.state = LAYER_INDEXED
    else:
        index.state = LAYER_ABSENT
        index.reason = "the input holds no feature rows" + (
            " before ##FASTA" if stopped_at_fasta else ""
        )
    return index


def resolve_feature_id(source, feature_id, name=None) -> FeatureMatch:
    """Index ``source`` and resolve ``feature_id`` against it in one call."""
    return build_feature_index(source, name=name).resolve(feature_id)


def _whole(text):
    """The integer value of a coordinate column, or None when it is not one."""
    return int(text) if DIGITS.fullmatch(text) else None


__all__ = [
    "FASTA_DIRECTIVE",
    "FEATURE_ROW_FIELDS",
    "GENE_ROW_TYPES",
    "LAYER_ABSENT",
    "LAYER_INDEXED",
    "LAYER_MALFORMED",
    "LAYER_STATES",
    "NOT_SCORED_OUTCOMES",
    "OUTCOME_ABSENT_LAYER",
    "OUTCOME_DUPLICATE_ROW",
    "OUTCOME_FOUND",
    "OUTCOME_MALFORMED_LAYER",
    "OUTCOME_NON_GENE_TARGET",
    "OUTCOME_NOT_FOUND",
    "OUTCOMES",
    "SCORED_OUTCOMES",
    "FeatureIndex",
    "FeatureMatch",
    "FeatureRow",
    "build_feature_index",
    "is_gene_row_type",
    "resolve_feature_id",
]

# The keys of FeatureRow.to_dict(), for consumers that read the JSON form.
FEATURE_ROW_FIELDS = (
    "line",
    "seqid",
    "source",
    "type",
    "start",
    "end",
    "score",
    "strand",
    "phase",
    "raw_id",
    "id",
    "parents",
    "gene",
)
