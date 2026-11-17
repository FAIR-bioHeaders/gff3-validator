# Fixture scope

`valid/` and `invalid/` classify **core GFF3 structure** for the catalogue tests.
They are not blanket FAIR-bioHeaders conformance labels. The unmarked pytest
lane intentionally disables optional header validation for deterministic core
rule results; when a header is present, its report contains HDR-002 and a
`skipped` reason explicitly
naming that test-only choice. Pytest's session header identifies this lane.
Tests marked `headers` use the real toolkit, or skip with an availability reason.

## Historical header and complete companion (#33)

| Input | What it establishes |
| --- | --- |
| `tests/fixtures/valid/fhgff3_header.gff3` | Historical core-structure example with three `#~` comment lines. Its bytes are preserved, SHA-256 `28f74236779c3572536cad46f97f14dac64e15a6f70d600b45909785b7a3a1ac`. It cites an FHR raw-main schema, uses a numeric version, and lacks required metadata and a checksum. It is **not** a conforming FHGFF3 header. With actual toolkit checks it is rejected by HDR-005/HDR-007. |
| `conformance/valid/fhgff3-header-valid.gff3` | Existing generated, complete checksummed companion citing immutable FHGFF3 `v0.4.0`, contract `1.0`. Real toolkit tests check its header and matching parent; the conformance generator owns its bytes. |

The issue originally named `conformance/fixtures/valid/fhgff3_header.gff3`;
that path does not exist. The historical input is under `tests/fixtures/`.
A URL replacement would not repair its other missing/invalid metadata.

The declared optional dependency remains `fair-bioheaders>=0.7,<0.9`. The
companion targets a release that this runtime bundles; it does **not** claim
support for the family's newer specification `v0.6.0` or change package pins.
The complete companion is reused, not copied or regenerated to rewrite history.

```sh
python scripts/check_header_fixtures.py \
  --gff3-validate /path/to/gff3-validate --mode checked
```

This exercises the installed CLI outside the checkout and reports
historical rejection, companion header checking, and explicit `--no-header`
checks as `not-run`. In a core-only environment use `--mode unavailable`:
headers report HDR-002 plus a reason, not a header-conformance pass. CI runs
both modes against the built wheel in an isolated environment, installing the
existing `headers` extra only between those two runs. No fixture is modified.

`Report.valid`/CLI exit 0 means no error finding, not that every optional layer
ran. Consult the `skipped`/`notChecked` fields and HDR-002/HDR-003 notes. Tests
of absent/stubbed checking verify that reporting behavior; they do not grant a
schema/checksum verdict.
