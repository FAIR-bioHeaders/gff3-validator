# Review packet — the rule catalogue with the Sequence Ontology group

Prepared for [#18](https://github.com/FAIR-bioHeaders/gff3-validator/issues/18)
(Refs #18). Draft packet, 2026-11-11; nothing in it is an SO decision or an
endorsement, and no new external contact is made or claimed by this document.
The live surface for the exchange is
[SO-Ontologies #685](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/685)
(open; the validator and this catalogue were introduced there by a maintainer
on 2026-10-09). Review happens when the maintainers route it; this packet only
makes it cheap.

## What we are asking for

A disposition per rule — confirm / correct / defer — written in the **Verdict**
column of the full table at the bottom (or in reply, by rule id). The items
that cost a reviewer most — and where a verdict changes engine behaviour —
are pre-extracted under **Start here**. Where the specification is ambiguous
we have already recorded
our proposed answer to the numbered questions in
[questions-for-SO.md](../questions-for-SO.md); the **Q** column links each rule
to its question, so most verdicts can be "agree" or "no — because".

## What is pinned

Everything below cites these exact artefacts; all were verified reachable on
2026-11-11.

| Artefact | Pin | Verified |
| --- | --- | --- |
| Rule catalogue | `rules/catalogue.yaml`, `catalogue_version: 0.1.0-draft`, 91 rules | this checkout |
| GFF3 1.26 (18 Aug 2020) | commit `fe73505276dd324bf6a55773f3413fe2bed47af4`, `gff3.md` | raw URL HTTP 200 |
| Sequence Ontology | so.obo data-version 2026-08-07, commit `4340c143bac3578bba0c013d02e8c5f0e51ad14a`, SHA-256 `22a8f3ec…55204`, 2620 terms (211 obsolete) | raw URL HTTP 200 |
| Validator requirements | FAIR-bioHeaders-Specification spec 009 (`main`) | referenced by catalogue sources |
| FHGFF3 header contract | spec 007 + FORMAT.md R1–R10 (`main`) | referenced by HDR rules |

Rule ids are stable only after the first release; while the catalogue is a
draft, retired ids are simply gone — GFF-STR-014 was removed on 2026-11-11
(see below), which is why the STR series jumps 013 → 015.

## Shape of the catalogue (as merged, 2026-11-11)

91 rules: 20 SYN, 17 ATT, 10 DIR, 14 STR, 9 SO, 11 BIO, 10 HDR.
84 implemented, 7 planned (the engine does not emit a planned rule; reports
list it as not checked). 44 error, 32 warning, 15 info. Every rule carries
`review: pending-SO`; 47 rules carry `needs_so: true` — they cannot be settled
without SO input. No rule is reviewed or endorsed yet.

**Changed shape note (PR #28, merged 2026-11-11).** The circulated draft of
that review classified the INSDC Annotation Minimum Specification v1.0 rules
with four new *planned catalogue entries* (94 rules). The merged version keeps
only **GFF-STR-015** in the catalogue — re-referenced from INSDC b.iv.1 to the
GFF3 ID column and design objective 6 — and moves the other three out as
**draft profile entries INSDC-014/015/016** in
[insdc-rule-placement.md](../insdc-rule-placement.md), which is repository
policy under #20, not GFF3 validity. Reviews of the catalogue therefore have
91 rows, not 94; nothing else about the rule set changed.

## Start here — the genuinely contentious items

1. **The seven planned rules.** Each is blocked on a review answer, listed
   with the question that gates it:
   - [GFF-SYN-011](../rules.md#gff-syn-011) *seqid is defined* (error, core) —
     a seqid naming no sequence is only detectable with `##sequence-region`
     or FASTA context; how strong should the rule be? (Q10/Q11 context)
   - [GFF-ATT-015](../rules.md#gff-att-015) *DBTAG is a registered
     abbreviation* (info, core) — the GO.xrf_abbs registry the specification
     cites is an FTP resource the validator must not fetch; needs SO to name a
     citable, versioned registry.
   - [GFF-ATT-017](../rules.md#gff-att-017) *Is_circular on the landmark*
     (info, core) — the specification states it on the landmark feature;
     unclear whether misuse is an error.
   - [GFF-STR-012](../rules.md#gff-str-012) *child extends beyond parent*
     (info, planned) and [GFF-STR-013](../rules.md#gff-str-013) *parent and
     child on one seqid* (warning, planned) — **Q11**: only SO can name the
     types where containment is expected.
   - [GFF-STR-015](../rules.md#gff-str-015) *segments of one feature do not
     overlap* (warning, planned) — the single INSDC-derived candidate that
     survived placement review, argued from GFF3's own design objective 6;
     provisional against the INSDC update gate (below).
   - [SO-007](../rules.md#so-007) *Derives_from typing* (info, planned) —
     **Q16**: not checked at all by design; SO must say whether to check it,
     or the rule is retired.
2. **The whole SO layer (SO-001…SO-009)** — severities, synonym handling,
   the allowed Parent relation set. Detailed with its question map in
   [term-parent-rules.md](term-parent-rules.md) (packet for #19); review the
   catalogue table there first if time is short.
3. **Rules implemented at a level the specification does not settle** — the
   "our proposal" in each answer may need correcting, not confirming:
   SYN-005 (CRLF), ATT-002/003/006 (empty values, repeated tags, comma
   semantics), STR-001–003 (what discontinuous lines must share), DIR-001
   and DIR-003 (`##sequence-region` position, `###` boundaries), SO-001
   (unknown type is a *warning*, deliberately, pending Q13/Q14).
4. **Items with live upstream discussion.** BIO-004–BIO-008 hang on the
   recoding/partiality conventions of **Q17** (SO-Ontologies #658 is closed;
   the INSDC `partial=start|end` vocabulary came from
   [#685](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/685#issuecomment-6080389993));
   BIO-010's trans-splicing exemption (**Q18**) is not implemented; the
   INSDC v1.0 pin behind GFF-STR-015's notes is under a stated **update
   gate** — re-check before INSDC publishes its revision, and INSDC outreach
   is deferred until then.
5. **Cheap wins: the specification errata list.** Seven concrete text fixes
   (invalid `Target=` example, phase `.` examples, the canonical gene's
   off-by-one CDS lengths, quoted Dbxref examples, the non-SO
   `nucleotide_to_protein_match` type, the obsolete `SO:1000069`, the six-digit
   `SO:000000` pattern) at the end of
   [questions-for-SO.md](../questions-for-SO.md#suggested-corrections-to-the-specification-text)
   — each one currently makes users copy invalid GFF3.

## The full catalogue, in review order

Verdict column left empty for the SO group. *Layer*: core = GFF3 1.26
syntax/directives/structure, so = Sequence Ontology, biology = optional
`--genome` checks, fhgff3 = the optional FAIR-bioHeaders header. *Evidence*:
the pinned source and section the rule cites (SPEC); the rule's `notes`,
linked from the id, record the reading decisions (decision trail) and the
questions.

| Rule | Layer | Level | Status | Purpose | Evidence (source — section) | Q | Verdict (SO) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [GFF-SYN-001](../rules.md#gff-syn-001) | core | error | implemented | First line is the ##gff-version 3 directive | GFF3 1.26 — Other Syntax: ##gff-version | 1 |  |
| [GFF-SYN-002](../rules.md#gff-syn-002) | core | error | implemented | Only one ##gff-version directive | GFF3 1.26 — Change Log 1.21: the ##gff-version pragma only appears once | — |  |
| [GFF-SYN-003](../rules.md#gff-syn-003) | core | error | implemented | Feature lines have nine tab-separated columns | GFF3 1.26 — Description of the Format | — |  |
| [GFF-SYN-004](../rules.md#gff-syn-004) | core | error | implemented | Undefined columns are ".", not empty | GFF3 1.26 — Description of the Format: undefined fields are replaced with the '.' character | — |  |
| [GFF-SYN-005](../rules.md#gff-syn-005) | core | error | implemented | No unescaped control characters | GFF3 1.26 — Description of the Format: escaping | 2 |  |
| [GFF-SYN-006](../rules.md#gff-syn-006) | core | warning | implemented | File is UTF-8 | GFF3 1.26 — Description of the Format: use of UTF-8 is recommended | — |  |
| [GFF-SYN-007](../rules.md#gff-syn-007) | core | info | implemented | Possible end-of-line comment | GFF3 1.26 — Other Syntax: end-of-line comments are not allowed | — |  |
| [GFF-SYN-008](../rules.md#gff-syn-008) | core | error | implemented | Percent-encoding is well formed | GFF3 1.26 — Description of the Format: RFC 3986 percent-encoding | — |  |
| [GFF-SYN-009](../rules.md#gff-syn-009) | core | warning | implemented | Characters encoded that need not be | GFF3 1.26 — Description of the Format: escaping | 3 |  |
| [GFF-SYN-010](../rules.md#gff-syn-010) | core | error | implemented | seqid uses the allowed characters | GFF3 1.26 — Column 1: seqid | 3 |  |
| [GFF-SYN-011](../rules.md#gff-syn-011) | core | error | planned | seqid is defined | GFF3 1.26 — Column 1: seqid | — |  |
| [GFF-SYN-012](../rules.md#gff-syn-012) | core | error | implemented | type is defined | GFF3 1.26 — Column 3: type | — |  |
| [GFF-SYN-013](../rules.md#gff-syn-013) | core | error | implemented | start and end are integers | GFF3 1.26 — Columns 4 & 5: start and end | — |  |
| [GFF-SYN-014](../rules.md#gff-syn-014) | core | error | implemented | start is at least 1 | GFF3 1.26 — Columns 4 & 5: start and end | — |  |
| [GFF-SYN-015](../rules.md#gff-syn-015) | core | error | implemented | start is not greater than end | GFF3 1.26 — Columns 4 & 5: start and end | — |  |
| [GFF-SYN-016](../rules.md#gff-syn-016) | core | error | implemented | score is a number or "." | GFF3 1.26 — Column 6: score | 7 |  |
| [GFF-SYN-017](../rules.md#gff-syn-017) | core | error | implemented | strand is +, -, . or ? | GFF3 1.26 — Column 7: strand | — |  |
| [GFF-SYN-018](../rules.md#gff-syn-018) | core | error | implemented | phase is 0, 1, 2 or "." | GFF3 1.26 — Column 8: phase | — |  |
| [GFF-SYN-019](../rules.md#gff-syn-019) | core | error | implemented | CDS features have a phase | GFF3 1.26 — Column 8: phase; Canonical Gene NOTE 4 | 6 |  |
| [GFF-SYN-020](../rules.md#gff-syn-020) | core | warning | implemented | phase is "." on features other than CDS | GFF3 1.26 — Column 8: phase | 6 |  |
| [GFF-ATT-001](../rules.md#gff-att-001) | core | error | implemented | Attributes are tag=value pairs separated by semicolons | GFF3 1.26 — Column 9: attributes | — |  |
| [GFF-ATT-002](../rules.md#gff-att-002) | core | error | implemented | Tags and values are not empty | GFF3 1.26 — Column 9: attributes | 4 |  |
| [GFF-ATT-003](../rules.md#gff-att-003) | core | info | implemented | Empty attribute pair or trailing semicolon | GFF3 1.26 — Circular Genomes (example ends with ';') | 4 |  |
| [GFF-ATT-004](../rules.md#gff-att-004) | core | error | implemented | Each tag appears once per line | GFF3 1.26 — Column 9: multiple attributes of the same type | — |  |
| [GFF-ATT-005](../rules.md#gff-att-005) | core | error | implemented | Reserved characters are escaped in tags and values | GFF3 1.26 — Description of the Format: reserved characters in column 9 | — |  |
| [GFF-ATT-006](../rules.md#gff-att-006) | core | error | implemented | Single-valued reserved tags have one value | GFF3 1.26 — Column 9: multiple values; Change Log 1.19 | 5 |  |
| [GFF-ATT-007](../rules.md#gff-att-007) | core | warning | implemented | Unknown reserved (upper-case) tag | GFF3 1.26 — Column 9: all attributes that begin with an uppercase letter are reserved | — |  |
| [GFF-ATT-008](../rules.md#gff-att-008) | core | warning | implemented | Tag differs from a reserved tag only by case | GFF3 1.26 — Column 9: attribute names are case sensitive | — |  |
| [GFF-ATT-009](../rules.md#gff-att-009) | core | info | implemented | Quoted attribute value | GFF3 1.26 — Column 9: attribute values do not need to be and should not be quoted | — |  |
| [GFF-ATT-010](../rules.md#gff-att-010) | core | error | implemented | Target has the form "target_id start end [strand]" | GFF3 1.26 — Column 9: Target; Alignments | — |  |
| [GFF-ATT-011](../rules.md#gff-att-011) | core | error | implemented | Gap is a list of operations | GFF3 1.26 — The Gap Attribute | — |  |
| [GFF-ATT-012](../rules.md#gff-att-012) | core | warning | implemented | Gap is given with Target | GFF3 1.26 — The Gap Attribute | — |  |
| [GFF-ATT-013](../rules.md#gff-att-013) | core | warning | implemented | Gap lengths agree with the feature and Target lengths | GFF3 1.26 — The Gap Attribute | — |  |
| [GFF-ATT-014](../rules.md#gff-att-014) | core | error | implemented | Dbxref and Ontology_term values are DBTAG:ID | GFF3 1.26 — Ontology Associations and DB Cross References | — |  |
| [GFF-ATT-015](../rules.md#gff-att-015) | core | info | planned | DBTAG is a registered database abbreviation | GFF3 1.26 — Ontology Associations and DB Cross References | — |  |
| [GFF-ATT-016](../rules.md#gff-att-016) | core | warning | implemented | Is_circular is "true" | GFF3 1.26 — Circular Genomes | — |  |
| [GFF-ATT-017](../rules.md#gff-att-017) | core | info | planned | Is_circular is on the landmark feature | GFF3 1.26 — Circular Genomes | — |  |
| [GFF-DIR-001](../rules.md#gff-dir-001) | core | error | implemented | ##sequence-region has the form: seqid start end | GFF3 1.26 — Other Syntax: ##sequence-region | 10 |  |
| [GFF-DIR-002](../rules.md#gff-dir-002) | core | error | implemented | One ##sequence-region per seqid | GFF3 1.26 — Other Syntax: ##sequence-region | — |  |
| [GFF-DIR-003](../rules.md#gff-dir-003) | core | error | implemented | ### closes all forward references | GFF3 1.26 — Other Syntax: ### | 9 |  |
| [GFF-DIR-004](../rules.md#gff-dir-004) | core | error | implemented | Only FASTA after ##FASTA | GFF3 1.26 — Other Syntax: ##FASTA | — |  |
| [GFF-DIR-005](../rules.md#gff-dir-005) | core | warning | implemented | FASTA section starts with ##FASTA | GFF3 1.26 — Other Syntax: ##FASTA (implied by a line beginning with >) | — |  |
| [GFF-DIR-006](../rules.md#gff-dir-006) | core | warning | implemented | FASTA records are well formed | GFF3 1.26 — Other Syntax: ##FASTA | — |  |
| [GFF-DIR-007](../rules.md#gff-dir-007) | core | warning | implemented | ##species is an NCBI Taxonomy URL | GFF3 1.26 — Other Syntax: ##species | — |  |
| [GFF-DIR-008](../rules.md#gff-dir-008) | core | warning | implemented | ##genome-build has a source and a build name | GFF3 1.26 — Other Syntax: ##genome-build | — |  |
| [GFF-DIR-009](../rules.md#gff-dir-009) | core | info | implemented | Ontology directives are recorded but not fetched | GFF3 1.26 — Other Syntax: ##feature-ontology, ##attribute-ontology, ##source-ontology | 13 |  |
| [GFF-DIR-010](../rules.md#gff-dir-010) | core | info | implemented | Unknown directive | GFF3 1.26 — Other Syntax: directives | — |  |
| [GFF-STR-001](../rules.md#gff-str-001) | core | error | implemented | IDs are unique, except for the lines of one discontinuous feature | GFF3 1.26 — Column 9: ID; Change Log 1.20 | 8 |  |
| [GFF-STR-002](../rules.md#gff-str-002) | core | warning | implemented | Lines of one feature share seqid and strand | GFF3 1.26 — Pathological Cases: trans-spliced transcript | 8 |  |
| [GFF-STR-003](../rules.md#gff-str-003) | core | warning | implemented | Lines of one feature have the same Parent | GFF3 1.26 — The Canonical Gene | 8 |  |
| [GFF-STR-004](../rules.md#gff-str-004) | core | error | implemented | Parent refers to an ID in the file | GFF3 1.26 — Parent (part_of) Relationships | — |  |
| [GFF-STR-005](../rules.md#gff-str-005) | core | error | implemented | Derives_from refers to an ID in the file | GFF3 1.26 — Pathological Cases: polycistronic transcripts, intein | — |  |
| [GFF-STR-006](../rules.md#gff-str-006) | core | error | implemented | No Parent cycles | GFF3 1.26 — Parent (part_of) Relationships | — |  |
| [GFF-STR-007](../rules.md#gff-str-007) | core | warning | implemented | No Derives_from cycles | GFF3 1.26 — Pathological Cases | 12 |  |
| [GFF-STR-008](../rules.md#gff-str-008) | core | error | implemented | Features are within their ##sequence-region | GFF3 1.26 — Other Syntax: ##sequence-region | 10 |  |
| [GFF-STR-009](../rules.md#gff-str-009) | core | info | implemented | seqid without ##sequence-region | GFF3 1.26 — Other Syntax: ##sequence-region | — |  |
| [GFF-STR-010](../rules.md#gff-str-010) | core | warning | implemented | seqids appear in the ##FASTA section | GFF3 1.26 — Other Syntax: ##FASTA | — |  |
| [GFF-STR-011](../rules.md#gff-str-011) | core | error | implemented | Features fit within the embedded sequence | GFF3 1.26 — Other Syntax: ##FASTA | — |  |
| [GFF-STR-012](../rules.md#gff-str-012) | core | info | planned | Child extends beyond its parent | GFF3 1.26 — Parent (part_of) Relationships | 11 |  |
| [GFF-STR-013](../rules.md#gff-str-013) | core | warning | planned | Parent and child are on the same seqid | GFF3 1.26 — Parent (part_of) Relationships | 11 |  |
| [GFF-STR-015](../rules.md#gff-str-015) | core | warning | planned | Segments of one feature do not overlap | GFF3 1.26 — Column 9: ID; Summary design objective 6 (disjunct regions) | — |  |
| [SO-001](../rules.md#so-001) | so | warning | implemented | type is an SO term name or accession | GFF3 1.26 — Column 3: type | 13, 14, 20 |  |
| [SO-002](../rules.md#so-002) | so | error | implemented | SO accession is well formed | GFF3 1.26 — Column 3: type (SO:000000 syntax) | — |  |
| [SO-003](../rules.md#so-003) | so | warning | implemented | type is sequence_feature or a subtype | GFF3 1.26 — Column 3: type; Change Log 1.23 | 14 |  |
| [SO-004](../rules.md#so-004) | so | warning | implemented | type is not obsolete | pinned SO — so.obo is_obsolete, replaced_by, consider | — |  |
| [SO-005](../rules.md#so-005) | so | warning | implemented | type is a synonym or case variant of an SO label | pinned SO — so.obo name and synonym | 14 |  |
| [SO-006](../rules.md#so-006) | so | warning | implemented | Parent relationship is an SO part_of relationship | GFF3 1.26 — Parent (part_of) Relationships; Canonical Gene NOTE 2 | 15, 20 |  |
| [SO-007](../rules.md#so-007) | so | info | planned | Derives_from relationship is an SO derives_from relationship | GFF3 1.26 — Pathological Cases: intein | 16 |  |
| [SO-008](../rules.md#so-008) | so | warning | implemented | SO terms in Ontology_term are valid | GFF3 1.26 — Pathological Cases: programmed frameshift | — |  |
| [SO-009](../rules.md#so-009) | so | info | implemented | type is outside SOFA | pinned SO — so.obo subset SOFA | — |  |
| [BIO-001](../rules.md#bio-001) | biology | error | implemented | seqid is in the genome | spec 009 — FR-003, FR-005 | — |  |
| [BIO-002](../rules.md#bio-002) | biology | error | implemented | Features fit within the genome sequence | GFF3 1.26 — Columns 4 & 5: start and end | — |  |
| [BIO-003](../rules.md#bio-003) | biology | warning | implemented | ##sequence-region agrees with the genome | GFF3 1.26 — Other Syntax: ##sequence-region | — |  |
| [BIO-004](../rules.md#bio-004) | biology | warning | implemented | CDS phases are consistent | GFF3 1.26 — Column 8: phase | 17 |  |
| [BIO-005](../rules.md#bio-005) | biology | warning | implemented | CDS segments lie within exons | GFF3 1.26 — The Canonical Gene | 17 |  |
| [BIO-006](../rules.md#bio-006) | biology | warning | implemented | CDS starts with a start codon | GFF3 1.26 — The Canonical Gene NOTE 5; Change Log 1.13 | 17, 19 |  |
| [BIO-007](../rules.md#bio-007) | biology | warning | implemented | CDS ends with a stop codon | GFF3 1.26 — The Canonical Gene NOTE 5 | 17 |  |
| [BIO-008](../rules.md#bio-008) | biology | warning | implemented | No internal stop codons | GFF3 1.26 — The Canonical Gene | 17 |  |
| [BIO-009](../rules.md#bio-009) | biology | info | implemented | CDS length is a multiple of three | GFF3 1.26 — Column 8: phase | — |  |
| [BIO-010](../rules.md#bio-010) | biology | warning | implemented | Strand is consistent within a gene | GFF3 1.26 — The Canonical Gene | 18 |  |
| [BIO-011](../rules.md#bio-011) | biology | info | implemented | Biology checks skipped | spec 009 — FR-005 | — |  |
| [HDR-001](../rules.md#hdr-001) | fhgff3 | error | implemented | FHGFF3 header present when required | spec 007 — FR-001 | — |  |
| [HDR-002](../rules.md#hdr-002) | fhgff3 | info | implemented | FHGFF3 header present but not validated | spec 009 — FR-006 | — |  |
| [HDR-003](../rules.md#hdr-003) | fhgff3 | info | implemented | Header checks skipped (--no-header) | spec 009 — FR-006 | — |  |
| [HDR-004](../rules.md#hdr-004) | fhgff3 | error | implemented | Header forms the leading block after ##gff-version | spec 007 — FR-001; FORMAT.md R10 | — |  |
| [HDR-005](../rules.md#hdr-005) | fhgff3 | error | implemented | Header checksum verifies | FORMAT — R1 to R5 | — |  |
| [HDR-006](../rules.md#hdr-006) | fhgff3 | error | implemented | Header lines are safe YAML | FORMAT — R6 to R8 | — |  |
| [HDR-007](../rules.md#hdr-007) | fhgff3 | error | implemented | Header metadata matches the FHGFF3 schema | spec 007 — FR-005, FR-010 | — |  |
| [HDR-008](../rules.md#hdr-008) | fhgff3 | error | implemented | The header identifies the annotated genome | spec 007 — FR-006, FR-007 | — |  |
| [HDR-009](../rules.md#hdr-009) | fhgff3 | error | implemented | The genome link matches the supplied genome | spec 007 — FR-015; spec 009 FR-006 | — |  |
| [HDR-010](../rules.md#hdr-010) | fhgff3 | warning | implemented | The header agrees with the native directives | spec 007 — FR-011 | — |  |

## What happens with a verdict

Replies are recorded against the rule ids in `rules/catalogue.yaml`
(`review:` field and `notes:`), the questions document is updated with the
SO answer as received, and severities move only through the normal
catalogue-render workflow (`scripts/render_rules.py`, conformance vectors
regenerated). A rule is never marked reviewed, adopted or endorsed by this
packet; an answer that leaves a question open keeps the rule at its current
level and status.

Companion packets: [term-parent-rules.md](term-parent-rules.md) (#19) and
[repository-profiles.md](repository-profiles.md) (#20).
