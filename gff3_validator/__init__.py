"""gff3-validator: validate GFF3 files against GFF3 1.26 and the Sequence Ontology.

Early 0.x release; catalogue review remains separate. Only the rules marked ``implemented`` in the catalogue are checked.
"""

__version__ = "0.1.0"

from gff3_validator.engine import Report, Validator, validate  # noqa: E402
from gff3_validator.features import (  # noqa: E402
    FeatureIndex,
    FeatureMatch,
    FeatureRow,
    build_feature_index,
    resolve_feature_id,
)
from gff3_validator.findings import Finding  # noqa: E402
from gff3_validator.genome import GenomeError  # noqa: E402
from gff3_validator.ontology import Ontology, OntologyError, load_ontology  # noqa: E402
from gff3_validator.profiles import Profile, ProfileError, load_profile  # noqa: E402
from gff3_validator.reader import InputError  # noqa: E402
from gff3_validator.rules import Catalogue, Rule, load_catalogue  # noqa: E402

__all__ = [
    "Catalogue",
    "FeatureIndex",
    "FeatureMatch",
    "FeatureRow",
    "Finding",
    "GenomeError",
    "InputError",
    "Ontology",
    "OntologyError",
    "Profile",
    "ProfileError",
    "Report",
    "Rule",
    "Validator",
    "__version__",
    "build_feature_index",
    "load_catalogue",
    "load_ontology",
    "load_profile",
    "resolve_feature_id",
    "validate",
]
