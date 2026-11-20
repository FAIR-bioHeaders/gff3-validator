# Distribution and Galaxy handoff

## Published 0.1.0, verified 2026-11-20 UTC

The published PyPI/Bioconda package and source `main` have different capabilities.
Bioconda [recipe #70098](https://github.com/bioconda/bioconda-recipes/pull/70098)
is merged. The downloaded noarch package is 67,248 bytes, SHA-256
`ba1b43c26187f24f72cf703af7bbabc63d9dd2d7a34bbc71d136aa0bba663637`.
The actual BioContainer is:

```text
quay.io/biocontainers/gff3-validator:0.1.0--pyhdfd78af_0
sha256:35ed8ccb21036bf4f87288d9d06aa427a8f24b082ee6d754a0db8d9887772cf5
```

Its installed CLI reports `0.1.0`. JSON, text, HTML and SARIF reports were
exercised with positive/rejection inputs and their expected exits. Planned or
skipped core/SO/biology/header checks remain explicit. The Galaxy depot
Singularity URL returned HTTP 404 in this verification; a Quay image does not
establish that separate artifact's availability.

## Galaxy wrapper scope

`galaxy/gff3_validator.xml` targets that published **0.1.0**. The wrapper accepts
plain/gzip GFF3, optional plain/gzip genome FASTA and a translation table, header
modes, HTML and optional JSON/SARIF reports. Invalid input (validator exit 1)
produces reports successfully; incomplete validation (exit 2) fails the job.

The published package has **no `--profile` option**. The former wrapper profile
selector and its unsupported ninth test have therefore been removed; their
fixture bytes are retained. Source-main profiles are not silently substituted
for the released dependency. Likewise, the lone-CR reader correction on `main`
is absent from 0.1.0; LF/CRLF support is not evidence of lone-CR row preservation.
The release's optional FAIR-header integration is not current header-contract
support. No new validator release is implied by this wrapper correction.

The wrapper's eight released-runtime cases cover valid/invalid reports,
translation tables, required/skipped headers, gzip input/genome and an unusable
genome's incomplete-run exit. Strict Planemo lint passes. Full managed-Galaxy
execution and external tools-iuc acceptance are recorded separately in
[distribution issue #21](https://github.com/FAIR-bioHeaders/gff3-validator/issues/21).
Neither a prepared wrapper nor a passing local run establishes IUC acceptance,
registry listing, or Sequence Ontology endorsement. Historical package license
metadata is preserved; current source guidance does not relabel old artifacts.
