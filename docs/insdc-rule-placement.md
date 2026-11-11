# INSDC Annotation v1.0: rule placement review

Evidence for
[#27](https://github.com/FAIR-bioHeaders/gff3-validator/issues/27)
(INSDC Annotation v1.0 rules missing from the catalogue). Nothing here is
adopted: the placements below are proposals for maintainer review, and no rule
logic, fixture or conformance case is implemented. The issue stops at "review of
rule placement and unresolved SO semantics", so this branch stops there too.

Companion documents: the rule catalogue
([rules/catalogue.yaml](../rules/catalogue.yaml), rendered as
[docs/rules.md](rules.md)), the profile mechanism
([docs/profiles.md](profiles.md)) and the SO questions
([docs/questions-for-SO.md](questions-for-SO.md)).

## Provisional scope and INSDC update gate

This is a draft review against Annotation v1.0 at `41f0dc4`, not a statement
about the forthcoming INSDC specification. Re-check the pin, rule numbers,
thresholds, table 2e exceptions and partial-marker vocabulary when INSDC
publishes its update. Defer INSDC outreach until that update. Questions 19/20
remain review questions, not SO decisions.

The catalogue retains only GFF-STR-015 as a planned, pending-SO core candidate,
with GFF3 as its authority. Segment order, paired internal boundaries and a
requirement to declare partiality do not follow from GFF3 1.26 or SO; they are
draft profile candidates INSDC-014/015/016 below, not catalogue rules.

## Source pin and how to check the citations

| | |
| --- | --- |
| Document | INSDC Annotation Minimum Specification v1.0 |
| Repository | [insdc/minimum-specifcations](https://github.com/insdc/minimum-specifcations) |
| Commit | `41f0dc424748c9f7e50a8b6bda9b888218c4b65e` |
| Path | `Annotations/Current version/Annotation Minimum Specification v1.0.docx.pdf` |
| [Link at the pin](https://github.com/insdc/minimum-specifcations/blob/41f0dc424748c9f7e50a8b6bda9b888218c4b65e/Annotations/Current%20version/Annotation%20Minimum%20Specification%20v1.0.docx.pdf) | verified HTTP 200 (blob and raw) |
| Git blob SHA-1 | `e88198524080bd0fcfaa7a4284430ead06c8d17a` (matches `git hash-object` of the downloaded file) |
| File SHA-256 | `bb7b89927c370b8745e7c8b8d4fa2b67e2e3ba679d42d341c127e66361efd20d` |
| Size, extent | 185312 bytes, 6 pages |

Citations give the rule number and the **PDF page**. This PDF is a Word export:
its text layer breaks almost every word onto its own line, so line numbers in an
extraction are an artefact of the tool and are not cited. Every sentence quoted
below is verbatim from the page given, extracted with `pypdf`
(`python3 -m venv /tmp/pdfenv && /tmp/pdfenv/bin/pip install pypdf`).

| Page | Contents |
| --- | --- |
| 1 | `a.i`; `b.i`–`b.ii`; `b.iii.1`–`b.iii.6`; `b.iv.1`–`b.iv.3` |
| 2 | `b.v.1`–`b.v.3`; `b.vi.1`–`b.vi.9`; `b.vii` with `b.vii.1`–`b.vii.2`; `b.viii.1`–`b.viii.4` |
| 3 | `b.ix.1`–`b.ix.4`; `c.i.1`, `c.ii`, `c.iii`; `d.i`–`d.v`; the table 2e heading and its `b.iii.2`, `b.iii.3` rows |
| 4 | table 2e rows `b.iv.1`, `b.iii.4`, `b.iii.6`, `b.v.1`, `b.v.3`, `b.vi.9`, `c.i.1`, `c.i.2`, `d.ii`, `d.iv`, `d.v`; then "Use cases" |
| 5–6 | availability, data formats, tools, standards |

`b.ii` (p. 1) is the clause that ties the asterisks to table 2e: "Exceptions to
feature validation rules exist for specific conditions, and are indicated with
\* below with further details described in table 2e". Of the rules #27 lists,
those carrying an asterisk, and so a written biological exception, are
`b.iii.4`, `b.iii.6`, `b.iv.1`, `b.v.1`, `b.v.3` and `c.i.1`. (Asterisks also
sit on `b.iii.2`, `b.iii.3`, `b.vi.1`, `b.vi.9`, `d.ii`, `d.iv` and `d.v`, which
#27 does not list.) `b.iii.5`, `b.v.2`, `b.vi.4`, `b.vi.7`, `b.vii.1`,
`b.vii.2` and `b.ix.1`–`b.ix.3` have no asterisk and no table 2e row, so those
rules are absolute as written; `c.ii` has neither. The two anomalies in the
document itself are reported under "Review items" (8).

## How the placement was decided

The catalogue header defines the layers — "`core` = GFF3 1.26 syntax, directives
and structure; `so` = Sequence Ontology terms and relationships; `biology` =
optional checks that need `--genome`; `fhgff3` = the optional FAIR-bioHeaders
header" — and says repository and community profiles "are separate files in
`profiles/`, layered on top … they never change this catalogue"
([rules/catalogue.yaml](../rules/catalogue.yaml)). [AGENTS.md](../AGENTS.md)
adds that GFF3 1.26 and the pinned SO release are the authorities, that
repository requirements must not be invented, and that profile findings never
change core validity. Three questions were put to each INSDC rule:

1. **Would a GFF3 1.26 reader disagree?** If the requirement follows from the
   GFF3 text — including from the semantics of a field GFF3 defines — it is a
   core rule; if it follows only from the pinned SO release, it is an SO rule.
2. **Does it need sequence knowledge?** A rule answerable only against the
   reference goes to the optional `--genome` biology layer, with the
   catalogue's own caveat that some gene-model rules need no sequence and simply
   run in that layer (BIO-005: "Does not need the genome (it could move to the
   structure layer) but runs with the biology layer").
3. **Is the number, the type pair or the vocabulary INSDC's own?** A threshold
   (30 aa, 50–150 bp, 10 bp), a Feature Table qualifier GFF3 1.26 does not define
   (`locus_tag`, `transcript_id`, `pseudo`, `product`, `translation`,
   `artificial_location`), or a scope condition the file cannot carry ("genome
   submission", "genome-scale annotation", "prokaryote") is submission policy:
   an INSDC or NCBI repository profile under
   [#20](https://github.com/FAIR-bioHeaders/gff3-validator/issues/20), or out of
   scope.

The GFF3 1.26 text at the pin the catalogue uses
([commit `fe73505`](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md))
was checked for each row. It never mentions `locus_tag`, `transcript_id`,
`artificial_location`, `pseudogene` or partial locations, and it states no
requirement about the order of the lines of one feature. On disjointness it goes
no further than a design objective — "Provides an explicit convention for
features that occupy disjunct regions" (Design objective 6) — and the trans-
splicing case remarks that an mRNA "occupies disjunct coordinates on the
genome"; neither is written as a validation rule. Those absences are what keep
most of the #27 rows out of the core layer, and objective 6 is what puts
`b.iv.1` into it.

## The classification

The issue's table has **12 rows covering 18 individual INSDC rule numbers**
(`b.iv.1`–`3`, `b.v.1`–`3` and `b.ix.1`–`3` each bundle three rules; the "13" in
the tasking note appears to have counted one row twice). All 18 are classified.
Rows appear in the issue's order and are split where their members do not belong
in the same place.

| INSDC rule (page) | Requirement, verbatim and abbreviated | Placement | Where it lands | Rationale in one line |
| --- | --- | --- | --- | --- |
| `b.iii.4` (p. 1) | "The order of intervals comprising a feature's location must be provided in order on the same strand (ascending order on the + strand, and descending order on the – strand)" | **profile** (INSDC/NCBI, #20), draft | draft `INSDC-014` | GFF3 fixes no line order, so ordering is submission policy (its two table 2e exceptions, p. 4, are trans-splicing and "use of `order` instead of `join`", and GFF3 has no `order` operator to mark the second). |
| `b.iii.5` (p. 1) | "Only the start and/or end of a feature may be marked as partial. Internal interval boundaries must not be marked as partial, and the direction of partiality must only indicate the feature is longer, not shorter (i.e., `<100..>200` and not `>100..<200`)" | **profile** (INSDC/NCBI, #20); blocked | draft `INSDC-001`; needs [question 19](questions-for-SO.md) | Partiality is Feature Table location notation and GFF3 1.26 defines no partial marker at all (BIO-006), so there is nothing for a core rule to read until SO settles the representation. |
| `b.iii.6` (p. 1) | "Explicitly paired CDS and mRNA features (either by a Parent relationship in GFF3 or a common transcript_id in feature table format) must have locations that are compatible (contained within and share internal interval boundaries denoted by the joined mRNA feature location)" | **profile** (INSDC/NCBI, #20), draft | draft `INSDC-015` | It is the other half of BIO-005 — boundary agreement, where BIO-005 has containment — and needs no sequence; table 2e (p. 4) exempts ribosomal slippage, which the catalogue already recognises as `recoded_codon`/`transl_except`. |
| `b.iv.1` (p. 1) | "Intervals comprising a feature's location must not overlap" | **core** (structure), warning | [GFF-STR-015](rules.md#gff-str-015), planned | The contradiction is inside one feature: GFF3's own design objective is "an explicit convention for features that occupy disjunct regions" (Summary, objective 6) and its ID column requires the lines of one ID to "collectively represent a single feature", yet disjointness is never written as a rule — hence a warning; sorting cannot rescue an overlap, unlike `b.iii.4`. |
| `b.iv.2` (p. 1) | "Ribosomal RNA features must not overlap CDS features or other rRNAs" | **profile** (INSDC/NCBI, #20) | draft `INSDC-002` | GFF3 lets distinct features overlap freely (the canonical gene's alternative transcripts and the operon example both do); naming the forbidden type pairs is INSDC content policy, not validity. |
| `b.iv.3` (p. 1) | "tRNA features must not fully overlap (be completely contained) within CDS exons" | **profile** (INSDC/NCBI, #20) | draft `INSDC-003` | Same reasoning; GFF3 not only allows containment between different features, GFF-STR-012 reports a child outside its parent as info only. |
| `b.v.1` (p. 2) | "Complete coding regions must be at least 30 amino acids long" | **profile** (INSDC/NCBI, #20) | draft `INSDC-004` | A threshold is policy — ENA's shipped engine enforces 25 aa for the same rule (tool evidence below) — and "complete" depends on the partial marker; its table 2e exception ("evidence or inference must be provided", p. 4) is Feature Table vocabulary. |
| `b.v.2` (p. 2) | "Complete tRNA features must be between 50 and 150 bps long" | **profile** (INSDC/NCBI, #20) | draft `INSDC-005` | A numeric range with no exception at all is repository policy; ranges differ between repositories and callers, and "complete" is marker-dependent. |
| `b.v.3` (p. 2) | "Introns must be at least 10 bps long" | **profile** (INSDC/NCBI, #20) | draft `INSDC-006` | Threshold policy whose four table 2e exceptions (p. 4) are all Feature Table vocabulary: `artificial_location` values, transcript or proteomic data, ribosomal slippage. |
| `b.vi.4` (p. 2) | "Coding regions with a phase ≠ 0 must be declared as partial" | **profile** (INSDC/NCBI, #20); blocked | draft `INSDC-016` | It reads the GFF3 phase column — which GFF3 does define — against the CDS's 5'-most segment, and is the mirror of the exemption BIO-006 already grants; blocked on the partiality representation, with no table 2e exception. |
| `b.vi.7` (p. 2) | "Product or translation must not be provided for a coding region with any pseudo parent features" | **profile** (INSDC/NCBI, #20); blocked | draft `INSDC-007`; needs [question 20](questions-for-SO.md) | `product`, `translation` and `pseudo` are none of them GFF3 1.26 attributes and "pseudo parent" has no agreed GFF3 representation, so a core rule would have to invent both. |
| `b.vii.1` (p. 2) | "In GFF3 format, this is indicated by the required `Parent=` attribute on the CDS feature" | **profile** (INSDC/NCBI, #20) | draft `INSDC-008` | GFF3 makes `Parent` optional for a CDS (ID is required only for features with children or spanning several lines), so "required" is submission policy; the community-profile layer already carries this shape as `AGB-007`. |
| `b.vii.2` (p. 2) | "In feature table format, this is indicated by a `/transcript_id` qualifier … Transcript_id values must be unique within the full genome annotation" | **covered / out of scope** | [GFF-STR-001](rules.md#gff-str-001) (implemented); nothing new | GFF3's analogue is file-wide ID uniqueness, which GFF-STR-001 already enforces; "within the full genome annotation" spans several files and this validator is single-file by design, so the cross-file half is out of scope rather than a missing rule. |
| `b.ix.1` (p. 3) | "Locus tags must be present in eukaryote and prokaryote genome submissions" | **profile** (INSDC/NCBI, #20) | draft `INSDC-009` | `locus_tag` is not a GFF3 attribute and "genome submission" is a scope the file does not state; a profile can require it once the submitter says what the file is. |
| `b.ix.2` (p. 3) | "Locus tag prefixes must be consistent within a single genome, and use an alphanumeric prefix that is uniquely assigned for the genome. The prefix must be separated from the tag value by an underscore, with exceptions made only for legacy genomes" | **profile** + **guidance** | draft `INSDC-010` | The underscore form and one-prefix-per-file are checkable offline; "uniquely assigned" needs the NCBI registry and the validator makes no network requests, so that half is guidance. |
| `b.ix.3` (p. 3) | "Each gene feature in a genome must have a unique locus tag" | **profile** (INSDC/NCBI, #20) | draft `INSDC-011` | Uniqueness of an INSDC qualifier among the gene lines of one file is a profile check; the genome-wide half is again outside a single file. |
| `c.i.1` (p. 3) | "Features can only be labelled partial if partiality is abutting a gap or the end of the sequence (within 2 bases to allow for non-complete codons…)" | **profile**, needs `--genome` | draft `INSDC-012` | Source-dependent and sequence-dependent: it needs a prokaryote declaration, the partial marker, and the assembly's gaps, which only the `--genome` reference carries. |
| `c.ii` (p. 3) | "Use of `artificial_location` (either low-quality sequence region or heterogeneous population sequenced) must be limited to genome-scale annotation" | **profile** (vocabulary) + **out of scope** (the limit) | draft `INSDC-013` and guidance | The two-value vocabulary of an INSDC qualifier is profile-checkable; that its use is "limited to genome-scale annotation" compares the file with a submission scope no GFF3 file expresses, exactly the reasoning that puts row AN.b.viii of the coverage matrix out of scope. |

Summary: **1 provisional catalogue candidate** (GFF-STR-015 at core);
**16 draft INSDC/NCBI profile candidates** under #20; **1 already covered**
(b.vii.2 by GFF-STR-001 in its GFF3 reading). Cross-file uniqueness, registry
assignment and the genome-scale limit remain outside this single-file validator.
Partiality and pseudo-parent candidates await questions 19/20 and the INSDC update.

## Cross-reference: what the INSDC tools themselves do

Two measured facts, both from
[#191](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/191)
(evidence run 2026-11-10, working area `…/T/opencode/insdc-191`, digests in its
`PROVENANCE.txt`), argue for keeping these rules out of core validity:

- **The submission tools never see an FHGFF3 header.** `table2asn` 1.29.324
  accepts a `#~` block and discards it (every output byte-identical to the
  header-free control); ENA's `gff3tools` 5.5.1 drops it on rewrite; DDBJ's
  `ddbj-validator` 1.0.94 rejects it. No amount of INSDC content checking here
  becomes a route to acceptance, so "may be refused at submission" is reported
  apart from core validity, in profile findings, and never as a core error.
- **An INSDC member already ships these content rules with its own numbers.**
  In `gff3tools-5.5.1.jar` (SHA-256
  `722b23c530447623597b58f5d3a929bcffe953062480ff3d2fddd6fc864c66cc`, the jar
  bundled inside `webin-cli-11.0.0`), the class
  `uk/ac/ebi/embl/gff3tools/validation/builtin/LengthValidation` carries rule ids
  `CDS_LENGTH`, `TRNA_LENGTH`, `INTRON_LENGTH` and `CDS_INTRON_LENGTH` and the
  description "Complete coding regions must be at least 25 amino acids long" —
  25 where `b.v.1` says 30. Its tRNA message repeats the 50–150 bp range of
  `b.v.2` ("measured across the segments sharing an ID that make up one spliced
  tRNA"), and its intron message ("Intron usually expected to be at least 10 nt
  long…") lists exactly the table 2e exemptions:
  `/artificial_location="heterogeneous population sequenced"`,
  `/artificial_location="low-quality sequence region"`, `/pseudo`,
  `/pseudogene`, `/trans_splicing`, `/ribosomal_slippage` or an `/exception`.
  Sibling classes implement `JOINED_LOCATION_ORDER` ("The segments of a joined
  feature must be listed in ascending coordinate order"),
  `JOINED_PARTIAL_ATTRIBUTE` ("Only the terminal segments of a joined feature
  may carry a partial attribute"), `CDS_MRNA_LOCATION` ("contained within the
  joined mRNA location and share its internal interval boundaries", with an
  `artificial_location` exemption), `FEATURE_INTERVAL_OVERLAP`,
  `RRNA_FEATURE_OVERLAP` and `TRNA_WITHIN_CDS_EXON` (the three `b.iv` rules, the
  first telling the user to "declare it with the ribosomal_slippage attribute"),
  `CDS_TRANSLATION_PRESENCE` and an `ERROR_PSEUDO_PRODUCT_CONFLICT` attribute
  relation (`pseudo`/`pseudogene` versus `product`), `LOCUS_TAG_EXISTS` and
  `ONE_PARENT_ONLY`. Its shipped `default-rule-severities.properties` sets
  `rule.LOCUS_TAG_EXISTS=ERROR` and `rule.GFF3_EXON_LENGTH_VALIDATION=WARN`.
  These strings were read from the compiled class constants (no Java runtime was
  available to disassemble the methods), so they evidence the rule names and the
  exemption vocabulary, not the tools' severities beyond that properties file.

The reading for #27: an INSDC member treats these as **repository checks with its
own thresholds and its own exemption vocabulary** — which is the profile layer —
and only the order, overlap and pairing consequences of GFF3's own feature model
are candidates for the shared catalogue.

## Draft profile entries (not added; for the #20 decision)

The profile-bound rows are written out here in the schema `profiles/*.yaml` uses
(`gff3_validator.profiles.parse_profile` accepts `id`, `level`, `title`,
`description`, `reference`, `example`, `fix`, `status`, plus `valid` and
`notes`), so opening the profile is a copy-and-review step rather than a
redesign. They are deliberately **not** committed as `profiles/insdc.yaml`:

1. A profile needs `source.license`, and `insdc/minimum-specifcations` declares
   **no license** at this pin (`GET /repos/insdc/minimum-specifcations` answers
   `"license": null`, and no `LICENSE` file exists in the tree at `41f0dc4`).
   [AGENTS.md](../AGENTS.md) and [docs/profiles.md](profiles.md) both forbid
   guessing that field.
2. A profile's `review` may record only a review that has happened; INSDC has
   reviewed nothing here.
3. Repository profiles are #20's scope. Creating one in this branch would decide
   the placement this issue asks maintainers to decide.

```yaml
# Draft: profiles/insdc.yaml — prefix INSDC, every rule status: planned.
# Metadata a maintainer must settle first:
#   license: UNKNOWN - insdc/minimum-specifcations declares no license at commit
#            41f0dc424748c9f7e50a8b6bda9b888218c4b65e (#20 blocker)
#   date:    take from Annotations/CHANGELOG.md at the pin, not from memory
#   review:  not reviewed by INSDC
# `b.iii.1` (location descriptors and strand for all features) needs no rule of
# its own: core GFF-SYN-013 to GFF-SYN-015 and GFF-SYN-017 already require a
# usable location and a strand value. What they allow that b.iii.1 arguably does
# not is strand "." and "?", and GFF-SYN-011 (a seqid must be given) is still
# planned, so a profile cannot raise it yet (#20 decides whether to state the
# stricter reading as a levels entry once GFF-SYN-011 is implemented, or as its
# own rule).

- id: INSDC-001
  level: error
  title: Partiality is marked only at a feature's outer ends
  description: >-
    A partial marker appears only on the segment a joined feature opens or
    closes with, never on an internal boundary, and it means the feature
    continues past the annotated end (b.iii.5: "Only the start and/or end of a
    feature may be marked as partial. Internal interval boundaries must not be
    marked as partial, and the direction of partiality must only indicate the
    feature is longer, not shorter").
  reference: {section: "b.iii.5 Feature location (p. 1)", anchor: ""}
  example: "ctg1\t.\tCDS\t1\t60\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t101\t160\t.\t+\t0\tID=c1;Parent=t1;partial=start\nctg1\t.\tCDS\t201\t260\t.\t+\t0\tID=c1;Parent=t1"
  fix: Move the partial marker to the first or last segment of the feature.
  status: planned
  notes: >-
    Blocked on question 19: GFF3 1.26 has no partial marker, so this rule cannot
    run until INSDC's partial=start / partial=end vocabulary is the agreed GFF3
    representation (today the catalogue reads those spellings, and the legacy
    start_range and end_range, only as BIO-006 and BIO-007 exemptions). b.iii.5
    has no asterisk: table 2e (pp. 3-4 at this pin) grants it no biological
    exception, unlike the adjacent c.i.1 (low quality sequence region). ENA's
    gff3tools 5.5.1 ships the same rule as JOINED_PARTIAL_ATTRIBUTE.

- id: INSDC-002
  level: warning
  title: rRNA does not overlap CDS or another rRNA
  description: >-
    An rRNA feature shares no base with a CDS or with another rRNA (b.iv.2:
    "Ribosomal RNA features must not overlap CDS features or other rRNAs").
  reference: {section: "b.iv.2 Feature overlaps (p. 1)", anchor: ""}
  example: "ctg1\t.\trRNA\t100\t300\t.\t+\t.\tID=r1\nctg1\t.\tCDS\t200\t900\t.\t+\t0\tID=c1;Parent=t1"
  fix: Correct one of the two locations, or annotate the feature the evidence supports.
  status: planned
  notes: >-
    No asterisk, so no exception as written. Overlapping distinct features are
    valid GFF3, which is why this stays a profile finding and never a core error.
    Needs the SO layer to recognise rRNA, CDS and their is_a subtypes. ENA's
    gff3tools 5.5.1 ships it as RRNA_FEATURE_OVERLAP, restricted to the same
    strand; whether the strand qualifier is INSDC's intent is a question for the
    specification editors.

- id: INSDC-003
  level: warning
  title: A tRNA is not contained within a CDS exon
  description: >-
    No tRNA lies completely inside the exons of a CDS (b.iv.3: "tRNA features
    must not fully overlap (be completely contained) within CDS exons").
  reference: {section: "b.iv.3 Feature overlaps (p. 1)", anchor: ""}
  example: "ctg1\t.\tCDS\t100\t900\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\ttRNA\t300\t370\t.\t+\t.\tID=t2"
  fix: Check the coordinates; a tRNA called wholly inside a coding exon is usually a mis-mapped call.
  status: planned
  notes: >-
    "CDS exons" are the intervals of the CDS lines, so no genome is needed. No
    table 2e exception. ENA's gff3tools 5.5.1 ships it as TRNA_WITHIN_CDS_EXON.

- id: INSDC-004
  level: warning
  title: A complete CDS is at least 30 amino acids
  description: >-
    A CDS that is not partial codes at least 30 amino acids (b.v.1: "Complete
    coding regions must be at least 30 amino acids long").
  reference: {section: "b.v.1 Feature lengths (p. 2)", anchor: ""}
  example: "ctg1\t.\tCDS\t1\t78\t.\t+\t0\tID=c1;Parent=t1"
  fix: Extend the CDS, mark it partial, or carry the evidence or inference that justifies a short product.
  status: planned
  notes: >-
    The coding length comes from the coordinates and phases, as BIO-009 already
    computes, so no genome is needed to measure it; deciding that a CDS is
    "complete" needs the partiality marker of question 19. Table 2e (p. 4) grants
    one exception - "evidence or inference must be provided" - which is Feature
    Table vocabulary GFF3 has no tag for (Dbxref or Note can carry it, at best).
    ENA's engine enforces 25 amino acids for the same rule, which is precisely
    why the number is a profile value and not a catalogue threshold.

- id: INSDC-005
  level: warning
  title: A complete tRNA is 50 to 150 bp
  description: >-
    A tRNA that is not partial spans between 50 and 150 bases, counted across
    the segments that share its ID (b.v.2: "Complete tRNA features must be
    between 50 and 150 bps long").
  reference: {section: "b.v.2 Feature lengths (p. 2)", anchor: ""}
  example: "ctg1\t.\ttRNA\t1\t40\t.\t+\t.\tID=t1"
  fix: Check the tRNA call, or mark a genuinely incomplete gene partial.
  status: planned
  notes: >-
    No asterisk, so no exception as written. ENA's TRNA_LENGTH uses the same
    range and the same across-segments measurement; other callers use other
    ranges, which is why the value lives in a profile.

- id: INSDC-006
  level: warning
  title: An intron is at least 10 bp
  description: >-
    The gap between two consecutive exons of a transcript is at least 10 bases
    (b.v.3: "Introns must be at least 10 bps long").
  reference: {section: "b.v.3 Feature lengths (p. 2)", anchor: ""}
  example: "ctg1\t.\texon\t1\t60\t.\t+\t.\tID=e1;Parent=t1\nctg1\t.\texon\t65\t160\t.\t+\t.\tID=e2;Parent=t1"
  fix: Merge the exons, correct the coordinates, or record the exception that justifies the short intron.
  status: planned
  notes: >-
    Table 2e (p. 4) grants four exceptions: low quality sequence region,
    heterogeneous population sequenced, "annotated by transcript or proteomic
    data", and ribosomal slippage. The first two are artificial_location values
    and the third an evidence qualifier, so the exemptions work only once the
    profile fixes that vocabulary; ENA's INTRON_LENGTH message lists exactly
    these options, and its CDS_INTRON_LENGTH measures the same thing between CDS
    segments. Without a marker a legitimately short intron is reported, as
    BIO-010 today reports unmarked trans-splicing.

- id: INSDC-007
  level: warning
  title: A CDS under a pseudo parent has no product or translation
  description: >-
    When any parent of a CDS is pseudo (a pseudogene or a pseudogenic
    transcript), the CDS carries neither product nor translation (b.vi.7:
    "Product or translation must not be provided for a coding region with any
    pseudo parent features").
  reference: {section: "b.vi.7 Coding regions (p. 2)", anchor: ""}
  example: "ctg1\t.\tpseudogene\t1\t900\t.\t+\t.\tID=g1\nctg1\t.\tCDS\t1\t900\t.\t+\t0\tID=c1;Parent=g1;product=hypothetical protein"
  fix: Drop product and translation from the CDS, or annotate the feature as the gene it is.
  status: planned
  notes: >-
    Blocked on question 20: whether a pseudo parent is written as an SO type
    (the pinned release has pseudogene SO:0000336, pseudogenic_transcript
    SO:0000516 part_of pseudogene and pseudogenic_CDS SO:0002087, each carrying
    the synonym INSDC_qualifier:pseudo) or as an application tag such as
    pseudo=1. product and translation are not reserved GFF3 attributes
    (GFF-ATT-007 warns only on unknown upper-case tags), so the rule reads INSDC
    vocabulary and belongs to the profile. No table 2e exception. ENA's
    gff3tools 5.5.1 ships CDS_TRANSLATION_PRESENCE and an
    ERROR_PSEUDO_PRODUCT_CONFLICT relation.

- id: INSDC-008
  level: error
  title: A CDS names its transcript
  description: >-
    Every CDS line has a Parent (b.vii.1: "In GFF3 format, this is indicated by
    the required Parent= attribute on the CDS feature").
  reference: {section: "b.vii.1 mRNA and CDS features (p. 2)", anchor: ""}
  example: "ctg1\t.\tCDS\t1\t900\t.\t+\t0\tID=c1"
  fix: "Add Parent=<transcript ID>; a Parent that does not resolve is core GFF-STR-004."
  status: planned
  notes: >-
    GFF3 leaves Parent optional for a CDS, so this is submission policy. The
    AgBioData profile already states the same expectation as AGB-007 (warning,
    CDS and exon features have a Parent), which is the pattern to follow; whether
    INSDC's reading is an error is a #20 decision. ENA's engine has
    ONE_PARENT_ONLY for the multi-parent half.

- id: INSDC-009
  level: error
  title: A genome annotation carries locus tags
  description: >-
    Gene features carry a locus_tag (b.ix.1: "Locus tags must be present in
    eukaryote and prokaryote genome submissions").
  reference: {section: "b.ix.1 Locus tags (p. 3)", anchor: ""}
  example: "ctg1\t.\tgene\t1\t900\t.\t+\t.\tID=g1"
  fix: Add locus_tag=<prefix>_<value> to every gene, or say the file is not a genome submission.
  status: planned
  notes: >-
    Applies once the submitter declares that this file is a genome annotation: a
    standalone transcript or alignment file is outside b.ix's scope and GFF3 says
    nothing about it. ENA's engine enforces this as LOCUS_TAG_EXISTS (ERROR in
    its shipped default-rule-severities.properties), whose implementation names
    sequence-comparison, repeat-region, biological-region and virus-lineage
    contexts; b.ix.4 points at the NCBI locus_tag page for the assignment rules.

- id: INSDC-010
  level: warning
  title: Locus tags share one prefix and use an underscore
  description: >-
    All locus_tag values in one file use the same alphanumeric prefix, separated
    from the tag value by an underscore (b.ix.2).
  reference: {section: "b.ix.2 Locus tags (p. 3)", anchor: ""}
  example: "ctg1\t.\tgene\t1\t900\t.\t+\t.\tID=g1;locus_tag=ABC123"
  valid: "ctg1\t.\tgene\t1\t900\t.\t+\t.\tID=g1;locus_tag=ABC_123"
  fix: Use <prefix>_<value>, with one prefix throughout the annotation.
  status: planned
  notes: >-
    "Exceptions made only for legacy genomes" has no GFF3 marker, so a legacy
    file is reported and silenced by the user. That the prefix is uniquely
    assigned is not checkable offline (the NCBI registry is a network resource)
    and stays guidance.

- id: INSDC-011
  level: error
  title: A locus tag names one gene
  description: >-
    No two gene features in the file share a locus_tag (b.ix.3: "Each gene
    feature in a genome must have a unique locus tag").
  reference: {section: "b.ix.3 Locus tags (p. 3)", anchor: ""}
  example: "ctg1\t.\tgene\t1\t900\t.\t+\t.\tID=g1;locus_tag=ABC_1\nctg1\t.\tgene\t2000\t2900\t.\t+\t.\tID=g2;locus_tag=ABC_1"
  fix: Give each gene its own locus tag.
  status: planned
  notes: Checked within one file; uniqueness across a multi-file genome
    submission is outside the validator's single-file scope.

- id: INSDC-012
  level: warning
  title: A partial feature in a prokaryote genome abuts a gap or the sequence end
  description: >-
    In a prokaryote genome annotation a partial marker is valid only within two
    bases of an assembly gap or of the sequence end (c.i.1: "Features can only be
    labelled partial if partiality is abutting a gap or the end of the sequence
    (within 2 bases to allow for non-complete codons; however, it is preferred to
    extend the feature and include the non-complete codon)").
  reference: {section: "c.i.1 Validations specific to prokaryote genomes (p. 3)", anchor: ""}
  example: "ctg1\t.\tCDS\t500\t1500\t.\t+\t0\tID=c1;Parent=t1;partial=start"
  fix: Extend the feature, drop the partial marker, or mark the region with the exception that justifies it.
  status: planned
  notes: >-
    Needs --genome to see the gap (a run of N) and the sequence end, a
    declaration that this is a prokaryote genome (GFF3 carries no molecule type,
    which is also why row AN.b.viii of the coverage matrix is out of scope), and
    the partiality marker of question 19. Table 2e (p. 4) grants one exception,
    low quality sequence region. The profile mechanism can declare a genome
    dependency for raised core biology rules but not yet for a profile's own
    rules: #20 decides how INSDC-012 reports without --genome rather than
    passing (AGENTS.md: a skipped check is never reported as passed).

- id: INSDC-013
  level: warning
  title: artificial_location uses an INSDC value
  description: >-
    An artificial_location attribute carries one of the two values the
    specification names, "low-quality sequence region" or "heterogeneous
    population sequenced" (c.ii).
  reference: {section: "c.ii Source-dependent validation (p. 3)", anchor: ""}
  example: "ctg1\t.\tCDS\t1\t300\t.\t+\t0\tID=c1;Parent=t1;artificial_location=hard call"
  fix: Use one of the two INSDC values, or drop the attribute.
  status: planned
  notes: >-
    The other half of c.ii - that its use "must be limited to genome-scale
    annotation" - compares the file with a submission scope no GFF3 file
    expresses, so it is out of validator scope and recorded as guidance, like row
    AN.b.viii. ENA's engine reads artificial_location as an intron-length
    exemption, so the value vocabulary is the checkable part.
```

If #20 prefers two profiles (`insdc` and `ncbi`) over one, the split is by
source document, not by subject: everything above cites `Annotations/…v1.0` at
this pin, which is INSDC text. The NCBI-specific detail — the locus_tag registry,
the 30 aa versus ENA's 25 aa threshold, the `/exception` vocabulary — needs its
own pinned NCBI document before any of it is written as an `NCBI-*` rule.

The repository is already prepared for this on the conformance side:
`scripts/make_conformance.py` reserves the case status `extension:insdc`
("Reserved for INSDC GFF3 extension cases (none yet)"), and
[conformance/README.md](../conformance/README.md) says the suite will carry INSDC
cases with that status as the INSDC GFF3 extension takes shape, inviting INSDC or
NCBI to contribute or review them. Implementing any drafted rule therefore
follows the existing workflow — `case(...)` in the generator with status
`extension:insdc`, regenerate, check — rather than inventing a harness.

## Out of validator scope

| INSDC rule | Why not |
| --- | --- |
| `b.vii.2` (genome-wide `transcript_id` uniqueness) | The validator reads one file at a time; GFF3's in-file equivalent is already GFF-STR-001, and `transcript_id` itself is Feature Table vocabulary. |
| `b.ix.2` ("uniquely assigned for the genome") | Requires the NCBI locus_tag registry; the validator makes no network requests (AGENTS.md, Security). |
| `c.ii` ("limited to genome-scale annotation") | Submission scope is not carried by a GFF3 file; the same reasoning the coverage matrix applies to row AN.b.viii. |
| `b.vi.6` (product names follow the international protein nomenclature guide) | Not machine-checkable from text; the pattern for guidance rows. #27 does not list it, and it is named here only so the b.vi family is fully dispositioned. |

## Additional draft profile candidates (review follow-up)

These replace the former proposed catalogue IDs GFF-STR-014, BIO-012 and
BIO-013. They are documentation-only drafts for #20; no profile is shipped and
no GFF3 validity requirement is added. Levels and exception markers need review.

```yaml
- id: INSDC-014
  level: info
  title: Segments of one feature are given in 5' to 3' order
  description: >-
    The lines sharing one ID normally appear in transcript order: ascending
    start on the + strand, descending on the -. GFF3 1.26 does not require an
    order, so this is reported as information; INSDC submission requires it
    (rule b.iii.4).
  reference: {anchor: "", section: "b.iii.4 Feature location (p. 1)"}
  example: "ctg1\t.\tmRNA\t1\t90\t.\t+\t.\tID=t1\nctg1\t.\tCDS\t61\t90\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t1\t30\t.\t+\t0\tID=c1;Parent=t1"
  valid: "ctg1\t.\tmRNA\t1\t90\t.\t+\t.\tID=t1\nctg1\t.\tCDS\t1\t30\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t61\t90\t.\t+\t0\tID=c1;Parent=t1"
  fix: None needed for validity. Listing the segments in transcript order keeps readers that take the order from the file in agreement with readers that sort by coordinate.
  status: planned
  notes: >-
    Proposed placement of INSDC Annotation Minimum Specification v1.0 b.iii.4
    ("The order of intervals comprising a feature's location must be provided
    in order on the same strand (ascending order on the + strand, and
    descending order on the - strand)", p. 1 of the PDF at insdc/minimum-
    specifcations commit 41f0dc424748c9f7e50a8b6bda9b888218c4b65e), reviewed in
    #27. GFF3 1.26 fixes no line order: the ID column only says that all lines
    sharing an ID "collectively represent a single feature", so readers
    diverge - GenomeTools sorts (gt gff3 -sort) and BIO-004 orders a CDS by
    start on + and by end on -, while INSDC reads the file's order. Kept as a
    draft profile candidate because GFF3 does not require line order; its
    profile severity remains for review under #20. Table 2e (p. 4
    at this pin) allows two exceptions: trans-splicing, and "Use of 'order'
    instead of 'join'"; GFF3 has no order operator, so the second cannot be
    expressed by a GFF3 submitter and cannot be told apart from an accident
    here. The level and the exemption marker follow from question 8 (what the
    lines of one feature must share); not implemented, no fixture yet.

- id: INSDC-015
  level: warning
  title: A CDS shares the internal boundaries of its transcript
  description: >-
    When a CDS and an mRNA are paired (the CDS names the mRNA in Parent), every
    internal boundary of the CDS is also a boundary of the joined mRNA
    location, and the CDS lies within it. A CDS that stops or starts inside an
    exon of its own transcript describes a protein the transcript does not
    carry.
  reference: {anchor: "", section: "b.iii.6 Feature location (p. 1)"}
  example: "ctg1\t.\tmRNA\t1\t500\t.\t+\t.\tID=t1\nctg1\t.\texon\t1\t100\t.\t+\t.\tID=e1;Parent=t1\nctg1\t.\texon\t201\t300\t.\t+\t.\tID=e2;Parent=t1\nctg1\t.\texon\t401\t500\t.\t+\t.\tID=e3;Parent=t1\nctg1\t.\tCDS\t1\t100\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t250\t300\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t401\t500\t.\t+\t0\tID=c1;Parent=t1"
  valid: "ctg1\t.\tmRNA\t1\t500\t.\t+\t.\tID=t1\nctg1\t.\texon\t1\t100\t.\t+\t.\tID=e1;Parent=t1\nctg1\t.\texon\t201\t300\t.\t+\t.\tID=e2;Parent=t1\nctg1\t.\texon\t401\t500\t.\t+\t.\tID=e3;Parent=t1\nctg1\t.\tCDS\t1\t100\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t201\t300\t.\t+\t0\tID=c1;Parent=t1\nctg1\t.\tCDS\t401\t500\t.\t+\t0\tID=c1;Parent=t1"
  fix: Move the CDS boundary onto the exon boundary of its transcript, or give the CDS the transcript whose exons it follows.
  status: planned
  notes: >-
    Proposed placement of INSDC Annotation Minimum Specification v1.0 b.iii.6
    ("Explicitly paired CDS and mRNA features (either by a Parent relationship
    in GFF3 or a common transcript_id in feature table format) must have
    locations that are compatible (contained within and share internal interval
    boundaries denoted by the joined mRNA feature location)", p. 1 of the PDF at
    insdc/minimum-specifcations commit
    41f0dc424748c9f7e50a8b6bda9b888218c4b65e), reviewed in #27. It complements
    BIO-005, which checks only that each CDS segment lies within an exon of its
    transcript: containment there, shared boundaries here. Like BIO-005 it needs
    no genome sequence, only the coordinates, but belongs in a repository profile because GFF3 does not require it. GFF3 1.26 gives no rule here (the canonical gene shows the
    shape but does not require it), so it is a profile candidate. The pairing is the GFF3
    Parent relationship; the feature-table transcript_id that b.iii.6 also names
    is not a GFF3 reserved tag, so a transcript_id-only pairing is out of this
    catalogue's reach (it is a profile question, docs/insdc-rule-placement.md).
    The asterisk on b.iii.6 points at table 2e (p. 4 at this pin), which allows
    one exception: "Where coding feature interval boundaries are not also
    represented in the mRNA feature location - ribosomal slippage". A slippage
    is recognised the way BIO-006 and BIO-008 recognise recoding (a recoded_codon
    SO:0000145 or an is_a subtype of it under the CDS, or the legacy
    transl_except), so it is exempt only when the SO layer can see it; the
    GFF3-specification's own programmed-frameshift example (mRNA tagged
    Ontology_term=SO:1000069, obsolete in the pinned release, and a CDS whose
    second segment restarts at phase 0) is the shape to test against.
    Trans-splicing is not an exception to b.iii.6. Not implemented, no fixture
    yet.

- id: INSDC-016
  level: warning
  title: A CDS that starts inside a codon is declared partial
  description: >-
    The 5'-most segment of a CDS with phase 1 or 2 begins in the middle of a
    codon, so the coding region is incomplete at that end. INSDC requires such a
    coding region to be declared partial.
  reference: {anchor: "", section: "b.vi.4 Coding regions (p. 2)"}
  example: "ctg1\t.\tmRNA\t1\t200\t.\t+\t.\tID=t1\nctg1\t.\tCDS\t1\t199\t.\t+\t1\tID=c1;Parent=t1"
  valid: "ctg1\t.\tmRNA\t1\t200\t.\t+\t.\tID=t1\nctg1\t.\tCDS\t1\t199\t.\t+\t1\tID=c1;Parent=t1;partial=start"
  fix: Declare the CDS partial at that end (partial=start; the legacy start_range, and on a minus-strand CDS the higher coordinate is the 5' end), or correct the phase.
  status: planned
  notes: >-
    Proposed placement of INSDC Annotation Minimum Specification v1.0 b.vi.4
    ("Coding regions with a phase != 0 must be declared as partial", p. 2 of the
    PDF at insdc/minimum-specifcations commit
    41f0dc424748c9f7e50a8b6bda9b888218c4b65e), reviewed in #27. Read as applying
    to the CDS's 5' end: an internal segment with phase 1 or 2 is the normal
    continuation of a codon split across a splice junction (the canonical gene's
    cds00003 has phase 1 on its second and third segments), and BIO-004 already
    computes the phases along the segments in 5' to 3' order. The rule is the
    mirror of the exemption BIO-006 grants ("a CDS whose first segment has phase
    1 or 2 starts inside a codon by definition and is not judged"): what BIO-006
    excuses, b.vi.4 asks to be said out loud. It is blocked on how partiality is
    written in GFF3 - question 17 and the new question 19 - because there is no
    GFF3 1.26 partial marker to require; the same answer settles whether the
    profile vocabulary can express it (#20). b.vi.4 carries no
    asterisk, so table 2e (pp. 3-4 at this pin) gives no biological exception:
    the slippage, trans-splicing, low-quality-region and heterogeneous-
    population exceptions are listed there for b.iii.2, b.iii.3, b.iii.4,
    b.iii.6, b.iv.1, b.v.1, b.v.3, b.vi.9, c.i.1, c.i.2, d.ii, d.iv and d.v, not
    for b.vi.4. A 5' partial marker exempt it, and a start_range/end_range file
    is read as BIO-006 reads it until the INSDC draft fixes the vocabulary. Not
    implemented, no fixture yet.
```

## Review items for the maintainers

1. **INSDC-014's profile level.** Segment order is submission policy, not a
   GFF3 core requirement. Confirm its profile severity after the INSDC update.
2. **GFF-STR-015 and INSDC-015 exemptions.** Both hinge on recognising ribosomal
   slippage. Is `recoded_codon` plus the legacy `transl_except` (the question 17
   convention) the marker, and may the rules warn when it is absent — as BIO-008
   does today for unmarked recoding — or must they stay silent until SO answers?
3. **INSDC-015's profile placement.** Shared internal boundaries are not a
   GFF3 requirement. The existing BIO-005 containment check is unchanged.
4. **INSDC-016's reading.** Confirm that b.vi.4 applies to the CDS's 5'-most
   segment only: an internal segment with phase 1 or 2 is the normal
   continuation of a codon split across a junction, and the specification's own
   canonical gene (cds00003) has phase 1 on its second and third segments.
5. **Open the INSDC/NCBI profile?** #20 owns this. It needs (a) the licence
   question above settled for `insdc/minimum-specifcations`, (b) one profile or
   two, and (c) a decision on whether a profile's own rule may require
   `--genome` (INSDC-012), since today only raised core rules declare that
   dependency.
6. **Context no file carries.** INSDC-009 and INSDC-012 need "this is a genome
   submission" and "this is prokaryote". Options: profile options, a declared
   command-line flag, or leaving them unchecked and documented. An FHGFF3 header
   is not a substitute: the header carries provenance only, and #27 records that
   no header change follows from this work.
7. **SO answers needed** for [question 19](questions-for-SO.md) (partiality in
   GFF3) and [question 20](questions-for-SO.md) (pseudo parents) before
   INSDC-001, INSDC-004, INSDC-005, INSDC-007, INSDC-012 and INSDC-016 can leave
   `planned`.
8. **Two anomalies to report upstream (via
   [#157](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/157)),**
   neither of which changes a placement here: table 2e (p. 4) cites a rule
   `c.i.2` ("Where coding features span multiple joined locations on bacteria")
   that the body of section `c.i` does not contain — `c.i` has a single numbered
   rule (p. 3); and `b.vi.1` carries an asterisk (p. 2) with no table 2e row. The
   `b.iv.2` wording also differs between the body ("must not overlap CDS features
   or other rRNAs", p. 1) and ENA's same-strand reading noted above.
9. **Coverage matrix.** Rows AN.b.iii, AN.b.iv, AN.b.v, AN.b.vi, AN.b.vii,
   AN.b.ix, AN.c.i and AN.c.ii of `FAIR-bioHeaders-Specification`
   `docs/insdc-coverage.md` (read from `origin/main` on 2026-11-10) point at #27.
   They must be re-rated when a rule is implemented, not when it is planned: a
   planned entry reports as "not checked" and covers nothing.

## After the placement review

Nothing is implemented yet, by design. When a placement is agreed, each rule
follows the existing workflow:

1. Flip `status: planned` to `implemented` only when the engine emits the rule
   and a fixture covers it (AGENTS.md).
2. Add fixtures under `tests/fixtures/` — a positive case, a rejection case and
   one case per table 2e exception — and list the ids in
   `tests/fixtures/expected.yaml`, which `test_every_implemented_rule_has_a_fixture`
   then requires.
3. Add the vector to `scripts/make_conformance.py` with the right status
   (`spec`, `proposed` with the open question cited, or `extension:insdc` for a
   profile case), regenerate, and run `scripts/check_conformance.py`.
4. Keep profile findings out of core validity: a profile entry is added to
   `profiles/ID.yaml` with its checks module, its own test in
   `tests/test_profiles.py`, and its mapping row generated into
   `docs/profiles.md`; `tests/test_profiles.py::test_shipped_profiles` pins the
   list of shipped profiles and is updated in the same commit.
5. Re-rate the coverage-matrix rows in `FAIR-bioHeaders-Specification` only then,
   and record the SO answers against questions 19 and 20 in
   [docs/questions-for-SO.md](questions-for-SO.md) as they arrive.

## Initial preparation checks (before review follow-up)

```text
python scripts/render_rules.py                                     # wrote the packaged catalogue copy and docs/rules.md
python scripts/render_rules.py --check                             # OK, no drift
python -m pytest                                                   # 888 passed, 30 skipped
python scripts/check_conformance.py                                # suite: 112 cases, 84 rules, 16 profile cases: OK
python scripts/check_conformance.py --gff3-validate <py> -m gff3_validator
                                                                   # 119/119 passed, 0 failed, 9 skipped
python -m ruff check .                                             # All checks passed
python -m black . --check                                          # 42 files unchanged
python -m isort . --check-only                                     # OK
git diff --check                                                   # no whitespace errors
```

Environment limitations, recorded as [AGENTS.md](../AGENTS.md) asks: `poetry` is
not installed on this host, so the checks above ran in a plain virtualenv
(Python 3.15) with `pytest`, `pyyaml`, `jsonschema`, `ruff`, `black` and `isort`,
and the CLI was invoked as `python -m gff3_validator` instead of the
`gff3-validate` console script. The optional `headers` extra
(`fair-bioheaders`) was not installed: the 30 skips are the FHGFF3 header tests
("needs the FAIR-bioHeaders toolkit with FHGFF3 support") and the 9 skipped
conformance cases are the `headers: checked` ones, so the header path and the
`--extras headers` CI job were not exercised here. The wheel build and
fresh-environment install from AGENTS.md's "complete verification" list were not
run: this branch changes no Python module, only `rules/catalogue.yaml`, its
generated copies and documentation. The JS/Pyodide parity check was likewise not
run for the same reason. `render_rules.py --check` and
`test_source_and_packaged_copy_are_identical` are the checks that matter for a
catalogue-only change, and both pass.

No engine code, fixture or conformance vector was added. Rule logic waits for the
placement review
([#27](https://github.com/FAIR-bioHeaders/gff3-validator/issues/27): "STOP AND
WAIT FOR REVIEW of rule placement and unresolved SO semantics"). The initial preparation did not publish a release or implement a rule.
Review follow-up checks and commits are recorded on PR #28.
