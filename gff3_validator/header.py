"""Optional FAIR-bioHeaders (FHGFF3) header checks.

Core validation never imports the FAIR-bioHeaders toolkit. This module only
looks for it when a header has to be checked. The header rules HDR-004 to
HDR-010 come from the toolkit's own reader (``bioheaders.gff3.header_report``,
FAIR-bioHeaders-Specification spec 007), so there is one implementation of the header
format. A toolkit without FHGFF3 support (fair-bioheaders before 0.6), or no
toolkit, leaves a present header unvalidated (HDR-002).
"""

import os

HEADER_PREFIX = "#~"
MODES = ("auto", "require", "skip")
# header_report result -> rule (FAIR-bioHeaders-Specification specs/007-gff3-header
# contracts/validator.md).
RESULT_RULES = (
    ("placement", "HDR-004"),
    ("checksum", "HDR-005"),
    ("yaml", "HDR-006"),
    ("schema", "HDR-007"),
    ("genome_link", "HDR-008"),
)


def toolkit_version():
    """Return the installed fair-bioheaders version, or None."""
    try:
        import bioheaders
    except ImportError:
        return None
    return getattr(bioheaders, "__version__", "unknown")


def toolkit_supports_fhgff3():
    """Whether the installed toolkit can check FHGFF3 headers."""
    try:
        import bioheaders
        import bioheaders.gff3  # noqa: F401
    except ImportError:
        return False
    return hasattr(bioheaders, "FHGFF3_SCHEMA")


def unavailable_reason():
    version = toolkit_version()
    if version is None:
        return (
            "header validation needs the optional FAIR-bioHeaders toolkit, which "
            'is not installed (pip install "gff3-validator[headers]")'
        )
    return (
        f"header validation needs FHGFF3 support, which fair-bioheaders {version} "
        "does not have"
    )


def file_path(source):
    """The path of ``source`` when it is a file on disk, else None (stdin, streams)."""
    if isinstance(source, (str, os.PathLike)) and str(source) != "-":
        return os.fspath(source)
    return None


def check(path, genome=None):
    """Return ``(findings, notes)`` for the header of the GFF3 file ``path``.

    ``findings`` is a list of ``(rule id, message)``; ``notes`` lists checks
    that could not run, as text for ``Report.skipped``.
    """
    from bioheaders.gff3 import header_report

    report = header_report(path, genome)
    findings, notes = [], []
    for key, rule_id in RESULT_RULES:
        result = report[key]
        if result["ok"] is False:
            findings.append((rule_id, result["message"]))
        elif result["ok"] is None and result["message"]:
            notes.append(f"{rule_id} {result['message']}")
    if genome is not None and report["genome_link"]["ok"]:
        status, detail = report["genome_match"], report["genome_detail"]
        if status == "not matched":
            findings.append(
                ("HDR-009", f"the genome link does not match --genome: {detail}")
            )
        elif status == "not checked":
            notes.append(f"HDR-009 not checked: {detail}")
    for warning in report["warnings"]:
        findings.append(("HDR-010", warning))
    return findings, notes
