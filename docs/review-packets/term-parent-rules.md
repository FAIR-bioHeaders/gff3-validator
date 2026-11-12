# Review packet — SO term and Parent relationship rules

Prepared for [#19](https://github.com/FAIR-bioHeaders/gff3-validator/issues/19)
(Refs #19; the SO-facing part of #18's catalogue review, and the gate on the
INSDC/NCBI draft profile rules of #20). Draft packet, 2026-11-11. This packet
contacts no one and records no review: every rule below stays exactly at its
catalogue level and status until SO answers, and no SO-dependent rule is
implemented on the strength of these documents.

## The pinned release

| | |
| --- | --- |
| Artefact | so.obo, data-version **2026-08-07** |
| Source pin | SO-Ontologies commit `4340c143bac3578bba0c013d02e8c5f0e51ad14a`, `Ontology_Files/so.obo` — raw URL verified HTTP 200 (2026-11-11) |
| Integrity | SHA-256 `22a8f3ec2b49125dbb6cee8456f0bca86dd8c98f433165ffa4b554da4f155204` (`gff3_validator/data/so-release.json`) |
| Size | 2620 terms, 211 obsolete |
| Bundled form | `data/so.json.gz` (derived_sha256 `38035072…6743`), regenerated only by `scripts/update_so.py`; `--so PATH` accepts another so.obo at run time |
| "Release" caveat | SO has published no GitHub release since v3.1 (2018), so the data-version **is** the release for our purposes — the point **Q13** asks SO to confirm |

Per term the engine keeps only what the rules consume (`gff3_validator/ontology.py`):
label, `is_a`, `part_of`, `member_of`, EXACT synonyms, subset membership
(SOFA), and `obsolete` with `replaced_by`/`consider`; ancestor closures and
part_of/member_of reachability are precomputed. Everything below describes
behaviour against this one artefact.

## The SO-backed rules today

Levels are as merged in `rules/catalogue.yaml` (all `review: pending-SO`);
none counts as SO-endorsed.

| Rule | Level | Status | What the engine actually does against the pinned release | Gated by |
| --- | --- | --- | --- | --- |
| [SO-001](../rules.md#so-001) | warning | implemented | column 3 equals an exact label or `SO:` accession of the pinned release, else warns (suggests up to three close labels). Deliberately **not** an error: the GFF3 text names no release (Q13) and terms are renamed (the pinned release has `lncRNA`, not `lnc_RNA`, and the latter is not a synonym) | Q13, Q14 |
| [SO-002](../rules.md#so-002) | error | implemented | any `SO:`-prefixed type must be `SO:` + seven digits (the specification's own six-digit `SO:000000` pattern is on the errata list) | — |
| [SO-003](../rules.md#so-003) | warning | implemented | resolved type must be `sequence_feature` (SO:0000110) or an **is_a** descendant; part_of-only descendants do not count | Q14 |
| [SO-004](../rules.md#so-004) | warning | implemented | obsolete label/accession reported with the release's `replaced_by`/`consider` text (suppresses SO-003/SO-009 for that type) | Q13 |
| [SO-005](../rules.md#so-005) | warning | implemented | EXACT synonym or case variant names a current term: warns with the canonical label; a **unique** match is then used by SO-003/004/006/009 but never satisfies the exact-label requirements (SO-001's accession path, CDS/exon/recoded_codon checks) | Q14 |
| [SO-006](../rules.md#so-006) | warning | implemented | a `Parent` edge is accepted when the child's type (or any is_a ancestor) is `part_of` **or `member_of`** the parent's type (or any is_a ancestor), directly or transitively. `member_of` was added because SO relates transcripts to genes *only* through `gene_member_region member_of gene` — with part_of alone the specification's canonical gene fails. The GFF3 text says a non-part-of Parent "should trigger a parse exception"; we warn | Q15 |
| [SO-007](../rules.md#so-007) | info | **planned — not checked** | `Derives_from` is not type-checked at all; reports list it as not checked. The specification's own examples (`CDS` derives_from `gene`) may not be SO derives_from relations | Q16 |
| [SO-008](../rules.md#so-008) | warning | implemented | `Ontology_term=SO:…` values must exist in the pinned release; obsolete values are *not* reported (the specification's `SO:1000069` example is obsolete in this release) | Q13 |
| [SO-009](../rules.md#so-009) | info | implemented | current SO term outside the **SOFA** subset gets an informational note (SOFA is the annotation subset GFF3 historically referenced; full SO is accepted) | Q13 |

SO also feeds rules outside the `so` layer — the same release, different
sections of the catalogue:

| Rule | How it consumes the pinned release |
| --- | --- |
| [GFF-SYN-019](../rules.md#gff-syn-019), [GFF-SYN-020](../rules.md#gff-syn-020) | phase required on `CDS` = label or SO:0000316 **and every is_a subtype** (so `CDS_predicted`, `edited_CDS` …); phase on any other *resolvable, current* type warns; unknown/obsolete types are not judged (Q6 implementation, depends on Q13/Q14 resolution behaviour) |
| [GFF-DIR-009](../rules.md#gff-dir-009) | `##feature-ontology` URIs are recorded, never fetched; the file is validated against the bundled (or `--so`) release and the report names it (Q13 proposal, implemented as proposed) |
| [BIO-004](../rules.md#bio-004)–[BIO-008](../rules.md#bio-008) | recoding exemptions are recognised as a `recoded_codon` (SO:0000145) or is_a-subtype child of the CDS, with legacy `transl_except` as fallback (Q17 / SO-Ontologies #658, now closed); partial exemptions read `partial=start,end` and legacy `start_range`/`end_range` (Q17/Q19) |
| [BIO-010](../rules.md#bio-010) | strand consistency is checked only along Parent edges SO-006 accepts (part_of/member_of chain); edges SO-006 reports are skipped; unresolvable types still get the plain comparison (Q18) |
| [GFF-ATT-007](../rules.md#gff-att-007) | not SO-driven, but it is where NCBI's `Is_pseudo` practice is on record as an unknown reserved tag — the attribute half of Q20 |
| profile `agbiodata` | raises SO-001 to error (profile finding; core level unchanged) — a preview of what Q14's answer would make universal if SO confirms the release binding |

## Unresolved semantics — which question gates which rule

| Q | Ask in one line | Gates (rules) | What the SO answer changes |
| --- | --- | --- | --- |
| [13](../questions-for-SO.md) | Confirm the pinned artefact (so.obo data-version = "the release"), the SOFA warning policy, and the handling of files naming old `##feature-ontology` releases | SO-001 (level), SO-004, SO-009, GFF-DIR-009; every rule's reproducibility statement | an "agree" lets SO-001 be judged at error-level policy in #18's severities pass; a different artefact choice re-bases `scripts/update_so.py` and the bundled files; nothing about the engine changes before an answer |
| [14](../questions-for-SO.md) | Exact label or accession only? EXACT synonyms and case variants acceptable at which level? is_a-only under sequence_feature? | SO-001, SO-003, SO-005 (and via them SO-006, BIO-010) | decides whether SO-001 becomes an error and SO-005 a note; whether `lnc_RNA`-style renamed labels are errors; whether the synonym pass-through in SO-003/004/006/009 stays |
| [15](../questions-for-SO.md) | Which relation set defines an allowed Parent — part_of only, part_of + member_of, inverse has_part, transitive closures? Error (as the spec's "parse exception" wording) or warning? | SO-006; BIO-010's edge filter; draft profile rule AGB-003 analogues; the pseudogene chain in Q20(ii) | an enumerated relation set replaces `PARENT_RELATIONS = ("part_of", "member_of")` in `ontology.py`; dropping member_of would flag the canonical gene's mRNA→gene edge; confirming "parse exception" raises SO-006 to error and re-tunes BIO-010 |
| [16](../questions-for-SO.md) | Should Derives_from be type-checked at all, given the spec's own examples? | SO-007 (planned, info) | "no" retires SO-007 (id retired, never reused post-release); a relation set makes it implementable — engine work and fixtures only start after the answer, never before |
| [19](../questions-for-SO.md) | What is the GFF3 partiality marker, allowed on which segment of a feature, and are `start`/`end` 5'/3' or genomic? | BIO-006 (exemption orientation, both ends currently exempted on minus strand); draft profile INSDC-001, -004, -005, -012, -016 in [insdc-rule-placement.md](../insdc-rule-placement.md) | fixes the vocabulary every partiality-dependent rule reads; decides core-vs-profile placement of b.iii.5/b.vi.4 checks; releases five draft rules that are otherwise blocked |
| [20](../questions-for-SO.md) | Is pseudo status carried by the SO type (`pseudogene`/`pseudogenic_transcript`/`pseudogenic_CDS`) or an attribute; does the Parent-chain check run transitively? | SO-001/SO-006 expectations for pseudogene models; draft profile INSDC-007; ATT-007's `Is_pseudo` note | the typed route is verified in the pinned release (checked 2026-11-11 against `data/so.json.gz`): SO:0000336 `pseudogene` is_a SO:0001411 `gene`; SO:0000516 `pseudogenic_transcript` part_of SO:0000336; SO:0002087 `pseudogenic_CDS` part_of SO:0000516; all three carry the EXACT synonym `INSDC_qualifier:pseudo` and all three are SOFA members — so `pseudogene → pseudogenic_transcript → pseudogenic_CDS` already passes SO-006 today. An attribute-route answer instead points the validator at `pseudo`/`pseudogene`/`Is_pseudo` tags (ENA gff3tools 5.5.1 reads `pseudo`/`pseudogene`; NCBI's GFF3 guidance uses `pseudogene=<TYPE>` on the gene and warns that `/pseudo` does **not** mean pseudogene) |

## Evidence already on hand for the reviewers

No contact beyond what already happened is claimed here; these are public
records the maintainers may attach when they route the questions.

- **Q19/Q17 vocabulary.** Terence Murphy (INSDC) on
  [SO-Ontologies #685](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/685#issuecomment-6080389993):
  the INSDC draft will use `partial=start`, `partial=end`, `partial=start,end`
  instead of the GVF-derived `start_range`/`end_range` (already quoted in
  Q17/Q19). The minus-strand 5'/3'-vs-genomic reading remains explicitly open.
  NCBI's *Annotating Genomes with GFF3 or GTF files* page (verified
  2026-11-11, page stamped "Last updated 2024-03-08") states the opposite
  practical extreme for submissions: partialness is *computed automatically*
  and "any attributes that are sometimes used to specify partialness, such as
  start_range or end_range, will be ignored" — i.e. at least one consumer
  reads no marker at all from GFF3 input.
- **Q20 practice.** NCBI's *Eukaryotic Genome Annotation Guide* (verified
  2026-11-11, stamped "Last updated 2025-03-21"): "Note that this qualifier
  [/pseudo] does NOT mean that the gene is a pseudogene"; true pseudogenes take
  `/pseudogene <TYPE>` from the INSDC qualifier vocabulary — an attribute
  route, while the pinned SO release offers the typed route quoted above.
- **Q13/SOFA demand.** Ensembl's GFF3 upload format page (verified 2026-11-11
  from the June 2026 archive, release 116) requires column 3 to be "a term or
  accession from the **SOFA** sequence ontology" — a live repository already
  pins the narrower subset, relevant to SO-009's policy.
- **Q15 precedent.** The Perl validator's disabled checks and GenomeTools'
  behaviour are summarised in the rules' notes; SO-006's `member_of`
  extension is documented in `ontology.py` with the `gene_member_region`
  argument so a reviewer can retrace the inference.

## The exact asks, ready to route (not sent)

If and when the maintainers authorize it, the #19 slice of the exchange is —
in order:

1. Q13: confirm the artefact and data-version-as-release, the SOFA note
   policy, and the treatment of stale `##feature-ontology` URIs.
2. Q14: confirm exact label/accession matching, the synonym/case-variant
   level, and is_a-only under `sequence_feature`.
3. Q15: enumerate the relations (and inferences) that make a Parent allowed,
   and confirm the severity against the specification's "parse exception"
   sentence — including whether `gene_member_region member_of gene` is the
   intended transcript-to-gene route.
4. Q16: state whether `Derives_from` should be type-checked at all.
5. Q19: name the GFF3 partiality marker, its per-segment rules, and whether
   `start`/`end` are 5'/3' or genomic.
6. Q20: confirm the typed (SO) route or the attribute route for pseudo
   parents, the intended transitive Parent chain, and whether
   `pseudogenic_CDS` must always sit under a `pseudogenic_transcript`.

Each answer lands as a dated note on the affected rules plus a resolution
entry in [questions-for-SO.md](../questions-for-SO.md); severities and
statuses move only through the catalogue's normal rendered workflow.

Companion packets: [catalogue-review.md](catalogue-review.md) (#18) and
[repository-profiles.md](repository-profiles.md) (#20).
