# gff3-validator Constitution

> **Status: draft.** Proposed for Spec Kit planning gates. It restates
> FHR-Specification spec 009 (GFF3 validator), the decisions recorded in
> FHR-Specification #61, and the FAIR-bioHeaders toolkit constitution, and adds
> no authority. David and Adam must approve it before it is treated as ratified.

## Core Principles

### I. The specification and the catalogue are the contract

The validator implements the GFF3 specification 1.26 and a pinned, recorded
Sequence Ontology release; it does not define GFF3. Every check is a numbered
rule in `rules/catalogue.yaml` with its specification reference, and every
finding cites its rule id. Rules are reviewed with the SO group; a rule's
review state is recorded, never assumed. Ambiguities in the specification are
written down as questions, not settled silently in code.

### II. Report, never rewrite

The validator reads bytes and reports. It does not sort, repair, deduplicate or
re-encode an annotation. A suggested fix is guidance only.

### III. Layers stay separate; plain GFF3 is first-class

Core syntax and structure, SO terms, optional biology checks (with `--genome`),
FHGFF3 header checks and repository profiles are distinct layers with distinct
rule ids. A file without a FAIR-bioHeaders header is valid GFF3; header checks
run when a header is present, are mandatory with `--require-header` and skipped
with `--no-header`. Core validation does not depend on the FAIR-bioHeaders
toolkit. Biological plausibility never silently becomes syntactic validity.

### IV. Fail closed and stay bounded on untrusted input

Inputs may come from anywhere. Unreadable or truncated input is a failed run
(exit 2), not a pass. Memory and time stay bounded; the strategy for stateful
checks is documented. No network access during validation. Untrusted text is
escaped in HTML reports.

### V. Honest results

Skipped, unimplemented or incomplete checks are reported as such. Exit codes:
0 no errors, 1 errors, 2 usage or read failure. The CLI, library and web page
give identical findings on the conformance suite.

### VI. Small, compatible, tested

Python (>=3.9), minimal runtime dependencies (PyYAML), browser build through
Pyodide (#61). Rule ids, levels, the JSON report and the CLI are public API once
released; changes need a catalogue version bump and a changelog note. Every
implemented rule ships with fixtures that make it fire and that show valid
input does not.

## Verification gates

Every plan names the checks it must pass, on Python 3.9 and 3.13:

```bash
poetry install
poetry run pytest
poetry run python scripts/render_rules.py --check
poetry run ruff check .
poetry run isort . --check-only
poetry run black . --check
poetry build
```

## Decision boundaries

David and Adam hold release authority. Publishing packages, archiving DOIs,
deploying the web page and claiming SO or repository endorsement are separate
maintainer actions; a spec, plan or task list never authorizes them.
Security-relevant findings follow the FHR-Specification SECURITY.md before any
public issue or PR.

## Governance

This constitution guides Spec Kit specify/plan/tasks gates. Amendments follow the
normal review process with a changelog note. On conflict, the GFF3
specification, spec 009 and maintainer decisions win.

**Version**: 0.1.0 (draft) | **Ratified**: pending maintainer approval | **Last Amended**: 2026-10-08
