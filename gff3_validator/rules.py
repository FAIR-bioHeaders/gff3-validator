"""The rule catalogue: loading and checking ``catalogue.yaml``.

The packaged ``catalogue.yaml`` is a generated copy of ``rules/catalogue.yaml``
in the source repository (see ``scripts/render_rules.py``).
"""

import re
from dataclasses import dataclass, field
from importlib import resources
from typing import Dict, List, Optional

import yaml

LEVELS = ("error", "warning", "info")
LAYERS = ("core", "so", "biology", "fhgff3")
STATUSES = ("implemented", "planned")
REVIEWS = ("pending-SO", "reviewed-SO", "accepted-with-changes", "rejected")
ID_PATTERN = re.compile(r"^(GFF-(SYN|ATT|DIR|STR)|SO|BIO|HDR)-\d{3}$")
REQUIRED = (
    "id",
    "level",
    "layer",
    "title",
    "description",
    "reference",
    "example",
    "fix",
    "status",
    "review",
)
OPTIONAL = ("needs_so", "notes", "valid")


@dataclass(frozen=True)
class Rule:
    id: str
    level: str
    layer: str
    title: str
    description: str
    reference: Dict[str, str]
    example: str
    fix: str
    status: str
    review: str
    needs_so: bool = False
    notes: Optional[str] = None
    valid: Optional[str] = None

    @property
    def category(self):
        """The id prefix, for example ``GFF-SYN`` or ``SO``."""
        return self.id.rsplit("-", 1)[0]


@dataclass
class Catalogue:
    version: str
    sources: Dict[str, Dict[str, str]]
    rules: Dict[str, Rule] = field(default_factory=dict)

    def __getitem__(self, rule_id):
        return self.rules[rule_id]

    def __iter__(self):
        return iter(self.rules.values())

    def implemented(self) -> List[Rule]:
        return [rule for rule in self if rule.status == "implemented"]

    def reference_url(self, rule):
        source = self.sources[rule.reference["source"]]
        anchor = rule.reference.get("anchor") or ""
        return source["url"] + (f"#{anchor}" if anchor else "")


def catalogue_problems(data) -> List[str]:
    """Return a list of problems with a parsed catalogue (empty when valid)."""
    problems = []
    if not isinstance(data, dict):
        return ["catalogue is not a mapping"]
    for key in ("catalogue_version", "sources", "rules"):
        if key not in data:
            problems.append(f"missing top-level key {key!r}")
    if problems:
        return problems
    seen = set()
    for index, rule in enumerate(data["rules"]):
        where = rule.get("id", f"rule #{index + 1}")
        for key in REQUIRED:
            if key not in rule:
                problems.append(f"{where}: missing {key!r}")
        for key in rule:
            if key not in REQUIRED + OPTIONAL:
                problems.append(f"{where}: unknown field {key!r}")
        if not ID_PATTERN.match(str(rule.get("id", ""))):
            problems.append(f"{where}: id does not match {ID_PATTERN.pattern}")
        if rule.get("id") in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(rule.get("id"))
        for key, allowed in (
            ("level", LEVELS),
            ("layer", LAYERS),
            ("status", STATUSES),
            ("review", REVIEWS),
        ):
            if key in rule and rule[key] not in allowed:
                problems.append(f"{where}: {key} must be one of {', '.join(allowed)}")
        reference = rule.get("reference")
        if isinstance(reference, dict):
            if reference.get("source") not in data["sources"]:
                problems.append(f"{where}: unknown reference source")
            if "section" not in reference:
                problems.append(f"{where}: reference needs a section")
        elif "reference" in rule:
            problems.append(f"{where}: reference must be a mapping")
    return problems


def parse_catalogue(text) -> Catalogue:
    data = yaml.safe_load(text)
    problems = catalogue_problems(data)
    if problems:
        raise ValueError("invalid rule catalogue:\n  " + "\n  ".join(problems))
    catalogue = Catalogue(version=data["catalogue_version"], sources=data["sources"])
    for entry in data["rules"]:
        catalogue.rules[entry["id"]] = Rule(**entry)
    return catalogue


_PACKAGED = None


def load_catalogue(path=None) -> Catalogue:
    """Load the packaged catalogue, or the catalogue file at ``path``."""
    global _PACKAGED
    if path is not None:
        with open(path, encoding="utf-8") as stream:
            return parse_catalogue(stream.read())
    if _PACKAGED is None:
        text = (
            resources.files("gff3_validator")
            .joinpath("catalogue.yaml")
            .read_text(encoding="utf-8")
        )
        _PACKAGED = parse_catalogue(text)
    return _PACKAGED
