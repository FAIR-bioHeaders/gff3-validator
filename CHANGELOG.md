# Changelog

## Unreleased

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
