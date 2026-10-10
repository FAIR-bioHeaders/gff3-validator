"""The Sequence Ontology (SO) release used by the SO rules (SO-001 to SO-009).

The validator never fetches the ontology while validating. Each release of the
package bundles one SO release (question 13): ``data/so.json.gz`` is a compact
file derived from ``so.obo`` by ``scripts/update_so.py``, and
``data/so-release.json`` records the release's data-version, date, source URL
and the sha256 of both files. ``--so PATH`` reads another ``so.obo`` (plain or
gzip) with the same standard-library parser.

Only what the rules need is kept per term: id, label, obsolete flag with
replaced_by and consider, EXACT synonyms, is_a, part_of and member_of parents
and subset membership (SOFA). Ancestor sets and part_of reachability are
computed on first use and memoized, so each lookup during validation is O(1)
after the first.
"""

import gzip
import hashlib
import json
import re
from importlib import resources
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

FORMAT = 1
SEQUENCE_FEATURE = "SO:0000110"
SOFA = "SOFA"
ACCESSION = re.compile(r"SO:[0-9]{7}")
ACCESSION_LIKE = re.compile(r"(?i)so:")
DATA = "data"
TERMS_FILE = "so.json.gz"
RELEASE_FILE = "so-release.json"
# The fields of a term in the derived file; empty ones are omitted.
FIELDS = ("name", "is_a", "part_of", "member_of", "synonyms", "subsets")
FIELDS += ("obsolete",)
FIELDS += ("replaced_by", "consider")
# Relations that allow a Parent (question 15). part_of as proposed; member_of
# too, because SO relates transcripts to genes only through
# gene_member_region member_of gene, so without it the specification's own
# canonical gene (mRNA Parent=gene) would be reported.
PARENT_RELATIONS = ("part_of", "member_of")
SYNONYM = re.compile(r'^"((?:[^"\\]|\\.)*)"\s+([A-Z]+)')
MAX_CACHE = 4096


class OntologyError(ValueError):
    """The ontology file cannot be read or parsed."""


# --------------------------------------------------------------------------
# so.obo (OBO 1.2/1.4 flat file), standard library only
# --------------------------------------------------------------------------


def _value(line):
    """The value of an OBO tag line without trailing modifiers or comment."""
    value = line.split(":", 1)[1].strip()
    # "SO:0000001 ! region" or "SO:0000001 {source=...} ! region"
    for mark in (" !", " {"):
        cut = value.find(mark)
        if cut >= 0:
            value = value[:cut]
    return value.strip()


def parse_obo(lines: Iterable[str]) -> Tuple[Dict[str, str], Dict[str, dict]]:
    """Parse ``so.obo`` lines into (header, terms).

    ``header`` holds ``data-version``, ``date`` and ``format-version``.
    ``terms`` maps SO ids to dicts with the keys in :data:`FIELDS` (empty
    values omitted). Stanzas other than ``[Term]`` (``[Typedef]``,
    ``[Instance]``) are skipped.
    """
    header: Dict[str, str] = {}
    terms: Dict[str, dict] = {}
    stanza = None
    term: Optional[dict] = None
    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line or line.startswith("!"):
            continue
        if line.startswith("["):
            stanza = line.strip()
            term = {} if stanza == "[Term]" else None
            continue
        if stanza is None:
            key, _, value = line.partition(":")
            if key in ("data-version", "date", "format-version"):
                header[key] = value.strip()
            continue
        if term is None:
            continue
        key = line.split(":", 1)[0]
        if key == "id":
            identifier = _value(line)
            if identifier in terms:
                raise OntologyError(f"duplicate term id {identifier}")
            terms[identifier] = term
        elif key == "name":
            term["name"] = line.split(":", 1)[1].strip()
        elif key == "is_a":
            term.setdefault("is_a", []).append(_value(line))
        elif key == "relationship":
            parts = _value(line).split()
            if len(parts) >= 2 and parts[0] in PARENT_RELATIONS:
                term.setdefault(parts[0], []).append(parts[1])
        elif key == "synonym":
            match = SYNONYM.match(line.split(":", 1)[1].strip())
            if match and match.group(2) == "EXACT":
                text = match.group(1).replace('\\"', '"').replace("\\\\", "\\")
                term.setdefault("synonyms", []).append(text)
        elif key == "subset":
            term.setdefault("subsets", []).append(_value(line))
        elif key == "is_obsolete":
            if _value(line) == "true":
                term["obsolete"] = True
        elif key in ("replaced_by", "consider"):
            term.setdefault(key, []).append(_value(line))
    for identifier, entry in terms.items():
        if "name" not in entry:
            raise OntologyError(f"term {identifier} has no name")
    if not terms:
        raise OntologyError("no [Term] stanzas found")
    return header, terms


def read_obo(path) -> Tuple[Dict[str, str], Dict[str, dict], str]:
    """Read ``so.obo`` (plain or gzip) at ``path``: (header, terms, sha256)."""
    try:
        with open(path, "rb") as stream:
            data = stream.read()
    except OSError as error:
        raise OntologyError(f"cannot read {path}: {error.strerror}") from None
    digest = hashlib.sha256(data).hexdigest()
    if data[:2] == b"\x1f\x8b":
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError) as error:
            raise OntologyError(f"{path}: bad gzip data ({error})") from None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise OntologyError(f"{path} is not UTF-8") from None
    header, terms = parse_obo(text.splitlines())
    return header, terms, digest


def derived_bytes(terms: Dict[str, dict]) -> bytes:
    """The deterministic gzip JSON form of ``terms`` (mtime 0, sorted keys)."""
    compact = {
        identifier: {
            key: terms[identifier][key] for key in FIELDS if key in terms[identifier]
        }
        for identifier in sorted(terms)
    }
    text = json.dumps(
        {"format": FORMAT, "terms": compact},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return gzip.compress(text.encode("utf-8"), compresslevel=9, mtime=0)


# --------------------------------------------------------------------------
# The ontology used during validation
# --------------------------------------------------------------------------


class Ontology:
    """Look up SO terms by label, accession, synonym or case variant.

    ``release`` describes where the terms came from (``data_version``,
    ``date``, ``source``, ``sha256``, ``bundled``).
    """

    def __init__(self, terms: Dict[str, dict], release: Dict[str, object]):
        self.terms = terms
        self.release = dict(release)
        self.by_label: Dict[str, str] = {}
        self.by_folded: Dict[str, List[str]] = {}
        self.by_synonym: Dict[str, List[str]] = {}
        for identifier, term in terms.items():
            label = term["name"]
            # A label shared by an obsolete and a current term: prefer current.
            known = self.by_label.get(label)
            if known is None or (
                terms[known].get("obsolete") and not term.get("obsolete")
            ):
                self.by_label[label] = identifier
        for identifier, term in terms.items():
            folded = term["name"].casefold()
            self.by_folded.setdefault(folded, []).append(identifier)
            for synonym in term.get("synonyms", ()):
                if synonym in self.by_label:
                    continue  # a label wins over a synonym of another term
                entry = self.by_synonym.setdefault(synonym.casefold(), [])
                if identifier not in entry:
                    entry.append(identifier)
        self._ancestors: Dict[str, FrozenSet[str]] = {}
        self._reach: Dict[str, FrozenSet[str]] = {}
        self._part_of: Dict[Tuple[str, str], bool] = {}

    # -- description ------------------------------------------------------

    @property
    def description(self) -> str:
        """For reports, for example ``so.obo data-version 2026-08-07 (bundled)``."""
        version = self.release.get("data_version") or "unknown data-version"
        where = "bundled" if self.release.get("bundled") else "--so"
        return f"Sequence Ontology so.obo data-version {version} ({where})"

    def to_dict(self):
        keys = ("data_version", "date", "source", "sha256", "bundled")
        return {key: self.release.get(key) for key in keys}

    # -- terms --------------------------------------------------------------

    def name(self, identifier) -> str:
        return self.terms[identifier]["name"]

    def is_obsolete(self, identifier) -> bool:
        return bool(self.terms[identifier].get("obsolete"))

    def replacements(self, identifier) -> Tuple[List[str], List[str]]:
        """(replaced_by, consider) of a term, as ids."""
        term = self.terms[identifier]
        return list(term.get("replaced_by", ())), list(term.get("consider", ()))

    def in_subset(self, identifier, subset=SOFA) -> bool:
        return subset in self.terms[identifier].get("subsets", ())

    def exact(self, value) -> Optional[str]:
        """The term whose label or accession is exactly ``value``."""
        found = self.by_label.get(value)
        if found is not None:
            return found
        if value in self.terms:
            return value
        return None

    def near(self, value) -> List[str]:
        """Terms whose label differs only by case, or with an EXACT synonym
        equal to ``value`` (ignoring case); current terms first."""
        folded = value.casefold()
        found = list(self.by_folded.get(folded, ()))
        for identifier in self.by_synonym.get(folded, ()):
            if identifier not in found:
                found.append(identifier)
        found.sort(key=lambda identifier: (self.is_obsolete(identifier), identifier))
        return found

    # -- relationships --------------------------------------------------------

    def ancestors(self, identifier) -> FrozenSet[str]:
        """The term and its is_a ancestors (memoized)."""
        found = self._ancestors.get(identifier)
        if found is not None:
            return found
        result = set()
        stack = [identifier]
        while stack:
            current = stack.pop()
            if current in result:
                continue
            result.add(current)
            term = self.terms.get(current)
            if term is not None:
                stack.extend(term.get("is_a", ()))
        found = self._ancestors[identifier] = frozenset(result)
        return found

    def is_a(self, identifier, ancestor) -> bool:
        return ancestor in self.ancestors(identifier)

    def descendants(self, identifier) -> FrozenSet[str]:
        """The current (not obsolete) term and its is_a descendants: ids."""
        return frozenset(
            other
            for other in self.terms
            if not self.is_obsolete(other) and identifier in self.ancestors(other)
        )

    def type_names(self, identifier) -> FrozenSet[str]:
        """Labels and accessions of a term and its is_a descendants, the
        column 3 values that name it or a subtype exactly."""
        names = set()
        for other in self.descendants(identifier):
            names.add(other)
            names.add(self.name(other))
        return frozenset(names)

    def _direct_part_of(self, identifier) -> List[str]:
        """part_of (and member_of) targets of the term, inherited through its
        is_a ancestors."""
        found = []
        for ancestor in self.ancestors(identifier):
            term = self.terms.get(ancestor)
            if term is not None:
                for relation in PARENT_RELATIONS:
                    found.extend(term.get(relation, ()))
        return found

    def reach(self, identifier) -> FrozenSet[str]:
        """Every term the given term is part_of, through is_a inheritance on
        both sides and the transitivity of part_of (memoized)."""
        found = self._reach.get(identifier)
        if found is not None:
            return found
        result = set()
        stack = self._direct_part_of(identifier)
        while stack:
            current = stack.pop()
            if current in result:
                continue
            result.add(current)
            stack.extend(self._direct_part_of(current))
        found = self._reach[identifier] = frozenset(result)
        return found

    def part_of(self, child, parent) -> bool:
        """Whether a feature of type ``child`` may have a Parent of type
        ``parent``: the child (or an is_a ancestor) is part_of the parent or
        an is_a ancestor of it, directly or by transitivity (question 15)."""
        key = (child, parent)
        found = self._part_of.get(key)
        if found is None:
            found = not self.reach(child).isdisjoint(self.ancestors(parent))
            if len(self._part_of) < MAX_CACHE * 16:
                self._part_of[key] = found
        return found


def _read_resource(name) -> bytes:
    return resources.files("gff3_validator").joinpath(DATA, name).read_bytes()


def load_bundled() -> Ontology:
    release = json.loads(_read_resource(RELEASE_FILE).decode("utf-8"))
    data = _read_resource(TERMS_FILE)
    digest = hashlib.sha256(data).hexdigest()
    if digest != release.get("derived_sha256"):
        raise OntologyError(
            f"the bundled {TERMS_FILE} does not match {RELEASE_FILE} (sha256)"
        )
    content = json.loads(gzip.decompress(data).decode("utf-8"))
    if content.get("format") != FORMAT:
        raise OntologyError(f"the bundled {TERMS_FILE} has an unknown format")
    release = {
        "data_version": release.get("data_version"),
        "date": release.get("date"),
        "source": release.get("source"),
        "sha256": release.get("sha256"),
        "bundled": True,
    }
    return Ontology(content["terms"], release)


def load_obo(path) -> Ontology:
    header, terms, digest = read_obo(path)
    release = {
        "data_version": header.get("data-version"),
        "date": header.get("date"),
        "source": str(path),
        "sha256": digest,
        "bundled": False,
    }
    return Ontology(terms, release)


_BUNDLED: Optional[Ontology] = None


def load_ontology(path=None) -> Ontology:
    """The bundled SO release, or the ``so.obo`` at ``path`` (``--so``)."""
    global _BUNDLED
    if path is not None:
        return load_obo(path)
    if _BUNDLED is None:
        _BUNDLED = load_bundled()
    return _BUNDLED
