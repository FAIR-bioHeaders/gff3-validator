# The feature-layer index (`gff3_validator.features`)

Design note for [issue #31](https://github.com/FAIR-bioHeaders/gff3-validator/issues/31).
It states the contract of the public feature-index API before the implementation,
because the contract is the thing four language libraries will code against.

The feature layer is the region of a GFF3 file **below** the header: the
tab-separated feature rows. FHGM **K4** — a model record's `featureId` resolves
to exactly one local `gene` row — is a question about that layer, and only about
that layer. Answering it needs row enumeration and row counting, not validation,
so it is exposed as an index rather than as a rule. **No rule id is added or
changed by this API**: the questions it answers are not catalogue rules, and the
catalogue in [docs/rules.md](rules.md) stays the public contract for what makes a
file valid GFF3.

## What the index does

```python
from gff3_validator import build_feature_index, resolve_feature_id

index = build_feature_index("annotation.gff3")     # path, "-" or a binary stream
match = index.resolve("gene:A,B")                 # one K4 predicate
match = resolve_feature_id("annotation.gff3", "gene:A%2CB")        # both steps
```

It reads each feature row and records the facts a pointer target needs:

| field | source |
|---|---|
| `line` | 1-based line number of the row |
| `seqid`, `source`, `type`, `strand`, `score`, `phase` | columns 1, 2, 3, 7, 6, 8, as written |
| `start`, `end` | columns 4 and 5 as integers, `None` when they are not whole numbers (not judged, only carried) |
| `raw_id` | the `ID=` value as written, percent escapes intact |
| `id` | `raw_id` percent-decoded — the form K4 compares |
| `parents` | the decoded `Parent=` values |
| `is_gene` | `type` is `gene` or `SO:0000704`, as a literal string test |

Rows without an `ID` are counted and enumerated but not addressable: a pointer
resolves against identifiers, and an anonymous row carries none. Iteration stops
at the `##FASTA` line; blank lines and every line starting with `#` — which is
the FHGFF3 header block (`#~`) and the `##` directives — are not feature rows.
These two rules match the FHGM authoring checker
(`FHGM-Specification/development/model/validate_fhgm.py`, `gene_targets`) and the
JavaScript library's local resolver (`src/features.js`), so the three count the
same rows.

## The outcomes, and the property that matters

`index.resolve(feature_id)` returns exactly one outcome:

| outcome | meaning | scored against the header? |
|---|---|---|
| `found` | exactly one row carries the decoded ID **and** it is a gene row | yes — this is K4 satisfied |
| `not-found` | the layer is usable; no row carries the decoded ID | yes — K4 not satisfied |
| `duplicate-row` | the layer is usable; more than one row carries the decoded ID | yes — K4 not satisfied |
| `non-gene-target` | exactly one row carries it, and that row is not a gene row | yes — K4 not satisfied |
| `malformed-layer` | rows were read, but at least one is not a nine-field feature row, so no row count can be trusted | **no** |
| `absent-layer` | there is no layer to index: the input could not be read (missing file, truncated or corrupt stream), or it holds no feature rows at all | **no** |

```python
from gff3_validator.features import NOT_SCORED_OUTCOMES, SCORED_OUTCOMES
```

**The load-bearing property: `absent-layer` and `malformed-layer` never score as
a pass and never score as a rejection.** They are reported by
`index.state` / `NOT_SCORED_OUTCOMES`, and a consumer must carry them as
`not-checked` — a header whose file it cannot see is neither certified nor
indicted. This is why the two are separate outcomes and not one: *nobody is
home* (absent) and *something is home but the shelves are in a heap* (malformed)
are different repairs, and a consumer that flattens them loses the reason it
could not check. Collapsing either into `pass` would certify a header against an
index that was never read; collapsing either into `not-found` would reject a
header for the validator's own blindness. `FeatureMatch.scored` is `False` for
both, and `FeatureMatch.passes` is `True` only for `found`.

A partially read input is `absent-layer`, not `malformed-layer`: a stream that
raised `InputError` mid-file may have skipped rows *and* may have skipped a
field-count defect, so the reason is recorded and nothing is counted.

Two details of the four scored outcomes:

- **The count is checked before the type.** Three rows sharing one ID where one
  of them is a gene row is `duplicate-row`, not `non-gene-target`: what K4
  cannot accept is that the pointer does not select one row. The same precedence
  is in the FHGM checker (`len(types) != 1 or types[0] not in (gene, SO:0000704)`).
- **`malformed-layer` is all-or-nothing for the whole file**, not per row. K4 is
  a counting predicate; if one row of the layer cannot be read, the count is not
  trustworthy, so the index refuses to answer rather than answering from the
  rows it happened to like. The unreadable rows are listed in `index.problems`
  with their line numbers; the catalogue's own syntax rules (GFF-SYN-003/-004)
  are what judge them.

## Percent-decoding: decoded on both sides

GFF3 escapes the characters that would break column 9, so a gene row writes
`ID=gene:A%2CB` for the identifier `gene:A,B` (a comma is reserved there and
must be escaped). An FHGM `featureId` is a YAML string, not a column-9 value, and
nothing forces its author to repeat the file's escaping. The index therefore
**percent-decodes both sides and compares identifiers**:

```python
decoded_row    = unquote(row["ID"] value as written)     # index key
decoded_target = unquote(feature_id)                     # lookup
```

Three candidate semantics exist, and the choice should be visible:

1. **Raw lookup on both sides** — compare the header string to the column-9
   bytes. This makes K4 a test of *spelling*: a correct model record written
   `featureId: gene:A,B` fails against a correct file that escapes the comma.
2. **Decode the file side only** — what the FHGM authoring checker does today
   (`unquote_to_bytes` on the row, a raw `featureId.encode()` lookup). It fixes
   half of case 1 and leaves the other half: the identifier is decoded when it
   comes from the file and left as written when it comes from the header, so the
   comparison is still a spelling test whenever the header escapes anything.
3. **Decode both sides** — chosen. Equality is then about the identifier, which
   is what "resolves to" means, and it is symmetric: neither side's serialization
   can decide the verdict.

Cases 2 and 3 coincide on every vector in the FHGM suite as it stands — the
vectors escape on neither side or on both — which is exactly why the choice was
never forced into the open. It is a decision in principle, so it is recorded here
and tested explicitly by
`tests/fixtures/features/percent_encoded_target.gff3` (a row
`ID=gene:A%2CB`) resolved by the decoded target `gene:A,B`, in
`tests/test_features.py::test_encoded_record_id_matches_literal_row`. That test
asserts the counterfactual as well: `gene:A%2CB` is what the row carries, so
semantics 2 looking the raw header string up in the file's as-written values finds
nothing and would report `not-found`, where this index reports `found`.

Two consequences of decoding both sides, both intended:

- Identifiers that differ **only** by the case of an escape's hex digits collapse
  onto one key (`gene:C%3BB` and `gene:C%3bB` are the identifier `gene:C;B`), so a
  layer that carries both now yields `duplicate-row`. Ambiguity surfaces as a
  scored rejection of the pointer rather than as a silent first match.
  `tests/fixtures/features/escape_case_collision.gff3` is that file, and note what
  it is *not*: it is valid GFF3, because one feature may occupy disjunct
  intervals, so `duplicate-row` is a verdict about the pointer selecting one row,
  never a restatement of `GFF-STR-001`.
- A malformed escape (`%2zz`, `%2`) is left as written by `urllib.parse.unquote`
  instead of raising: identifiers are data, and a target that carries the same
  broken escape matches the row that carries it
  (`tests/fixtures/features/invalid_escape.gff3`).

## What the index explicitly does not do

- **No header parsing.** The FHGFF3 header (`#~` lines) is read by the
  FAIR-bioHeaders toolkit; `gff3_validator/header.py` delegates to it and this
  module never looks at a `#~` line as anything but a comment. The index is the
  layer *below* the header, and growing a second header implementation into the
  validator is the failure mode this boundary exists to prevent.
- **No findings, no rule ids, no severity.** The index reports facts and a
  K4-shaped outcome. It does not emit `Finding`s, does not touch
  `rules/catalogue.yaml`, and does not change any existing rule's verdict or
  level. Running it on a file cannot change whether that file is valid GFF3.
- **No SO validation.** `is_gene` is a literal test of the type column against
  `gene` / `SO:0000704` — the two spellings the FHGM K-layer accepts — with no
  ontology loaded. A row typed `protein_coding_gene` is not a gene row for K4;
  whether a type is a real SO term is `SO-001`'s and `GFF-SYN-012`'s business.
  The index works with no `data/so.json.gz` and no `--so`.
- **No coordinate biology, no `Parent` graph, no duplicate-identifier rule.**
  Out-of-range coordinates, unresolved parents, cycles, interval overlap and
  duplicate IDs stay the 91-rule catalogue's job (structure, attributes,
  sequence-ontology, biology and profile layers). `start`/`end` are carried
  unparsed-by-judgement; nothing here says whether they are sane.
- **No network, no new dependencies.** Standard library plus this package's own
  reader and attribute parser, so it stays offline, and reads plain, gzip and
  BGZF input the same way the validator does.
- **Not a replacement for a validation run.** `--list-features` and
  `--feature-id` inspect; they report nothing about validity and their exit
  status is not the validator's verdict on the file.

## Command line

The same contract is reachable without importing the package:

```bash
gff3-validate --list-features annotation.gff3                   # enumerate the layer
gff3-validate --feature-id 'gene:A,B' annotation.gff3             # one K4 predicate
gff3-validate --feature-id gene:MY_GENE --format json annotation.gff3
```

Exit codes for the inspection modes answer *"did the index reach a verdict"*:

| code | meaning |
|---|---|
| 0 | `found` (and, for `--list-features`, a usable layer) |
| 1 | a scored outcome that is not a pass: `not-found`, `duplicate-row`, `non-gene-target` |
| 2 | no verdict: `absent-layer`, `malformed-layer`, unreadable input, or a usage error |

`2` for the not-scored outcomes is the point: a shell script cannot read "could
not see the layer" as either a pass (`0`) or a rejection (`1`).

## Who consumes this

- **`FAIR-bioHeaders-Tools-JavaScript`** (`src/features.js`) already ships a
  resolver of its own; this API gives it an owner to check itself against, and
  the agreement table below is that check.
- **`FAIR-bioHeaders-Tools-Julia`** records K4 as `not-supported-yet` with the
  reason "resolving a `featureId` needs the GFF3 feature layer, which belongs to
  `gff3-validator`". With this index published, that reason has an answer here
  and the Julia lane can retire it; the decision and the work are Julia's.
- **R and Java** take the same contract.

`tests/fixtures/features/outcomes.json` is the machine-readable parity artifact:
each fixture, the target queried, and the outcome this implementation reports.
The same table, run through the JavaScript resolver, is the agreement table.

## Cross-implementation agreement

Run against `FAIR-bioHeaders-Tools-JavaScript` `src/features.js` as shipped on
`main` (commit `d8552f6`, blob `5d3ba3d`, SHA-256
`b99f49dd273e25cf40ff01abc78591552508603a6d39d3be27f70ec1a611969f`), with the K4
predicate of that library's `src/fhgm.js` applied to the rows its index returns.
Reproduce it with:

```bash
poetry run python scripts/feature_index_agreement.py --js ../FAIR-bioHeaders-Tools-JavaScript/src/features.js
poetry run python scripts/feature_index_agreement.py --js PATH --markdown   # this table
poetry run python scripts/feature_index_agreement.py                        # this side only, for CI
```

`scripts/feature_index_agreement.py` only reads the sibling file; it writes
nothing to it and uses no network. `tests/test_features.py` runs it when
`GFF3_VALIDATOR_JS_FEATURES` points at a `features.js` and skips with that reason
otherwise, so CI (which has no sibling checkout) does not silently stop checking
it. **18 of 21 cases agree.**

| fixture | featureId | this index | `src/features.js` verdict | that verdict in this vocabulary | agreement |
|---|---|---|---|---|---|
| `positive.gff3` | `gene:G1` | `found` | pass | `found` | same |
| `positive.gff3` | `rna:R1` | `non-gene-target` | reject | `non-gene-target` | same |
| `positive.gff3` | `gene:NOPE` | `not-found` | reject | `not-found` | same |
| `not_found.gff3` | `gene:G1` | `not-found` | reject | `not-found` | same |
| `duplicate_row.gff3` | `gene:G1` | `duplicate-row` | reject | `duplicate-row` | same |
| `non_gene_target.gff3` | `rna:R1` | `non-gene-target` | reject | `non-gene-target` | same |
| `percent_encoded_target.gff3` | `gene:A%2CB` | `found` | pass | `found` | same |
| `percent_encoded_target.gff3` | `gene:A,B` | `found` | pass | `found` | same |
| `malformed_layer.gff3` | `gene:G1` | `malformed-layer` | unchecked | `malformed-layer` | same |
| `absent_layer.gff3` | `gene:G1` | `absent-layer` | reject | `not-found` | **DIFFERS** |
| `accession_type.gff3` | `gene:G1` | `found` | pass | `found` | same |
| `rows_without_id.gff3` | `gene:G1` | `not-found` | reject | `not-found` | same |
| `escape_case_collision.gff3` | `gene:C%3BB` | `duplicate-row` | reject | `duplicate-row` | same |
| `escape_case_collision.gff3` | `gene:C;B` | `duplicate-row` | reject | `duplicate-row` | same |
| `after_fasta.gff3` | `gene:BEFORE` | `found` | pass | `found` | same |
| `after_fasta.gff3` | `gene:AFTER` | `not-found` | reject | `not-found` | same |
| `invalid_escape.gff3` | `gene:bad%2zz` | `found` | pass | `found` | same |
| `implied_fasta.gff3` | `gene:G1` | `malformed-layer` | unchecked | `malformed-layer` | same |
| `repeated_id_tag.gff3` | `gene:A` | `found` | pass | `found` | same |
| `repeated_id_tag.gff3` | `gene:B` | `not-found` | pass | `found` | **DIFFERS** |
| `empty_id.gff3` | *(empty)* | `not-found` | pass | `found` | **DIFFERS** |

### The three disagreements, as findings

Nothing here was bent to match the other side, and nothing there was edited. The
three differences are reported for the owner of each repository to decide.

1. **`absent_layer.gff3` — a file with no feature rows is a rejection in
   JavaScript.** `src/features.js` distinguishes a usable layer from an
   untrustworthy one, and `src/fhgm.js` distinguishes both from a caller that
   passed no layer at all (`not-checked`). A file that *was* passed and contains
   no feature rows lands in the usable branch with an empty index, so K4 says
   `reject`: a header is indicted for a layer nobody could see. This index calls
   it `absent-layer`, which is not scored. This is the exact collapse the
   vocabulary exists to prevent, and it is the finding Julia should carry when it
   retires its `not-supported-yet`: the not-scored state has to be reachable from
   the file, not only from the caller's options.
2. **`repeated_id_tag.gff3` — two `ID=` tags on one row.** `src/features.js`
   collects every `ID=` attribute, so `gene:B` resolves to a gene row and K4
   passes. This index reads one identifier per row — the first — because that is
   what the catalogue's own reader does (`parse_attributes`, with `GFF-ATT-004`
   judging the repetition as an error). A header pointing at the second tag is
   `not-found` here. Which behaviour a library should have is a real question; it
   belongs to the FHGM rule text, not to either implementation's convenience.
3. **`empty_id.gff3` — `ID=` with no value.** `src/features.js` indexes the empty
   string as an identifier, so a pointer whose `featureId` is empty resolves
   against it; this index has no empty key, because an attribute with no value
   names nothing.

The two remaining shapes are **not** comparable case-by-case and are listed here
rather than in the table:

- **A path that cannot be opened** (missing file, unreadable, truncated stream)
  is `absent-layer` here. `src/features.js` is handed content, never a path, so
  the case never reaches it; whoever wraps it owns that state. This is finding 1's
  general shape: the not-scored outcome has to come from somewhere.
- **Compressed input.** `src/features.js` refuses bytes that still carry the gzip
  magic and records it as a layer problem (its stated reason: a gzip stream
  scanned as text would produce a confidently wrong index). This index reads
  gzip/BGZF through the validator's own reader, so the same bytes are a usable
  layer. Both answers decline to guess, which is the property that matters; a
  consumer delegating to this index gets rows where the local resolver reported a
  defect, so decompression belongs to whoever calls `src/features.js`.
- **`escape_case_collision.gff3` is listed twice** because the two spellings are
  one identifier; both rows and both pointers agree on all three spellings.

The `synthetic` block of `tests/fixtures/features/outcomes.json` records the
file-less cases (no such path, truncated gzip, empty input) so that a library can
test them without inventing its own.

## Status of this document

The contract above is implemented in `gff3_validator/features.py` and exposed on
the CLI as `--list-features` and `--feature-id`. FHGM is a **draft** and is not a
header type (rule V7): an index that answers K4's predicate does not make the
model-record rules supported or released anywhere, and nothing in this module is
wired into the validation report.
