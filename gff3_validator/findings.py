"""The finding model shared by all report formats."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Finding:
    """One problem (or note) found in a file, citing a catalogue rule.

    ``line`` is the 1-based line number in the decompressed input, or None for
    findings about the whole file. ``field`` is the 1-based GFF3 column (1 to
    9) when the finding concerns one column. Character offsets are not
    reported. ``core_level`` is set only on a profile finding for a core rule
    whose level the profile raises: it is the rule's catalogue level.
    """

    rule: str
    level: str
    message: str
    line: Optional[int] = None
    field: Optional[int] = None
    fix: Optional[str] = None
    core_level: Optional[str] = None

    def to_dict(self):
        return {
            "rule": self.rule,
            "level": self.level,
            "line": self.line,
            "field": self.field,
            "message": self.message,
            "fix": self.fix,
        }
