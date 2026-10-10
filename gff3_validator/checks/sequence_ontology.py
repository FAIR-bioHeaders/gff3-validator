"""Sequence Ontology rules SO-001 to SO-006, SO-008, SO-009 and GFF-SYN-020.

The type in column 3 is looked up in the SO release in use
(:mod:`gff3_validator.ontology`), following the proposed answers in
docs/questions-for-SO.md (pending SO review):

- question 14: the exact label or accession matches (case-sensitive); a case
  variant or EXACT synonym is a warning that names the label (SO-005); a type
  that is neither is an error (SO-001), since the specification constrains
  column 3 to an SO term or accession; a malformed accession is SO-002; a
  term that is not an is_a descendant of sequence_feature is a warning
  (SO-003);
- question 13: an obsolete term is a warning with its replacement (SO-004),
  and a term outside SOFA is a note (SO-009);
- question 15: a Parent is accepted when the child's type is part_of (or
  member_of) the Parent's type, through is_a inheritance and transitivity;
  anything else is a warning (SO-006);
- question 16: Derives_from is not type-checked (SO-007 stays planned);
- question 6: a phase on a feature whose type is not CDS or an is_a subtype
  of it is a warning (GFF-SYN-020, a core rule that needs SO); CDS subtypes
  need a phase like CDS (GFF-SYN-019, checked with the syntax rules).

Findings about a type, or about a pair of child and Parent types, are
reported once, at the first line, with the number of further lines, so a file
using one unknown type throughout gives one finding. Results are memoized per
distinct type (at most :data:`MAX_TYPES` of them; beyond that each line is
reported on its own), and Parent references to IDs not defined yet are kept
per referenced ID and child type until the ID appears.
"""

import difflib
from typing import Dict, Iterator, List, Optional, Tuple

from gff3_validator.checks.attributes import decode
from gff3_validator.checks.structure import Structure, show_id
from gff3_validator.ontology import (
    ACCESSION,
    ACCESSION_LIKE,
    SEQUENCE_FEATURE,
    Ontology,
)

CDS = "SO:0000316"
EXON = "SO:0000147"
RECODED_CODON = "SO:0000145"
MAX_TYPES = 4096
MAX_SUGGESTED = 100  # distinct unknown types that get close-match suggestions
UNDEFINED = ("", ".")
PHASES = ("0", "1", "2")

# (rule id, line or None, message)
Problem = Tuple[str, object, str]
# (rule id, key, message) for a finding about a type, before it has a line.
Note = Tuple[str, str, str]


class TypeInfo:
    """What the SO layer knows about one column 3 value.

    ``term`` is the resolved term (exact, or a unique case variant or
    synonym), ``current`` the same unless the term is obsolete, ``phase_free``
    whether a phase is reported (GFF-SYN-020), and ``notes`` the findings
    about the type itself.
    """

    __slots__ = ("term", "current", "phase_free", "notes")

    def __init__(self, term: Optional[str], notes: List[Note], ontology, cds_terms):
        self.term = term
        self.notes = notes
        current = term if term is not None and not ontology.is_obsolete(term) else None
        self.current = current
        self.phase_free = current is not None and current not in cds_terms


class SequenceOntology:
    def __init__(self, ontology: Ontology, structure: Structure):
        self.ontology = ontology
        self.structure = structure
        self.release = ontology.description
        self.types: Dict[str, TypeInfo] = {}
        self.suggested = 0
        # (rule, key) -> [message, first line, count]
        self.summary: Dict[Tuple[str, str], list] = {}
        # Parent ID not defined yet -> {child type: [first line, count]}.
        self.pending: Dict[str, Dict[str, list]] = {}
        self.edges: Dict[Tuple[str, str], Optional[bool]] = {}
        self.cds_terms = ontology.descendants(CDS)
        self.cds_types = ontology.type_names(CDS)
        self.exon_types = ontology.type_names(EXON)
        self.recoded_types = ontology.type_names(RECODED_CODON)

    # -- types ------------------------------------------------------------

    def info(self, type_) -> TypeInfo:
        found = self.types.get(type_)
        if found is None:
            found = self._classify(type_)
            if len(self.types) < MAX_TYPES:
                self.types[type_] = found
        return found

    def term_of(self, type_) -> Optional[str]:
        """The SO term a column 3 value names, if it can be resolved."""
        if type_ in UNDEFINED:
            return None
        return self.info(type_).term

    def _show(self, identifier):
        return f"{show_id(self.ontology.name(identifier))} ({identifier})"

    def _classify(self, raw) -> TypeInfo:
        ontology = self.ontology
        value = decode(raw)
        shown = show_id(raw)
        notes: List[Note] = []
        term = ontology.exact(value)
        if term is None and ACCESSION_LIKE.match(value):
            if not ACCESSION.fullmatch(value):
                notes.append(
                    (
                        "SO-002",
                        raw,
                        f"type {shown} is not a well-formed SO accession "
                        "(SO: and seven digits, for example SO:0000704)",
                    )
                )
                return self._info(None, notes)
            notes.append(
                ("SO-001", raw, f"type {shown} is not an accession in {self.release}")
            )
            return self._info(None, notes)
        if term is None:
            near = ontology.near(value)
            if not near:
                hint = self._suggest(value)
                notes.append(
                    (
                        "SO-001",
                        raw,
                        f"type {shown} is not a term name or accession in "
                        f"{self.release}{hint}",
                    )
                )
                return self._info(None, notes)
            labels = ", ".join(self._show(identifier) for identifier in near[:3])
            how = (
                "differs only by case from"
                if any(
                    ontology.name(identifier).casefold() == value.casefold()
                    for identifier in near
                )
                else "is an EXACT synonym of"
            )
            if len(near) > 1:
                notes.append(
                    (
                        "SO-005",
                        raw,
                        f"type {shown} {how} several SO terms: {labels}; use "
                        "the label of the one meant",
                    )
                )
                return self._info(None, notes)
            notes.append(
                ("SO-005", raw, f"type {shown} {how} the SO label {labels}; use it")
            )
            term = near[0]
        if ontology.is_obsolete(term):
            replaced_by, consider = ontology.replacements(term)
            if replaced_by:
                hint = "replaced by " + ", ".join(map(self._show, replaced_by))
            elif consider:
                hint = "consider " + ", ".join(map(self._show, consider))
            else:
                hint = "no replacement is given"
            notes.append(
                (
                    "SO-004",
                    raw,
                    f"type {shown} is obsolete in {self.release}; {hint}",
                )
            )
            return self._info(term, notes)
        if not ontology.is_a(term, SEQUENCE_FEATURE):
            notes.append(
                (
                    "SO-003",
                    raw,
                    f"type {shown} ({term}) is not sequence_feature or an is_a "
                    "subtype of it, so it is not a located sequence feature",
                )
            )
        elif not ontology.in_subset(term):
            notes.append(
                (
                    "SO-009",
                    raw,
                    f"type {shown} ({term}) is not in SOFA, the SO subset for "
                    "feature annotation",
                )
            )
        return self._info(term, notes)

    def _info(self, term, notes):
        return TypeInfo(term, notes, self.ontology, self.cds_terms)

    def _suggest(self, value):
        if self.suggested >= MAX_SUGGESTED:
            return ""
        self.suggested += 1
        close = difflib.get_close_matches(
            value, list(self.ontology.by_label), n=3, cutoff=0.75
        )
        if not close:
            return ""
        return "; did you mean " + " or ".join(map(show_id, close)) + "?"

    # -- per line -----------------------------------------------------------

    def _note(self, rule, key, message, line, count=1):
        """Count a finding under ``(rule, key)``; return it as a Problem to
        report at once only when too many keys are kept already."""
        entry = self.summary.get((rule, key))
        if entry is not None:
            entry[2] += count
            return None
        if len(self.summary) >= MAX_TYPES * 4:
            if count > 1:
                message += f" (and {count - 1} more lines like this)"
            return (rule, line, message)
        self.summary[(rule, key)] = [message, line, count]
        return None

    def feature(self, line, type_, phase, attributes) -> List[Problem]:
        """The findings to report at once for one feature line (most are
        counted and reported by :meth:`finish`)."""
        out: List[Problem] = []
        if type_ not in UNDEFINED:
            info = self.types.get(type_) or self.info(type_)
            for rule, key, message in info.notes:
                direct = self._note(rule, key, message, line)
                if direct is not None:
                    out.append(direct)
            if info.phase_free and phase in PHASES:
                direct = self._note(
                    "GFF-SYN-020",
                    type_,
                    f"phase {phase} on a feature of type {show_id(type_)}; phase "
                    "is defined only for CDS (and its SO subtypes)",
                    line,
                )
                if direct is not None:
                    out.append(direct)
            if info.current is not None and attributes.parents:
                edges = self.edges
                type_of = self.structure.type_of
                for parent in attributes.parents:
                    parent_type = type_of(parent)
                    if parent_type is None:
                        self._pending(line, type_, parent)
                    elif edges.get((type_, parent_type), False) is False:
                        self._edge(out, line, type_, parent, parent_type)
            if self.pending:
                identifier = attributes.id
                waiting = self.pending.pop(identifier, None) if identifier else None
                if waiting:
                    for child_type, (first, count) in waiting.items():
                        self._edge(out, first, child_type, identifier, type_, count)
        value = attributes.tags.get("Ontology_term")
        if value:
            self._ontology_terms(out, line, value)
        return out

    def _pending(self, line, child_type, parent):
        """Keep a Parent reference to an ID not defined yet."""
        waiting = self.pending.setdefault(parent, {})
        entry = waiting.get(child_type)
        if entry is None:
            waiting[child_type] = [line, 1]
        else:
            entry[1] += 1

    def _edge(self, out, line, child_type, parent, parent_type, count=1):
        if self.allowed(child_type, parent_type) is not False:
            return
        child = self.term_of(child_type)
        message = (
            f"a feature of type {show_id(child_type)} has the Parent "
            f"{show_id(parent)} of type {show_id(parent_type)}, but "
            f"{self.ontology.name(child)} is not "
            f"part_of {self.ontology.name(self.term_of(parent_type))} in SO "
            "(directly, through is_a or transitively)"
        )
        key = child_type + "\t" + parent_type
        direct = self._note("SO-006", key, message, line, count)
        if direct is not None:
            out.append(direct)

    def allowed(self, child_type, parent_type) -> Optional[bool]:
        """Whether SO allows a Parent of ``parent_type`` for ``child_type``
        (question 15), or None when either type cannot be resolved or is
        obsolete. Memoized per pair of column 3 values."""
        key = (child_type, parent_type)
        try:
            return self.edges[key]
        except KeyError:
            pass
        child = self.term_of(child_type)
        parent = self.term_of(parent_type)
        result = None
        if child is not None and parent is not None:
            ontology = self.ontology
            if not (ontology.is_obsolete(child) or ontology.is_obsolete(parent)):
                result = ontology.part_of(child, parent)
        if len(self.edges) < MAX_TYPES * 4:
            self.edges[key] = result
        return result

    def _ontology_terms(self, out, line, value):
        for item in value.split(","):
            item = decode(item).strip()
            if not item.startswith("SO:"):
                continue
            if not ACCESSION.fullmatch(item):
                message = (
                    f"Ontology_term value {show_id(item)} is not a well-formed "
                    "SO accession (SO: and seven digits)"
                )
            elif item not in self.ontology.terms:
                message = (
                    f"Ontology_term value {show_id(item)} is not a term in "
                    f"{self.release}"
                )
            else:
                continue
            direct = self._note("SO-008", item, message, line)
            if direct is not None:
                out.append(direct)

    # -- end of file ------------------------------------------------------------

    def finish(self) -> Iterator[Problem]:
        """The summarised findings, one per type or pair, at the first line."""
        self.pending.clear()
        for (rule, _), (message, line, count) in self.summary.items():
            if count > 1:
                message += f" (and {count - 1} more lines like this)"
            yield (rule, line, message)
        self.summary.clear()
