# AgBioData GFF3 recommendations profile (`agbiodata`)

<!-- Generated from profiles/agbiodata.yaml by scripts/render_rules.py; do not edit. -->

**Profile version 0.1.0-draft; not reviewed by the AgBioData GFF3 working group.** Use it with `gff3-validate --profile agbiodata`. See [profiles.md](../profiles.md) for how profiles work and how they are reported.

Recommendations of the AgBioData GFF3 working group (AgBioData, the Alliance of Genome Resources and NCBI) for producing GFF3 that databases and tools can use without reformatting. They follow GFF3 1.26 "with emphases and additions"; this profile checks the additions that software can check, on top of the core rules.

- Source: [AgBioData GFF3 working group recommendations (Recommendations.md)](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md)
- License of the source: CC0-1.0
- Version of the source: commit 32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8, 2021-12-29
- Rule ids: `AGB-NNN`

Profile findings are reported apart from the core findings and never change whether a file is valid GFF3. A file complies with the profile when it is valid GFF3 and has no profile errors.

## Summary

| Id | Level | Status | Title |
|---|---|---|---|
| [AGB-001](#agb-001) | warning | implemented | Ontology_term is avoided |
| [AGB-002](#agb-002) | warning | implemented | GO terms are not given in Dbxref or Ontology_term |
| [AGB-003](#agb-003) | warning | implemented | Child features lie within their parent |
| [AGB-004](#agb-004) | info | implemented | Child features are listed after their parent |
| [AGB-005](#agb-005) | info | implemented | One Parent per feature |
| [AGB-006](#agb-006) | info | implemented | No polypeptide features |
| [AGB-007](#agb-007) | warning | implemented | CDS and exon features have a Parent |
| [AGB-008](#agb-008) | warning | implemented | so_term_name names a subtype of the feature's type |
| [AGB-009](#agb-009) | error | implemented | Target fields are single-space delimited and target_id is a seqid |
| [AGB-010](#agb-010) | info | implemented | Ontology directives use OBO PURLs |
| [AGB-011](#agb-011) | info | implemented | ##species is an NCBITaxon CURIE |
| [AGB-012](#agb-012) | warning | implemented | ##Score directive has name, min, max and best |
| [AGB-013](#agb-013) | warning | implemented | seqid does not list several sequences |

## Core rules with a raised level

The core finding keeps its catalogue level; the profile reports it again at the raised level.

| Rule | Catalogue level | Profile level | Source | Reason |
|---|---|---|---|---|
| [SO-001](../rules.md#so-001) | warning | error | [Type (column 3), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#type) | "Must be a valid SO term or SO accession number." The core rule is a warning until SO answers question 14. Case variants and EXACT synonyms (SO-005) name a valid term and stay warnings. |
| [BIO-008](../rules.md#bio-008) | warning | error | [Phase (column 8), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#phase) | "If no CDS/protein fasta is available: Check for internal stops in the protein sequence - validation fails if stops are present." Needs --genome; stops covered by a recoded_codon child or a transl_except attribute (the NCBI convention the same section recommends) are exempt, as in the core rule. |

## Rules

### AGB-001

**Ontology_term is avoided**

- Level: warning; status: implemented
- Reference: [Attributes : Ontology_term, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--ontology_term)

The working group advises against Ontology_term and against functional annotation in GFF3 in general (use GAF or GPAD); its validation entry asks the validator to warn when Ontology_term is used. Reported once, at the first line, with a count.

Example (not compliant):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Ontology_term=GO:0046703
```

Compliant:

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
```

Fix: Move the ontology annotations to a GAF or GPAD file, or to the complex metadata attributes described in the recommendations.

Notes: The same entry says the value "should be a CURIE that resolves into a published ontology term": the CURIE form is core GFF-ATT-014 and SO terms are checked by SO-008; other ontologies are not fetched.

### AGB-002

**GO terms are not given in Dbxref or Ontology_term**

- Level: warning; status: implemented
- Reference: [Attributes complex metadata / functional annotations, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes-complex-metadata--functional-annotations)

"These use of GO term or functional annotations should never be incorporated into gff within the Dbxref or Ontology_term fields." A Dbxref or Ontology_term value with the GO prefix is reported, once at the first line with a count.

Example (not compliant):

```text
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Dbxref=GO:0004381
```

Compliant:

```text
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Dbxref=MaizeGDB.locus:12098
```

Fix: Give GO annotations, with their evidence, in a GAF or GPAD file (or the go_annotations attribute) instead.

### AGB-003

**Child features lie within their parent**

- Level: warning; status: implemented
- Reference: [Modeling hierarchical relationships of a protein-coding gene, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene)

"Child coordinates that are not contained within parent coordinates often indicate an error and should trigger a warning in a gff3 validator." A feature whose start or end is outside the extent of a Parent (all lines of that ID read so far), or on another seqid, is reported.

Example (not compliant):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
ctg1→.→mRNA→1→120→.→+→.→ID=t1;Parent=g1
```

Compliant:

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Parent=g1
```

Fix: Correct the coordinates of the child or of the parent so the parent spans its children.

Notes: A child listed before its parent is compared with the parent at the end of the file (at most 100,000 such children are kept; beyond that the report says the check was partial). Parent extents cost 16 bytes per ID.

### AGB-004

**Child features are listed after their parent**

- Level: info; status: implemented
- Reference: [Modeling hierarchical relationships of a protein-coding gene, Best practices (sort order)](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene)

"Child features should be listed after parent features." A Parent that is defined only later in the file is reported, once at the first line with a count. Forward references are valid GFF3.

Example (not compliant):

```text
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Parent=g1
ctg1→.→gene→1→90→.→+→.→ID=g1
```

Compliant:

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Parent=g1
```

Fix: Sort the file so that each gene model is written top down, parents first.

### AGB-005

**One Parent per feature**

- Level: info; status: implemented
- Reference: [Modeling hierarchical relationships of a protein-coding gene, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene)

"Strongly encourage only one parent per feature. However, parsers and validators should still support multiple parents per feature." A feature with several Parent values is noted, once at the first line with a count.

Example (not compliant):

```text
ctg1→.→exon→1→90→.→+→.→ID=e1;Parent=t1,t2
```

Compliant:

```text
ctg1→.→exon→1→90→.→+→.→ID=e1;Parent=t1
```

Fix: Where the model allows it, give each feature one Parent (for example one exon line per transcript); multiple Parents remain valid.

### AGB-006

**No polypeptide features**

- Level: info; status: implemented
- Reference: [Attributes : Derives_from, Best practices; Modeling hierarchical relationships of a protein-coding gene](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--derives_from)

"Polypeptide features are not required or recommended", and "we recommend not specifying a polypeptide feature if you're modeling a typical protein-coding gene". A feature whose type is polypeptide or an SO is_a subtype of it is noted, once per type with a count.

Example (not compliant):

```text
ctg1→.→polypeptide→1→90→.→+→.→ID=p1;Derives_from=c1
```

Fix: Leave out polypeptide features from protein-coding gene models; the CDS implies the protein.

### AGB-007

**CDS and exon features have a Parent**

- Level: warning; status: implemented
- Reference: [Modeling hierarchical relationships of a protein-coding gene, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene)

"Entries that are non-parent entries should have a valid parent entry via the ID." In the protein-coding gene model the section describes, the entries that are not parents are the CDS and exon features, so a CDS or exon (or an SO is_a subtype) without a Parent is reported, once at the first line with a count.

Example (not compliant):

```text
ctg1→.→exon→1→90→.→+→.→ID=e1
```

Compliant:

```text
ctg1→.→exon→1→90→.→+→.→ID=e1;Parent=t1
```

Fix: Give the exon or CDS the ID of its transcript in Parent.

Notes: Read narrowly: the document does not list which types are "non-parent entries"; other leaf features (for example a SNP or a match_part) are not checked. A Parent that does not resolve is core GFF-STR-004.

### AGB-008

**so_term_name names a subtype of the feature's type**

- Level: warning; status: implemented
- Reference: [Type (column 3), Best practice](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#type)

"Optionally, include a so_term_name attribute in column 9 to specify the child (type) of gene - e.g. protein_coding_gene, ncRNA_gene". When so_term_name is present, its value is an SO term label or accession that is the column 3 term or an is_a subtype of it.

Example (not compliant):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;so_term_name=mRNA
```

Compliant:

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;so_term_name=protein_coding_gene
```

Fix: Give the SO label of the specific kind of gene (for example protein_coding_gene), or leave so_term_name out.

Notes: Not checked when column 3 is not an SO term (SO-001 reports that).

### AGB-009

**Target fields are single-space delimited and target_id is a seqid**

- Level: error; status: implemented
- Reference: [Attributes : Target, Gap, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--target-gap)

"The components of the encoded attribute must be single-space delimited and must consist of not less than 3 and not more than 4 fields. Field 1 must conform to the same syntax and semantics as specified for Column 1 (seqid)." The field count, coordinates and strand are core GFF-ATT-010; this rule adds single spaces (no leading, trailing or repeated spaces) and the seqid character set for target_id (characters outside [a-zA-Z0-9.:^*$@!+_?-|] percent-encoded).

Example (not compliant):

```text
ctg1→blastn→match_part→1→90→.→+→.→ID=m1;Target=EST#23  1 90 +
```

Compliant:

```text
ctg1→blastn→match_part→1→90→.→+→.→ID=m1;Target=EST23 1 90 +
```

Fix: Separate the Target fields by one space each and percent-encode characters of the target_id outside the seqid set (for example "#" as %23).

Notes: Checked only when the Target passes GFF-ATT-010.

### AGB-010

**Ontology directives use OBO PURLs**

- Level: info; status: implemented
- Reference: [Pragmas, Ontology URIs](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#pragmas)

Ontology URIs in directives such as ##feature-ontology "can be specified via cv URLs ... These URLs should be avoided. Instead, we recommend using the official OBO version IRI PURLs, for example http://purl.obolibrary.org/obo/so.obo." A ##feature-ontology, ##attribute-ontology or ##source-ontology URI that is not under purl.obolibrary.org/obo/ is noted.

Example (not compliant):

```text
##feature-ontology http://song.cvs.sourceforge.net/*checkout*/song/ontology/sofa.obo?revision=1.6
```

Compliant:

```text
##feature-ontology http://purl.obolibrary.org/obo/so.obo
```

Fix: Use the OBO PURL of the ontology, for example http://purl.obolibrary.org/obo/so.obo.

### AGB-011

**##species is an NCBITaxon CURIE**

- Level: info; status: implemented
- Reference: [Pragmas, Species](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#pragmas)

"The current specification recommends using NCBI URLs to specify the species ... in the ##species pragma. We recommend using an OBO CURIE, instead. Example: ##species NCBITaxon:9606". A ##species value that is not NCBITaxon: followed by digits is noted.

Example (not compliant):

```text
##species https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606
```

Compliant:

```text
##species NCBITaxon:9606
```

Fix: Write the taxon as an OBO CURIE, for example "##species NCBITaxon:9606".

Notes: This conflicts with GFF3 1.26, which prefers the NCBI Taxonomy URL (core warning GFF-DIR-007): either form gets one of the two findings. The profile does not lower core rules.

### AGB-012

**##Score directive has name, min, max and best**

- Level: warning; status: implemented
- Reference: [Score (column 6), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#score)

"Optionally, there is a ##score pragma in the following format: ##Score name="[name/calculated-by]";min=[min-value]; max=[max-val];best=[lower/higher]". When the directive is present (any letter case), it has the four semicolon-separated keys, min and max are numbers and best is lower or higher. Spaces around the pairs are allowed, as in the document's example.

Example (not compliant):

```text
##Score name="AED";best=low
```

Compliant:

```text
##Score name="AED (Annotation Edit Distance) score"; min=0;max=1;best=lower
```

Fix: Write the directive as ##Score name="...";min=N;max=N;best=lower (or higher).

Notes: The core rules note ##Score as a directive GFF3 does not define (GFF-DIR-010).

### AGB-013

**seqid does not list several sequences**

- Level: warning; status: implemented
- Reference: [Modeling hierarchical relationships of a protein-coding gene, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene)

"Do not list multiple values in column 1 (for features split across scaffolds)". A seqid with an unescaped comma is reported.

Example (not compliant):

```text
scaffold1,scaffold2→.→gene→1→90→.→+→.→ID=g1
```

Compliant:

```text
scaffold1→.→gene→1→90→.→+→.→ID=g1
```

Fix: Write one line per sequence, with the same ID on each line of the split feature.

Notes: A comma is outside the GFF3 seqid character set, which the core rules do not check yet (GFF-SYN-010, question 3).

## Guidance, not checked by profile rules

| Source | Recommendation | Covered by | Why no profile rule |
|---|---|---|---|
| [Seqid (column 1), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#seqid) | An optional ##alias-table directive gives a resolvable URL of the GenBank alias table, or starts an inline alias table. | nothing | The validator makes no network requests, so it cannot check that the link is active; the document says the inline table is not validated. |
| [Source (column 2), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#source) | Use "." when there is no source; follow the GFF3 encoding rules; separate several sources by a literal comma, not %2C; name the tool, method or database and its version. | [GFF-SYN-004](../rules.md#gff-syn-004), [GFF-SYN-005](../rules.md#gff-syn-005), [GFF-SYN-008](../rules.md#gff-syn-008), [GFF-SYN-009](../rules.md#gff-syn-009) | The encoding rules, including %2C in column 2, are core rules. Whether a source names a tool and version, and the optional ##Source directive (given in two different forms in the document), cannot be checked. |
| [Type (column 3), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#type) | All child rows should use a type within the hierarchy of the parent; the SO is fetched from sofa.obo by default. | [SO-006](../rules.md#so-006), [SO-009](../rules.md#so-009) | SO-006 checks child and parent types against SO part_of at its core level. The validator never fetches the ontology; it uses the bundled SO release and notes types outside SOFA (SO-009). Which transcript type is "appropriate" cannot be checked. |
| [Start, End (columns 4 and 5), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#start-end) | start and end are 1-based, start is at most end, zero-length and one-base features have start = end, and Is_circular=true allows end beyond the sequence. | [GFF-SYN-013](../rules.md#gff-syn-013), [GFF-SYN-014](../rules.md#gff-syn-014), [GFF-SYN-015](../rules.md#gff-syn-015), [GFF-ATT-016](../rules.md#gff-att-016), [GFF-STR-008](../rules.md#gff-str-008) | Core rules. |
| [Score (column 6), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#score) | A score is a floating point number or "."; describe the score in a ##Score directive, using EDAM where possible. | [GFF-SYN-016](../rules.md#gff-syn-016), [AGB-012](#agb-012) | The number format is a core rule and the directive format is AGB-012; whether the description uses EDAM cannot be checked. |
| [Strand (column 7), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#strand) | Strand is +, -, . or ?. | [GFF-SYN-017](../rules.md#gff-syn-017) | Core rule. |
| [Phase (column 8), Best practices and Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#phase) | Validate the phase; give non-standard translation tables per sequence in a phase directive; compare CDS and protein FASTA, when given, with the sequence derived from the GFF3. | [BIO-004](../rules.md#bio-004), [BIO-006](../rules.md#bio-006), [BIO-007](../rules.md#bio-007), [BIO-008](../rules.md#bio-008) | Phase consistency and codons are checked with --genome (BIO-008 raised to error). The phase directive is written two ways in the document (##phase SEQID TABLE and ##Translation-table TABLE SEQIDS) and per-sequence tables are not supported (use --translation-table); CDS and protein FASTA are not read. |
| [Attributes : ID, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--id) | Validate only that IDs are unique in the file, except for discontinuous features; keep persistent identifiers in other attributes (gene_id, transcript_id, protein_id, feature_id, or Dbxref). | [GFF-STR-001](../rules.md#gff-str-001) | Uniqueness is a core rule. The document limits validation to uniqueness, so the identifier attribute conventions are not checked. |
| [Attributes : Name, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--name) | Follow the nomenclature standards of your community; Name is not a unique identifier. | nothing | "No automated validation currently possible." |
| [Attributes : Alias, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--alias) | Alias is for alternative and historical names; avoid commas, tabs and pipes in alias names; values cannot include a semicolon. | [GFF-ATT-005](../rules.md#gff-att-005) | "The validator won't check Alias values." Unescaped semicolons are a core error. |
| [Attributes : Dbxref, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--dbxref) | A Dbxref refers to the same entity in a registered database and resolves to a URL that returns HTTP 200; it contains no semicolons. | [GFF-ATT-005](../rules.md#gff-att-005), [GFF-ATT-014](../rules.md#gff-att-014) | The DBTAG:ID form and escaping are core rules. Resolving URLs needs network requests, which the validator never makes, and whether a record is the same entity cannot be checked. |
| [Attributes : Derives_from, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--derives_from) | Avoid Derives_from between CDS and polypeptide by not modelling polypeptides. | [AGB-006](#agb-006) | "This needs more analysis and discussion." Polypeptide features are noted by AGB-006. |
| [Attributes : Note, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--note) | Note may not include a semicolon and may be repeated. | [GFF-ATT-004](../rules.md#gff-att-004), [GFF-ATT-005](../rules.md#gff-att-005) | Repeating the Note tag on one line (as in the document's example) is a GFF3 1.26 error, GFF-ATT-004; give several values separated by commas. The profile does not relax core rules. |
| [Attributes : Ontology_term, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--ontology_term) | Ontology_term values are CURIEs that resolve to published ontology terms. | [GFF-ATT-014](../rules.md#gff-att-014), [SO-008](../rules.md#so-008), [AGB-001](#agb-001) | The CURIE form is a core rule and SO terms are checked against the bundled release; other ontologies are not fetched. |
| [Attributes : Target, Gap, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--target-gap) | Prefer BAM or PAF to Target and Gap for alignments; target_id should be a sequence identifier usable in column 1. | [GFF-ATT-010](../rules.md#gff-att-010), [GFF-ATT-011](../rules.md#gff-att-011), [AGB-009](#agb-009) | The choice of format cannot be checked; the Target syntax is GFF-ATT-010 and AGB-009. |
| [Attributes complex metadata / functional annotations, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes-complex-metadata--functional-annotations) | go_annotations, gene_product and provenance values are lower-case, URL-encoded lists of rank and key=value annotations; GO annotations carry evidence codes. | [AGB-002](#agb-002) | Not checked. The separators are described inconsistently ("separated by a comma (url-encoded %3B)", "separated by a semi-colon (url-encoded as %2C)"), so a check would have to guess; evidence cannot be judged. |
| [Modeling hierarchical relationships of a protein-coding gene, Best practices and Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | Parent and child have a part_of relationship; IDs should be internally resolvable; ### may separate gene models; introns are optional; types are SO terms. | [SO-006](../rules.md#so-006), [GFF-STR-004](../rules.md#gff-str-004), [GFF-DIR-003](../rules.md#gff-dir-003), [SO-001](../rules.md#so-001), [AGB-003](#agb-003), [AGB-004](#agb-004), [AGB-005](#agb-005), [AGB-006](#agb-006), [AGB-007](#agb-007), [AGB-013](#agb-013) | Core and SO rules, plus the profile rules listed. Edge cases (ribosome slippage, trans-splicing, split features) have no recommendation yet. |
| [Pragmas, Dbxref](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#pragmas) | An optional ##dbxref=<Namespace:ID,refsrc=URL> directive registers a cross-reference source with identifiers.org. | nothing | The format and the example disagree, and checking registration needs network requests. |
| [Other caveats and unresolved issues](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#other-caveats-and-unresolved-issues) | FASTA deflines, QTL and miRNA models, split gene models, pan-genome context and provenance directives. | nothing | Open issues without a recommendation. |
