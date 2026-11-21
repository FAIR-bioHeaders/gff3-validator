> Every PR requires independent review by another actual model (another family
> preferred); a human alone merges. Agents never enable auto-merge, queue merges
> or substitute default-branch pushes. See [AGENTS.md](AGENTS.md) for current policy.

# Contributing

Start with an issue describing the use case or failure and a small reproducible
GFF3 example. Submit a focused branch/PR with behaviour, the rule ids affected
and tests. Link related work in
[FAIR-bioHeaders-Specification](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification)
(spec 009 and issues #61 to #71). Do not include private annotation or genome
data, credentials, or unrelated formatting in fixtures.

## Setup and checks

From this checkout, on Python 3.9 and 3.13:

```bash
poetry install
poetry run pytest
poetry run python scripts/render_rules.py --check
poetry run ruff check .
poetry run isort . --check-only
poetry run black . --check
poetry build
```

## Rules

- Every check is a rule in `rules/catalogue.yaml`. Add or change the rule there
  first, with its GFF3 1.26 or SO reference, a bad example and a fix, then run
  `python scripts/render_rules.py` and commit the regenerated files.
- A rule is `implemented` only when the engine emits it and a test with a small
  fixture in `tests/fixtures/` shows it firing (and not firing on valid input).
- Rule ids are stable. Do not reuse a retired id; record retired or replaced
  rules and level changes in the catalogue and CHANGELOG.
- Where the GFF3 specification is ambiguous, record it in the rule's `notes`
  and in `docs/questions-for-SO.md` rather than deciding silently. Plausibility
  checks are not core validity: put them in the biology layer or at info level.
- Expected results in tests come from the rules, not from recording the current
  output, and not from what another validator reports.

## Maintainers and policies

David Molik and Adam Wright are the maintainers
([GOVERNANCE](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/blob/main/GOVERNANCE.md)).
SO review of the catalogue is recorded per rule (`review`). Follow the
[code of conduct](CODE_OF_CONDUCT.md) and report security issues privately as in
[SECURITY.md](SECURITY.md).

## Releasing

The 0.1.0 package is published; SO catalogue review remains a separate gate.
A subsequent release needs the configured PyPI trusted publisher/environment
and explicit maintainer authority (see `.github/workflows/release.yml`). Preparing
a release does not authorize publishing, tagging or minting a DOI; those are
maintainer actions.

## License of contributions

New project contributions from March 2025 onward use [MPL-2.0](LICENSE). The existing MIT notice is retained verbatim for previously MIT-licensed material; prior permissions remain available. Third-party code and assets retain their own terms. Consult LICENSE and version history for scope. New contributions must have the rights needed for their declared license; retain source notices.
