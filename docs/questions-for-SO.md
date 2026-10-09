# Questions for the Sequence Ontology group

Draft for the catalogue review
([FHR-Specification #62](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/62)).
Each question is a place where the GFF3 specification 1.26 (commit
[fe73505](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md))
is silent, ambiguous or contradicts itself. The rule ids link to
[rules.md](rules.md), where each rule's `notes` give the detail and our
proposal. 45 of the 88 draft rules are marked "needs SO input". Until SO
answers, these rules stay at the level shown in the catalogue, and none
counts as SO-endorsed.

## Decisions on the core format

1. **Version line.** Is `##gff-version 3` the canonical form, and is
   `3.1.26` (as in the specification's examples) a version producers should
   write? Should the revision numbers be checked? Proposal: accept `3`,
   `3.N`, `3.N.N`. ([GFF-SYN-001](rules.md#gff-syn-001))
2. **Line endings.** Are CRLF files invalid (the CR is an unescaped control
   character)? Proposal: one error per file. ([GFF-SYN-005](rules.md#gff-syn-005))
3. **Escaping.** The text says "no other characters may be encoded", but
   seqids "must escape" characters outside `[a-zA-Z0-9.:^*$@!+_?-|]`, and
   Target ids escape spaces. Is over-encoding an error, a warning or allowed?
   Is the seqid set read literally (`?`, `-`, `|` as characters)? Must an
   escaped seqid match the escaped or the decoded FASTA id?
   ([GFF-SYN-009](rules.md#gff-syn-009), [GFF-SYN-010](rules.md#gff-syn-010))
4. **Empty values and separators.** Is `Note=` valid? Are `;;` and a trailing
   `;` valid (the circular-genome example ends with `;`)?
   ([GFF-ATT-002](rules.md#gff-att-002), [GFF-ATT-003](rules.md#gff-att-003))
5. **Multiple values.** Derives_from is not in the multi-valued list (1.19):
   is `Derives_from=g1,g2` allowed? In lower-case application tags, is a
   comma a separator or text? ([GFF-ATT-006](rules.md#gff-att-006))
6. **Phase.** Is a phase on non-CDS features (for example GTF-style
   start_codon) an error, a warning or allowed? Does "phase is required for
   CDS" cover SO subtypes of CDS? ([GFF-SYN-019](rules.md#gff-syn-019),
   [GFF-SYN-020](rules.md#gff-syn-020))
7. **Score.** Which number syntax is "floating point" (exponents yes; `nan`,
   `inf`, hexadecimal no)? ([GFF-SYN-016](rules.md#gff-syn-016))

## Structure

8. **Discontinuous features.** What must lines sharing an ID have in common?
   Proposal: same type is required (error); different seqid, strand or Parent
   is a warning. Are IDs compared after percent-decoding?
   ([GFF-STR-001](rules.md#gff-str-001) to [GFF-STR-003](rules.md#gff-str-003))
9. **`###`.** After `###`, may a line still name an earlier ID as Parent, or
   continue an earlier discontinuous feature? Error or warning?
   ([GFF-DIR-003](rules.md#gff-dir-003))
10. **`##sequence-region`.** Must start be 1? Must the directive precede the
    features on that seqid? For a circular landmark, is the bound 2 x length?
    ([GFF-DIR-001](rules.md#gff-dir-001), [GFF-STR-008](rules.md#gff-str-008))
11. **Containment and seqids.** The specification does not require a child to
    lie within its parent. Can SO name the types where containment is
    expected (exon in transcript), so we warn only there? May a parent and
    child be on different seqids? ([GFF-STR-012](rules.md#gff-str-012),
    [GFF-STR-013](rules.md#gff-str-013))
12. **Derives_from cycles** are not mentioned; should they be errors?
    ([GFF-STR-007](rules.md#gff-str-007))

## Sequence Ontology

13. **Which release.** Which SO artefact should be pinned (so.obo, the
    SO-Ontologies release tag, a PURL with version)? The candidate is so.obo
    data-version 2026-08-07. How should a file whose `##feature-ontology`
    names an old (now unreachable SourceForge) release be validated?
    ([GFF-DIR-009](rules.md#gff-dir-009))
14. **Matching types.** Exact label only, or also EXACT synonyms and case
    variants (the specification's NOTE 1 writes `cds`)? Only is_a descendants
    of sequence_feature? ([SO-001](rules.md#so-001), [SO-003](rules.md#so-003),
    [SO-005](rules.md#so-005))
15. **Parent and part_of.** The specification says a Parent that is not an SO
    part-of relationship "should trigger a parse exception". Which relations
    and inferences define "allowed" (part_of, member_of, has_part inverses,
    is_a inheritance, transitivity as in NOTE 2)? We propose a warning until
    this is settled. ([SO-006](rules.md#so-006))
16. **Derives_from typing.** Should Derives_from be type-checked at all? The
    specification's examples (CDS derives from gene) may not follow SO
    derives_from. ([SO-007](rules.md#so-007))

## Biology (optional checks)

17. **Partial and exceptional CDS.** How should a partial CDS, a programmed
    frameshift, selenocysteine or stop-codon readthrough be marked, so phase,
    start, stop and internal-stop checks can exempt them?
    ([BIO-004](rules.md#bio-004) to [BIO-008](rules.md#bio-008))

## Suggested corrections to the specification text

Found while drafting; each makes users copy invalid GFF3.

- The `##FASTA` example writes `Target=cdna0123+12+462` ("+" for space,
  which the text forbids). ([GFF-ATT-010](rules.md#gff-att-010))
- The single-exon and polycistronic examples have CDS lines with phase `.`
  and use `name=` for Name. ([GFF-SYN-019](rules.md#gff-syn-019),
  [GFF-ATT-008](rules.md#gff-att-008))
- Dbxref and Ontology_term examples are quoted. ([GFF-ATT-009](rules.md#gff-att-009))
- The accession pattern is written `SO:000000` (six digits).
  ([SO-002](rules.md#so-002))
- Dead links: SourceForge SO release URIs, the GO.xrf_abbs FTP registry, and
  the "GFF3 Validator" section points to modENCODE-DCC/validator
  (last changed 2012). Spec 009 SC-004 proposes pointing it to this
  validator once SO endorses it.
