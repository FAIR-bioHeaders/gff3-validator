# Questions for the Sequence Ontology group

Draft for the catalogue review
([FHR-Specification #62](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/62)).
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

14. **Matching types.** Exact label only, or also EXACT synonyms and case
    variants (the specification's NOTE 1 writes `cds`)? Only is_a descendants
    of sequence_feature? ([SO-001](rules.md#so-001), [SO-003](rules.md#so-003),
    [SO-005](rules.md#so-005))

   **SO expertise.** Proposed: match the exact label or SO accession, case-sensitive; an EXACT synonym or case variant is a warning that suggests the canonical label; column 3 must be an is_a descendant of sequence_feature (warning until confirmed).

15. **Parent and part_of.** The specification says a Parent that is not an SO
    part-of relationship "should trigger a parse exception". Which relations
    and inferences define "allowed" (part_of, member_of, has_part inverses,
    is_a inheritance, transitivity as in NOTE 2)? ([SO-006](rules.md#so-006))

   **SO expertise.** Proposed: a Parent is allowed when the child is part_of the parent, including via is_a inheritance and transitive part_of; anything else is a warning until SO settles the relation set.

16. **Derives_from typing.** Should Derives_from be type-checked at all? The
    specification's examples (CDS derives from gene) may not follow SO
    derives_from. ([SO-007](rules.md#so-007))

   **SO expertise.** Proposed: do not type-check Derives_from for now (an informational note at most).


## Biology (optional checks)

17. **Partial and exceptional CDS.** How should a partial CDS, a programmed
    frameshift, selenocysteine or stop-codon readthrough be marked, so phase,
    start, stop and internal-stop checks can exempt them?
    ([BIO-004](rules.md#bio-004) to [BIO-008](rules.md#bio-008))
    For translation exceptions the SO/NCBI discussion in
    [SO-Ontologies#658](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/658)
    converges on a `recoded_codon` (SO:0000145) feature, or a subtype such as
    `stop_codon_redefined_as_selenocysteine` (SO:0000885), that is a child
    (`Parent=`) of the CDS and carries `recoded_amino_acid=<amino acid name>`
    (`amino_acid` for other or unknown), split over several lines with one ID
    when the codon spans a splice junction. The validator already exempts
    codons covered by such features (and, as a fallback, NCBI's
    `transl_except` attribute on the CDS), pending SO confirmation. Partial
    CDS and frameshifts remain open: `partial`, `start_range` and `end_range`
    are not honoured, so these rules stay warnings.
18. **Strand within a gene.** Without the SO layer the validator compares the
    strand of every child with its Parent (when both are `+` or `-`). Should
    this be limited to gene parts, and how should trans-splicing be marked?
    ([BIO-010](rules.md#bio-010))

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
- The accession pattern is written `SO:000000` (six digits).
  ([SO-002](rules.md#so-002))
- Dead links: SourceForge SO release URIs, the GO.xrf_abbs FTP registry, and
  the "GFF3 Validator" section points to modENCODE-DCC/validator
  (last changed 2012). Spec 009 SC-004 proposes pointing it to this
  validator once SO endorses it.
