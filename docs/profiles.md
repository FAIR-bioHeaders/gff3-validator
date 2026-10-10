# Repository and community profiles

A profile adds the requirements of a repository or community to the core
GFF3 1.26 and Sequence Ontology rules (spec 009 FR-011; the profile mechanism
is [FHR-Specification #51](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/51),
the first profile [#70](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/70)).
Profiles are optional: without `--profile` nothing changes.

| Profile | Version | Source | Rules |
|---|---|---|---|
| `agbiodata` | 0.1.0-draft (not reviewed by the AgBioData GFF3 working group) | [AgBioData GFF3 working group recommendations](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md) (CC0-1.0, commit 32c8a38, 2021-12-29) | [profiles/agbiodata.md](profiles/agbiodata.md) |

```bash
gff3-validate --list-profiles
gff3-validate --profile agbiodata annotation.gff3
gff3-validate --profile agbiodata --genome genome.fa --format json annotation.gff3
gff3-validate --profile my-profile.yaml annotation.gff3   # a profile file
```

On the web page, choose the profile under "Profile"; in Galaxy, set the
"Profile" parameter.

## What a profile can do

A profile is a YAML file (`profiles/ID.yaml`, shipped in the package) that
can:

1. **Raise the level of core rules**, for example make the warning SO-001 an
   error because the source document says types "must" be SO terms. A
   profile can only raise levels (info to warning or error, warning to
   error), never lower them, and never turn off a core rule.
2. **Add checks** with ids in its own namespace (`AGB-001` for AgBioData),
   documented with the same fields as catalogue rules: level, title,
   description, reference to a section of the source document, an example
   that does not comply, a compliant example, a fix, status and notes. The
   code is in `gff3_validator/profiles/ID.py`.
3. **List guidance**: the recommendations of the source that no profile rule
   checks, with the core rules that already cover them and the reason there
   is no profile rule (not machine-checkable, needs network access, the
   document is ambiguous, or it conflicts with GFF3 1.26).

## How profile findings are reported

Profile findings are kept apart from the core findings, so that "valid GFF3"
keeps its meaning:

- The core findings, counts and `valid` are exactly the same with or without
  a profile. A core finding whose level the profile raises keeps its catalogue
  level among the core findings, and is reported again among the profile
  findings at the raised level, with its catalogue level (`core_level`).
- A file **complies** with a profile when it is valid GFF3 and has no profile
  errors. The verdict gives both, for example
  `no errors (0 errors, 2 warnings, 0 notes; 40 lines); AgBioData profile: 3 errors, 1 warnings, 0 notes (not compliant)`.
- Text: profile findings are labelled, for example
  `annotation.gff3:12 (column 9): AgBioData profile warning AGB-001: ...`, and
  the summary names the profile version and its source.
- JSON: the `profile` object (null without a profile) has `id`, `name`,
  `version`, `review`, `source` (`title`, `url`, `license`, `commit`, `date`),
  `docs`, `compliant`, `counts`, `not_checked`, `truncated_findings` and
  `findings` (each with `core_level`, null for profile rules).
- HTML: a "Profile" entry in the summary and a separate profile section with
  its own verdict and findings table.
- SARIF: the profile is a tool extension (`runs[0].tool.extensions[0]`) with
  its rules; profile results reference it (`rule.toolComponent`) and carry
  `properties.profile`; `runs[0].properties.profile` has the metadata,
  counts and `compliant`.
- Exit status: 1 when the file is not valid GFF3 or has profile errors, so a
  pipeline step `gff3-validate --profile agbiodata` fails on either.

Profile checks that were not run (for example a raised biology rule without
`--genome`) are listed under "not checked", never as passed.

## Writing or changing a profile

1. Start from the source document of the repository or community, pinned to
   a commit or dated version, and check that its licence allows quoting it.
2. Write `profiles/ID.yaml` (see [profiles/agbiodata.yaml](../profiles/agbiodata.yaml)
   for every field). For each statement of the document decide: a core rule
   already covers it (guidance with `covered_by`), a core rule's level should
   be raised (`levels`), a new check is needed (`rules`), or it cannot be
   checked (guidance with the reason). Translate only what the document
   says; record how a statement was read in the rule's `notes`.
3. Implement new checks in `gff3_validator/profiles/ID.py`: a `RULES` tuple
   and a `Checker(profile, context)` class with `directive`, `feature`,
   `finish` and `skip_reasons` methods (see `agbiodata.py`). Keep memory
   bounded and make no network requests. Set `checks: ID` in the YAML. A
   rule is `implemented` only when the checker emits it and a test covers it.
4. Add a test with a non-compliant and a compliant example for each rule
   (`tests/test_profiles.py`) and conformance cases with status
   `extension:ID` (`scripts/make_conformance.py`).
5. Run `python scripts/render_rules.py` to write the packaged copy, the
   profile's page in `docs/profiles/` and its table below, then the checks in
   [AGENTS.md](../AGENTS.md).
6. Ask the repository or community to review the profile, and record the
   review in `review` only when it has happened.

A profile file given by path (`--profile path.yaml`) can raise levels and
use the checks shipped in this package; it cannot load code from elsewhere.

## AgBioData

The [AgBioData GFF3 working group recommendations](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md)
(AgBioData, the Alliance of Genome Resources and NCBI; CC0-1.0) give, for
each column and reserved attribute, a change level, best practices and a
"Validation" entry. The profile translates the statements that software can
check. Levels follow the wording: error where a Validation entry says "must"
or "validation fails", warning where it says "should" or asks the validator
to warn (or a best practice says "should never" or "do not"), info for other
best practices.

Points to know:

- The document recommends `##species NCBITaxon:9606` (AGB-011, info), while
  GFF3 1.26 prefers the NCBI Taxonomy URL (core warning GFF-DIR-007). Either
  form gets one of the two findings; the profile does not lower core rules.
- Its Note example repeats the Note tag on one line, which GFF3 1.26 forbids
  (GFF-ATT-004, an error). Use one Note with comma-separated values.
- Its "Validation" for Dbxref, Seqid alias tables and Ontology_term asks for
  URLs to be resolved; the validator makes no network requests, so these are
  guidance.
- The phase directive is written two ways (`##phase` and
  `##Translation-table`), and the complex metadata separators are described
  inconsistently; neither is checked.

<!-- profile-mapping:agbiodata:start (generated by scripts/render_rules.py; do not edit) -->
AgBioData GFF3 recommendations 0.1.0-draft: 13 profile rules, 2 raised core rules and 19 recommendations kept as guidance.

| Recommendation (source section) | Checked by | What |
|---|---|---|
| [Seqid (column 1), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#seqid) | guidance, not checked | An optional ##alias-table directive gives a resolvable URL of the GenBank alias table, or starts an inline alias table. |
| [Source (column 2), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#source) | guidance, not checked (core or profile rules: [GFF-SYN-004](rules.md#gff-syn-004), [GFF-SYN-005](rules.md#gff-syn-005), [GFF-SYN-008](rules.md#gff-syn-008), [GFF-SYN-009](rules.md#gff-syn-009)) | Use "." when there is no source; follow the GFF3 encoding rules; separate several sources by a literal comma, not %2C; name the tool, method or database and its version. |
| [Type (column 3), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#type) | [SO-001](rules.md#so-001) raised to error | type is an SO term name or accession (core level warning) |
| [Type (column 3), Best practice](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#type) | [AGB-008](profiles/agbiodata.md#agb-008) (warning) | so_term_name names a subtype of the feature's type |
| [Type (column 3), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#type) | guidance, not checked (core or profile rules: [SO-006](rules.md#so-006), [SO-009](rules.md#so-009)) | All child rows should use a type within the hierarchy of the parent; the SO is fetched from sofa.obo by default. |
| [Start, End (columns 4 and 5), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#start-end) | guidance, not checked (core or profile rules: [GFF-SYN-013](rules.md#gff-syn-013), [GFF-SYN-014](rules.md#gff-syn-014), [GFF-SYN-015](rules.md#gff-syn-015), [GFF-ATT-016](rules.md#gff-att-016), [GFF-STR-008](rules.md#gff-str-008)) | start and end are 1-based, start is at most end, zero-length and one-base features have start = end, and Is_circular=true allows end beyond the sequence. |
| [Score (column 6), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#score) | [AGB-012](profiles/agbiodata.md#agb-012) (warning) | ##Score directive has name, min, max and best |
| [Score (column 6), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#score) | guidance, not checked (core or profile rules: [GFF-SYN-016](rules.md#gff-syn-016), [AGB-012](profiles/agbiodata.md#agb-012)) | A score is a floating point number or "."; describe the score in a ##Score directive, using EDAM where possible. |
| [Strand (column 7), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#strand) | guidance, not checked (core or profile rules: [GFF-SYN-017](rules.md#gff-syn-017)) | Strand is +, -, . or ?. |
| [Phase (column 8), Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#phase) | [BIO-008](rules.md#bio-008) raised to error | No internal stop codons (core level warning) |
| [Phase (column 8), Best practices and Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#phase) | guidance, not checked (core or profile rules: [BIO-004](rules.md#bio-004), [BIO-006](rules.md#bio-006), [BIO-007](rules.md#bio-007), [BIO-008](rules.md#bio-008)) | Validate the phase; give non-standard translation tables per sequence in a phase directive; compare CDS and protein FASTA, when given, with the sequence derived from the GFF3. |
| [Attributes : ID, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--id) | guidance, not checked (core or profile rules: [GFF-STR-001](rules.md#gff-str-001)) | Validate only that IDs are unique in the file, except for discontinuous features; keep persistent identifiers in other attributes (gene_id, transcript_id, protein_id, feature_id, or Dbxref). |
| [Attributes : Name, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--name) | guidance, not checked | Follow the nomenclature standards of your community; Name is not a unique identifier. |
| [Attributes : Alias, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--alias) | guidance, not checked (core or profile rules: [GFF-ATT-005](rules.md#gff-att-005)) | Alias is for alternative and historical names; avoid commas, tabs and pipes in alias names; values cannot include a semicolon. |
| [Attributes : Dbxref, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--dbxref) | guidance, not checked (core or profile rules: [GFF-ATT-005](rules.md#gff-att-005), [GFF-ATT-014](rules.md#gff-att-014)) | A Dbxref refers to the same entity in a registered database and resolves to a URL that returns HTTP 200; it contains no semicolons. |
| [Attributes : Derives_from, Best practices; Modeling hierarchical relationships of a protein-coding gene](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--derives_from) | [AGB-006](profiles/agbiodata.md#agb-006) (info) | No polypeptide features |
| [Attributes : Derives_from, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--derives_from) | guidance, not checked (core or profile rules: [AGB-006](profiles/agbiodata.md#agb-006)) | Avoid Derives_from between CDS and polypeptide by not modelling polypeptides. |
| [Attributes : Note, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--note) | guidance, not checked (core or profile rules: [GFF-ATT-004](rules.md#gff-att-004), [GFF-ATT-005](rules.md#gff-att-005)) | Note may not include a semicolon and may be repeated. |
| [Attributes : Ontology_term, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--ontology_term) | [AGB-001](profiles/agbiodata.md#agb-001) (warning) | Ontology_term is avoided |
| [Attributes : Ontology_term, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--ontology_term) | guidance, not checked (core or profile rules: [GFF-ATT-014](rules.md#gff-att-014), [SO-008](rules.md#so-008), [AGB-001](profiles/agbiodata.md#agb-001)) | Ontology_term values are CURIEs that resolve to published ontology terms. |
| [Attributes : Target, Gap, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--target-gap) | [AGB-009](profiles/agbiodata.md#agb-009) (error) | Target fields are single-space delimited and target_id is a seqid |
| [Attributes : Target, Gap, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes--target-gap) | guidance, not checked (core or profile rules: [GFF-ATT-010](rules.md#gff-att-010), [GFF-ATT-011](rules.md#gff-att-011), [AGB-009](profiles/agbiodata.md#agb-009)) | Prefer BAM or PAF to Target and Gap for alignments; target_id should be a sequence identifier usable in column 1. |
| [Attributes complex metadata / functional annotations, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes-complex-metadata--functional-annotations) | [AGB-002](profiles/agbiodata.md#agb-002) (warning) | GO terms are not given in Dbxref or Ontology_term |
| [Attributes complex metadata / functional annotations, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#attributes-complex-metadata--functional-annotations) | guidance, not checked (core or profile rules: [AGB-002](profiles/agbiodata.md#agb-002)) | go_annotations, gene_product and provenance values are lower-case, URL-encoded lists of rank and key=value annotations; GO annotations carry evidence codes. |
| [Modeling hierarchical relationships of a protein-coding gene, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | [AGB-003](profiles/agbiodata.md#agb-003) (warning) | Child features lie within their parent |
| [Modeling hierarchical relationships of a protein-coding gene, Best practices (sort order)](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | [AGB-004](profiles/agbiodata.md#agb-004) (info) | Child features are listed after their parent |
| [Modeling hierarchical relationships of a protein-coding gene, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | [AGB-005](profiles/agbiodata.md#agb-005) (info) | One Parent per feature |
| [Modeling hierarchical relationships of a protein-coding gene, Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | [AGB-007](profiles/agbiodata.md#agb-007) (warning) | CDS and exon features have a Parent |
| [Modeling hierarchical relationships of a protein-coding gene, Best practices](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | [AGB-013](profiles/agbiodata.md#agb-013) (warning) | seqid does not list several sequences |
| [Modeling hierarchical relationships of a protein-coding gene, Best practices and Validation](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#modeling-hierarchical-relationships-of-a-protein-coding-gene) | guidance, not checked (core or profile rules: [SO-006](rules.md#so-006), [GFF-STR-004](rules.md#gff-str-004), [GFF-DIR-003](rules.md#gff-dir-003), [SO-001](rules.md#so-001), [AGB-003](profiles/agbiodata.md#agb-003), [AGB-004](profiles/agbiodata.md#agb-004), [AGB-005](profiles/agbiodata.md#agb-005), [AGB-006](profiles/agbiodata.md#agb-006), [AGB-007](profiles/agbiodata.md#agb-007), [AGB-013](profiles/agbiodata.md#agb-013)) | Parent and child have a part_of relationship; IDs should be internally resolvable; ### may separate gene models; introns are optional; types are SO terms. |
| [Pragmas, Ontology URIs](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#pragmas) | [AGB-010](profiles/agbiodata.md#agb-010) (info) | Ontology directives use OBO PURLs |
| [Pragmas, Species](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#pragmas) | [AGB-011](profiles/agbiodata.md#agb-011) (info) | ##species is an NCBITaxon CURIE |
| [Pragmas, Dbxref](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#pragmas) | guidance, not checked | An optional ##dbxref=<Namespace:ID,refsrc=URL> directive registers a cross-reference source with identifiers.org. |
| [Other caveats and unresolved issues](https://github.com/NAL-i5K/AgBioData_GFF3_recommendation/blob/32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8/Recommendations.md#other-caveats-and-unresolved-issues) | guidance, not checked | FASTA deflines, QTL and miRNA models, split gene models, pan-genome context and provenance directives. |
<!-- profile-mapping:agbiodata:end -->
