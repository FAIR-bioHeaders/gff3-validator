"""The validation engine: reads lines, runs the rules, collects findings."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from gff3_validator import header
from gff3_validator.checks import syntax
from gff3_validator.findings import Finding
from gff3_validator.reader import iter_lines
from gff3_validator.rules import load_catalogue

REPORT_VERSION = "0.1-draft"
DEFAULT_MAX_FINDINGS = 10000
BOM = "\ufeff"


@dataclass
class Report:
    """The result of validating one input.

    ``skipped`` lists layers or checks that were not run, with the reason, so
    that a report without errors never implies that unrun checks passed.
    """

    source: str
    catalogue_version: str
    findings: List[Finding] = field(default_factory=list)
    counts: Dict[str, int] = field(
        default_factory=lambda: {"error": 0, "warning": 0, "info": 0}
    )
    truncated: int = 0
    lines: int = 0
    header_lines: int = 0
    skipped: List[Dict[str, str]] = field(default_factory=list)

    @property
    def valid(self):
        return self.counts["error"] == 0

    def to_dict(self):
        from gff3_validator import __version__

        return {
            "report_version": REPORT_VERSION,
            "tool": {"name": "gff3-validator", "version": __version__},
            "catalogue_version": self.catalogue_version,
            "source": self.source,
            "valid": self.valid,
            "counts": dict(self.counts),
            "lines": self.lines,
            "header_lines": self.header_lines,
            "skipped": list(self.skipped),
            "truncated_findings": self.truncated,
            "findings": [finding.to_dict() for finding in self.findings],
        }


class Validator:
    """Validate GFF3 input against the implemented catalogue rules.

    ``header_mode`` is ``"auto"`` (check a header when present), ``"require"``
    (``--require-header``) or ``"skip"`` (``--no-header``). ``genome`` is
    accepted for the planned biology layer, which is not implemented.
    """

    def __init__(
        self,
        header_mode="auto",
        genome: Optional[str] = None,
        max_findings=DEFAULT_MAX_FINDINGS,
        catalogue=None,
    ):
        if header_mode not in header.MODES:
            raise ValueError(f"header_mode must be one of {header.MODES}")
        self.header_mode = header_mode
        self.genome = genome
        self.max_findings = max_findings
        self.catalogue = catalogue or load_catalogue()

    def _add(self, report, rule_id, message, line=None, field=None):
        rule = self.catalogue[rule_id]
        report.counts[rule.level] += 1
        if self.max_findings is not None and len(report.findings) >= self.max_findings:
            report.truncated += 1
            return
        report.findings.append(
            Finding(rule_id, rule.level, message, line=line, field=field, fix=rule.fix)
        )

    def validate(self, source, name=None) -> Report:
        """Validate ``source`` (path, ``"-"`` or binary stream).

        Raises ``InputError`` if the input cannot be read completely.
        """
        report = Report(
            source=name or str(source), catalogue_version=self.catalogue.version
        )
        version_seen = False
        in_fasta = False
        for number, line in iter_lines(source):
            report.lines = number
            if number == 1:
                if syntax.is_version_line(line):
                    version_seen = True
                else:
                    hint = ""
                    if line.startswith(BOM):
                        hint = " (the file starts with a byte order mark)"
                        line = line[len(BOM) :]
                    self._add(
                        report,
                        "GFF-SYN-001",
                        f"first line is {syntax.show(line)}, not ##gff-version 3"
                        + hint,
                        line=1,
                    )
            if in_fasta:
                continue  # FASTA content rules (GFF-DIR-004, -006) are planned.
            if line.startswith("#"):
                if line.startswith(header.HEADER_PREFIX):
                    report.header_lines += 1
                elif line.startswith("##gff-version") and number > 1:
                    if version_seen:
                        self._add(
                            report,
                            "GFF-SYN-002",
                            "repeated ##gff-version directive",
                            line=number,
                        )
                    version_seen = True
                elif line.rstrip("\r") == "##FASTA":
                    in_fasta = True
                continue
            if line.startswith(">"):
                in_fasta = True  # An implied ##FASTA (GFF-DIR-005, planned).
                continue
            if line.strip() == "":
                continue
            for rule_id, column, message in syntax.check_feature(line):
                self._add(report, rule_id, message, line=number, field=column)
        if report.lines == 0:
            self._add(report, "GFF-SYN-001", "the input is empty")
        self._finish_header(report)
        self._record_skipped(report)
        return report

    def _finish_header(self, report):
        if self.header_mode == "skip":
            self._add(report, "HDR-003", "header checks skipped (--no-header)")
            report.skipped.append({"layer": "fhgff3", "reason": "--no-header"})
            return
        if report.header_lines == 0:
            if self.header_mode == "require":
                self._add(
                    report,
                    "HDR-001",
                    "no FAIR-bioHeaders header (#~ lines) found, but "
                    "--require-header was given",
                )
            return
        reason = header.unavailable_reason()
        self._add(
            report,
            "HDR-002",
            f"{report.header_lines} FAIR-bioHeaders header lines found; {reason}",
        )
        report.skipped.append({"layer": "fhgff3", "reason": reason})

    def _record_skipped(self, report):
        implemented = {rule.category for rule in self.catalogue.implemented()}
        report.skipped.append(
            {
                "layer": "core",
                "reason": "partial: only the rules marked implemented in the "
                "catalogue are checked (attributes, directives and structure "
                "rules are planned)",
                "checked": ", ".join(sorted(implemented)),
            }
        )
        report.skipped.append({"layer": "so", "reason": "not implemented"})
        reason = (
            "not implemented (--genome was given but is not used yet)"
            if self.genome
            else "not implemented; would need --genome"
        )
        report.skipped.append({"layer": "biology", "reason": reason})


def validate(source, **options) -> Report:
    """Validate ``source`` with a new :class:`Validator`; see its options."""
    return Validator(**options).validate(source)
