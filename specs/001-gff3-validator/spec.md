> Copied from FHR-Specification
> [specs/009-gff3-validator/spec.md](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/009-gff3-validator/spec.md)
> (main at commit 2ef8da7, 2026-10-08), which remains the authoritative version. Decisions since
> then: FR-013 was decided in
> [FHR-Specification #61](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/61)
> (Python with Pyodide; separate `gff3-validator` package; header validated when
> present, `--require-header`, `--no-header`).

# Feature Specification: One-stop GFF3 validator

**Feature Branch**: `009-gff3-validator`

**Created**: 2026-10-08

**Status**: Draft

**Input**: Decision 9 in #54 (Adam): "people don't know where to go and there are
just old perl validators. We need a one-stop shop." The Sequence Ontology (SO)
group is on board with FAIR-bioHeaders doing this work. Existing options are
fragmented: the SO-era Perl GFF3 validator and its online service, GenomeTools
`gt gff3validator` (C, terse messages), AGAT checks, the NAL i5k `gff3toolkit`
QC, NCBI `table2asn` submission checks, and small unmaintained repositories.
Adam's 2024 prototype (FHGFF3 repository: validator script and web app) and
the LinkML GFF3 data model are starting points to evaluate, not finished bases.

## Goal

One place, one name, three interfaces (web page, CLI, library) that tells a user
whether a GFF3 file is valid against the GFF3 specification and the Sequence
Ontology, explains every problem in plain language with the line and a fix, and
also checks the FHGFF3 provenance header and its link to the genome.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Check a file in the browser (Priority: P1)

A biologist drags a GFF3 file onto a web page and gets a readable report. The
file never leaves their computer.

**Independent Test**: The hosted page validates the conformance suite with the
same results as the CLI, offline after load.

### User Story 2 - Validate in a pipeline (Priority: P1)

A pipeline runs `gff3-validate annotation.gff3.gz --genome genome.fa` and fails
on errors, with a machine-readable JSON report.

### User Story 3 - Prepare a submission (Priority: P2)

A curator validates against a repository profile (NCBI, Ensembl, Alliance) that
adds that repository's rules on top of the core checks.

### User Story 4 - Check the provenance header (Priority: P2)

The validator reports whether the FHGFF3 header is present and valid, whether the
checksum verifies, and whether the referenced genome matches (`--genome`).

## Requirements *(mandatory)*

### Rule catalogue (shared with SO)

- **FR-001**: Every check is a numbered rule in a public catalogue (id, level
  error/warning/info, description, specification reference, example, fix),
  maintained with the SO group. Reports cite rule ids.
- **FR-002**: Syntax rules from the GFF3 specification: `##gff-version 3`
  first line; nine tab-separated columns; 1-based `start <= end`; score,
  strand and phase values; phase required for CDS; percent-encoding of reserved
  characters; attribute syntax and reserved tags (ID, Name, Alias, Parent,
  Target, Gap, Derives_from, Note, Dbxref, Ontology_term, Is_circular);
  directives (`##sequence-region`, `###`, `##FASTA`, `##species`,
  `##genome-build`).
- **FR-003**: Structure rules: ID uniqueness (shared IDs only for multi-line
  features), Parent and Derives_from references resolve, no cycles, features
  within `##sequence-region` bounds, seqids consistent with `##FASTA`
  and with a supplied genome.
- **FR-004**: Sequence Ontology rules: feature types are SO terms (name or
  accession) from a pinned, recorded SO release; parent and child types follow
  SO relationships (for example exon part_of transcript); obsolete terms are
  reported with replacements.
- **FR-005**: Biology rules (optional, need `--genome`): CDS phase consistency,
  CDS within exons, start and stop codons under a chosen translation table,
  strand consistency within a gene.
- **FR-006**: FHGFF3 header rules: delegate to the shared FAIR-bioHeaders core
  (header block, checksum R1–R10, schema validation, `derivedFrom` link check).

### Interfaces and outputs

- **FR-007**: CLI with exit codes (0 valid, 1 errors, 2 usage), gzip/BGZF and
  stdin input, streaming with bounded memory for files with millions of
  features.
- **FR-008**: Reports in plain text, JSON (rule id, level, line, column, message,
  fix) and HTML; optional SARIF for CI annotations.
- **FR-009**: A static web page (hosted on the FAIR-bioHeaders site) running the
  same engine in the browser, so files stay local.
- **FR-010**: Distribution on PyPI and Bioconda, plus a Galaxy tool wrapper, a
  Nextflow module (FHR-Nextflow) and a container.
- **FR-011**: Repository profiles layered on the core rules (NCBI, Ensembl,
  Alliance), consistent with the community profiles in #51.

### Engineering

- **FR-012**: A GFF3 conformance suite (valid and invalid files, each with the
  expected rule ids), co-curated with SO, run in CI, reusable by other tools.
- **FR-013**: Implementation language and packaging [NEEDS CLARIFICATION:
  Python engine reusing the converter's streaming core, with the browser build
  via Pyodide (recommended for a small team), or a Rust engine with Python
  bindings and WebAssembly for speed? And a separate, discoverable package and
  repository (`gff3-validator`, names free on PyPI and Bioconda) that the `fhr`
  toolkit depends on, or commands inside `fhr`? Recommendation: separate
  package and repository, because GFF3 users without FHR headers must find it].
- **FR-014**: Evaluate the FHGFF3 prototype and the LinkML GFF3 model; reuse what
  fits and record what was replaced and why.

## Success Criteria *(mandatory)*

- **SC-001**: The rule catalogue is reviewed and endorsed by the SO group.
- **SC-002**: The conformance suite covers every catalogue rule; the CLI, library
  and web page give identical results on it.
- **SC-003**: Validates a full vertebrate annotation (e.g. human GENCODE, about 3
  million lines) within minutes and with bounded memory.
- **SC-004**: Listed by SO and the FAIR-bioHeaders site as the recommended GFF3
  validator; the old validators' pages point to it.

## Assumptions

- GFF3 specification version 1.26 (the current SO-hosted version) is the baseline.
- GTF and GFF2 are out of scope; converting them is left to existing tools.
