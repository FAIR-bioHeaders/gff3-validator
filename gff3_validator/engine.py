"""The validation engine: reads lines, runs the rules, collects findings."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from gff3_validator import codons, header
from gff3_validator.checks import syntax
from gff3_validator.checks.attributes import parse_attributes
from gff3_validator.checks.biology import Biology
from gff3_validator.checks.directives import (
    FastaSection,
    check_directive,
    sequence_region,
    split_directive,
)
from gff3_validator.checks.structure import Structure
from gff3_validator.findings import Finding
from gff3_validator.genome import Genome
from gff3_validator.reader import iter_lines
from gff3_validator.rules import load_catalogue

REPORT_VERSION = "0.1-draft"
DEFAULT_MAX_FINDINGS = 10000
BOM = "\ufeff"
# Rules that can fire on most lines of a file are reported once, at their
# first occurrence, with a count, so that they cannot crowd errors out of the
# findings cap.
SUMMARISED = ("GFF-SYN-006", "GFF-SYN-009", "GFF-ATT-003", "GFF-ATT-009")


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
    the path of a genome FASTA (plain or gzip/BGZF); with it the biology rules
    run, translating CDS with NCBI ``translation_table`` (default 1).
    """

    def __init__(
        self,
        header_mode="auto",
        genome: Optional[str] = None,
        max_findings=DEFAULT_MAX_FINDINGS,
        catalogue=None,
        translation_table=codons.DEFAULT_TABLE,
    ):
        if header_mode not in header.MODES:
            raise ValueError(f"header_mode must be one of {header.MODES}")
        if translation_table not in codons.TABLES:
            raise ValueError(
                f"translation table {translation_table} is not available; "
                f"choose one of {sorted(codons.TABLES)}"
            )
        self.header_mode = header_mode
        self.genome = genome
        self.table = codons.table(translation_table)
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

        Raises ``InputError`` if the input cannot be read completely, and
        ``GenomeError`` (an ``InputError``) if the genome cannot be used.
        """
        if self.genome is None:
            return self._validate(source, name, None)
        with Genome(self.genome) as genome:
            return self._validate(source, name, genome)

    def _validate(self, source, name, genome) -> Report:
        report = Report(
            source=name or str(source), catalogue_version=self.catalogue.version
        )
        summary = {}

        def emit(rule_id, message, line=None, field=None):
            if rule_id in SUMMARISED:
                entry = summary.get(rule_id)
                if entry is None:
                    summary[rule_id] = [message, line, field, 1]
                else:
                    entry[3] += 1
                return
            self._add(report, rule_id, message, line=line, field=field)

        def invalid_utf8(number):
            emit("GFF-SYN-006", "line is not valid UTF-8", line=number)

        structure = Structure()
        biology = None if genome is None else Biology(genome, self.table, structure)
        fasta = None
        version_seen = False
        for number, line in iter_lines(source, invalid_utf8):
            report.lines = number
            if line.endswith("\r"):
                # A CRLF line ending is not reported (question 2).
                line = line[:-1]
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
            if fasta is not None:
                for rule_id, at, message in fasta.line(number, line):
                    emit(rule_id, message, line=at)
                continue
            if line.startswith("#"):
                if line.startswith(header.HEADER_PREFIX):
                    report.header_lines += 1
                elif line.startswith("##"):
                    fasta = self._directive(
                        report, emit, structure, number, line, version_seen
                    )
                    if biology is not None and line.rstrip() == "###":
                        for rule_id, at, message in biology.flush():
                            emit(rule_id, message, line=at)
                    if number > 1 and line.startswith("##gff-version"):
                        version_seen = True
                continue
            if line.startswith(">"):
                emit(
                    "GFF-DIR-005",
                    "a line starting with '>' begins a FASTA section without "
                    "##FASTA",
                    line=number,
                )
                fasta = FastaSection(structure.fasta_record)
                for rule_id, at, message in fasta.line(number, line):
                    emit(rule_id, message, line=at)
                continue
            if line.strip() == "":
                continue
            fields = line.split("\t")
            for rule_id, column, message in syntax.check_columns(fields, line):
                emit(rule_id, message, line=number, field=column)
            if len(fields) != 9:
                continue
            coordinates = syntax.coordinates(fields[3], fields[4])
            if coordinates is None:
                attributes, problems = parse_attributes(fields[8])
            else:
                attributes, problems = parse_attributes(fields[8], *coordinates)
            for rule_id, message in problems:
                emit(rule_id, message, line=number, field=9)
            for rule_id, at, message in structure.feature(
                number, fields[0], fields[2], fields[6], coordinates, attributes
            ):
                emit(rule_id, message, line=at)
            if biology is not None:
                for rule_id, at, message in biology.feature(
                    number,
                    fields[0],
                    fields[2],
                    fields[6],
                    fields[7],
                    coordinates,
                    attributes,
                ):
                    emit(rule_id, message, line=at)
        if report.lines == 0:
            self._add(report, "GFF-SYN-001", "the input is empty")
        if fasta is not None:
            for rule_id, at, message in fasta.finish():
                emit(rule_id, message, line=at)
        for rule_id, at, message in structure.finish():
            emit(rule_id, message, line=at)
        if biology is not None:
            for rule_id, at, message in biology.finish():
                emit(rule_id, message, line=at)
        for rule_id, (message, line, column, count) in summary.items():
            if count > 1:
                message += f" (and {count - 1} more like this in the file)"
            self._add(report, rule_id, message, line=line, field=column)
        self._finish_header(report)
        self._record_skipped(report, biology)
        return report

    def _directive(self, report, emit, structure, number, line, version_seen):
        """Handle a "##" line; return a FastaSection if it starts one."""
        if line.rstrip() == "###":
            structure.resolution_point()
            return None
        name, arguments = split_directive(line)
        if line.startswith("##gff-version"):
            if number > 1 and version_seen:
                emit("GFF-SYN-002", "repeated ##gff-version directive", line=number)
            return None
        if name == "FASTA":
            return FastaSection(structure.fasta_record)
        if name == "sequence-region":
            problem, region = sequence_region(arguments)
            if problem:
                emit("GFF-DIR-001", f"##sequence-region {problem}", line=number)
            else:
                for rule_id, at, message in structure.sequence_region(number, *region):
                    emit(rule_id, message, line=at)
            return None
        for rule_id, message in check_directive(name, arguments):
            emit(rule_id, message, line=number)
        return None

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

    def _record_skipped(self, report, biology):
        planned = [
            rule.id
            for rule in self.catalogue
            if rule.layer == "core" and rule.status != "implemented"
        ]
        if planned:
            report.skipped.append(
                {
                    "layer": "core",
                    "reason": "partial: these core rules are planned and not "
                    "checked: " + ", ".join(planned),
                }
            )
        report.skipped.append({"layer": "so", "reason": "not implemented"})
        if biology is None:
            report.skipped.append(
                {"layer": "biology", "reason": "not run; needs --genome"}
            )
            return
        reasons = biology.skip_reasons()
        if reasons:
            report.skipped.append(
                {"layer": "biology", "reason": "partial: " + "; ".join(reasons)}
            )


def validate(source, **options) -> Report:
    """Validate ``source`` with a new :class:`Validator`; see its options."""
    return Validator(**options).validate(source)
