# Agent instructions

## Current repository context

This repository owns core GFF3 syntax/structure, ontology and optional biology
checks, repository profiles and the optional FHGFF3 header integration. Plain GFF3
remains usable without FAIR BioHeaders. Shared header contracts are published in
FAIR-bioHeaders-Specification; FHGFF3 development and its inherited feature models
are separate. A new catalogue/profile rule is not automatically a header-schema
addition; identify each contract affected and preserve the core/profile boundary.

## Schema additions and their own development cycle

A new optional field, structured alternative, enum value, constraint, required
field or changed meaning is a schema-contract change, even when motivated by a
UI, exporter, parser fix or documentation task. Identify it explicitly as a
**schema addition** or other contract change in its issue and PR. Supporting an
already adopted field in a consumer is implementation work, not a new field.

Schema additions have their own proposal, review, compatibility, versioning and
release cycle. Keep them separately reviewable from routine fixes, website work,
packaging and dependency updates; link dependent implementation PRs rather than
silently adopting a field downstream. Shared fields/objects and cross-type rules
belong in FAIR-bioHeaders-Specification; type-specific design starts in the owning
development repository and is coordinated into shared publication. Name affected
types, requiredness, semantics, mappings, serializers and conformance fixtures.

During active construction of FHP, FHT and FHGFF3, maintainers may iterate on draft
fields with lighter process and include coordinated schema/implementation work in
one clearly scoped PR. Record the proposal and compatibility impact in that PR;
this flexibility does not make every field adopted or supported. Preserve already
published contracts and cited versions, label draft behavior, and obtain joint
maintainer review before publication. FHR additions retain the separate cycle.
Do not apply draft flexibility to released FHP/FHGFF3 schemas retroactively.

Use the shared specification's `docs/SCHEMA-VERSIONS.md` and
`schemas/versions.json`: contract versions are per type, distinct from repository
release tags and biological resource versions. Additive changes that preserve all
valid values and meanings qualify for a minor increment; invalidating records or
changing meanings requires a major increment. Do not assign a new version merely
for implementing an existing contract. Never rewrite immutable releases, fixed
schema aliases or existing file-bound headers as incidental cleanup. Header edits
require checksum recomputation and may affect downstream parent links.

Proposals are not adopted contracts: FAIR-bioHeaders-Specification#139 / draft
PR #140 (structured vouchers) and profiles still under review in that repository
(#56) remain proposals until adopted. Implemented subsets do not establish full
profile or header-family support. The mapping page in fair-bioheaders.github.io#29
depends on approved profiles.

## Strategy and boundaries

Read README, spec 009 (`specs/001-gff3-validator/spec.md`, and the original in
FAIR-bioHeaders-Specification), the relevant issue (#61 to #71) and current code before
editing. The validator reports; it never rewrites annotation files.

- The GFF3 specification 1.26 and the pinned SO release are the authorities.
  Cite a rule id from `rules/catalogue.yaml` for every check you add or change,
  and give the specification section it comes from. Do not invent rules,
  ontology relationships, repository requirements or metadata. Where the
  specification is ambiguous, add a `notes` entry and a question in
  `docs/questions-for-SO.md` instead of choosing silently.
- Keep layers separate: core GFF3 syntax and structure, SO terms, optional
  biology checks (need `--genome`), FHGFF3 header checks (optional extra
  `fair-bioheaders`), and repository or community profiles (`profiles/`),
  whose findings never change core validity. Core validation must not
  import FAIR-bioHeaders. Plain GFF3 without a header is valid input.
- A profile translates only what its source document says, cites the
  section for every rule, can only raise core levels, and records the
  repository's review only once it has happened.
- Do not mark a rule `implemented` unless the engine emits it and a fixture test
  covers it. Do not record SO endorsement (`review`) that has not happened.
- Skipped or unimplemented checks are reported as such, never as passed.

David and Adam are the maintainers and jointly hold release authority
(FAIR-bioHeaders-Specification GOVERNANCE.md).

## Repository map

`gff3_validator/reader.py` opens plain, gzip/BGZF or stdin input and yields
lines. `rules.py` loads the packaged catalogue (`gff3_validator/catalogue.yaml`,
a generated copy of `rules/catalogue.yaml`). `engine.py` runs the checks in
`checks/` and collects `Finding`s; `genome.py` indexes the `--genome` FASTA and reads slices on demand;
`codons.py` holds the NCBI translation tables used by `checks/biology.py`;
`ontology.py` loads the bundled SO release (`data/so.json.gz`, derived from
so.obo by `scripts/update_so.py`, recorded in `data/so-release.json`) or a
`--so` so.obo, and `checks/sequence_ontology.py` holds the SO rules;
`header.py` holds the optional FHGFF3 hook;
`profiles/` (the package) loads repository and community profiles
(`profiles/*.yaml` at the top level, packaged as generated copies) and holds
their checks (`agbiodata.py`); see `docs/profiles.md`;
`report.py` renders text, JSON, HTML and SARIF 2.1.0; `web.py` is the
Python side of the in-browser page; `cli.py` is the `gff3-validate` command.
`scripts/render_rules.py` generates `docs/rules.md`, the packaged copy and the
README rule list, and for each profile its packaged copy,
`docs/profiles/ID.md` and its table in `docs/profiles.md`. Tests and fixtures are in `tests/`. `conformance/` is the
implementation-neutral conformance suite, generated by
`scripts/make_conformance.py` and checked (and run against a validator) by
`scripts/check_conformance.py`; edit the generator, never the files.
`web/` is the in-browser page (`glue.js` is shared by its worker and the
Pyodide parity test in `web/test/`); `scripts/build_web.py` builds `web/dist`.

## Verification

```bash
poetry install
poetry run pytest
poetry run python scripts/render_rules.py --check
poetry run ruff check .
poetry run isort . --check-only
poetry run black . --check
poetry run python scripts/check_conformance.py --gff3-validate gff3-validate
```

Test installed commands from outside the checkout. Record environment
limitations and failed checks.

## Security

Inputs are untrusted. Keep memory and time bounded, escape untrusted text in
HTML output, make no network requests during validation, and report suspected
vulnerabilities privately as described in the FAIR-bioHeaders-Specification
[SECURITY.md](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/blob/main/SECURITY.md),
not in a public issue. Publishing packages, tags and DOIs are separate
maintainer actions; a spec, plan or task list never authorizes them.

## Licensing policy (2026-10-09)

New FAIR BioHeaders project contributions from March 2025 onward use MPL-2.0.
David Molik left USDA in February 2025. Preserve historical USDA public-domain
material, previously granted permissions, and third-party licenses/notices;
do not label all current contributors as government employees. See LICENSE
for scope. Do not rewrite historical releases or silently relicense upstream
material. Keep README badges, package metadata and citation metadata consistent.
