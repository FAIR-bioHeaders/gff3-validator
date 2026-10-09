# Agent instructions

## Strategy and boundaries

Read README, spec 009 (`specs/001-gff3-validator/spec.md`, and the original in
FHR-Specification), the relevant issue (#61 to #71) and current code before
editing. The validator reports; it never rewrites annotation files.

- The GFF3 specification 1.26 and the pinned SO release are the authorities.
  Cite a rule id from `rules/catalogue.yaml` for every check you add or change,
  and give the specification section it comes from. Do not invent rules,
  ontology relationships, repository requirements or metadata. Where the
  specification is ambiguous, add a `notes` entry and a question in
  `docs/questions-for-SO.md` instead of choosing silently.
- Keep layers separate: core GFF3 syntax and structure, SO terms, optional
  biology checks (need `--genome`), FHGFF3 header checks (optional extra
  `fair-bioheaders`), and later repository profiles. Core validation must not
  import FAIR-bioHeaders. Plain GFF3 without a header is valid input.
- Do not mark a rule `implemented` unless the engine emits it and a fixture test
  covers it. Do not record SO endorsement (`review`) that has not happened.
- Skipped or unimplemented checks are reported as such, never as passed.

David and Adam are the maintainers and jointly hold release authority
(FHR-Specification GOVERNANCE.md).

## Repository map

`gff3_validator/reader.py` opens plain, gzip/BGZF or stdin input and yields
lines. `rules.py` loads the packaged catalogue (`gff3_validator/catalogue.yaml`,
a generated copy of `rules/catalogue.yaml`). `engine.py` runs the checks in
`checks/` and collects `Finding`s; `genome.py` indexes the `--genome` FASTA and reads slices on demand;
`codons.py` holds the NCBI translation tables used by `checks/biology.py`;
`header.py` holds the optional FHGFF3 hook;
`report.py` renders text, JSON, HTML and SARIF 2.1.0; `web.py` is the
Python side of the in-browser page; `cli.py` is the `gff3-validate` command.
`scripts/render_rules.py` generates `docs/rules.md`, the packaged copy and the
README rule list. Tests and fixtures are in `tests/`.
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
```

Test installed commands from outside the checkout. Record environment
limitations and failed checks.

## Security

Inputs are untrusted. Keep memory and time bounded, escape untrusted text in
HTML output, make no network requests during validation, and report suspected
vulnerabilities privately as described in the FHR-Specification
[SECURITY.md](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/SECURITY.md),
not in a public issue. Publishing packages, tags and DOIs are separate
maintainer actions; a spec, plan or task list never authorizes them.
