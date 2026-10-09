"""Text and JSON renderings of a :class:`~gff3_validator.engine.Report`."""

import json


def to_json(report):
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"


def to_text(report):
    lines = []
    for finding in report.findings:
        where = report.source
        if finding.line is not None:
            where += f":{finding.line}"
        if finding.field is not None:
            where += f" (column {finding.field})"
        lines.append(f"{where}: {finding.level} {finding.rule}: {finding.message}")
        if finding.fix and finding.level != "info":
            lines.append(f"    fix: {finding.fix}")
    if report.truncated:
        lines.append(f"... {report.truncated} more findings not shown")
    counts = report.counts
    verdict = "no errors" if report.valid else "INVALID"
    lines.append(
        f"{report.source}: {verdict} ({counts['error']} errors, "
        f"{counts['warning']} warnings, {counts['info']} notes; "
        f"{report.lines} lines)"
    )
    for item in report.skipped:
        lines.append(f"  not checked: {item['layer']}: {item['reason']}")
    return "\n".join(lines) + "\n"
