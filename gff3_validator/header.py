"""Optional FAIR-bioHeaders (FHGFF3) header checks.

Core validation never imports the FAIR-bioHeaders toolkit. This module only
looks for it when a header has to be checked. FHGFF3 header validation is not
implemented yet: the toolkit (fair-bioheaders 0.4) has no GFF3 support, so a
present header is reported with HDR-002 and the header layer is incomplete.
"""

HEADER_PREFIX = "#~"
MODES = ("auto", "require", "skip")


def toolkit_version():
    """Return the installed fair-bioheaders version, or None."""
    try:
        import bioheaders
    except ImportError:
        return None
    return getattr(bioheaders, "__version__", "unknown")


def unavailable_reason():
    version = toolkit_version()
    if version is None:
        return (
            "header validation is not implemented in this version and the "
            "optional FAIR-bioHeaders toolkit is not installed "
            '(pip install "gff3-validator[headers]")'
        )
    return (
        "header validation is not implemented in this version "
        f"(fair-bioheaders {version} has no FHGFF3 support yet)"
    )
