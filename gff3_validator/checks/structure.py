"""Structure rules: IDs, Parent and Derives_from references, bounds.

GFF-STR-001 to -011, GFF-DIR-002 and GFF-DIR-003.

Memory is O(number of distinct IDs) plus O(number of seqids):

- each ID (and each referenced but not yet defined ID) gets an integer index
  in ``index``; four parallel ``array`` columns hold its first line, its
  (seqid, type, strand) combination, its first Parent and a hash of its
  Parent list (about 32 bytes per ID plus the dictionary entry and the ID
  string itself);
- features with several Parents and features with Derives_from keep the
  extra edges in sparse dictionaries;
- forward references that are not resolved yet are kept per referenced ID
  (first line and count), not per referencing line;
- per seqid a few extremes (first line, furthest start and end) and at most
  ``MAX_DEFERRED`` deferred bounds findings.

Features without an ID cost nothing after their line, except when their
Parent or Derives_from is not yet defined.
"""

from array import array
from typing import Dict, Iterator, List, Tuple

from gff3_validator.checks.attributes import decode

MAX_DEFERRED = 100
UNDEFINED = ("", ".")

# (rule id, line or None, message)
Problem = Tuple[str, object, str]


def show_id(value, limit=60):
    text = value.encode("unicode_escape").decode("ascii")
    if len(text) > limit:
        text = text[: limit - 3] + "..."
    return f'"{text}"'


class Sequence:
    """What is known about one seqid."""

    __slots__ = (
        "first_line",
        "max_end",
        "max_end_line",
        "max_start",
        "max_start_line",
        "circular",
        "early",
        "deferred",
        "more",
    )

    def __init__(self, line):
        self.first_line = line
        self.max_end = self.max_start = 0
        self.max_end_line = self.max_start_line = line
        self.circular = False
        # Extremes of the features seen before the ##sequence-region line:
        # [min start, line, max end, line, max start, line] (GFF-STR-008).
        self.early = None
        # Features beyond the region end, kept until the end of the file
        # because a later Is_circular=true exempts them.
        self.deferred: List[Tuple[int, int, int]] = []
        self.more = [0, 0]  # not kept: beyond end, starting beyond end


class Structure:
    def __init__(self):
        self.index: Dict[str, int] = {}
        self.first_line = array("q")  # 0: referenced but not defined (yet)
        self.combo = array("q")
        self.parent = array("q")  # first Parent index, -1 for none
        self.parent_hash = array("q")
        self.extra_parents: Dict[int, List[int]] = {}
        self.derives: Dict[int, List[int]] = {}
        # Unresolved references: index -> [Parent line, Parent count,
        # Derives_from line, Derives_from count, ### generation].
        self.pending: Dict[int, list] = {}
        self.combos: List[Tuple[str, str, str]] = []
        self.combo_index: Dict[Tuple[str, str, str], int] = {}
        self.generation = 0
        self.sequences: Dict[str, Sequence] = {}
        self.regions: Dict[str, Tuple[int, int, int]] = {}
        self.fasta: Dict[str, int] = {}

    # -- directives -----------------------------------------------------

    def resolution_point(self):
        """A ### line: all forward references seen so far must be resolved."""
        self.generation += 1

    def sequence_region(self, line, seqid, start, end) -> Iterator[Problem]:
        known = self.regions.get(seqid)
        if known is not None:
            same = "the same bounds" if known[:2] == (start, end) else "other bounds"
            yield (
                "GFF-DIR-002",
                line,
                f"second ##sequence-region for {show_id(seqid)} ({same}; first "
                f"at line {known[2]})",
            )
            return
        self.regions[seqid] = (start, end, line)

    # -- features -------------------------------------------------------

    def _lookup(self, value):
        found = self.index.get(value)
        if found is None:
            found = self.index[value] = len(self.first_line)
            self.first_line.append(0)
            self.combo.append(-1)
            self.parent.append(-1)
            self.parent_hash.append(0)
        return found

    def _reference(self, value, line, derives):
        target = self._lookup(value)
        if self.first_line[target] == 0:
            entry = self.pending.get(target)
            if entry is None:
                entry = self.pending[target] = [0, 0, 0, 0, self.generation]
            slot = 2 if derives else 0
            if entry[slot] == 0:
                entry[slot] = line
            entry[slot + 1] += 1
        return target

    def feature(
        self, line, seqid, type_, strand, coordinates, attributes
    ) -> Iterator[Problem]:
        if seqid in UNDEFINED:
            pass  # GFF-SYN-004 or GFF-SYN-011; nothing to bounds-check.
        elif coordinates is not None:
            yield from self._bounds(line, seqid, coordinates, attributes.circular)
        elif seqid not in self.sequences:
            self.sequences[seqid] = Sequence(line)
        parents = [self._reference(v, line, False) for v in attributes.parents]
        derives = [self._reference(v, line, True) for v in attributes.derives_from]
        identifier = attributes.id
        if identifier is None:
            return
        key = (seqid, type_, strand)
        combo = self.combo_index.get(key)
        if combo is None:
            combo = self.combo_index[key] = len(self.combos)
            self.combos.append(key)
        parent_hash = hash(tuple(sorted(set(parents)))) if parents else 0
        node = self._lookup(identifier)
        first = self.first_line[node]
        if first == 0:
            self.first_line[node] = line
            self.combo[node] = combo
            self.parent_hash[node] = parent_hash
            if parents:
                self.parent[node] = parents[0]
                if len(parents) > 1:
                    self.extra_parents[node] = parents[1:]
            if derives:
                self.derives[node] = derives
            entry = self.pending.pop(node, None)
            if entry is not None and entry[4] < self.generation:
                yield (
                    "GFF-DIR-003",
                    entry[0] or entry[2],
                    f"{show_id(identifier)} is referenced here but defined only "
                    f"at line {line}, after a ### directive that declared all "
                    "forward references resolved",
                )
            return
        if combo != self.combo[node]:
            old_seqid, old_type, old_strand = self.combos[self.combo[node]]
            if type_ != old_type:
                yield (
                    "GFF-STR-001",
                    line,
                    f"ID {show_id(identifier)} is already used at line {first} "
                    f"by a {show_id(old_type)} feature; this line is a "
                    f"{show_id(type_)}",
                )
                return
            changes = [
                f"{name} {show_id(new)} (line {first}: {show_id(old)})"
                for name, old, new in (
                    ("seqid", old_seqid, seqid),
                    ("strand", old_strand, strand),
                )
                if old != new
            ]
            yield (
                "GFF-STR-002",
                line,
                f"line of ID {show_id(identifier)} has " + " and ".join(changes),
            )
        if parent_hash != self.parent_hash[node]:
            yield (
                "GFF-STR-003",
                line,
                f"ID {show_id(identifier)} has a different Parent list than on "
                f"line {first}",
            )
            known = {self.parent[node], *self.extra_parents.get(node, ())}
            new = [p for p in parents if p not in known]
            if new:
                if self.parent[node] == -1:
                    self.parent[node] = new.pop(0)
                if new:
                    self.extra_parents.setdefault(node, []).extend(new)
        if derives:
            known = self.derives.setdefault(node, [])
            known.extend(d for d in derives if d not in known)

    def _bounds(self, line, seqid, coordinates, circular):
        start, end = coordinates
        sequence = self.sequences.get(seqid)
        if sequence is None:
            sequence = self.sequences[seqid] = Sequence(line)
        if circular:
            sequence.circular = True
        if end > sequence.max_end:
            sequence.max_end, sequence.max_end_line = end, line
        if start > sequence.max_start:
            sequence.max_start, sequence.max_start_line = start, line
        region = self.regions.get(seqid)
        if region is None:
            early = sequence.early
            if early is None:
                sequence.early = [start, line, end, line, start, line]
            else:
                if start < early[0]:
                    early[0:2] = start, line
                if end > early[2]:
                    early[2:4] = end, line
                if start > early[4]:
                    early[4:6] = start, line
            return
        low, high, region_line = region
        if start < low:
            yield (
                "GFF-STR-008",
                line,
                f"feature starts at {start}, before the ##sequence-region start "
                f"{low} of {show_id(seqid)} (line {region_line})",
            )
        elif end > high:
            if len(sequence.deferred) < MAX_DEFERRED:
                sequence.deferred.append((line, start, end))
            else:
                sequence.more[0] += 1
                if start > high:
                    sequence.more[1] += 1

    def strand_of(self, identifier):
        """The strand of the first line with ID ``identifier``, if seen yet."""
        node = self.index.get(identifier)
        if node is None or self.first_line[node] == 0:
            return None
        return self.combos[self.combo[node]][2]

    def type_of(self, identifier):
        """The type of the first line with ID ``identifier``, if seen yet."""
        node = self.index.get(identifier)
        if node is None or self.first_line[node] == 0:
            return None
        return self.combos[self.combo[node]][1]

    # -- FASTA ----------------------------------------------------------

    def fasta_record(self, name, length):
        self.fasta[name] = length

    # -- end of file ----------------------------------------------------

    def finish(self) -> Iterator[Problem]:
        yield from self._unresolved()
        names = None
        for rule, edges in (
            ("GFF-STR-006", self._parent_edges),
            ("GFF-STR-007", self._derives_edges),
        ):
            for cycle in find_cycles(len(self.first_line), edges, self._roots(rule)):
                if names is None:
                    names = list(self.index)
                line = min(self.first_line[node] for node in cycle)
                path = " -> ".join(show_id(names[node]) for node in cycle[:6])
                if len(cycle) > 6:
                    path += f" -> ... ({len(cycle)} features)"
                path += f" -> {show_id(names[cycle[0]])}"
                relation = "Parent" if rule == "GFF-STR-006" else "Derives_from"
                yield (rule, line, f"{relation} cycle: {path}")
        yield from self._sequence_findings()

    def _unresolved(self):
        if not self.pending:
            return
        names = list(self.index)
        for node, entry in self.pending.items():
            name = show_id(names[node])
            for rule, slot, tag in (
                ("GFF-STR-004", 0, "Parent"),
                ("GFF-STR-005", 2, "Derives_from"),
            ):
                if entry[slot + 1]:
                    others = entry[slot + 1] - 1
                    more = f" (and {others} more lines)" if others else ""
                    yield (
                        rule,
                        entry[slot],
                        f"{tag} {name} is not the ID of any feature in the file" + more,
                    )

    def _roots(self, rule):
        if rule == "GFF-STR-006":
            return (n for n in range(len(self.parent)) if self.parent[n] != -1)
        return iter(list(self.derives))

    def _parent_edges(self, node):
        first = self.parent[node]
        if first == -1:
            return ()
        extra = self.extra_parents.get(node)
        edges = [first, *extra] if extra else [first]
        return [p for p in edges if self.first_line[p]]

    def _derives_edges(self, node):
        return [d for d in self.derives.get(node, ()) if self.first_line[d]]

    def _sequence_findings(self):
        fasta = self.fasta
        for seqid, sequence in self.sequences.items():
            region = self.regions.get(seqid)
            if region is not None:
                yield from self._region_findings(seqid, sequence, region)
            elif self.regions:
                yield (
                    "GFF-STR-009",
                    sequence.first_line,
                    f"seqid {show_id(seqid)} has no ##sequence-region, so its "
                    "features are not bounds-checked",
                )
            if not fasta:
                continue
            length = fasta.get(seqid)
            if length is None:
                length = fasta.get(decode(seqid))
            if length is None:
                yield (
                    "GFF-STR-010",
                    sequence.first_line,
                    f"seqid {show_id(seqid)} is not in the ##FASTA section",
                )
                continue
            if sequence.circular:
                beyond, line = sequence.max_start, sequence.max_start_line
                what = "starts at"
            else:
                beyond, line = sequence.max_end, sequence.max_end_line
                what = "ends at"
            if beyond > length:
                yield (
                    "GFF-STR-011",
                    line,
                    f"feature {what} {beyond}, beyond the {length} bases of "
                    f"{show_id(seqid)} in the ##FASTA section (the furthest "
                    "feature on that sequence is reported)",
                )

    def _region_findings(self, seqid, sequence, region):
        low, high, region_line = region
        where = f"the ##sequence-region of {show_id(seqid)} (line {region_line})"
        early = sequence.early
        if early is not None:
            if early[0] < low:
                yield (
                    "GFF-STR-008",
                    early[1],
                    f"feature starts at {early[0]}, before the start {low} of " + where,
                )
            if sequence.circular:
                if early[4] > high:
                    yield (
                        "GFF-STR-008",
                        early[5],
                        f"feature starts at {early[4]}, after the end {high} of "
                        + where,
                    )
            elif early[2] > high:
                yield (
                    "GFF-STR-008",
                    early[3],
                    f"feature ends at {early[2]}, after the end {high} of " + where,
                )
        for line, start, end in sequence.deferred:
            if sequence.circular and start <= high:
                continue
            what = "starts" if sequence.circular else "ends"
            value = start if sequence.circular else end
            yield (
                "GFF-STR-008",
                line,
                f"feature {what} at {value}, after the end {high} of " + where,
            )
        more = sequence.more[1] if sequence.circular else sequence.more[0]
        if more:
            yield (
                "GFF-STR-008",
                None,
                f"{more} more features on {show_id(seqid)} lie beyond the end "
                f"{high} of its ##sequence-region (only the first "
                f"{MAX_DEFERRED} are listed)",
            )


def find_cycles(size, edges, roots) -> Iterator[List[int]]:
    """Yield each cycle found by an iterative depth-first search.

    ``edges(node)`` returns the successors of ``node``; nodes are integers
    below ``size``. Every cycle reachable from ``roots`` is found at least
    once; each is yielded as a list of nodes in edge order.
    """
    state = bytearray(size)  # 0 new, 1 on the current path, 2 done
    for root in roots:
        if state[root]:
            continue
        path = [root]
        stack = [iter(edges(root))]
        state[root] = 1
        while stack:
            successor = next(stack[-1], None)
            if successor is None:
                state[path.pop()] = 2
                stack.pop()
                continue
            if state[successor] == 1:
                yield path[path.index(successor) :]
            elif state[successor] == 0:
                state[successor] = 1
                path.append(successor)
                stack.append(iter(edges(successor)))
