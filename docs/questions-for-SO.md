# Questions for the Sequence Ontology group

Draft for the catalogue review
([FAIR-bioHeaders-Specification #62](https://github.com/FAIR-bioHeaders/FAIR-bioHeaders-Specification/issues/62)).
Each question is a place where the GFF3 specification 1.26 (commit
[fe73505](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md))
is silent, ambiguous or contradicts itself. Every question ends with **our
proposed answer**, so a reply of "agree" is enough wherever you do. The rule ids
link to [rules.md](rules.md), where each rule's `notes` give the detail. Until SO
answers, these rules stay at the level shown in the catalogue and none counts as
SO-endorsed; implemented rules report only what the specification text settles.

Each question is marked with what we need:

- **Confirm**: the specification or common sense points to one answer; please
  confirm or correct it.
- **Choose**: several answers are defensible; we need SO to pick one so that all
  tools agree.
- **SO expertise**: needs ontology knowledge only SO can supply.

| # | Topic | Kind |
| --- | --- | --- |
| 1 | Version line | Confirm |
| 2 | Line endings | Choose |
| 3 | Escaping | Confirm |
| 4 | Empty values and separators | Choose |
| 5 | Multiple values | Choose |
| 6 | Phase | Choose |
| 7 | Score | Confirm |
| 8 | Discontinuous features | Confirm |
| 9 | `###` | Choose |
| 10 | `##sequence-region` | Choose |
| 11 | Containment and seqids | Choose |
| 12 | Derives_from cycles | Confirm |
| 13 | SO release and artefact | Confirm (release); SO expertise (artefact) |
| 14 | Matching types | SO expertise |
| 15 | Parent and part_of | SO expertise |
| 16 | Derives_from typing | SO expertise |
| 17 | Partial and exceptional CDS | Choose |
| 18 | Strand within a gene | Choose |
| 19 | Partiality of a feature in GFF3 | Choose |
| 20 | Pseudo parents | Choose; SO expertise |

## Decisions on the core format

1. **Version line.** Is `##gff-version 3` the canonical form, and is
   `3.1.26` (as in the specification's examples) a version producers should
   write? Should the revision numbers be checked? ([GFF-SYN-001](rules.md#gff-syn-001))

   **Confirm.** Proposed: accept `3`, `3.N` and `3.N.N`; producers may write either `3` or the full version; revision numbers are not checked.

2. **Line endings.** Are CRLF files invalid (the CR is an unescaped control
   character)? ([GFF-SYN-005](rules.md#gff-syn-005))

   **Choose.** Proposed: accept CRLF files with one warning per file, since many real files have them and the content is unambiguous.

3. **Escaping.** The text says "no other characters may be encoded", but
   seqids "must escape" characters outside `[a-zA-Z0-9.:^*$@!+_?-|]`, and
   Target ids escape spaces. Is over-encoding an error, a warning or allowed?
   Is the seqid set read literally (`?`, `-`, `|` as characters)? Must an
   escaped seqid match the escaped or the decoded FASTA id?
   ([GFF-SYN-009](rules.md#gff-syn-009), [GFF-SYN-010](rules.md#gff-syn-010))

   **Confirm.** Proposed: decode any valid `%XX` everywhere; over-encoding is a warning, not an error; read the seqid set literally; compare seqids with FASTA ids after decoding.

4. **Empty values and separators.** Is `Note=` valid? Are `;;` and a trailing
   `;` valid (the circular-genome example ends with `;`)?
   ([GFF-ATT-002](rules.md#gff-att-002), [GFF-ATT-003](rules.md#gff-att-003))

   **Choose.** Proposed: an empty value (`Note=`) is a warning; `;;` and a trailing `;` are allowed.

5. **Multiple values.** Derives_from is not in the multi-valued list (1.19):
   is `Derives_from=g1,g2` allowed? In lower-case application tags, is a
   comma a separator or text? ([GFF-ATT-006](rules.md#gff-att-006))

   **Choose.** Proposed: comma separates multiple values for every tag, including Derives_from and lower-case application tags, as the general attribute rule says; a literal comma must be encoded as `%2C`.

6. **Phase.** Is a phase on non-CDS features (for example GTF-style
   start_codon) an error, a warning or allowed? Does "phase is required for
   CDS" cover SO subtypes of CDS? ([GFF-SYN-019](rules.md#gff-syn-019),
   [GFF-SYN-020](rules.md#gff-syn-020))

   **Choose.** Proposed: phase is required on CDS and its SO subtypes; a phase on other features is a warning.

   *Implemented as proposed* (GFF-SYN-019 for CDS and its is_a subtypes; GFF-SYN-020 as a warning).

7. **Score.** Which number syntax is "floating point" (exponents yes; `nan`,
   `inf`, hexadecimal no)? ([GFF-SYN-016](rules.md#gff-syn-016))

   **Confirm.** Proposed: decimal numbers with an optional exponent; `nan`, `inf` and hexadecimal are errors.


## Structure

8. **Discontinuous features.** What must lines sharing an ID have in common
   (type, seqid, strand, Parent)? Are IDs compared after percent-decoding?
   ([GFF-STR-001](rules.md#gff-str-001) to [GFF-STR-003](rules.md#gff-str-003))

   **Confirm.** Proposed: same type required (error); different seqid, strand or Parent is a warning; IDs compared after percent-decoding.

9. **`###`.** After `###`, may a line still name an earlier ID as Parent, or
   continue an earlier discontinuous feature? Error or warning?
   ([GFF-DIR-003](rules.md#gff-dir-003))

   **Choose.** Proposed: after `###`, a reference to an earlier ID, or a continuation of an earlier discontinuous feature, is a warning.

10. **`##sequence-region`.** Must start be 1? Must the directive precede the
    features on that seqid? For a circular landmark, is the bound 2 x length?
    ([GFF-DIR-001](rules.md#gff-dir-001), [GFF-STR-008](rules.md#gff-str-008))

   **Choose.** Proposed: start need not be 1 (no finding); the directive should precede that seqid's features (warning); for a circular landmark, features may extend past the end by wrapping (bound: start within 1..length).

11. **Containment and seqids.** The specification does not require a child to
    lie within its parent. Can SO name the types where containment is
    expected (exon in transcript), so we warn only there? May a parent and
    child be on different seqids? ([GFF-STR-012](rules.md#gff-str-012),
    [GFF-STR-013](rules.md#gff-str-013))

   **Choose.** Proposed: a parent and child on different seqids is an error; containment is warned about only for the types SO names (for example exon in transcript).

12. **Derives_from cycles** are not mentioned; should they be errors?
    ([GFF-STR-007](rules.md#gff-str-007))

   **Confirm.** Proposed: a Derives_from cycle is an error.


## Sequence Ontology

13. **Which release.** Which SO artefact should be pinned (so.obo, the
    SO-Ontologies release tag, a PURL with version)? The current candidate is so.obo
    data-version 2026-08-07. How should a file whose `##feature-ontology`
    names an old (now unreachable SourceForge) release be validated?
    ([GFF-DIR-009](rules.md#gff-dir-009))

   **Confirm (release), SO expertise (artefact).** Proposed: each validator release bundles the latest SO release, every report states which release it used, CI opens an update when SO publishes a new one, and `--so` selects another release. Which artefact: full SO (`so.obo`), with a warning for terms outside SOFA, the annotation subset that GFF3 historically referenced? A file whose `##feature-ontology` names an old release is validated against the bundled release, with an informational note.

   *Implemented as proposed*: so.obo data-version 2026-08-07 is bundled, full SO
   with a note (SO-009, info) for terms outside SOFA. SO has published no GitHub
   release since v3.1 (2018), so the "release" is the so.obo data-version.

14. **Matching types.** Exact label only, or also EXACT synonyms and case
    variants (the specification's NOTE 1 writes `cds`)? Only is_a descendants
    of sequence_feature? ([SO-001](rules.md#so-001), [SO-003](rules.md#so-003),
    [SO-005](rules.md#so-005))

   **SO expertise.** Proposed: match the exact label or SO accession, case-sensitive; an EXACT synonym or case variant is a warning that suggests the canonical label; column 3 must be an is_a descendant of sequence_feature (warning until confirmed).

   *Implemented as proposed*, with one level choice: a type that matches no label,
   accession or synonym (SO-001) is a warning, not an error, until SO answers,
   because the specification does not name a release and terms are renamed
   (`lnc_RNA`, used by NCBI and Ensembl, is now `lncRNA` and not a synonym).

15. **Parent and part_of.** The specification says a Parent that is not an SO
    part-of relationship "should trigger a parse exception". Which relations
    and inferences define "allowed" (part_of, member_of, has_part inverses,
    is_a inheritance, transitivity as in NOTE 2)? ([SO-006](rules.md#so-006))

   **SO expertise.** Proposed: a Parent is allowed when the child is part_of the parent, including via is_a inheritance and transitive part_of; anything else is a warning until SO settles the relation set.

   *Implemented as proposed*, also following member_of: SO relates transcripts to
   genes only through `gene_member_region member_of gene`, so with part_of alone
   the canonical gene's `mRNA Parent=gene` would be reported. Is that the
   intended relation?

16. **Derives_from typing.** Should Derives_from be type-checked at all? The
    specification's examples (CDS derives from gene) may not follow SO
    derives_from. ([SO-007](rules.md#so-007))

   **SO expertise.** Proposed: do not type-check Derives_from for now (an informational note at most).

   *Implemented as proposed*: not checked; reports list SO-007 as not checked.


## Biology (optional checks)

17. **Partial and exceptional CDS.** How should a partial CDS, a programmed
    frameshift, selenocysteine or stop-codon readthrough be marked, so phase,
    start, stop and internal-stop checks can exempt them?
    ([BIO-004](rules.md#bio-004) to [BIO-008](rules.md#bio-008))

   **Choose.** GFF3 defines no standard marker. Proposed: for translation
   exceptions, follow the convention SO and NCBI are converging on in
   [SO-Ontologies#658](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/658):
   a `recoded_codon` (SO:0000145) child of the CDS, or a subtype such as
   `stop_codon_redefined_as_selenocysteine`, with a `recoded_amino_acid=`
   attribute. The codon may be split across a splice junction as lines sharing
   one ID. The legacy `transl_except` attribute is honoured as a fallback. For
   partial CDS, follow INSDC, which will use `partial=start`, `partial=end` and
   `partial=start,end` instead of the GVF-derived `start_range`/`end_range`
   ([Terence Murphy, SO-Ontologies#685](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/685#issuecomment-6080389993));
   the legacy attributes and `partial=true` are still honoured. Open: on the
   minus strand, are `start` and `end` genomic or 5'/3'? The validator exempts
   both ends there until the INSDC draft settles it. Is this the convention SO
   will recommend?

18. **Strand within a gene.** Without the SO layer the validator compares the
    strand of every child with its Parent (when both are `+` or `-`). Should
    this be limited to gene parts, and how should trans-splicing be marked?
    ([BIO-010](rules.md#bio-010))

   **Choose.** Proposed: once the SO layer exists, check strand only along
   part_of chains (gene → transcript → exon/CDS); until then, every Parent edge
   is checked, as a warning. Exempt features marked `exception=trans-splicing`,
   mirroring the INSDC `/exception="trans-splicing"` qualifier. Is there a
   better marker?

   *Implemented as proposed* for the part_of restriction (the edges SO-006
   accepts); the trans-splicing exemption is not implemented yet.

## What a repository requires but GFF3 cannot yet say

Added while placing the INSDC Annotation Minimum Specification v1.0 rules
([#27](https://github.com/FAIR-bioHeaders/gff3-validator/issues/27), evidence in
[insdc-rule-placement.md](insdc-rule-placement.md)). Both questions cite that
document at insdc/minimum-specifcations commit
[41f0dc4](https://github.com/insdc/minimum-specifcations/tree/41f0dc424748c9f7e50a8b6bda9b888218c4b65e/Annotations);
neither can be answered from the GFF3 1.26 text, and the answer decides whether
the check lands in the core catalogue or in a repository profile.

19. **Partiality of a feature in GFF3.** Question 17 settled how a *partial
   CDS* is marked so that the codon checks can exempt it. The INSDC Annotation
   Minimum Specification v1.0 now asks the harder half, for **every** feature
   type and about the marker's own semantics (rule b.iii.5, p. 1: "Only the
   start and/or end of a feature may be marked as partial. Internal interval
   boundaries must not be marked as partial, and the direction of partiality
   must only indicate the feature is longer, not shorter (i.e., `<100..>200`
   and not `>100..<200`)"; rule b.vi.4, p. 2: "Coding regions with a phase ≠ 0
   must be declared as partial"; rule c.i.1, p. 3, which requires a partial
   marker to abut an assembly gap or the sequence end). GFF3 1.26 defines no
   partiality marker of any kind, so there is nothing to validate until SO
   names one. ([BIO-006](rules.md#bio-006), draft profile `INSDC-016` in [insdc-rule-placement.md](insdc-rule-placement.md);
   profile rules `INSDC-001`, `INSDC-004`, `INSDC-005` and `INSDC-012` in
   [insdc-rule-placement.md](insdc-rule-placement.md))

   **Choose.** Proposed: the marker is the INSDC spelling of question 17 —
   `partial=start`, `partial=end`, `partial=start,end`, with the GVF-derived
   `start_range` and `end_range` read as legacy synonyms — and it (a) is
   allowed on any feature, not only a CDS, (b) may appear **only** on the
   segment a discontinuous feature opens or closes with in 5'-to-3' order, so
   an internal segment carrying it is a mistake, (c) always means "the real
   feature continues past this point", never "it is shorter here", and (d)
   `start` and `end` name the **5' and 3' ends of the feature** (so on a
   minus-strand feature `start` is the higher coordinate), which is the point
   question 17 left open and BIO-006 currently exempts both ends for. Confirm
   (a) to (d). If SO prefers a per-segment spelling over a feature-level one,
   say so: the validator reads what SO names, and both placements (core biology
   versus an INSDC profile rule under #20) follow from this answer.

20. **Pseudo parents.** INSDC Annotation Minimum Specification v1.0 b.vi.7
   (p. 2) says "Product or translation must not be provided for a coding region
   with any pseudo parent features". In GFF3 neither half is defined:
   `product`, `translation` and `pseudo` are not reserved attributes (a
   lower-case `product=` is an application tag, and an upper-case one is the
   unknown reserved tag of [GFF-ATT-007](rules.md#gff-att-007)), and
   [GFF-ATT-007](rules.md#gff-att-007) already lists NCBI's `Is_pseudo` as an
   open practice. The pinned SO release offers a typed route: `pseudogene`
   (SO:0000336), `pseudogenic_transcript` (SO:0000516, part_of `pseudogene`)
   and `pseudogenic_CDS` (SO:0002087, part_of `pseudogenic_transcript`), each
   carrying the synonym `INSDC_qualifier:pseudo`.
   ([SO-001](rules.md#so-001), [SO-006](rules.md#so-006); INSDC profile rule
   `INSDC-007` in [insdc-rule-placement.md](insdc-rule-placement.md))

   **Choose, with SO expertise.** Proposed: the *type* states pseudogene
   status — a `pseudogene`, `pseudogenic_transcript` or `pseudogenic_CDS` (or
   an is_a subtype of one) in column 3 — and a `pseudo=` attribute is read as a
   legacy synonym, not as the canonical form. On that reading please confirm
   three things: (i) a feature whose Parent chain reaches a pseudogene-typed
   ancestor is "a coding region with a pseudo parent", so the check follows
   Parent transitively (gene → mRNA → CDS) rather than only the direct Parent;
   (ii) an mRNA or CDS that is part of a pseudogene is a legitimate GFF3
   relationship under SO-006 (is `pseudogenic_CDS part_of pseudogene` the
   intended chain, or must a pseudogenic transcript sit between them?); and
   (iii) if a pseudogene has no CDS child at all, that is the expected shape —
   i.e. the annotation should carry the pseudogene and its pseudogenic parts,
   not an ordinary CDS under it. ENA's gff3tools 5.5.1 recognises `pseudo` and
   `pseudogene` attributes in its CDS-translation and intron-exemption checks,
   so an attribute-only answer is also workable; the validator will follow
   whichever SO names, and no rule leaves `planned` before this answer.

## Suggested corrections to the specification text

Found while drafting; each makes users copy invalid GFF3.

- The `##FASTA` example writes `Target=cdna0123+12+462` ("+" for space,
  which the text forbids). ([GFF-ATT-010](rules.md#gff-att-010))
- The single-exon and polycistronic examples have CDS lines with phase `.`
  and use `name=` for Name. ([GFF-SYN-019](rules.md#gff-syn-019),
  [GFF-ATT-008](rules.md#gff-att-008))
- In the canonical gene, cds00001 and cds00002 have 2305 and 1402 coding
  bases, one more than a whole number of codons (their last segment, 7000 to
  7600, is one base longer than the frame needs), while cds00003 and cds00004
  end on a codon boundary at 7600. ([BIO-009](rules.md#bio-009))
- Dbxref and Ontology_term examples are quoted. ([GFF-ATT-009](rules.md#gff-att-009))
- The Gap examples use the type `nucleotide_to_protein_match`, which is not an
  SO term, and the programmed frameshift example's `Ontology_term=SO:1000069`
  is obsolete in so.obo data-version 2026-08-07. ([SO-001](rules.md#so-001),
  [SO-008](rules.md#so-008))
- The accession pattern is written `SO:000000` (six digits).
  ([SO-002](rules.md#so-002))
- Dead links: SourceForge SO release URIs, the GO.xrf_abbs FTP registry, and
  the "GFF3 Validator" section points to modENCODE-DCC/validator
  (last changed 2012). Spec 009 SC-004 proposes pointing it to this
  validator once SO endorses it.
