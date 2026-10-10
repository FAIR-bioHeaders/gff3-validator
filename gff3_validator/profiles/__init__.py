"""Repository and community profiles layered on the core rules (spec 009
FR-011, FHR-Specification #51 and #70).

A profile is a YAML file. The profiles shipped with the package are generated
copies of ``profiles/*.yaml`` in the source repository (see
``scripts/render_rules.py``); ``--profile PATH`` loads any other file. A
profile has:

- metadata: ``id``, ``name``, ``version``, ``description``, ``review`` and
  ``source`` (the document it follows: ``title``, ``url``, ``license``,
  ``commit``, ``date``);
- ``levels``: core catalogue rules whose level the profile raises (for
  example a warning that the source document makes a requirement), each with
  a ``reference`` into the source and a ``reason``;
- ``rules``: the profile's own checks, with ids in the profile namespace
  (``prefix``, for example ``AGB-001``) and the same fields as catalogue
  rules (level, title, description, reference, example, fix, status). Their
  code is a module of this package named by ``checks``; only modules shipped
  here are imported, never code named by a profile file from elsewhere;
- ``guidance``: the source's recommendations that are not checked by a
  profile rule, with the core rules that cover them (``covered_by``) and the
  reason (``reason``), so the profile documents everything it read.

Profile findings never change core validity: a report says whether the file
is valid GFF3 (core rules at their catalogue levels) and, separately, whether
it complies with the profile.
"""

import importlib
import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from gff3_validator.rules import LEVELS, STATUSES

PROFILE_FORMAT = 1
LEVEL_RANK = {"info": 0, "warning": 1, "error": 2}
PROFILE_ID = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
PREFIX = re.compile(r"^[A-Z]{2,6}$")
REQUIRED = (
    "profile_format",
    "id",
    "name",
    "version",
    "description",
    "review",
    "source",
    "prefix",
    "rules",
)
OPTIONAL = ("checks", "docs", "levels", "guidance")
SOURCE_REQUIRED = ("title", "url", "license")
SOURCE_OPTIONAL = ("commit", "date")
RULE_REQUIRED = (
    "id",
    "level",
    "title",
    "description",
    "reference",
    "example",
    "fix",
    "status",
)
RULE_OPTIONAL = ("notes", "valid")
LEVEL_REQUIRED = ("rule", "level", "reference", "reason")
GUIDANCE_REQUIRED = ("reference", "recommendation", "reason")
GUIDANCE_OPTIONAL = ("covered_by",)
REFERENCE_KEYS = ("section", "anchor")
REPOSITORY = "https://github.com/FAIR-bioHeaders/gff3-validator"


@dataclass(frozen=True)
class ProfileRule:
    """A check added by a profile, documented like a catalogue rule."""

    id: str
    level: str
    title: str
    description: str
    reference: Dict[str, str]
    example: str
    fix: str
    status: str
    notes: Optional[str] = None
    valid: Optional[str] = None


@dataclass(frozen=True)
class LevelChange:
    """A core rule whose level the profile raises."""

    rule: str
    level: str
    reference: Dict[str, str]
    reason: str


@dataclass(frozen=True)
class Guidance:
    """A recommendation of the source that no profile rule checks."""

    reference: Dict[str, str]
    recommendation: str
    reason: str
    covered_by: Tuple[str, ...] = ()


@dataclass
class Profile:
    id: str
    name: str
    version: str
    description: str
    review: str
    source: Dict[str, str]
    prefix: str
    rules: Dict[str, ProfileRule] = field(default_factory=dict)
    levels: Dict[str, LevelChange] = field(default_factory=dict)
    guidance: List[Guidance] = field(default_factory=list)
    checks: Optional[str] = None
    docs: Optional[str] = None

    def __iter__(self):
        return iter(self.rules.values())

    def implemented(self) -> List[ProfileRule]:
        return [rule for rule in self if rule.status == "implemented"]

    def reference_url(self, reference):
        anchor = reference.get("anchor") or ""
        return self.source["url"] + (f"#{anchor}" if anchor else "")

    def rule_url(self, rule_id):
        """Where a profile rule is documented (its docs page, else the source)."""
        if self.docs:
            return f"{self.docs}#{rule_id.lower()}"
        rule = self.rules.get(rule_id)
        if rule is not None:
            return self.reference_url(rule.reference)
        return self.source["url"]

    def checker(self, context):
        """A new checker for one validation run, or None if the profile only
        changes levels. ``context`` gives the run's ``ontology``,
        ``structure`` and ``so_layer``."""
        if not self.checks:
            return None
        module = importlib.import_module(f"{__name__}.{self.checks}")
        return module.Checker(self, context)

    def to_dict(self):
        """Metadata for reports."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "review": self.review,
            "source": dict(self.source),
            "docs": self.docs,
        }

    @property
    def label(self):
        """Short name for report lines, for example "AgBioData profile"."""
        return f"{self.short_name} profile"

    @property
    def short_name(self):
        return self.name.split(" ")[0]


def _reference_problems(where, reference):
    if not isinstance(reference, dict):
        return [f"{where}: reference must be a mapping"]
    problems = []
    if "section" not in reference:
        problems.append(f"{where}: reference needs a section")
    for key in reference:
        if key not in REFERENCE_KEYS:
            problems.append(f"{where}: unknown reference field {key!r}")
    return problems


def _fields(where, entry, required, optional):
    if not isinstance(entry, dict):
        return [f"{where}: must be a mapping"]
    problems = [f"{where}: missing {key!r}" for key in required if key not in entry]
    problems += [
        f"{where}: unknown field {key!r}"
        for key in entry
        if key not in required + optional
    ]
    return problems


def profile_problems(data, catalogue=None) -> List[str]:
    """Return a list of problems with a parsed profile (empty when valid).

    With ``catalogue``, level changes are checked against it: the rule exists,
    is implemented, and the new level is more severe than its own.
    """
    problems = _fields("profile", data, REQUIRED, OPTIONAL)
    if problems:
        return problems
    if data["profile_format"] != PROFILE_FORMAT:
        problems.append(f"profile: profile_format must be {PROFILE_FORMAT}")
    if not PROFILE_ID.match(str(data["id"])):
        problems.append(f"profile: id does not match {PROFILE_ID.pattern}")
    if not PREFIX.match(str(data["prefix"])):
        problems.append(f"profile: prefix does not match {PREFIX.pattern}")
    problems += _fields("source", data["source"], SOURCE_REQUIRED, SOURCE_OPTIONAL)
    checks = data.get("checks")
    if checks is not None and checks not in builtin_checks():
        problems.append(
            f"profile: checks {checks!r} is not a checks module of gff3_validator."
            "profiles"
        )
    id_pattern = re.compile(rf"^{data['prefix']}-\d{{3}}$")
    seen = set()
    for index, rule in enumerate(data["rules"] or ()):
        where = rule.get("id", f"rule #{index + 1}") if isinstance(rule, dict) else ""
        problems += _fields(where, rule, RULE_REQUIRED, RULE_OPTIONAL)
        if not isinstance(rule, dict):
            continue
        if not id_pattern.match(str(rule.get("id", ""))):
            problems.append(f"{where}: id does not match {id_pattern.pattern}")
        if rule.get("id") in seen:
            problems.append(f"{where}: duplicate id")
        seen.add(rule.get("id"))
        if rule.get("level") not in LEVELS:
            problems.append(f"{where}: level must be one of {', '.join(LEVELS)}")
        if rule.get("status") not in STATUSES:
            problems.append(f"{where}: status must be one of {', '.join(STATUSES)}")
        if rule.get("status") == "implemented" and checks is None:
            problems.append(f"{where}: implemented, but the profile has no checks")
        if "reference" in rule:
            problems += _reference_problems(where, rule["reference"])
    changed = set()
    for index, change in enumerate(data.get("levels") or ()):
        where = f"levels #{index + 1}"
        problems += _fields(where, change, LEVEL_REQUIRED, ())
        if not isinstance(change, dict):
            continue
        rule_id = change.get("rule")
        where = f"levels {rule_id}"
        if rule_id in changed:
            problems.append(f"{where}: changed twice")
        changed.add(rule_id)
        if change.get("level") not in LEVELS:
            problems.append(f"{where}: level must be one of {', '.join(LEVELS)}")
        if "reference" in change:
            problems += _reference_problems(where, change["reference"])
        if catalogue is not None:
            rule = catalogue.rules.get(rule_id)
            if rule is None:
                problems.append(f"{where}: not a catalogue rule")
            elif rule.status != "implemented":
                problems.append(f"{where}: the catalogue rule is not implemented")
            elif LEVEL_RANK.get(change.get("level"), -1) <= LEVEL_RANK[rule.level]:
                problems.append(
                    f"{where}: a profile can only raise a level (the catalogue "
                    f"level is {rule.level})"
                )
    for index, item in enumerate(data.get("guidance") or ()):
        where = f"guidance #{index + 1}"
        problems += _fields(where, item, GUIDANCE_REQUIRED, GUIDANCE_OPTIONAL)
        if isinstance(item, dict) and "reference" in item:
            problems += _reference_problems(where, item["reference"])
        if isinstance(item, dict) and catalogue is not None:
            for rule_id in item.get("covered_by") or ():
                if rule_id not in catalogue.rules and rule_id not in seen:
                    problems.append(f"{where}: covered_by {rule_id} is unknown")
    return problems


def parse_profile(text, catalogue=None) -> Profile:
    from gff3_validator.rules import load_catalogue

    catalogue = catalogue or load_catalogue()
    data = yaml.safe_load(text)
    problems = profile_problems(data, catalogue)
    if problems:
        raise ValueError("invalid profile:\n  " + "\n  ".join(problems))
    profile = Profile(
        id=data["id"],
        name=data["name"],
        version=str(data["version"]),
        description=data["description"],
        review=data["review"],
        source={key: str(value) for key, value in data["source"].items()},
        prefix=data["prefix"],
        checks=data.get("checks"),
        docs=data.get("docs"),
    )
    for entry in data["rules"] or ():
        profile.rules[entry["id"]] = ProfileRule(**entry)
    for entry in data.get("levels") or ():
        profile.levels[entry["rule"]] = LevelChange(**entry)
    for entry in data.get("guidance") or ():
        entry = dict(entry)
        entry["covered_by"] = tuple(entry.get("covered_by") or ())
        profile.guidance.append(Guidance(**entry))
    if profile.checks:
        module = importlib.import_module(f"{__name__}.{profile.checks}")
        provided = set(module.RULES)
        for rule in profile:
            if rule.status == "implemented" and rule.id not in provided:
                raise ValueError(
                    f"invalid profile: {rule.id} is implemented but "
                    f"{profile.checks} does not check it"
                )
    return profile


def builtin_checks():
    """Names of the checks modules shipped in this package."""
    package = resources.files(__name__)
    return sorted(
        entry.name[:-3]
        for entry in package.iterdir()
        if entry.name.endswith(".py") and not entry.name.startswith("_")
    )


def builtin_ids() -> List[str]:
    """Ids of the profiles shipped in this package."""
    package = resources.files(__name__)
    return sorted(
        entry.name[:-5] for entry in package.iterdir() if entry.name.endswith(".yaml")
    )


_BUILTIN: Dict[str, Profile] = {}


class ProfileError(ValueError):
    """A profile cannot be found or is not valid."""


def load_profile(name_or_path) -> Profile:
    """Load a shipped profile by id, or the profile YAML file at a path."""
    value = str(name_or_path)
    if value in builtin_ids():
        if value not in _BUILTIN:
            text = (
                resources.files(__name__)
                .joinpath(f"{value}.yaml")
                .read_text(encoding="utf-8")
            )
            _BUILTIN[value] = parse_profile(text)
        return _BUILTIN[value]
    path = Path(value)
    if not (path.suffix in (".yaml", ".yml") or path.exists()):
        raise ProfileError(
            f"unknown profile {value!r}; shipped profiles: "
            f"{', '.join(builtin_ids())} (or give the path of a profile YAML file)"
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ProfileError(f"cannot read profile {value}: {error}") from error
    try:
        return parse_profile(text)
    except (ValueError, yaml.YAMLError) as error:
        raise ProfileError(f"{value}: {error}") from error


def list_profiles() -> List[Profile]:
    return [load_profile(name) for name in builtin_ids()]
