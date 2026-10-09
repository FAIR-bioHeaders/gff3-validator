"""gff3-validator: validate GFF3 files against GFF3 1.26 and the Sequence Ontology.

Pre-release. Only the rules marked ``implemented`` in the catalogue are checked.
"""

__version__ = "0.0.1.dev0"

from gff3_validator.engine import Report, Validator, validate  # noqa: E402
from gff3_validator.findings import Finding  # noqa: E402
from gff3_validator.genome import GenomeError  # noqa: E402
from gff3_validator.reader import InputError  # noqa: E402
from gff3_validator.rules import Catalogue, Rule, load_catalogue  # noqa: E402

__all__ = [
    "Catalogue",
    "Finding",
    "GenomeError",
    "InputError",
    "Report",
    "Rule",
    "Validator",
    "__version__",
    "load_catalogue",
    "validate",
]
