# Evaluation of the prototype, the LinkML model and existing GFF3 validators

For [FHR-Specification #63](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/63)
(spec 009 FR-014). Run date 2026-10-08. Other tools' results are comparison
evidence, not the source of truth: where they disagree with the catalogue the
catalogue cites GFF3 1.26, or the case is a question in
[questions-for-SO.md](questions-for-SO.md).

## Summary

- **Adam's 2024 prototype** contributes the right shape (one engine, a CLI
  class and a web page with a per-line error table), a check list taken from
  the SO-era Perl validator, and good provenance notes. It does not run, and
  most checks would be wrong if it did, so no code is reused; its ideas are in
  the catalogue.
- **The LinkML GFF3 model** is a 2021 draft data model, not a validator or a
  streaming parser. Possible later use is as an export or documentation model.
- **GenomeTools `gt gff3validator`** is the strongest existing checker of
  structure (IDs, Parent, cycles, multi-line features, sequence regions). It
  caught 15 of the 19 broken fixtures (16 with `-typecheck so`). But it stops
  at the first error, has no rule ids or fixes, uses a 2016 SO file, and
  misses some syntax (empty columns, Gap).
- **AGAT** is a repair tool, not a validator. It exits 0 on every fixture,
  silently fixes or drops data (it removed three valid CDS lines from the
  specification's own canonical gene), and is GPL-3.0.
- **GFF3toolkit `gff3_QC`** has the closest thing to a rule catalogue (about
  50 numbered error codes), but assumes one canonical gene model per
  transcript (it reports "wrong phase" on the specification's own example),
  crashed on a non-integer coordinate, and exits 0 when it finds errors.
- **The Perl validator** (2006 to 2011) documented its checks best and is the
  basis of most of the catalogue's syntax rules; it needs a database and a CGI
  server and is unmaintained.
- **NCBI table2asn** is a submission pipeline, not a GFF3 validator; it is the
  reference for a future NCBI profile (#70).

## Adam's prototype (FHGFF3, November 2024)

Files: [`python/gff3-validator.py`](https://github.com/FAIR-bioHeaders/FHGFF3/blob/9c8cf644/python/gff3-validator.py),
[`jsonschema/gff3-validator-webapp.py`](https://github.com/FAIR-bioHeaders/FHGFF3/blob/9c8cf644/jsonschema/gff3-validator-webapp.py)
and [`.html`](https://github.com/FAIR-bioHeaders/FHGFF3/blob/9c8cf644/jsonschema/gff3-validator-webapp.html)
(commits 54ae2f98 and 9c8cf644). The prototype is acknowledged as
unfinished; this review is about what to carry forward.

### What to keep

- **One engine, two front ends.** A `GFF3Validator` class with
  `validate_line` and `validate_file`, used by both the command line and the
  web page. This is the design of spec 009 (CLI, library and page share one
  engine). Kept as `gff3_validator.Validator`.
- **The check list.** The docstring names its sources (biodatamodels
  gff-schema and the tharris Perl validator), and the checks follow the Perl
  validator: nine columns, coordinates, strand, phase, duplicate IDs, Parent
  and Derives_from resolution, cycles, Target and Gap syntax, Alias and Note
  values. Each became a catalogue rule (GFF-SYN-003, -013 to -018,
  GFF-STR-001, -004 to -006, GFF-ATT-010, -011).
- **GVF awareness.** Checks on Variant_seq, Amino_acid and Codon show that GVF files will arrive. They belong in a GVF profile later,
  not in the core (GFF-ATT-007 notes).
- **The report UI.** A file chooser and a table of errors grouped by line is
  the right minimal page for FR-009. The new page should add the rule id,
  level and fix columns and run in the browser.
- **Recording provenance.** Naming the upstream sources in the code is the
  practice AGENTS.md asks for.

### What to replace, and why

Probe: `scripts/evaluation/probe_prototype.py` with linkml-runtime 1.12.0 on
Python 3.13.

| Problem | Evidence | Replacement |
|---|---|---|
| Does not start | `SchemaView('gff.py')` fails (`ParserError`: gff.py is generated Python, not a schema). With `src/schema/gff.yaml` it fails with `AttributeError: 'SchemaView' object has no attribute 'all_class_names'`; `has_class`, `has_slot` and `ClassDefinition.typeof` do not exist either, and the schema has no `Seqid`, `Source` or `Type` classes. | Plain Python checks; no LinkML runtime dependency (about 90 MB installed). |
| Wrong line numbers | `line_number` counts only non-comment lines. | Physical line numbers from the reader. |
| Forward references rejected | Parent and Derives_from must already be in `seen_ids`, but GFF3 allows forward references until `###`. | GFF-STR-004/-005 resolve at `###` or end of file. |
| Valid multi-line features rejected | Any repeated ID is "Duplicate ID", but CDS and match lines share IDs by design. | GFF-STR-001: only lines of different type are an error. |
| Crash on common input | `id_value` is undefined when a line has Parent but no ID (exons usually have none): `NameError`. | Not applicable. |
| Wrong rules | `?` strand rejected; seqid character set applied to ID and Alias values; Target id looked up among feature IDs (it names an external sequence); Gap parsed as `int("M8")`; phase never required on CDS; a file "misses feature types" unless it uses every type in the schema. | GFF-SYN-017, -010, GFF-ATT-010, -011, GFF-SYN-019; the last check dropped. |
| No percent-decoding, no `##gff-version`, no `##FASTA` | FASTA lines would be validated as features. | Reader state machine; GFF-SYN-001, GFF-DIR-004. |
| Web app sends the file to a server | Flask upload saved to `uploads/` and never deleted; `debug=True`; hard-coded `secret_key`; Bootstrap from a CDN. The template has a syntax error (`{% endw ith %}`), is not in Flask's `templates/` directory, and `from .gff3_validator import` cannot import a file named `gff3-validator.py`. | Static page with Pyodide (#61, #69): the file stays local, no server, assets pinned. |
| No tests, no licence | FHGFF3 and its upstream biodatamodels/gff-schema have no licence file. | New code under MIT; nothing copied. Ask biodatamodels before reusing any of its files. |

## LinkML GFF3 model (biodatamodels/gff-schema, forked as FHGFF3)

[`src/schema/gff.yaml`](https://github.com/FAIR-bioHeaders/FHGFF3/blob/9c8cf644/src/schema/gff.yaml),
by Chris Mungall, last changed 2021 ("Playing around with GFF spec").

- **Useful:** separates the data model from the TSV serialization; enums for
  strand (including `?`) and phase; directives modelled as document metadata
  (sequence-region, genome-build, species, ontology URIs); mappings of
  start, end and strand to FALDO and Biolink. That is a good starting point for
  a JSON-LD or RDF export of validated files and for documenting terms.
- **Not a validator:** it has no notion of escaping, multi-line features,
  forward references, `###`, `##FASTA` or column 9 syntax. Several slots
  differ from the specification: `type` must match `^SO:\d+` (names are
  allowed), `gff version` must be `3.N.N` (rejects `3`), the end comment says
  `end > start` (it is `>=`), and the slot names `Aliases`, `Derives from`,
  `Is circular` and `Ontology term` do not match the tags.
- **Recommendation:** do not build the engine on it. Revisit as an export
  model after the core is stable, with the licence clarified upstream. The
  FHGFF3 header schema is separate (spec 007 FR-005).

## Existing tools

| Tool | What it checks | Gaps for spec 009 | Maintenance | Licence | Reuse or learn |
|---|---|---|---|---|---|
| GenomeTools `gt gff3validator` 1.6.6 (C) | Columns, coordinates, score, strand, phase, CDS phase, version pragma, sequence-region bounds, ID/Parent resolution, cycles, multi-feature type consistency, Is_circular value; SO types and part_of with `-typecheck so` | Stops at first error; no rule ids, levels or fixes; bundled so.obo is from 2016 (so-xp 2015-11-24); accepts empty columns, CRLF, bad Gap, `50%` unescaped, Dbxref without DBTAG | Active (v1.6.6, October 2025) | ISC | Best cross-check for structure; adopt its multi-feature rule (GFF-STR-001) and its hint to merge files with `gt gff3 -sort` |
| AGAT 1.7.0 (Perl) | Reads GFF/GTF into a gene model, reports and repairs: missing parents, duplicates, locations, phases (separate scripts) | Repairs silently and exits 0; drops features; assumes level1/2/3 gene models; bundled SO 2021-11-22 | Active (v1.7.0, April 2026) | GPL-3.0 | Not a validator. Its repair heuristics can inform fix texts, but code cannot be copied into MIT code |
| NAL i5k GFF3toolkit 2.1.0, `gff3_QC` (Python) | About 50 coded errors (Esf, Ema, Emr): syntax, escaping, attributes, sequence-region, embedded and external FASTA (Ns, lengths), model consistency, phase, internal stops | Canonical gene model assumptions; needs IDs on genes; one CDS per mRNA; crashed on `1.0`; exits 0 on errors; messages sometimes wrong | PyPI release December 2021; repository commits in October 2026 | US Government work (public domain) | Its error list is a cross-check for the catalogue; its FASTA-based checks map to GFF-STR-010/-011 and BIO-001/-002 |
| SO-era Perl validator (tharris/gff3_validator, CSHL) | Documented step by step: directives, column syntax, attribute syntax, reserved tags, unique IDs with multi-feature handling, types and part_of against an ontology (fetched from `##feature-ontology`) | Needs MySQL or SQLite and a CGI server; fetches ontologies over the network; Derives_from typing disabled; README says "under development" | Last change 2011 | Same terms as Perl (Artistic); CSHL disclaimer | Basis for many catalogue rules; credit it in docs/rules.md references |
| modENCODE-DCC/validator (Perl) | Linked from the GFF3 specification as "the" validator; modENCODE submission pipeline (Chado) | Project-specific; unmaintained | Last change 2012 | None stated | Spec link should move to the new validator (SC-004) |
| NCBI table2asn (C++, docs only) | Builds GenBank submission files (.sqn) from FASTA plus a feature table or GFF3; with validation and discrepancy reports it checks submission rules (locus tags, products, translations) | Applies NCBI submission policy, not GFF3 conformance; output is ASN.1 validation reports | Actively released by NCBI | US Government work (public domain) | Source for a future NCBI profile (#70), with its documentation pinned; not run here |

## Side-by-side run on the fixtures

Fixtures from [`tests/fixtures/`](../tests/fixtures/) with expected rule ids
from [`expected.yaml`](../tests/fixtures/expected.yaml). Commands are in
[`scripts/evaluation/compare_tools.sh`](../scripts/evaluation/compare_tools.sh):
gff3-validator 0.0.1.dev0; `gt gff3validator` from genometools-genometools 1.6.6 (bioconda; `-typecheck
so` was run only on the fixtures noted);
`agat_convert_sp_gxf2gxf.pl` from AGAT 1.7.0 (bioconda); `gff3_QC` from
gff3tool 2.1.0 (PyPI), given a small made-up FASTA for ctg1 and ctg123.

"yes" means the tool reported the problem (any wording); "planned" means our
rule exists in the catalogue but is not implemented yet.

| Fixture | Rule | gff3-validator | gt | AGAT | gff3_QC |
|---|---|---|---|---|---|
| valid/canonical_gene (specification example) | none | valid | valid | warns on TF_binding_site; **removes 3 CDS lines** of cds00004 as "duplicates" | **Ema0006 "wrong phase"** on 4 correct CDS lines |
| syn001_missing_version | GFF-SYN-001 | yes | yes | not reported | yes (Esf0014) |
| syn002_repeated_version | GFF-SYN-002 | yes | yes | not reported | reported as "missing from the first line" |
| syn003_spaces | GFF-SYN-003 | yes | yes | refuses file ("less than 8 columns") | yes (Esf0022) |
| syn004_empty_column | GFF-SYN-004 | yes | **no** (also not with `-typecheck so`) | rewritten as "." | reported as wrong field count |
| syn013_noninteger (`1.0`) | GFF-SYN-013 | yes | yes | passed through | **crash** (TypeError, exit 1) |
| syn014_zero_start | GFF-SYN-014 | yes | yes | **changed to 1** | yes (Esf0002) |
| syn015_start_after_end | GFF-SYN-015 | yes | yes | **gene removed** from output | yes (Esf0018) |
| syn016_bad_score | GFF-SYN-016 | yes | yes | passed through | yes (Esf0024) |
| syn017_bad_strand (`1`) | GFF-SYN-017 | yes | yes | **changed to "."** | yes (Esf0025) |
| syn018_bad_phase (`3`) | GFF-SYN-018 | yes | yes | passed through | yes (Esf0026) |
| syn019_cds_no_phase | GFF-SYN-019 | yes | yes | passed through | yes (Esf0027) |
| att001_gtf_attributes | GFF-ATT-001 | planned | yes | takes first value as ID | stops ("Missing ID"), exit 0 |
| att011_bad_gap (`8M3D6M`) | GFF-ATT-011 | planned | no | **feature dropped** | no |
| str001_duplicate_id (gene and mRNA share an ID) | GFF-STR-001 | planned | yes | **renames** mRNA ID and attaches it to the gene | no (Ema0004 info only) |
| str004_unresolved_parent | GFF-STR-004 | planned | yes | **creates** placeholder gene and RNA | log warning; Ema0004 info |
| str006_parent_cycle | GFF-STR-006 | planned | yes (with `-typecheck so`, a part_of type error is reported first) | passed through | reported as "Duplicate ID" |
| str008_outside_sequence_region | GFF-STR-008 | planned | yes | not reported in the log | reported against the FASTA length (Esf0011) |
| att008_lowercase_parent (`parent=t1`) | GFF-ATT-008 | planned | no | not recorded | no (Ema0004 info only) |
| so001_unknown_type | SO-001 | planned | no (yes with `-typecheck so`) | "unknown" type in log | no |

Exit codes: gff3-validator and gt exit 1 on errors; AGAT exited 0 on every
fixture, and gff3_QC exited 0 except for the crash.

### Findings from the run

1. Both AGAT and gff3_QC model one CDS per transcript and so mishandle the
   specification's own canonical gene, where mRNA00003 has two CDS
   (alternative starts). The conformance suite (#68) should include it, and
   the biology rules must not assume one CDS per transcript (BIO-004 notes).
   By hand: cds00003's first segment, 3301..3902, is 602 bp, so the next
   segment's phase is (3 - 602 mod 3) mod 3 = 1, as the specification says.
2. Repair tools change data silently. Spec 009's "report, never rewrite" is a
   real difference, not a nicety: a pipeline that runs AGAT as a "check"
   publishes altered annotations.
3. gt shows that one streaming pass can check structure with bounded state,
   but stopping at the first error is the main usability gap that spec 009
   names (FR-001, FR-008).
4. No tool tested checks Gap syntax or empty columns, and none cites a rule or
   suggests a fix.

## Conformance suite: GenomeTools (2026-10-09)

The [conformance suite](../conformance/README.md) (#68) scored
`gt gff3validator` from GenomeTools 1.6.6 (bioconda
`genometools-genometools`, default options, no `-typecheck`) on the 67 cases
whose verdict the GFF3 1.26 text settles (status `spec`), comparing only the
exit status:

```bash
python scripts/check_conformance.py --command 'gt gff3validator {file}' --status spec
```

**Result: 48 of 60 scored cases passed; 7 skipped** (they need a genome,
which `gt gff3validator` does not take). gt accepted every valid file
(including the gzip and BGZF copies, comments and blank lines, a circular
feature beyond its `##sequence-region`, Gap alignments and percent-encoding)
and rejected 23 of the 35 scored invalid files. The 12 failures are invalid
files that gt accepts (exit 0):

| Case | Defect gt accepts |
|---|---|
| syn-004-empty-column | empty source column |
| syn-005-control-character | unescaped U+0007 in column 9 |
| syn-008-bare-percent | `50%` not written `50%25` |
| syn-010-seqid-whitespace | seqid `chr 1` |
| syn-012-undefined-type | type `.` |
| syn-019-cds-without-phase | CDS with phase `.` |
| att-006-id-with-comma | `ID=g1,g2` |
| att-011-sam-style-gap | `Gap=8M3D6M` |
| att-014-dbxref-without-dbtag | `Dbxref=AA816246` |
| dir-004-feature-after-fasta | feature line after `##FASTA` |
| str-005-unresolved-derives-from | Derives_from names no ID |
| str-011-beyond-fasta-sequence | feature beyond the embedded sequence |

On the 14 scorable `proposed` cases gt agreed with the suite 11 times. It
differed on the three open points where gt is stricter than the catalogue's
current reading: an unknown upper-case tag (`Gene_biotype`, GFF-ATT-007),
`Is_circular=yes` (GFF-ATT-016) and the lines of one CDS naming different
Parents (GFF-STR-003, question 8); gt treats all three as errors, the suite
as warnings. These are evidence for the SO questions, not gt bugs.

This is a comparison, not a judgement of gt: it stops at the first error,
reports no rule ids, and several of the cases above are syntax checks it
does not attempt. gff3-validator 0.1.0 passes all 92 cases with full
findings comparison (CI runs this on every push).

<details>
<summary>Full table (spec cases)</summary>

| case | status | expected | got | result | detail |
|---|---|---|---|---|---|
| canonical-gene | spec | valid | valid | pass |  |
| canonical-gene-gzip | spec | valid | valid | pass |  |
| canonical-gene-bgzf | spec | valid | valid | pass |  |
| minimal | spec | valid | valid | pass |  |
| comments-and-blank-lines | spec | valid | valid | pass |  |
| multiple-parents | spec | valid | valid | pass |  |
| discontinuous-features | spec | valid | valid | pass |  |
| forward-references | spec | valid | valid | pass |  |
| polycistronic-derives-from | spec | valid | valid | pass |  |
| circular-genome | spec | valid | valid | pass |  |
| embedded-fasta | spec | valid | valid | pass |  |
| alignments-gap | spec | valid | valid | pass |  |
| percent-encoding | spec | valid | valid | pass |  |
| attribute-values | spec | valid | valid | pass |  |
| directives | spec | valid | valid | pass |  |
| genes-with-genome | spec | valid |  | skip | needs a genome ({genome} not in the command) |
| genes-with-gzip-genome | spec | valid |  | skip | needs a genome ({genome} not in the command) |
| syn-001-comment-before-version | spec | invalid | invalid | pass |  |
| syn-001-version-2 | spec | invalid | invalid | pass |  |
| syn-002-repeated-version | spec | invalid | invalid | pass |  |
| syn-003-spaces-not-tabs | spec | invalid | invalid | pass |  |
| syn-003-eight-columns | spec | invalid | invalid | pass |  |
| syn-004-empty-column | spec | invalid | valid | fail | accepted (exit 0) |
| syn-005-control-character | spec | invalid | valid | fail | accepted (exit 0) |
| syn-006-not-utf8 | spec | valid | valid | pass |  |
| syn-007-end-of-line-comment | spec | valid | valid | pass |  |
| syn-008-bare-percent | spec | invalid | valid | fail | accepted (exit 0) |
| syn-010-seqid-whitespace | spec | invalid | valid | fail | accepted (exit 0) |
| syn-012-undefined-type | spec | invalid | valid | fail | accepted (exit 0) |
| syn-013-non-integer-coordinates | spec | invalid | invalid | pass |  |
| syn-014-zero-start | spec | invalid | invalid | pass |  |
| syn-015-start-after-end | spec | invalid | invalid | pass |  |
| syn-016-score-not-a-number | spec | invalid | invalid | pass |  |
| syn-017-bad-strand | spec | invalid | invalid | pass |  |
| syn-018-bad-phase | spec | invalid | invalid | pass |  |
| syn-019-cds-without-phase | spec | invalid | valid | fail | accepted (exit 0) |
| att-001-gtf-style | spec | invalid | invalid | pass |  |
| att-002-empty-tag | spec | invalid | invalid | pass |  |
| att-004-repeated-tag | spec | invalid | invalid | pass |  |
| att-005-unescaped-reserved | spec | invalid | invalid | pass |  |
| att-006-id-with-comma | spec | invalid | valid | fail | accepted (exit 0) |
| att-008-case-variant-tag | spec | valid | valid | pass |  |
| att-009-quoted-value | spec | valid | valid | pass |  |
| att-010-target-missing-end | spec | invalid | invalid | pass |  |
| att-011-sam-style-gap | spec | invalid | valid | fail | accepted (exit 0) |
| att-014-dbxref-without-dbtag | spec | invalid | valid | fail | accepted (exit 0) |
| dir-001-sequence-region-two-fields | spec | invalid | invalid | pass |  |
| dir-002-repeated-sequence-region | spec | invalid | invalid | pass |  |
| dir-003-reference-across-resolution | spec | invalid | invalid | pass |  |
| dir-004-feature-after-fasta | spec | invalid | valid | fail | accepted (exit 0) |
| dir-005-implied-fasta | spec | valid | valid | pass |  |
| dir-007-species-name | spec | valid | valid | pass |  |
| dir-009-feature-ontology | spec | valid | valid | pass |  |
| dir-010-unknown-directive | spec | valid | valid | pass |  |
| str-001-duplicate-id | spec | invalid | invalid | pass |  |
| str-004-unresolved-parent | spec | invalid | invalid | pass |  |
| str-005-unresolved-derives-from | spec | invalid | valid | fail | accepted (exit 0) |
| str-006-parent-cycle | spec | invalid | invalid | pass |  |
| str-008-outside-sequence-region | spec | invalid | invalid | pass |  |
| str-009-seqid-without-sequence-region | spec | valid | valid | pass |  |
| str-010-seqid-not-in-fasta | spec | valid | valid | pass |  |
| str-011-beyond-fasta-sequence | spec | invalid | valid | fail | accepted (exit 0) |
| bio-001-seqid-not-in-genome | spec | invalid |  | skip | needs a genome ({genome} not in the command) |
| bio-002-beyond-genome | spec | invalid |  | skip | needs a genome ({genome} not in the command) |
| bio-003-sequence-region-longer | spec | valid |  | skip | needs a genome ({genome} not in the command) |
| bio-009-length-not-multiple-of-three | spec | valid |  | skip | needs a genome ({genome} not in the command) |
| bio-011-cds-without-strand | spec | valid |  | skip | needs a genome ({genome} not in the command) |

</details>

## Recommendation

Build the engine new, in Python (#61), from the catalogue. Reuse no
executable code from the prototype or the LinkML model; keep the prototype's
design and check list (done, in the catalogue) and its page layout (for #69).
Use gt and gff3_QC as comparison tools in the conformance work (#68), never as
oracles. Ask biodatamodels about a licence before reusing the LinkML schema
for export, and pin NCBI documentation before drafting the NCBI profile.
