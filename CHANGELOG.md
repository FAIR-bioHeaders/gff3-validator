# Changelog

## Unreleased

- Document the MPL-2.0 transition for new project contributions from March 2025 onward, preserve historical permissions and third-party notices, and align README/package/citation licensing. No runtime behavior changes.

- Galaxy tool wrapper (`galaxy/`, FHR-Specification #71): `gff3_validator`,
  following the IUC standards, with HTML, JSON and SARIF reports, optional
  genome and translation table, header mode and Planemo tests on conformance
  files. To be submitted to tools-iuc once the Bioconda recipe is merged.
- Conformance suite (`conformance/`, FHR-Specification #68, spec 009
  FR-012): 92 small cases (53 valid, 39 invalid; 67 settled by GFF3 1.26, 22
  depending on an open SO question, 3 for the FHGFF3 header layer) covering
  all 68 implemented rules, with a manifest of expected verdicts and findings.
  `scripts/make_conformance.py` generates it byte-identically;
  `scripts/check_conformance.py` checks it and scores gff3-validator (full
  findings) or any other tool (exit status). CI runs it against the CLI.
  docs/EVALUATION.md adds a GenomeTools score on the specification-settled
  cases.

## 0.1.0 — 2026-10-09

First release. 68 of 88 catalogue rules are implemented; the Sequence
Ontology rules await the SO review. Also usable in the browser at
https://fair-bioheaders.github.io/gff3-validator/.


- Repository bootstrapped: package skeleton, draft rule catalogue
  (FHR-Specification #62), evaluation of existing validators (#63). Not released.
- Attribute (column 9), directive and structure rules: GFF-ATT-001 to -014
  and -016, GFF-DIR-001 to -010, GFF-STR-001 to -011, and GFF-SYN-005 to
  -010 and -012. Rules that depend on an open SO question are implemented
  only as far as the specification text settles them; each rule's notes say
  what is and is not reported. Structure state is O(number of IDs); an
  opt-in performance test measures runtime and memory.
- Biology rules BIO-001 to BIO-011 with `--genome` (plain or gzip/BGZF
  FASTA, indexed like .fai and read on demand) and `--translation-table N`
  (NCBI tables, default 1). Codon rules are warnings; codons covered by a
  `recoded_codon` child of the CDS or by `transl_except` are exempt
  (SO-Ontologies#658, pending SO). A genome that cannot be indexed exits 2.
- The JSON report's "skipped" entry for the core layer now lists the planned
  core rules instead of the checked categories.
- Reports: `--format html` (one self-contained, accessible page with its own
  CSP; findings sortable by line, rule and level; rule ids link to
  docs/rules.md; lists the layers not checked, the GFF3 and SO sources and the
  limitations) and `--format sarif` (SARIF 2.1.0 with the catalogue as rules,
  tested against the vendored OASIS schema). SARIF regions give the line; the
  GFF3 column is in each result's properties (FHR-Specification #67).
- In-browser page (`web/`, FHR-Specification #69): the wheel runs in Pyodide
  314.0.7 in a Web Worker, reading the file in slices (plain or gzip), with
  optional genome, header and translation-table options, the HTML report
  inline and JSON, SARIF and HTML downloads. A Content-Security-Policy limits
  connections to the site and the pinned Pyodide release; `pyodide.js` and
  `pyodide-lock.json` are pinned with SRI. `scripts/build_web.py` builds
  `web/dist`; `.github/workflows/pages.yml` deploys it to GitHub Pages after a
  parity check (`web/test/parity.mjs`, also a CI job) shows the same JSON,
  SARIF and HTML reports as the CLI on every fixture.
