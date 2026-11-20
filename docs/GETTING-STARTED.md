# Getting started and Python API

Use an isolated Python environment (supported runtime Python 3.9+):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install gff3-validator==0.1.0
gff3-validate --version
gff3-validate --help
```

The published 0.1.0 wheel is distinct from current source. In particular, its
optional `headers` extra pins `fair-bioheaders>=0.4,<0.5`; current source declares
`>=0.7,<0.9`. Neither installation should be described as supporting all current
family contracts. Core validation needs no toolkit. For header work inspect the
installed dependency/version and the actual report; HDR-002/not-run is not a
header pass. This documentation task does not repin or publish the validator.

For a source checkout use `poetry install --extras headers`, then prefix commands
with `poetry run`. Full source validation and catalogue/browser checks are in
[AGENTS.md](../AGENTS.md). Test installed wheels from outside the checkout.

## A small local check

```sh
demo_dir=$(mktemp -d "${TMPDIR:-/tmp}/gff3-demo.XXXXXX")
printf '##gff-version 3\nchr1\tdemo\tgene\t1\t4\t.\t+\t.\tID=gene1\n' > "$demo_dir/example.gff3"
gff3-validate "$demo_dir/example.gff3" --no-header --format json > "$demo_dir/report.json"
```

Read the report's findings and not-checked layers. The command never rewrites the
input. Text, JSON, HTML and SARIF are report formats; HTML escapes input values.
Gzip/BGZF is detected from content. Exit 0 means no error-level findings, 1 means
validation errors or a noncompliant profile, and 2 means a usage/input problem; retain stderr for incomplete
input. Warnings, profile results and unavailable biology/header checks retain
separate meanings. A core pass does not establish SO endorsement or biological
correctness. Add `--genome` only for the matching reference and use the documented
translation table. Profiles can raise findings but do not silently change core validity.

## Important Python helpers

These describe current source. A released wheel may precede feature-index/API
additions; inspect the installed version before depending on a source-only helper.

```python
from gff3_validator.engine import validate
from gff3_validator.report import to_json

report = validate("example.gff3", header_mode="skip")
text = to_json(report)
```

`engine.validate(source, **options)` creates a fresh `Validator`; source may be a
path, `-` or a binary stream. `Validator` options include header mode, genome,
translation table, ontology/profile selection and finding limit. The returned
`Report` retains core and profile findings, ontology provenance, counts and
not-checked/truncation information. `report.to_dict()` supplies structured output;
`gff3_validator.report.to_json`, `to_text`, `to_html`, and `to_sarif` render it.
`reader.iter_lines` yields numbered decoded lines and raises `InputError` for
unreadable/truncated input. `genome.Genome` serves explicit reference slices;
`features.build_feature_index` and `resolve_feature_id` expose row/ID evidence,
not schema, checksum or biological validation. Preserve original source bytes.

`OntologyError`/`ProfileError` (ValueError subclasses) signal unavailable/invalid
configuration; filesystem/input errors are not valid reports. Handle them at the
application boundary instead of replacing them with success. Feature indexes
and structural checks retain information proportional to the file; a finding
limit bounds retained findings, not all CPU/memory or decompressed input size.
Apply process, input-size, disk and wall-time limits for untrusted uploads. No
network request is required for ordinary validation; explicit ontology inputs
are local files. See [the maintenance record](ROUND16-MAINTENANCE.md).
