"""Checks of the AgBioData GFF3 profile (``profiles/agbiodata.yaml``).

Each rule cites a statement of the AgBioData GFF3 working group
recommendations (Recommendations.md, CC0-1.0); the profile file gives the
section. The checker runs after the core rules on each line and keeps its own
state:

- the extent (lowest start, highest end) of every ID, in two ``array``
  columns indexed like the core structure rules' ID index (16 bytes per ID),
  for AGB-003;
- children whose Parent is not defined yet, per Parent ID (at most
  ``MAX_DEFERRED`` of them; beyond that AGB-003 is reported as partial), for
  AGB-003 and AGB-004;
- one summary entry per rule (or per rule and type) for the rules reported
  once with a count.
"""

import re
from array import array
from typing import Dict, List, Optional, Tuple

from gff3_validator.checks.attributes import decode
from gff3_validator.checks.syntax import FLOAT, PERCENT, SEQID_PLAIN, show

RULES = (
    "AGB-001",
    "AGB-002",
    "AGB-003",
    "AGB-004",
    "AGB-005",
    "AGB-006",
    "AGB-007",
    "AGB-008",
    "AGB-009",
    "AGB-010",
    "AGB-011",
    "AGB-012",
    "AGB-013",
)
CDS = "SO:0000316"
EXON = "SO:0000147"
POLYPEPTIDE = "SO:0000104"
MAX_DEFERRED = 100_000
ONTOLOGY_DIRECTIVES = ("feature-ontology", "attribute-ontology", "source-ontology")
OBO_PURL = re.compile(r"https?://purl\.obolibrary\.org/obo/\S+")
NCBITAXON = re.compile(r"NCBITaxon:[0-9]+")
SCORE_KEYS = ("name", "min", "max", "best")

# (rule id, line or None, column or None, message)
Problem = Tuple[str, Optional[int], Optional[int], str]


class Checker:
    def __init__(self, profile, context):
        self.profile = profile
        self.ontology = context.ontology
        self.structure = context.structure
        self.so_layer = context.so_layer
        ontology = self.ontology
        self.leaf_terms = ontology.descendants(CDS) | ontology.descendants(EXON)
        self.polypeptide_terms = ontology.descendants(POLYPEPTIDE)
        self.start = array("q")
        self.end = array("q")
        # Parent ID not defined yet -> [first child line, count].
        self.forward: Dict[str, List[int]] = {}
        # Parent ID not defined yet -> [(line, seqid, start, end)] (AGB-003).
        self.deferred: Dict[str, List[Tuple[int, str, int, int]]] = {}
        self.deferred_count = 0
        self.dropped = 0
        # (rule, key) -> [message, line, column, count]
        self.summary: Dict[Tuple[str, str], list] = {}

    # -- helpers ------------------------------------------------------------

    def _note(self, rule, key, message, line, column=None):
        """A finding reported once per (rule, key), at the earliest line."""
        entry = self.summary.get((rule, key))
        if entry is None:
            self.summary[(rule, key)] = [message, line, column, 1]
            return
        entry[3] += 1
        if line is not None and (entry[1] is None or line < entry[1]):
            entry[0:3] = [message, line, column]

    def _term(self, type_):
        return self.so_layer.term_of(type_)

    # -- directives -----------------------------------------------------------

    def directive(self, line, name, arguments, text) -> List[Problem]:
        out: List[Problem] = []
        if name in ONTOLOGY_DIRECTIVES and arguments:
            uri = arguments[0]
            if not OBO_PURL.fullmatch(uri):
                out.append(
                    (
                        "AGB-010",
                        line,
                        None,
                        f"##{name} {show(uri)} is not an OBO PURL "
                        "(http://purl.obolibrary.org/obo/...)",
                    )
                )
        elif name == "species" and arguments:
            value = " ".join(arguments)
            if not NCBITAXON.fullmatch(value):
                out.append(
                    (
                        "AGB-011",
                        line,
                        None,
                        f"##species {show(value)} is not an NCBITaxon CURIE "
                        "(for example NCBITaxon:9606)",
                    )
                )
        elif name.lower() == "score":
            problem = score_problem(text[2 + len(name) :])
            if problem:
                out.append(("AGB-012", line, None, f"##{name} {problem}"))
        return out

    # -- features -------------------------------------------------------------

    def feature(self, line, fields, coordinates, attributes) -> List[Problem]:
        out: List[Problem] = []
        seqid, type_ = fields[0], fields[2]
        tags = attributes.tags
        if "," in seqid:
            self._note(
                "AGB-013",
                seqid,
                f"seqid {show(seqid)} lists several sequences (unescaped comma)",
                line,
                1,
            )
        term = self._term(type_)
        if term is not None:
            if term in self.polypeptide_terms:
                self._note(
                    "AGB-006",
                    type_,
                    f"{show(type_)} feature (polypeptide features are not "
                    "recommended)",
                    line,
                    3,
                )
            if term in self.leaf_terms and not attributes.parents:
                self._note(
                    "AGB-007",
                    "",
                    f"{show(type_)} feature has no Parent",
                    line,
                    9,
                )
            so_term_name = tags.get("so_term_name")
            if so_term_name:
                self._so_term_name(line, type_, term, decode(so_term_name))
        if "Ontology_term" in tags:
            self._note(
                "AGB-001",
                "",
                "Ontology_term is used; the AgBioData recommendations advise "
                "against it",
                line,
                9,
            )
        for tag in ("Dbxref", "Ontology_term"):
            value = tags.get(tag)
            if value and "GO:" in value:
                for item in value.split(","):
                    if decode(item).startswith("GO:"):
                        self._note(
                            "AGB-002",
                            "",
                            f"{tag} gives the GO term {show(decode(item))}",
                            line,
                            9,
                        )
                        break
        if len(attributes.parents) > 1:
            self._note(
                "AGB-005",
                "",
                f"feature has {len(attributes.parents)} Parents",
                line,
                9,
            )
        target = tags.get("Target")
        if target is not None and attributes.target is not None:
            problem = target_problem(target)
            if problem:
                out.append(("AGB-009", line, 9, f"Target {show(target)} {problem}"))
        out.extend(self._hierarchy(line, seqid, coordinates, attributes))
        return out

    def _so_term_name(self, line, type_, term, value):
        ontology = self.ontology
        named = ontology.exact(value)
        if named is None:
            message = (
                f"so_term_name {show(value)} is not an SO term label or accession "
                f"in {self.so_layer.release}"
            )
        elif not ontology.is_a(named, term):
            message = (
                f"so_term_name {show(value)} is not {show(type_)} or an is_a "
                "subtype of it"
            )
        else:
            return
        self._note("AGB-008", f"{value}\t{type_}", message, line, 9)

    def _hierarchy(self, line, seqid, coordinates, attributes) -> List[Problem]:
        out: List[Problem] = []
        structure = self.structure
        identifier = attributes.id
        for parent in attributes.parents:
            if parent == identifier:
                continue  # a Parent cycle, GFF-STR-006
            node = structure.index.get(parent)
            if node is not None and structure.first_line[node] != 0:
                if coordinates is not None:
                    problem = self._outside(node, parent, seqid, *coordinates)
                    if problem:
                        out.append(("AGB-003", line, None, problem))
                continue
            entry = self.forward.get(parent)
            if entry is None:
                self.forward[parent] = [line, 1]
            else:
                entry[1] += 1
            if coordinates is not None:
                if self.deferred_count < MAX_DEFERRED:
                    self.deferred.setdefault(parent, []).append(
                        (line, seqid, *coordinates)
                    )
                    self.deferred_count += 1
                else:
                    self.dropped += 1
        if identifier is None:
            return out
        node = structure.index.get(identifier)
        if node is None:
            return out
        if coordinates is not None:
            self._extend(node, *coordinates)
        if structure.first_line[node] == line:
            entry = self.forward.pop(identifier, None)
            if entry is not None:
                first, count = entry
                more = f" ({count} child lines before it)" if count > 1 else ""
                self._note(
                    "AGB-004",
                    "",
                    f"Parent {show(identifier)} is defined later, at line {line}"
                    + more,
                    first,
                    9,
                )
        return out

    def _extend(self, node, start, end):
        size = len(self.start)
        if node >= size:
            grow = node + 1 - size
            self.start.extend([0] * grow)
            self.end.extend([0] * grow)
        if self.end[node] == 0:
            self.start[node], self.end[node] = start, end
            return
        if start < self.start[node]:
            self.start[node] = start
        if end > self.end[node]:
            self.end[node] = end

    def _outside(self, node, parent, seqid, start, end) -> Optional[str]:
        if node >= len(self.end) or self.end[node] == 0:
            return None  # the Parent has no valid coordinates
        structure = self.structure
        parent_seqid = structure.combos[structure.combo[node]][0]
        if seqid != parent_seqid:
            return (
                f"feature is on {show(seqid)} but its Parent {show(parent)} is on "
                f"{show(parent_seqid)}"
            )
        low, high = self.start[node], self.end[node]
        if start < low or end > high:
            return (
                f"feature {start}..{end} is not within its Parent {show(parent)} "
                f"({low}..{high})"
            )
        return None

    # -- end of file ------------------------------------------------------------

    def finish(self) -> List[Problem]:
        out: List[Problem] = []
        structure = self.structure
        for parent, children in self.deferred.items():
            node = structure.index.get(parent)
            if node is None or structure.first_line[node] == 0:
                continue  # unresolved: GFF-STR-004
            for line, seqid, start, end in children:
                problem = self._outside(node, parent, seqid, start, end)
                if problem:
                    out.append(("AGB-003", line, None, problem))
        out.sort(key=lambda problem: problem[1])
        for (rule, _), (message, line, column, count) in self.summary.items():
            if count > 1:
                message += f" (and {count - 1} more like this in the file)"
            out.append((rule, line, column, message))
        return out

    def skip_reasons(self) -> List[str]:
        if not self.dropped:
            return []
        return [
            f"partial: AGB-003 did not compare {self.dropped} features listed "
            f"before their Parent (more than {MAX_DEFERRED})"
        ]


def target_problem(value) -> Optional[str]:
    """AGB-009 for a Target that passed GFF-ATT-010."""
    if "" in value.split(" "):
        return "fields are not separated by single spaces"
    target_id = PERCENT.sub("", value.split(" ", 1)[0])
    bad = [c for c in target_id if ord(c) not in SEQID_PLAIN]
    if bad:
        return (
            f"target_id has {show(''.join(dict.fromkeys(bad)))}, outside the "
            "seqid characters [a-zA-Z0-9.:^*$@!+_?-|] (percent-encode them)"
        )
    return None


def score_problem(text) -> Optional[str]:
    """AGB-012: the arguments of a ##Score directive."""
    pairs = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        key, equals, value = part.partition("=")
        if not equals:
            return f"has {show(part)}, not a key=value pair"
        pairs[key.strip()] = value.strip()
    missing = [key for key in SCORE_KEYS if key not in pairs]
    if missing:
        return "has no " + ", ".join(missing) + " (expected name, min, max, best)"
    for key in ("min", "max"):
        if not FLOAT.fullmatch(pairs[key]):
            return f"{key} {show(pairs[key])} is not a number"
    if pairs["best"] not in ("lower", "higher"):
        return f"best is {show(pairs['best'])}, not lower or higher"
    return None
