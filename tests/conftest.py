"""Test configuration.

FHGFF3 header checks depend on the optional FAIR-bioHeaders toolkit (the
headers extra). So that results do not depend on what happens to be installed,
tests run as if it were absent (HDR-002), except tests marked ``headers``,
which use the real toolkit and are skipped when it lacks FHGFF3 support.
"""

import pytest

from gff3_validator import header

REAL_SUPPORT = header.toolkit_supports_fhgff3()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "headers: needs the FAIR-bioHeaders toolkit with FHGFF3 support"
    )


@pytest.fixture(autouse=True)
def _header_support(request, monkeypatch):
    if request.node.get_closest_marker("headers"):
        if not REAL_SUPPORT:
            pytest.skip("needs the FAIR-bioHeaders toolkit with FHGFF3 support")
        return
    monkeypatch.setattr(header, "toolkit_supports_fhgff3", lambda: False)
