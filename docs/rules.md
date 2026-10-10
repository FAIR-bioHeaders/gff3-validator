# GFF3 validator rule catalogue

<!-- Generated from rules/catalogue.yaml by scripts/render_rules.py; do not edit. -->

**Catalogue version 0.1.0-draft. Draft under review with the Sequence Ontology group ([FHR-Specification #62](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/62)).** Rule ids may still change before the first release. Open questions are collected in [questions-for-SO.md](questions-for-SO.md).

Levels: **error** (the file violates GFF3 1.26 or the layer's requirement), **warning** (probably wrong, or a specification recommendation), **info** (worth knowing; never affects validity). Layers: `core` (GFF3 syntax and structure), `so` (Sequence Ontology), `biology` (optional, needs `--genome`), `fhgff3` (optional FAIR-bioHeaders header). A suggested fix is guidance; the validator never rewrites a file. In examples, `→` stands for a tab. Rules of repository and community profiles (for example `AGB-*`) are not part of this catalogue; see [profiles.md](profiles.md).

Sources:

- `gff3`: [GFF3 specification 1.26 (18 August 2020)](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md)
- `so`: [Sequence Ontology so.obo data-version 2026-08-07 (SO-Ontologies commit 4340c14), bundled with the validator (question 13)](https://github.com/The-Sequence-Ontology/SO-Ontologies/blob/4340c143bac3578bba0c013d02e8c5f0e51ad14a/Ontology_Files/so.obo)
- `fhr-format`: [FAIR-bioHeaders format rules R1 to R10 (docs/FORMAT.md)](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/docs/FORMAT.md)
- `spec007`: [FHR-Specification spec 007, GFF3 annotation header (FHGFF3)](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/007-gff3-header/spec.md)
- `spec009`: [FHR-Specification spec 009, GFF3 validator](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/009-gff3-validator/spec.md)

## Summary

| Category | Rules | Implemented | Planned | Need SO input |
|---|---|---|---|---|
| [GFF-SYN](#gff-syn) Syntax: file, lines and columns 1 to 8 | 20 | 19 | 1 | 9 |
| [GFF-ATT](#gff-att) Attributes (column 9) | 17 | 15 | 2 | 12 |
| [GFF-DIR](#gff-dir) Directives | 10 | 10 | 0 | 5 |
| [GFF-STR](#gff-str) Structure: IDs, references and bounds | 13 | 11 | 2 | 7 |
| [SO](#so) Sequence Ontology | 9 | 8 | 1 | 7 |
| [BIO](#bio) Biology (optional, with --genome) | 11 | 11 | 0 | 6 |
| [HDR](#hdr) FHGFF3 header (optional, FAIR-bioHeaders) | 9 | 3 | 6 | 0 |
| **Total** | 89 | 77 | 12 | 46 |

## GFF-SYN

Syntax: file, lines and columns 1 to 8

| Id | Level | Status | Title |
|---|---|---|---|
| [GFF-SYN-001](#gff-syn-001) | error | implemented | First line is the ##gff-version 3 directive |
| [GFF-SYN-002](#gff-syn-002) | error | implemented | Only one ##gff-version directive |
| [GFF-SYN-003](#gff-syn-003) | error | implemented | Feature lines have nine tab-separated columns |
| [GFF-SYN-004](#gff-syn-004) | error | implemented | Undefined columns are ".", not empty |
| [GFF-SYN-005](#gff-syn-005) | error | implemented | No unescaped control characters |
| [GFF-SYN-006](#gff-syn-006) | warning | implemented | File is UTF-8 |
| [GFF-SYN-007](#gff-syn-007) | info | implemented | Possible end-of-line comment |
| [GFF-SYN-008](#gff-syn-008) | error | implemented | Percent-encoding is well formed |
| [GFF-SYN-009](#gff-syn-009) | warning | implemented | Characters encoded that need not be |
| [GFF-SYN-010](#gff-syn-010) | error | implemented | seqid uses the allowed characters |
| [GFF-SYN-011](#gff-syn-011) | error | planned | seqid is defined |
| [GFF-SYN-012](#gff-syn-012) | error | implemented | type is defined |
| [GFF-SYN-013](#gff-syn-013) | error | implemented | start and end are integers |
| [GFF-SYN-014](#gff-syn-014) | error | implemented | start is at least 1 |
| [GFF-SYN-015](#gff-syn-015) | error | implemented | start is not greater than end |
| [GFF-SYN-016](#gff-syn-016) | error | implemented | score is a number or "." |
| [GFF-SYN-017](#gff-syn-017) | error | implemented | strand is +, -, . or ? |
| [GFF-SYN-018](#gff-syn-018) | error | implemented | phase is 0, 1, 2 or "." |
| [GFF-SYN-019](#gff-syn-019) | error | implemented | CDS features have a phase |
| [GFF-SYN-020](#gff-syn-020) | warning | implemented | phase is "." on features other than CDS |

### GFF-SYN-001

**First line is the ##gff-version 3 directive**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ##gff-version](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

The ##gff-version directive must be present and must be the topmost line of the file. The version is 3, optionally followed by .major and .minor revision numbers (3, 3.1, 3.1.26).

Example (invalid):

```text
# made by mytool
##gff-version 3
```

Valid:

```text
##gff-version 3
```

Fix: Put "##gff-version 3" on the first line, before any comment or header line.

Notes: The specification says "3.#.#" with optional revision numbers, and its own examples write "##gff-version 3.1.26", which reads as the specification revision; older tools (the Perl validator, GFF3toolkit) accept only "3". The validator accepts 3, 3.N and 3.N.N. Is "3.1.26" meant to be written by producers, and must the revision numbers be checked? A UTF-8 byte order mark before "##" also fails this rule (the specification does not mention BOMs).

### GFF-SYN-002

**Only one ##gff-version directive**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Change Log 1.21: the ##gff-version pragma only appears once](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#change-log) (gff3)

The ##gff-version directive appears once, on the first line.

Example (invalid):

```text
##gff-version 3
ctg1→.→gene→1→90→.→+→.→ID=g1
##gff-version 3
```

Fix: Remove the repeated directive. If two files were concatenated, split them or merge them with a GFF3-aware tool.

### GFF-SYN-003

**Feature lines have nine tab-separated columns**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Description of the Format](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

A line that is not blank, a comment (#) or a directive (##) is a feature line with exactly nine columns separated by single tab characters. Spaces do not separate columns.

Example (invalid):

```text
ctg1 . gene 1 90 . + . ID=g1
```

Fix: Separate the nine columns with tabs; replace a missing column by ".".

Notes: A trailing tab gives ten columns (the last empty) and fails this rule; some tools tolerate it. Blank lines are ignored as the specification asks.

### GFF-SYN-004

**Undefined columns are ".", not empty**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Description of the Format: undefined fields are replaced with the '.' character](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

A column with no value contains a single "." character; an empty column is not allowed.

Example (invalid):

```text
ctg1→→gene→1→90→.→+→.→ID=g1
```

Fix: Write "." in the empty column.

Notes: The source column (2) is free text: the validator applies no character set to it (the Perl validator did), only the encoding rules GFF-SYN-005 and GFF-SYN-008.

### GFF-SYN-005

**No unescaped control characters**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Description of the Format: escaping](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Tab (outside column separators), newline, carriage return and other control characters (0x00 to 0x1F, 0x7F) must be percent-encoded.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Note=first<CR>second
```

Fix: Percent-encode the character (for example %09 for tab, %0D for carriage return).

Notes: The specification does not address line endings. Are CRLF files invalid (the CR is an unescaped control character in column 9) or should a CRLF terminator be accepted? Proposal: report CRLF once per file as an error under this rule. Until SO answers, the validator reports control characters inside a line and does not report a carriage return immediately before the line feed (a CRLF line ending), which it removes before checking the line.

### GFF-SYN-006

**File is UTF-8**

- Level: warning; layer: core; status: implemented; review: pending-SO
- Reference: [Description of the Format: use of UTF-8 is recommended](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

UTF-8 is the only recommended character encoding (since 1.26).

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Note=caf\xe9 (Latin-1 byte)
```

Fix: Re-encode the file as UTF-8.

Notes: Reported once per file, at the first line that is not valid UTF-8, with the number of further such lines. Invalid bytes are replaced by U+FFFD for the other checks.

### GFF-SYN-007

**Possible end-of-line comment**

- Level: info; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: end-of-line comments are not allowed](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

End-of-line comments are not allowed. A "#" in a feature or directive line is data; text such as " # comment" at the end of column 9 is probably a misplaced comment.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1 # check this
```

Fix: Move the comment to its own line starting with "#".

Notes: Heuristic; "#" is a legal character in values, so this is info only. Checked in column 9 only: whitespace followed by "#".

### GFF-SYN-008

**Percent-encoding is well formed**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Description of the Format: RFC 3986 percent-encoding](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

A "%" must start a percent-encoded octet, "%" followed by two hexadecimal digits (RFC 3986). A literal percent sign is written %25.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Note=50% identity
```

Fix: Write a literal percent sign as %25.

Notes: Backslash escapes and "+" for space are not allowed, but cannot be told apart from literal text; they are not checked. Checked in all nine columns.

### GFF-SYN-009

**Characters encoded that need not be**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Description of the Format: escaping](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Only tab, newline, carriage return, percent and control characters (and, in column 9, the reserved characters ; = & ,) are to be encoded; "no other characters may be encoded".

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Name=EDEN%2D1
```

Fix: Write the character literally (here "-").

Notes: Conflicts with column 1, where characters outside [a-zA-Z0-9.:^*$@!+_?-|] "must" be escaped, and with Target, where spaces in target ids are escaped as %20. Proposal: allow any encoding in column 1 and in Target ids, warn elsewhere. Is over-encoding an error, a warning, or allowed? Implemented as the proposal while question 3 is open: in column 1 only encoding a character of the seqid set is reported, %20 is allowed in Target values, and other encoded characters (including UTF-8 octets of non-ASCII characters) are reported. Reported once per file, at the first occurrence, with a count.

### GFF-SYN-010

**seqid uses the allowed characters**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 1: seqid](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The seqid (column 1) may contain any characters but must escape those not in [a-zA-Z0-9.:^*$@!+_?-|]. It may not contain unescaped whitespace and must not begin with an unescaped ">".

Example (invalid):

```text
chr 1→.→gene→1→90→.→+→.→ID=g1
```

Fix: Percent-encode the character (here "chr%201") or rename the sequence consistently in the genome too.

Notes: Read as a regular-expression class, "?-|" would be a character range; the validator reads the list literally (? - | as three characters). Widely used seqids contain "#" or "=" (for example some assembly names); escaping them breaks the link to the FASTA name. Confirm the literal reading and whether escaped seqids must match escaped or decoded FASTA ids. Implemented for unescaped whitespace only. The character set is not checked until SO answers question 3. A seqid beginning with ">" cannot be told apart from a FASTA header: the line starts an implied FASTA section (GFF-DIR-005).

### GFF-SYN-011

**seqid is defined**

- Level: error; layer: core; status: planned; review: pending-SO; **needs SO input**
- Reference: [Column 1: seqid](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The seqid is the landmark for the coordinates and cannot be undefined (".").

Example (invalid):

```text
.→.→gene→1→90→.→+→.→ID=g1
```

Fix: Give the name of the sequence the coordinates refer to.

Notes: Not stated explicitly; follows from the definition of seqid. The Perl validator treats "." as an error. Confirm.

### GFF-SYN-012

**type is defined**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Column 3: type](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The type (column 3) is required; "." is not a valid type. Term validity is checked by the SO rules.

Example (invalid):

```text
ctg1→.→.→1→90→.→+→.→ID=g1
```

Fix: Give a Sequence Ontology term name or accession.

### GFF-SYN-013

**start and end are integers**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Columns 4 & 5: start and end](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Columns 4 and 5 are positive 1-based integer coordinates, written as decimal digits.

Example (invalid):

```text
ctg1→.→gene→1.0→9e1→.→+→.→ID=g1
```

Fix: Write the coordinates as whole numbers, for example 1 and 90.

Notes: The validator accepts only ASCII digits: a leading "+" sign or "." is an error. Leading zeros ("0100") are accepted; confirm.

### GFF-SYN-014

**start is at least 1**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Columns 4 & 5: start and end](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Coordinates are 1-based, so start and end are 1 or more.

Example (invalid):

```text
ctg1→.→gene→0→90→.→+→.→ID=g1
```

Fix: Convert 0-based coordinates (as in BED) to 1-based by adding 1 to start.

### GFF-SYN-015

**start is not greater than end**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Columns 4 & 5: start and end](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Start is always less than or equal to end, whatever the strand. For a feature crossing the origin of a circular sequence, end is given as the position past the origin plus the length of the landmark.

Example (invalid):

```text
ctg1→.→gene→90→1→.→-→.→ID=g1
```

Fix: Swap start and end; give the orientation in the strand column.

Notes: Zero-length features (insertion sites) have start equal to end, with the site to the right of the indicated base; there is then no way to tell a zero-length feature from a one-base feature. Should SO types such as insertion_site be checked for this convention?

### GFF-SYN-016

**score is a number or "."**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 6: score](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The score (column 6) is a floating point number, or "." when undefined.

Example (invalid):

```text
ctg1→blastn→match→1→90→high→+→.→ID=m1
```

Fix: Write a number (for example 0.5, 12, 1e-10) or ".".

Notes: "Floating point" is not defined further. The validator accepts decimal numbers with optional sign, fraction and exponent (1, -1.5, .5, 5., 1e-10, 1E+10) and rejects "nan", "inf" and hexadecimal. Confirm the grammar.

### GFF-SYN-017

**strand is +, -, . or ?**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Column 7: strand](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Strand (column 7) is "+" or "-" relative to the landmark, "." for features that are not stranded, or "?" when strandedness is relevant but unknown.

Example (invalid):

```text
ctg1→.→gene→1→90→.→1→.→ID=g1
```

Fix: Use + or -, or "." for unstranded and "?" for unknown.

### GFF-SYN-018

**phase is 0, 1, 2 or "."**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Column 8: phase](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The phase (column 8) is one of the integers 0, 1 or 2, or "." when not defined.

Example (invalid):

```text
ctg1→.→CDS→1→90→.→+→3→ID=c1
```

Fix: Use 0, 1 or 2 (bases to skip from the 5' end of this CDS segment to the first full codon).

### GFF-SYN-019

**CDS features have a phase**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 8: phase; Canonical Gene NOTE 4](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The phase is required for all CDS features.

Example (invalid):

```text
ctg1→.→CDS→1→90→.→+→.→ID=c1;Parent=t1
```

Fix: Give the phase (0, 1 or 2) of each CDS segment.

Notes: Applied to type "CDS" and accession SO:0000316. Does it also apply to SO subtypes of CDS (for example CDS_fragment, edited_CDS)? The specification's own single-exon and polycistronic examples write CDS lines with phase "."; they are placeholders (XXXX coordinates) but are copied by users. With the SO layer, applied as proposed in question 6 to the label and accession of CDS and of every is_a subtype of CDS in the SO release (for example CDS_predicted, edited_CDS); a case variant such as "cds" is SO-005, not this rule.

### GFF-SYN-020

**phase is "." on features other than CDS**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 8: phase](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Phase is defined only for CDS features; other features normally have ".".

Example (invalid):

```text
ctg1→.→exon→1→90→.→+→0→Parent=t1
```

Fix: Use "." for the phase of features that are not CDS.

Notes: The specification does not forbid it. GTF-derived files put a phase on start_codon and stop_codon. Is a phase on non-CDS features an error, a warning, or allowed? Implemented as proposed in question 6, as a warning, for types the SO layer resolves to a current term that is not CDS or an is_a subtype of it; unknown and obsolete types are not judged. Reported once per type, at the first line, with a count.

## GFF-ATT

Attributes (column 9)

| Id | Level | Status | Title |
|---|---|---|---|
| [GFF-ATT-001](#gff-att-001) | error | implemented | Attributes are tag=value pairs separated by semicolons |
| [GFF-ATT-002](#gff-att-002) | error | implemented | Tags and values are not empty |
| [GFF-ATT-003](#gff-att-003) | info | implemented | Empty attribute pair or trailing semicolon |
| [GFF-ATT-004](#gff-att-004) | error | implemented | Each tag appears once per line |
| [GFF-ATT-005](#gff-att-005) | error | implemented | Reserved characters are escaped in tags and values |
| [GFF-ATT-006](#gff-att-006) | error | implemented | Single-valued reserved tags have one value |
| [GFF-ATT-007](#gff-att-007) | warning | implemented | Unknown reserved (upper-case) tag |
| [GFF-ATT-008](#gff-att-008) | warning | implemented | Tag differs from a reserved tag only by case |
| [GFF-ATT-009](#gff-att-009) | info | implemented | Quoted attribute value |
| [GFF-ATT-010](#gff-att-010) | error | implemented | Target has the form "target_id start end [strand]" |
| [GFF-ATT-011](#gff-att-011) | error | implemented | Gap is a list of operations |
| [GFF-ATT-012](#gff-att-012) | warning | implemented | Gap is given with Target |
| [GFF-ATT-013](#gff-att-013) | warning | implemented | Gap lengths agree with the feature and Target lengths |
| [GFF-ATT-014](#gff-att-014) | error | implemented | Dbxref and Ontology_term values are DBTAG:ID |
| [GFF-ATT-015](#gff-att-015) | info | planned | DBTAG is a registered database abbreviation |
| [GFF-ATT-016](#gff-att-016) | warning | implemented | Is_circular is "true" |
| [GFF-ATT-017](#gff-att-017) | info | planned | Is_circular is on the landmark feature |

### GFF-ATT-001

**Attributes are tag=value pairs separated by semicolons**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Column 9: attributes](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Column 9 is "." or a list of tag=value pairs separated by ";". Each pair has one "=" separating a tag from its value.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID g1; Name EDEN
```

Fix: Write tag=value pairs (ID=g1;Name=EDEN). This is GTF syntax; convert GTF with a converter rather than by hand.

### GFF-ATT-002

**Tags and values are not empty**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 9: attributes](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Every pair has a non-empty tag and a non-empty value.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;=EDEN
```

Fix: Give the tag, or remove the pair.

Notes: The specification does not say values must be non-empty; the Perl validator and GFF3toolkit treat empty values as errors. Is "Note=" an error, a warning, or valid? Until SO answers question 4, only an empty tag ("=value") is reported; empty values ("Note=", "Parent=a,,b") are not.

### GFF-ATT-003

**Empty attribute pair or trailing semicolon**

- Level: info; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Circular Genomes (example ends with ';')](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#circular-genomes) (gff3)

An empty pair (";;") or a trailing ";" carries no data.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;;Name=EDEN;
```

Fix: Remove the extra semicolons (optional).

Notes: The specification's own circular-genome example ends column 9 with ";" so a trailing semicolon appears to be allowed. Confirm that both are valid. Info only, so it never affects validity; reported once per file, at the first occurrence, with a count.

### GFF-ATT-004

**Each tag appears once per line**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Column 9: multiple attributes of the same type](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Multiple values of a tag are separated by commas within one pair, not by repeating the tag.

Example (invalid):

```text
ctg1→.→exon→1→90→.→+→.→Parent=t1;Parent=t2
```

Fix: Join the values with a comma (Parent=t1,t2).

Notes: Implied by the specification and enforced by the Perl validator and GFF3toolkit.

### GFF-ATT-005

**Reserved characters are escaped in tags and values**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Description of the Format: reserved characters in column 9](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

In column 9 ";", "=", "&" and "," have reserved meanings and must be escaped (%3B, %3D, %26, %2C) when used in a tag or value. Tags are case sensitive.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Note=a=b & c
```

Fix: Escape the characters (Note=a%3Db %26 c).

Notes: "&" has no syntactic role in GFF3 but is still reserved. Comma handling is in GFF-ATT-006. An unescaped ";" cannot be detected, since it splits the pair. A "," in a tag is reported here; commas in values are GFF-ATT-006.

### GFF-ATT-006

**Single-valued reserved tags have one value**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 9: multiple values; Change Log 1.19](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Only Parent, Alias, Note, Dbxref and Ontology_term can have multiple comma-separated values. A comma in the value of another reserved tag (ID, Name, Target, Gap, Derives_from, Is_circular) must be escaped as %2C.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1,g2
```

Fix: Use one value (and a separate feature for the second ID), or escape the comma.

Notes: Derives_from is not in the multi-valued list (1.19), yet a feature can derive from several (the polycistronic and trans-splicing examples use one Derives_from per line). Is Derives_from=g1,g2 allowed? For lower-case (application) tags, is an unescaped comma a value separator or literal text? The validator will not interpret commas in application tags. Implemented for ID, Name, Target, Gap and Is_circular. Derives_from is not checked until question 5 is answered; for GFF-STR-005 its commas are read as separators.

### GFF-ATT-007

**Unknown reserved (upper-case) tag**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 9: all attributes that begin with an uppercase letter are reserved](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Tags beginning with an upper-case letter are reserved. Only ID, Name, Alias, Parent, Target, Gap, Derives_from, Note, Dbxref, Ontology_term and Is_circular are defined.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Gene_biotype=protein_coding
```

Fix: Use a lower-case tag for application data (gene_biotype=protein_coding).

Notes: Common in practice (GVF tags such as Variant_seq, mirGFF3 Variant/Cigar, NCBI "Is_pseudo"?). Should known extensions (GVF, mirGFF3) be recognized by profile rather than warned about? Implemented as a warning for any tag beginning with an upper-case letter that is not reserved and is not a case variant of a reserved tag (that is GFF-ATT-008).

### GFF-ATT-008

**Tag differs from a reserved tag only by case**

- Level: warning; layer: core; status: implemented; review: pending-SO
- Reference: [Column 9: attribute names are case sensitive](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Tags are case sensitive; "parent" is not "Parent", so a lower-case reserved name is an application tag and has no effect.

Example (invalid):

```text
ctg1→.→exon→1→90→.→+→.→parent=t1
```

Fix: Use the reserved spelling (Parent=t1) if a part-of relationship was meant.

Notes: The specification's own pathological-case examples write "name=resA"; that is valid (an application tag) but probably meant Name.

### GFF-ATT-009

**Quoted attribute value**

- Level: info; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 9: attribute values do not need to be and should not be quoted](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Values should not be quoted; quotes are part of the value.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Dbxref="EMBL:AA816246"
```

Fix: Remove the quotes unless they belong to the value.

Notes: The Ontology Associations section shows Dbxref="EMBL:AA816246" with quotes. Are those examples meant literally? A value that starts and ends with a double quote is reported; info only, once per file, at the first occurrence, with a count.

### GFF-ATT-010

**Target has the form "target_id start end [strand]"**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 9: Target; Alignments](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Target values are a target id, start and end (positive integers, start <= end) and an optional strand "+" or "-", separated by spaces. Spaces in the target id are escaped as %20.

Example (invalid):

```text
ctg1→.→cDNA_match→1050→1500→.→+→.→ID=m1;Target=cdna0123+12+462
```

Fix: Separate target_id, start and end by spaces, escape spaces in target_id as %20, and give the strand as + or - (Target=cdna0123 12 462 +).

Notes: The ##FASTA example writes Target=cdna0123+12+462 ("+" for space), which the specification otherwise forbids; it fails this rule. Implemented for the stated form: three or four fields separated by spaces (runs of spaces are accepted), positive integer start and end, strand + or -. Until SO answers, start > end within Target is not reported (the Alignments section says orientation goes in column 7 "and not by changing the order of the start and end positions"), and a strand on a protein target is accepted.

### GFF-ATT-011

**Gap is a list of operations**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Gap Attribute](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-gap-attribute) (gff3)

Gap is a space-separated list of operations, each a code M, I, D, F or R followed by a positive length (for example "M8 D3 M6 I1 M6").

Example (invalid):

```text
chr3→.→match→1→23→.→.→.→ID=m1;Target=EST23 1 21;Gap=8M3D6M
```

Fix: Write the code before the length (M8 D3 M6); this is not SAM CIGAR order.

Notes: The Perl validator also accepted lower-case codes. Are lower-case codes and multiple spaces valid? Until SO answers, only the upper-case codes are accepted, runs of spaces between operations are accepted, and a zero length is reported.

### GFF-ATT-012

**Gap is given with Target**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Gap Attribute](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-gap-attribute) (gff3)

The Gap attribute describes the alignment of the feature to its Target, so a Gap without a Target cannot be interpreted.

Example (invalid):

```text
chr3→.→match→1→23→.→.→.→ID=m1;Gap=M8 D3 M6 I1 M6
```

Fix: Add the Target attribute.

### GFF-ATT-013

**Gap lengths agree with the feature and Target lengths**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Gap Attribute](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-gap-attribute) (gff3)

For nucleotide alignments, M + D lengths equal the feature length and M + I lengths equal the Target length; for protein-to-nucleotide matches, M, I and D count residues (three bases each) and F, R count bases.

Example (invalid):

```text
chr3→.→match→1→30→.→.→.→ID=m1;Target=EST23 1 21;Gap=M8 D3 M6 I1 M6
```

Fix: Correct the coordinates or the Gap string so they describe the same alignment.

Notes: Which types are protein-to-nucleotide (nucleotide_to_protein_match, protein_match and subtypes?) must come from SO. For multi-line matches, lengths apply per line. Implemented without SO: a line is accepted if either reading fits, nucleotide (no F or R; M + D = feature length; M + I = Target length) or protein (3 x (M + D) + F - R = feature length; M + I = Target length), and a warning is given when neither does. Checked only when Target and Gap are well formed.

### GFF-ATT-014

**Dbxref and Ontology_term values are DBTAG:ID**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Ontology Associations and DB Cross References](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#ontology-associations-and-db-cross-references) (gff3)

Each value has a database tag, a colon and an identifier; split on the first colon, so the DBTAG contains no colon and the ID may.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Dbxref=AA816246
```

Fix: Prefix the identifier with its database tag (Dbxref=EMBL:AA816246).

### GFF-ATT-015

**DBTAG is a registered database abbreviation**

- Level: info; layer: core; status: planned; review: pending-SO; **needs SO input**
- Reference: [Ontology Associations and DB Cross References](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#ontology-associations-and-db-cross-references) (gff3)

The DBTAG should come from the GO database cross-reference registry named by the specification.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1;Dbxref=MyLab:123
```

Fix: Use a registered abbreviation where one exists.

Notes: The specification points to ftp://ftp.geneontology.org/pub/go/doc/GO.xrf_abbs, which is no longer served; GO now publishes db-xrefs.yaml. Which registry (or Bioregistry prefixes) should be pinned, and is this worth checking?

### GFF-ATT-016

**Is_circular is "true"**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Circular Genomes](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#circular-genomes) (gff3)

Is_circular is a flag; the specification uses the value "true".

Example (invalid):

```text
J02448→GenBank→region→1→6407→.→+→.→ID=J02448;Is_circular=yes
```

Fix: Write Is_circular=true, or remove the attribute for a linear sequence.

Notes: Is Is_circular=false valid (meaning linear), or must the tag be absent? Until SO answers, Is_circular=false is not reported; any value other than true and false is.

### GFF-ATT-017

**Is_circular is on the landmark feature**

- Level: info; layer: core; status: planned; review: pending-SO; **needs SO input**
- Reference: [Circular Genomes](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#circular-genomes) (gff3)

Is_circular marks the landmark (a feature covering the whole sequence named in column 1), not features on it.

Example (invalid):

```text
J02448→GenBank→CDS→6006→7238→.→+→0→ID=geneII;Is_circular=true
```

Fix: Put Is_circular=true on a region feature spanning the whole sequence.

Notes: How is the landmark identified: a feature whose ID equals the seqid, one spanning 1..length, or a particular SO type (region, chromosome, plasmid)?

## GFF-DIR

Directives

| Id | Level | Status | Title |
|---|---|---|---|
| [GFF-DIR-001](#gff-dir-001) | error | implemented | ##sequence-region has the form: seqid start end |
| [GFF-DIR-002](#gff-dir-002) | error | implemented | One ##sequence-region per seqid |
| [GFF-DIR-003](#gff-dir-003) | error | implemented | ### closes all forward references |
| [GFF-DIR-004](#gff-dir-004) | error | implemented | Only FASTA after ##FASTA |
| [GFF-DIR-005](#gff-dir-005) | warning | implemented | FASTA section starts with ##FASTA |
| [GFF-DIR-006](#gff-dir-006) | warning | implemented | FASTA records are well formed |
| [GFF-DIR-007](#gff-dir-007) | warning | implemented | ##species is an NCBI Taxonomy URL |
| [GFF-DIR-008](#gff-dir-008) | warning | implemented | ##genome-build has a source and a build name |
| [GFF-DIR-009](#gff-dir-009) | info | implemented | Ontology directives are recorded but not fetched |
| [GFF-DIR-010](#gff-dir-010) | info | implemented | Unknown directive |

### GFF-DIR-001

**##sequence-region has the form: seqid start end**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ##sequence-region](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

The directive gives a seqid and integer start and end with 1 <= start <= end.

Example (invalid):

```text
##sequence-region ctg123 1497228
```

Fix: Write ##sequence-region ctg123 1 1497228.

Notes: Must start be 1? Must the directive come before the features on that seqid, or may it appear anywhere (gt gff3 moves them to the top)? Until SO answers question 10, a start other than 1 and a directive after the features on its seqid are not reported. The fields are separated by whitespace.

### GFF-DIR-002

**One ##sequence-region per seqid**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##sequence-region](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

Only one ##sequence-region directive may be given for any seqid.

Example (invalid):

```text
##sequence-region ctg1 1 1000
##sequence-region ctg1 1 2000
```

Fix: Keep one directive covering the whole region.

Notes: An exact repeat (same bounds) could be a warning; proposal keeps it an error as the text says.

### GFF-DIR-003

**### closes all forward references**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ###](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

"###" declares that all forward references to feature IDs seen so far are resolved. A Parent or Derives_from seen before "###" must refer to an ID that also appears before it, and features after it should not add parts to features before it.

Example (invalid):

```text
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Parent=g1
###
ctg1→.→gene→1→90→.→+→.→ID=g1
```

Fix: Move "###" after the features it closes, or put parents before it.

Notes: The text says forward references are resolved; it does not say whether a later line may still name an earlier ID as Parent, or continue a discontinuous feature (same ID) after "###". Streaming readers close objects at "###", so both break them. Error or warning? Implemented for the part the text states: a Parent or Derives_from seen before ### that names an ID first defined after it (reported at the first such reference). Until SO answers question 9, a later line naming an earlier ID, and the continuation of a discontinuous feature after ###, are not reported. An ID that is never defined is GFF-STR-004 or GFF-STR-005 instead.

### GFF-DIR-004

**Only FASTA after ##FASTA**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##FASTA](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

After ##FASTA the rest of the file is one or more FASTA records; no feature lines or other content may follow.

Example (invalid):

```text
##FASTA
>ctg1
ACGT
ctg1→.→gene→1→4→.→+→.→ID=g1
```

Fix: Move all feature lines before ##FASTA.

Notes: Are blank lines and "#" comments allowed inside the FASTA section? Feature lines (lines with a tab) and "##" directives after ##FASTA are reported; blank lines and "#" comment lines are not, until SO answers.

### GFF-DIR-005

**FASTA section starts with ##FASTA**

- Level: warning; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##FASTA (implied by a line beginning with >)](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

A line beginning with ">" implies a ##FASTA directive (kept for Artemis compatibility); writing ##FASTA is clearer.

Example (invalid):

```text
ctg1→.→gene→1→4→.→+→.→ID=g1
>ctg1
ACGT
```

Fix: Insert a ##FASTA line before the first sequence.

### GFF-DIR-006

**FASTA records are well formed**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ##FASTA](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

Each record has a ">" header with an id, at least one sequence line, and ids are unique.

Example (invalid):

```text
##FASTA
>ctg1
>ctg2
ACGT
```

Fix: Give each sequence a unique id and its sequence lines.

Notes: Which alphabet is accepted (IUPAC nucleotides, amino acids, lower case, "*", "-")? Is the FASTA id the first word of the header? Implemented without an alphabet check: a header with no id, a repeated id, a record without sequence lines, and sequence lines before the first header (once) are reported. The id is taken as the first word of the header, as FASTA readers do.

### GFF-DIR-007

**##species is an NCBI Taxonomy URL**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ##species](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

The preferred format is an NCBI Taxonomy browser URL by id or name.

Example (invalid):

```text
##species Caenorhabditis elegans
```

Fix: Write ##species https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=6239.

Notes: The specification gives http URLs only, as "preferred". Accept https, identifiers.org/NCBITaxon CURIEs (NCBITaxon:6239)? Proposal: warning only when the value is not a URL or CURIE. Until SO answers, anything other than the two NCBI Taxonomy browser URL forms (http or https) is reported, including NCBITaxon CURIEs.

### GFF-DIR-008

**##genome-build has a source and a build name**

- Level: warning; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##genome-build](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

The directive gives the source of the assembly and its build name.

Example (invalid):

```text
##genome-build GRCh38
```

Fix: Give both, for example ##genome-build NCBI GRCh38.p14.

Notes: An FHGFF3 header records the genome more precisely (checksum, accession, SeqCol). Reported when fewer than two values are given; the content is not checked.

### GFF-DIR-009

**Ontology directives are recorded but not fetched**

- Level: info; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ##feature-ontology, ##attribute-ontology, ##source-ontology](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

##feature-ontology, ##attribute-ontology and ##source-ontology name ontologies by URI. The validator never fetches URIs during validation; types are checked against the pinned SO release and the directive is reported.

Example (invalid):

```text
##feature-ontology http://song.cvs.sourceforge.net/viewvc/*checkout*/song/ontology/so.obo?revision=1.263
```

Fix: None needed; to use another ontology, supply it locally (planned option).

Notes: The release URIs in the specification (SourceForge CVS) are dead. Should the specification list current SO release URIs (PURLs with version), and how should a file that names an old release be validated? As proposed in question 13, ##feature-ontology is validated against the release in use (bundled, or --so), and the note names it.

### GFF-DIR-010

**Unknown directive**

- Level: info; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: directives](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

Application-specific directives are allowed and need not be supported; unknown ones are reported for information.

Example (invalid):

```text
##date 2026-10-08
```

Fix: None needed.

Notes: Directives defined elsewhere (GVF ##file-version, ##reference-fasta) could be listed as known by profile.

## GFF-STR

Structure: IDs, references and bounds

| Id | Level | Status | Title |
|---|---|---|---|
| [GFF-STR-001](#gff-str-001) | error | implemented | IDs are unique, except for the lines of one discontinuous feature |
| [GFF-STR-002](#gff-str-002) | warning | implemented | Lines of one feature share seqid and strand |
| [GFF-STR-003](#gff-str-003) | warning | implemented | Lines of one feature have the same Parent |
| [GFF-STR-004](#gff-str-004) | error | implemented | Parent refers to an ID in the file |
| [GFF-STR-005](#gff-str-005) | error | implemented | Derives_from refers to an ID in the file |
| [GFF-STR-006](#gff-str-006) | error | implemented | No Parent cycles |
| [GFF-STR-007](#gff-str-007) | warning | implemented | No Derives_from cycles |
| [GFF-STR-008](#gff-str-008) | error | implemented | Features are within their ##sequence-region |
| [GFF-STR-009](#gff-str-009) | info | implemented | seqid without ##sequence-region |
| [GFF-STR-010](#gff-str-010) | warning | implemented | seqids appear in the ##FASTA section |
| [GFF-STR-011](#gff-str-011) | error | implemented | Features fit within the embedded sequence |
| [GFF-STR-012](#gff-str-012) | info | planned | Child extends beyond its parent |
| [GFF-STR-013](#gff-str-013) | warning | planned | Parent and child are on the same seqid |

### GFF-STR-001

**IDs are unique, except for the lines of one discontinuous feature**

- Level: error; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 9: ID; Change Log 1.20](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

IDs must be unique within the file. The same ID may appear on several lines only when those lines collectively represent a single discontinuous feature (for example the segments of a CDS or a cDNA_match). Lines sharing an ID with different types are two features with one ID.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=x1
ctg1→.→mRNA→1→90→.→+→.→ID=x1;Parent=x1
```

Valid:

```text
ctg1→.→CDS→1→30→.→+→0→ID=c1;Parent=t1
ctg1→.→CDS→61→90→.→+→0→ID=c1;Parent=t1
```

Fix: Give each feature its own ID.

Notes: The specification does not say what lines of one feature must share. Proposal: same type is required (error); seqid, strand and Parent differences are GFF-STR-002 and GFF-STR-003. Is that the intended reading? IDs are compared after percent-decoding; confirm. Until SO answers, lines sharing an ID with different types are reported (one finding per later line); IDs, Parent and Derives_from values are compared after percent- decoding.

### GFF-STR-002

**Lines of one feature share seqid and strand**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Pathological Cases: trans-spliced transcript](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#pathological-cases) (gff3)

Lines with the same ID describe one feature; a change of seqid or strand between them is unusual.

Example (invalid):

```text
chr1→.→CDS→1→30→.→+→0→ID=c1;Parent=t1
chr2→.→CDS→61→90→.→-→0→ID=c1;Parent=t1
```

Fix: Check that the lines are parts of the same feature.

Notes: Trans-splicing between strands or chromosomes is biologically real; the specification's trans-splicing example stays on one strand and seqid. Should a change of seqid or strand be allowed, warned or an error? Implemented as a warning until SO answers question 8.

### GFF-STR-003

**Lines of one feature have the same Parent**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Canonical Gene](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-canonical-gene) (gff3)

A single feature has one set of parents; lines with the same ID but different Parent values are probably different features.

Example (invalid):

```text
ctg1→.→CDS→1→30→.→+→0→ID=c1;Parent=t1
ctg1→.→CDS→61→90→.→+→0→ID=c1;Parent=t2
```

Fix: Give the features different IDs, or the same Parent list.

Notes: Can the Parent list legitimately be split across the lines of a feature (the union being the parents)? Implemented as a warning until SO answers. For GFF-STR-006 the union of the Parent lists is used.

### GFF-STR-004

**Parent refers to an ID in the file**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Parent (part_of) Relationships](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#parent-part_of-relationships) (gff3)

Every Parent value is the ID of a feature in the same file. Forward references are allowed (up to "###" or the end of the file).

Example (invalid):

```text
ctg1→.→exon→1→90→.→+→.→Parent=mRNA0001
```

Fix: Add the parent feature, or correct the ID (IDs are case sensitive).

Notes: Checked at the end of the file; a reference that crosses a ### is GFF- DIR-003. One finding per missing ID, at its first reference, with the number of other referencing lines.

### GFF-STR-005

**Derives_from refers to an ID in the file**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Pathological Cases: polycistronic transcripts, intein](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#pathological-cases) (gff3)

Every Derives_from value is the ID of a feature in the same file.

Example (invalid):

```text
chrX→.→polypeptide→1→90→.→+→.→ID=p1;Derives_from=cds99
```

Fix: Add the feature it derives from, or correct the ID.

Notes: Checked at the end of the file, like GFF-STR-004. Commas in Derives_from are read as separators (question 5).

### GFF-STR-006

**No Parent cycles**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Parent (part_of) Relationships](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#parent-part_of-relationships) (gff3)

A set of Parent relationships that forms a cycle (including a feature that is its own parent) must be rejected.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=a;Parent=b
ctg1→.→mRNA→1→90→.→+→.→ID=b;Parent=a
```

Fix: Remove the Parent that closes the loop.

Notes: Checked at the end of the file by an iterative depth-first search over the Parent graph of features with IDs (no recursion limit). A cycle is reported at the line of its first-defined feature.

### GFF-STR-007

**No Derives_from cycles**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Pathological Cases](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#pathological-cases) (gff3)

A feature that (indirectly) derives from itself is probably an error.

Example (invalid):

```text
chrX→.→polypeptide→1→90→.→+→.→ID=p1;Derives_from=p2
chrX→.→polypeptide→1→90→.→+→.→ID=p2;Derives_from=p1
```

Fix: Remove the Derives_from that closes the loop.

Notes: The specification forbids Parent cycles only. Should Derives_from cycles be an error too? Implemented as a warning, with the same search as GFF-STR-006, until SO answers question 12.

### GFF-STR-008

**Features are within their ##sequence-region**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##sequence-region](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

When a ##sequence-region is given for a seqid, every feature on it lies within that range, unless the landmark is marked Is_circular.

Example (invalid):

```text
##sequence-region ctg1 1 1000
ctg1→.→gene→900→1200→.→+→.→ID=g1
```

Fix: Correct the coordinates or the ##sequence-region bounds.

Notes: For a circular landmark, the bound is presumably 2 x length (end = position past the origin + length); confirm. Until SO answers question 10, features before the directive are also checked, and when any feature on the seqid has Is_circular=true (which feature is the landmark is open, GFF-ATT-017) only the start is checked; no 2 x length bound is applied. At most 100 lines per seqid beyond the end are listed, then a count.

### GFF-STR-009

**seqid without ##sequence-region**

- Level: info; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##sequence-region](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

The directive is optional but strongly encouraged; when some seqids have one and others do not, the others cannot be bounds-checked.

Example (invalid):

```text
##sequence-region ctg1 1 1000
ctg2→.→gene→1→90→.→+→.→ID=g1
```

Fix: Add ##sequence-region lines for all sequences (optional).

Notes: Reported only when the file has at least one ##sequence-region; once per seqid, at its first feature.

### GFF-STR-010

**seqids appear in the ##FASTA section**

- Level: warning; layer: core; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Other Syntax: ##FASTA](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

When the file has a ##FASTA section, features normally refer to sequences in it.

Example (invalid):

```text
ctg2→.→gene→1→4→.→+→.→ID=g1
##FASTA
>ctg1
ACGT
```

Fix: Add the sequence, or correct the seqid.

Notes: Not required by the specification; the FASTA section may hold only some sequences (for example protein Targets). Warning or info? Implemented as a warning, once per seqid, at its first feature. The seqid is matched as written, then percent-decoded (question 3).

### GFF-STR-011

**Features fit within the embedded sequence**

- Level: error; layer: core; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##FASTA](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

A feature's end is not beyond the length of its sequence in the ##FASTA section, unless the landmark is circular.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
##FASTA
>ctg1
ACGT
```

Fix: Correct the coordinates or the sequence.

Notes: Reported once per seqid, at the feature that reaches furthest. For a seqid with Is_circular=true only the start is checked.

### GFF-STR-012

**Child extends beyond its parent**

- Level: info; layer: core; status: planned; review: pending-SO; **needs SO input**
- Reference: [Parent (part_of) Relationships](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#parent-part_of-relationships) (gff3)

GFF3 does not require features to lie within their parents (for example an enhancer part of a gene). Reported as information only.

Example (invalid):

```text
ctg1→.→gene→100→200→.→+→.→ID=g1
ctg1→.→mRNA→50→200→.→+→.→ID=t1;Parent=g1
```

Fix: None required; check the coordinates if containment was expected.

Notes: Other validators treat this as an error (GFF3toolkit Ema0001/Ema0003). Could SO identify the types for which containment is expected (exon in transcript), so a warning could be given for those only?

### GFF-STR-013

**Parent and child are on the same seqid**

- Level: warning; layer: core; status: planned; review: pending-SO; **needs SO input**
- Reference: [Parent (part_of) Relationships](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#parent-part_of-relationships) (gff3)

A part-of relationship across sequences is unusual.

Example (invalid):

```text
chr1→.→gene→1→90→.→+→.→ID=g1
chr2→.→mRNA→1→90→.→+→.→ID=t1;Parent=g1
```

Fix: Check the seqid or the Parent.

Notes: Not addressed by the specification (trans-splicing across chromosomes exists).

## SO

Sequence Ontology

| Id | Level | Status | Title |
|---|---|---|---|
| [SO-001](#so-001) | warning | implemented | type is an SO term name or accession |
| [SO-002](#so-002) | error | implemented | SO accession is well formed |
| [SO-003](#so-003) | warning | implemented | type is sequence_feature or a subtype |
| [SO-004](#so-004) | warning | implemented | type is not obsolete |
| [SO-005](#so-005) | warning | implemented | type is a synonym or case variant of an SO label |
| [SO-006](#so-006) | warning | implemented | Parent relationship is an SO part_of relationship |
| [SO-007](#so-007) | info | planned | Derives_from relationship is an SO derives_from relationship |
| [SO-008](#so-008) | warning | implemented | SO terms in Ontology_term are valid |
| [SO-009](#so-009) | info | implemented | type is outside SOFA |

### SO-001

**type is an SO term name or accession**

- Level: warning; layer: so; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 3: type](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The type is a term from the Sequence Ontology or an SO accession (SO:0000704), checked against the bundled SO release (or the so.obo given with --so), which every report names.

Example (invalid):

```text
ctg1→.→protein_coding_gene_model→1→90→.→+→.→ID=g1
```

Fix: Use an SO term (for example gene, mRNA) or accession; see the suggestions in the message.

Notes: Exact label matching is case sensitive ("CDS"); the specification's NOTE 1 table writes "cds". Are exact synonyms (EXACT in so.obo) acceptable as types? Are labels with spaces valid? Unknown types in SOFA but not SO? Implemented as proposed in question 14: the exact label or accession matches; a case variant or EXACT synonym is SO-005, not this rule; up to three close labels are suggested. A warning, not an error, until SO answers: the specification constrains the type to an SO term but does not say which release (question 13), and terms are renamed between releases (lnc_RNA, used by NCBI and Ensembl, is now lncRNA and not a synonym), and the specification's own Gap example uses nucleotide_to_protein_match, which is not an SO term. A type of "." is GFF-SYN-012 only.

### SO-002

**SO accession is well formed**

- Level: error; layer: so; status: implemented; review: pending-SO
- Reference: [Column 3: type (SO:000000 syntax)](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

An accession type has the form SO:NNNNNNN (seven digits).

Example (invalid):

```text
ctg1→.→SO:704→1→90→.→+→.→ID=g1
```

Fix: Write the accession as SO: followed by seven digits (for example SO:0000704).

Notes: The specification writes "SO:000000" (six zeros) as the pattern; SO accessions have seven digits. Any type starting with "SO:" (in any case) that is not SO: and seven digits is reported; a well-formed accession that is not in the release is SO-001.

### SO-003

**type is sequence_feature or a subtype**

- Level: warning; layer: so; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 3: type; Change Log 1.23](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The type must be sequence_feature (SO:0000110) or an is_a descendant of it, not, for example, an SO attribute or a variant effect term.

Example (invalid):

```text
ctg1→.→coding_sequence_variant→1→90→.→+→.→ID=v1
```

Fix: Use a located sequence feature type.

Notes: Confirm that only is_a (not part_of) descendants count, and how GVF types (sequence_alteration is a sequence_feature) and terms outside SOFA are treated. Implemented as proposed in question 14 (is_a descendants only), as a warning until SO confirms; obsolete terms are SO-004 instead, and terms outside SOFA are SO-009.

### SO-004

**type is not obsolete**

- Level: warning; layer: so; status: implemented; review: pending-SO; **needs SO input**
- Reference: [so.obo is_obsolete, replaced_by, consider](https://github.com/The-Sequence-Ontology/SO-Ontologies/blob/4340c143bac3578bba0c013d02e8c5f0e51ad14a/Ontology_Files/so.obo) (so)

Obsolete SO terms are reported with their replaced_by or consider suggestions from the pinned release.

Example (invalid):

```text
ctg1→.→RNA_polymerase_promoter→1→90→.→+→.→ID=p1
```

Fix: Use the suggested replacement term. The validator never rewrites the type.

Notes: RNA_polymerase_promoter (SO:0001203) is obsolete in so.obo data-version 2026-08-07, replaced by promoter. Implemented as proposed in question 13; an obsolete type is not also reported by SO-003 or SO-009.

### SO-005

**type is a synonym or case variant of an SO label**

- Level: warning; layer: so; status: implemented; review: pending-SO; **needs SO input**
- Reference: [so.obo name and synonym](https://github.com/The-Sequence-Ontology/SO-Ontologies/blob/4340c143bac3578bba0c013d02e8c5f0e51ad14a/Ontology_Files/so.obo) (so)

The type matches an SO synonym or differs from a label only by case; the label is preferred.

Example (invalid):

```text
ctg1→.→five_prime_utr→1→90→.→+→.→Parent=t1
```

Fix: Use the SO label named in the message (for example five_prime_UTR for 5'UTR).

Notes: Depends on the SO-001 decision on synonyms. Implemented as proposed in question 14: a type that differs from a label only by case, or that equals an EXACT synonym (compared ignoring case), is reported with the label. A unique match is then treated as that term by the other SO rules (SO-003, SO-004, SO-006, SO-009) but not by the CDS, exon and recoded_codon checks, which need the exact label or accession. A synonym of several terms lists them and is not checked further.

### SO-006

**Parent relationship is an SO part_of relationship**

- Level: warning; layer: so; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Parent (part_of) Relationships; Canonical Gene NOTE 2](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#parent-part_of-relationships) (gff3)

Features must respect SO part-of relationships: the child's type should be part_of the parent's type (directly, through is_a inheritance, or by the transitivity of part_of, so an exon can be attached to a gene).

Example (invalid):

```text
ctg1→.→mRNA→1→90→.→+→.→ID=t1;Parent=e1
ctg1→.→exon→1→90→.→+→.→ID=e1
```

Fix: Check the Parent; for example, an exon is part of a transcript, not the reverse.

Notes: The specification says such a Parent "should trigger a parse exception", but SO does not enumerate every permitted annotation model (the operon example notes promoters could not be part_of an operon). Which relations and inference (part_of, member_of, has_part inverses, is_a, transitivity) define "allowed"? Until SO decides, this is a warning, not an error. Implemented as proposed in question 15: a Parent is allowed when the child's type, or an is_a ancestor of it, is part_of the Parent's type or an is_a ancestor of it, directly or through a chain of such steps. SO relates transcripts to genes only through gene_member_region member_of gene, so member_of is followed like part_of; with part_of alone the specification's canonical gene (mRNA Parent=gene) would be reported. has_part inverses are not used. Types that are unknown, ambiguous synonyms or obsolete are not checked. One finding per pair of child and Parent types, at the first line, with a count.

### SO-007

**Derives_from relationship is an SO derives_from relationship**

- Level: info; layer: so; status: planned; review: pending-SO; **needs SO input**
- Reference: [Pathological Cases: intein](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#pathological-cases) (gff3)

The feature's type derives_from the referenced feature's type in SO (for example polypeptide derives_from mRNA or CDS).

Example (invalid):

```text
chrX→.→exon→1→90→.→+→.→ID=e1;Derives_from=g1
```

Fix: Check the relationship; use Parent for part-of.

Notes: The Perl validator disabled this check. The specification's examples have CDS Derives_from gene and mature_polypeptide Derives_from gene, which may not be derives_from relations in SO. Should this be checked at all? Not checked, as proposed in question 16; reports list the rule as not checked.

### SO-008

**SO terms in Ontology_term are valid**

- Level: warning; layer: so; status: implemented; review: pending-SO
- Reference: [Pathological Cases: programmed frameshift](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#pathological-cases) (gff3)

Ontology_term values with the SO prefix name terms in the pinned release (for example SO:1000069 on a frameshifted mRNA).

Example (invalid):

```text
chrX→.→mRNA→1→90→.→+→.→ID=t1;Ontology_term=SO:9999999
```

Fix: Use an existing SO accession.

Notes: Values with the DBTAG "SO" that are not SO: and seven digits, or not a term in the release, are reported once per value. Obsolete terms are not reported: the specification's own example, SO:1000069, is obsolete in so.obo data-version 2026-08-07.

### SO-009

**type is outside SOFA**

- Level: info; layer: so; status: implemented; review: pending-SO; **needs SO input**
- Reference: [so.obo subset SOFA](https://github.com/The-Sequence-Ontology/SO-Ontologies/blob/4340c143bac3578bba0c013d02e8c5f0e51ad14a/Ontology_Files/so.obo) (so)

The type is an SO term that is not in SOFA, the SO subset for feature annotation that GFF3 historically referenced. Such types are valid; the note helps tools that accept only SOFA.

Example (invalid):

```text
ctg1→.→protein_coding_gene→1→90→.→+→.→ID=g1
```

Valid:

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
```

Fix: None needed; use a SOFA term if a downstream tool needs one.

Notes: Added for question 13, which proposes validating against full SO with a note for terms outside SOFA. Reported once per type, at the first line, with a count.

## BIO

Biology (optional, with --genome)

| Id | Level | Status | Title |
|---|---|---|---|
| [BIO-001](#bio-001) | error | implemented | seqid is in the genome |
| [BIO-002](#bio-002) | error | implemented | Features fit within the genome sequence |
| [BIO-003](#bio-003) | warning | implemented | ##sequence-region agrees with the genome |
| [BIO-004](#bio-004) | warning | implemented | CDS phases are consistent |
| [BIO-005](#bio-005) | warning | implemented | CDS segments lie within exons |
| [BIO-006](#bio-006) | warning | implemented | CDS starts with a start codon |
| [BIO-007](#bio-007) | warning | implemented | CDS ends with a stop codon |
| [BIO-008](#bio-008) | warning | implemented | No internal stop codons |
| [BIO-009](#bio-009) | info | implemented | CDS length is a multiple of three |
| [BIO-010](#bio-010) | warning | implemented | Strand is consistent within a gene |
| [BIO-011](#bio-011) | info | implemented | Biology checks skipped |

### BIO-001

**seqid is in the genome**

- Level: error; layer: biology; status: implemented; review: pending-SO
- Reference: [FR-003, FR-005](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/009-gff3-validator/spec.md#requirements-mandatory) (spec009)

Every seqid names a sequence in the genome supplied with --genome.

Example (invalid):

```text
Chr1→.→gene→1→90→.→+→.→ID=g1   (genome has chr1)
```

Fix: Use the genome the annotation was made on, or the same sequence names. The validator does not map names.

Notes: Seqids of feature lines and of ##sequence-region lines are looked up as written and then percent-decoded; names are never mapped (chr1 and 1 differ). When no seqid matches, the genome is probably the wrong one: one BIO-001 error is reported for the file instead of one per seqid, and the codon checks are skipped (BIO-011), not failed.

### BIO-002

**Features fit within the genome sequence**

- Level: error; layer: biology; status: implemented; review: pending-SO
- Reference: [Columns 4 & 5: start and end](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

A feature's end is not beyond the length of its sequence in the genome, unless the landmark is circular.

Example (invalid):

```text
chr1→.→gene→1→2000→.→+→.→ID=g1   (chr1 is 1500 bp)
```

Fix: Check the genome version and coordinates.

Notes: On a circular landmark (Is_circular=true) only the start must lie within the sequence. Reported once per seqid, for the furthest feature, as GFF-STR-011 does for the ##FASTA section; a CDS beyond the sequence is not translated (BIO-011).

### BIO-003

**##sequence-region agrees with the genome**

- Level: warning; layer: biology; status: implemented; review: pending-SO
- Reference: [Other Syntax: ##sequence-region](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#other-syntax) (gff3)

A ##sequence-region covering a whole sequence has the genome sequence's length.

Example (invalid):

```text
##sequence-region chr1 1 2000   (chr1 is 1500 bp)
```

Fix: Check the genome version.

Notes: A sequence-region may cover only part of a sequence, so only a region longer than the sequence is certain to be wrong. Not reported for a circular landmark, whose bound is an open question (question 10).

### BIO-004

**CDS phases are consistent**

- Level: warning; layer: biology; status: implemented; review: pending-SO; **needs SO input**
- Reference: [Column 8: phase](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

Along a CDS (all lines with one ID, in 5' to 3' order on its strand), the phase of each segment follows from the previous segments' lengths and phases: phase(n+1) = (3 - ((length(n) - phase(n)) mod 3)) mod 3.

Example (invalid):

```text
ctg1→.→CDS→1→31→.→+→0→ID=c1
ctg1→.→CDS→61→90→.→+→0→ID=c1
```

Fix: Recompute phases from the segment lengths (here the second phase is 2).

Notes: Phase is not frame. Programmed frameshifts (the specification's example resets phase to 0), ribosomal slippage and partial CDS at the 5' end break the formula; the first segment of a 5'-partial CDS may have any phase. Is this a warning, and which annotations exempt it? Implemented as a warning: a CDS is the CDS lines sharing an ID or, for lines without ID, sharing a Parent list (grouping by Parent alone would merge cds00003 and cds00004 of the canonical gene, which share mRNA00003). Segments are ordered by start on + and by end on -, and the first segment's phase is not judged. A CDS on strand . or ?, with a missing phase or with lines on different seqids or strands is skipped and counted in BIO-011. Segments are kept until the next ### or the end of the file (memory: about 40 bytes per CDS line). When phases are inconsistent, stop codons (BIO-007, BIO-008) are not checked, since the annotation then implies a frameshift.

### BIO-005

**CDS segments lie within exons**

- Level: warning; layer: biology; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Canonical Gene](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-canonical-gene) (gff3)

When a transcript has exon children, each CDS segment of that transcript lies within one of its exons.

Example (invalid):

```text
ctg1→.→exon→100→200→.→+→.→Parent=t1
ctg1→.→CDS→150→250→.→+→0→ID=c1;Parent=t1
```

Fix: Correct the CDS or exon coordinates.

Notes: Does not need the genome (it could move to the structure layer) but runs with the biology layer. Implemented as a warning: each CDS segment is compared with the exons whose Parent is a Parent of the CDS, collected until the next ### or the end of the file. Not applicable when the exon features are omitted (single-exon case in Pathological Cases).

### BIO-006

**CDS starts with a start codon**

- Level: warning; layer: biology; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Canonical Gene NOTE 5; Change Log 1.13](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-canonical-gene) (gff3)

When a CDS is complete, its first three bases are a start codon under the translation table chosen with --translation-table. Start and stop codons are included in the CDS.

Example (invalid):

```text
CDS 1..90 on +, genome bases 1..3 are CCC
```

Fix: Check the CDS start; mark partial CDS as such.

Notes: GFF3 has no standard way to mark a partial CDS (attributes such as partial=true or start_range are profile-specific). The table is never inferred from the organism. How should incompleteness be expressed? Implemented as a warning. Partial markers: INSDC will use partial=start, partial=end and partial=start,end (Terence Murphy, NCBI, in SO-Ontologies#685), replacing the GVF-derived start_range and end_range that NCBI has used; both, and partial=true, are honoured. A partial 5' end exempts this check, a partial 3' end exempts BIO-007, and either exempts BIO-009; exempted checks are counted in BIO-011. start_range and end_range refer to the low and high genomic ends. Until the INSDC draft says whether start and end are genomic or 5'/3', partial=start or partial=end on a minus- strand CDS exempts both ends. A CDS whose first segment has phase 1 or 2 starts inside a codon by definition and is not judged, and a codon with bases other than A, C, G and T is not judged. The default table is 1 (--translation-table N; bacteria, archaea and plastids use 11); tables 27, 28 and 31 are not offered because their stop codons depend on context. Translation exceptions follow the SO/NCBI discussion in SO-Ontologies#658 (pending SO confirmation, question 17): a codon wholly covered by a recoded_codon (SO:0000145) feature, or a subtype (stop_codon_read_through SO:0000883, stop_codon_redefined_as_selenocysteine SO:0000885, stop_codon_redefined_as_pyrrolysine SO:0000884), whose Parent is the CDS, is exempt; such a feature carries recoded_amino_acid=<amino acid name> and may be split across a splice junction as several lines with one ID. The legacy NCBI transl_except attribute on the CDS is honoured as a fallback. With the SO layer, recoded_codon and every is_a subtype of it in the SO release count (by exact label or accession; the three subtypes above are always included), as do CDS subtypes for the CDS and exon subtypes for BIO-005; the recoded_amino_acid value is not checked yet.

### BIO-007

**CDS ends with a stop codon**

- Level: warning; layer: biology; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Canonical Gene NOTE 5](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-canonical-gene) (gff3)

When a CDS is complete, its last three bases are a stop codon under the chosen translation table.

Example (invalid):

```text
CDS 1..90 on +, genome bases 88..90 are GGG
```

Fix: Check the CDS end; mark partial CDS as such.

Notes: Stop codons completed by polyadenylation (some mitochondrial genes) need an exception. Implemented as a warning, with the same partial-CDS caveat as BIO-006. Not judged when the coding length is not a multiple of three (BIO-009 reports that) or when the phases are inconsistent (BIO-004). A stop codon completed by polyadenylation is exempt when marked as a recoded codon (see BIO-006); BIO-009 is then not reported if the recoded codon covers the trailing partial codon.

### BIO-008

**No internal stop codons**

- Level: warning; layer: biology; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Canonical Gene](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-canonical-gene) (gff3)

The translated CDS has no in-frame stop codon before its end.

Example (invalid):

```text
CDS whose codon 10 is TAA under table 1
```

Fix: Check exon boundaries and phases; mark selenocysteine, pyrrolysine or readthrough with a recoded_codon child of the CDS.

Notes: Selenocysteine, pyrrolysine and stop-codon readthrough are legitimate; how should they be annotated so the check can exempt them? Kept at warning, not error, because legitimate recoding still exists in files that do not mark it. Translation exceptions follow the SO/NCBI discussion in SO-Ontologies#658 (pending SO confirmation, question 17): a codon wholly covered by a recoded_codon (SO:0000145) feature, or a subtype (stop_codon_read_through SO:0000883, stop_codon_redefined_as_selenocysteine SO:0000885, stop_codon_redefined_as_pyrrolysine SO:0000884), whose Parent is the CDS, is exempt; such a feature carries recoded_amino_acid=<amino acid name> and may be split across a splice junction as several lines with one ID. The legacy NCBI transl_except attribute on the CDS is honoured as a fallback. With the SO layer, recoded_codon and every is_a subtype of it in the SO release count (by exact label or accession; the three subtypes above are always included), as do CDS subtypes for the CDS and exon subtypes for BIO-005; the recoded_amino_acid value is not checked yet. The last complete codon is the terminal codon (BIO-007), never internal. One finding per CDS gives the first internal stop and the count.

### BIO-009

**CDS length is a multiple of three**

- Level: info; layer: biology; status: implemented; review: pending-SO
- Reference: [Column 8: phase](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#description-of-the-format) (gff3)

The coding length of a complete CDS (sum of segment lengths minus the first segment's phase) is a multiple of three.

Example (invalid):

```text
CDS segments 1..31 and 61..90 with phase 0
```

Fix: Check the coordinates.

Notes: Coding lengths are computed from the coordinates, so the genome is needed only to run the layer. The specification's canonical gene has two such CDS (cds00001 with 2305 and cds00002 with 1402 coding bases), so the example itself is reported (see the suggested corrections in questions-for-SO.md).

### BIO-010

**Strand is consistent within a gene**

- Level: warning; layer: biology; status: implemented; review: pending-SO; **needs SO input**
- Reference: [The Canonical Gene](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md#the-canonical-gene) (gff3)

The parts of a gene (transcripts, exons, CDS) are on the same strand as the gene.

Example (invalid):

```text
ctg1→.→gene→1→90→.→+→.→ID=g1
ctg1→.→mRNA→1→90→.→-→.→ID=t1;Parent=g1
```

Fix: Correct the strand.

Notes: Does not need the genome but runs with the biology layer. Trans-splicing and genes with strand "?" or "." are exceptions; error or warning? Implemented as a warning where both lines have strand + or -; the Parent's strand is that of its first line. As proposed in question 18, with the SO layer only Parent relations that SO-006 accepts (part_of or member_of, through is_a and transitivity) are checked; a relation SO-006 reports is skipped, and one involving a type the SO layer cannot resolve is still checked. Trans-splicing has no marker yet and is reported.

### BIO-011

**Biology checks skipped**

- Level: info; layer: biology; status: implemented; review: pending-SO
- Reference: [FR-005](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/009-gff3-validator/spec.md#requirements-mandatory) (spec009)

Reported when --genome was given but some biology checks could not run, with the reasons and counts (CDS on seqids not in the genome, on strand . or ?, with a missing phase, with lines on different seqids or strands, beyond the end of the sequence, or with inconsistent phases). Without --genome the whole biology layer is listed as not checked in the report. Skipped checks are never counted as passed.

Example (invalid):

```text
chr1→.→CDS→1→90→.→.→0→ID=c1   (with --genome; strand . has no 5' end)
```

Fix: Follow the reason given, for example give each CDS a strand and a phase, or use the genome the annotation was made on.

Notes: Without --genome no finding is emitted (it would be on every file); the report's skipped list says that the biology layer needs --genome. Table 1 is used when --translation-table is not given; the table is never inferred.

## HDR

FHGFF3 header (optional, FAIR-bioHeaders)

| Id | Level | Status | Title |
|---|---|---|---|
| [HDR-001](#hdr-001) | error | implemented | FHGFF3 header present when required |
| [HDR-002](#hdr-002) | info | implemented | FHGFF3 header present but not validated |
| [HDR-003](#hdr-003) | info | implemented | Header checks skipped (--no-header) |
| [HDR-004](#hdr-004) | error | planned | Header forms the leading block after ##gff-version |
| [HDR-005](#hdr-005) | error | planned | Header checksum verifies |
| [HDR-006](#hdr-006) | error | planned | Header lines are safe YAML |
| [HDR-007](#hdr-007) | error | planned | Header metadata matches the FHR schema |
| [HDR-008](#hdr-008) | error | planned | derivedFrom identifies the annotated genome |
| [HDR-009](#hdr-009) | error | planned | derivedFrom matches the supplied genome |

### HDR-001

**FHGFF3 header present when required**

- Level: error; layer: fhgff3; status: implemented; review: pending-SO
- Reference: [FR-001](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/007-gff3-header/spec.md#requirements-mandatory) (spec007)

With --require-header the file must carry a FAIR-bioHeaders header (#~ lines). Without the option a file without a header is plain GFF3 and valid.

Example (invalid):

```text
gff3-validate --require-header plain.gff3
```

Fix: Add a header with the FAIR-bioHeaders toolkit, or drop --require-header.

### HDR-002

**FHGFF3 header present but not validated**

- Level: info; layer: fhgff3; status: implemented; review: pending-SO
- Reference: [FR-006](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/009-gff3-validator/spec.md#requirements-mandatory) (spec009)

The file has #~ header lines, but header validation is not available in this version (it needs the headers extra and FHGFF3 support in the FAIR-bioHeaders toolkit). The header is neither accepted nor rejected.

Example (invalid):

```text
##gff-version 3
#~schema: https://...
ctg1→.→gene→1→90→.→+→.→ID=g1
```

Fix: None in this version; validate the header with the toolkit when FHGFF3 support is released.

### HDR-003

**Header checks skipped (--no-header)**

- Level: info; layer: fhgff3; status: implemented; review: pending-SO
- Reference: [FR-006](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/009-gff3-validator/spec.md#requirements-mandatory) (spec009)

Header checks were skipped on request; #~ lines are treated as ordinary comments.

Example (invalid):

```text
gff3-validate --no-header annotated.gff3
```

Fix: None needed.

### HDR-004

**Header forms the leading block after ##gff-version**

- Level: error; layer: fhgff3; status: planned; review: pending-SO
- Reference: [FR-001; FORMAT.md R10](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/007-gff3-header/spec.md#requirements-mandatory) (spec007)

The first line stays ##gff-version 3; #~ lines follow it and form the leading header block, which ends at the first feature line or ##FASTA. ##sequence-region and other ## directives and comments may appear among the #~ lines. A #~ line later in the file (for example from concatenation) makes the file invalid FHGFF3 (R10).

Example (invalid):

```text
##gff-version 3
ctg1→.→gene→1→90→.→+→.→ID=g1
#~checksum: ...
```

Fix: Strip the header and combine it again with the FAIR-bioHeaders toolkit.

Notes: Delegated to the FAIR-bioHeaders toolkit once it supports GFF3; not a GFF3 core rule.

### HDR-005

**Header checksum verifies**

- Level: error; layer: fhgff3; status: planned; review: pending-SO
- Reference: [R1 to R5](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/docs/FORMAT.md) (fhr-format)

Exactly one root-level #~checksum line; SHA-512/256 over the exact decompressed bytes of the whole file, including any ##FASTA section, excluding that line, in padded base64 (R1 to R5).

Example (invalid):

```text
#~checksum: (value that does not match the file)
```

Fix: If the annotation changed on purpose, recompute the header with the toolkit; otherwise the file was altered.

### HDR-006

**Header lines are safe YAML**

- Level: error; layer: fhgff3; status: planned; review: pending-SO
- Reference: [R6 to R8](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/docs/FORMAT.md) (fhr-format)

Header lines are UTF-8 without YAML line-break characters; no byte order mark; no duplicate keys, anchors, aliases or merge keys (R6 to R8).

Example (invalid):

```text
#~name: a
#~name: b
```

Fix: Remove the duplicate or unsafe construct.

### HDR-007

**Header metadata matches the FHR schema**

- Level: error; layer: fhgff3; status: planned; review: pending-SO
- Reference: [FR-003, FR-004](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/007-gff3-header/spec.md#requirements-mandatory) (spec007)

The header metadata validates against the FAIR-bioHeaders schema for the FHGFF3 subject (annotation).

Example (invalid):

```text
#~annotation: (missing required fields)
```

Fix: Add the required fields reported by the schema.

### HDR-008

**derivedFrom identifies the annotated genome**

- Level: error; layer: fhgff3; status: planned; review: pending-SO
- Reference: [FR-003](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/007-gff3-header/spec.md#requirements-mandatory) (spec007)

FHGFF3 requires derivedFrom with relationship "annotates", giving either the genome's FHR checksum or its accession plus SeqCol ID.

Example (invalid):

```text
#~derivedFrom: [] 
```

Fix: Record the genome's FHR checksum, or its accession and SeqCol ID.

### HDR-009

**derivedFrom matches the supplied genome**

- Level: error; layer: fhgff3; status: planned; review: pending-SO
- Reference: [FR-003; spec 009 FR-006](https://github.com/FAIR-bioHeaders/FHR-Specification/blob/main/specs/007-gff3-header/spec.md#requirements-mandatory) (spec007)

With --genome, the genome's FHR checksum (or SeqCol ID, when that is what the header records) matches derivedFrom. An accession plus SeqCol ID is not an FHR file checksum and is reported as such.

Example (invalid):

```text
gff3-validate --genome other_assembly.fa annotated.gff3
```

Fix: Use the genome named in the header.
