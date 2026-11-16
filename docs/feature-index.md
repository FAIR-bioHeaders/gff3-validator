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
match = index.resolve("gene:My%20gene")            # one K4 predicate
match = resolve_feature_id("annotation.gff3", "gene:My%20gene")   # both steps
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
`ID=gene:My%20gene` for the identifier `gene:My gene`. An FHGM `featureId` is a
YAML string, not a column-9 value, and nothing forces its author to repeat the
file's escaping. The index therefore **percent-decodes both sides and compares
identifiers**:

```python
decoded_row    = unquote(row["ID"] value as written)     # index key
decoded_target = unquote(feature_id)                     # lookup
```

Three candidate semantics exist, and the choice should be visible:

1. **Raw lookup on both sides** — compare the header string to the column-9
   bytes. This makes K4 a test of *spelling*, so a correct model record written
   `featureId: gene:My gene` fails against a correct file that escapes it, and a
   correct model record written with the escape fails against a file that (in
   breach of GFF3) writes the space literally.
2. **Decode the file side only** — what the FHGM authoring checker does today
   (`unquote_to_bytes` on the row, a raw `featureId.encode()` lookup). It fixes
   half of case 1 and leaves the other half: the identifier is decoded when it
   comes from the file and left as data when it comes from the header, so the
   comparison is still a spelling test whenever the header escapes anything.
3. **Decode both sides** — chosen. Equality is then about the identifier, which
   is what "resolves to" means, and it is symmetric: neither side's serialization
   can decide the verdict.

Cases 2 and 3 coincide on every vector in the FHGM suite as it stands (the
vectors either escape on neither side or on both), which is exactly why the
choice had never been forced into the open; it is a decision in principle, so it
is recorded here and tested explicitly by
`tests/fixtures/features/percent_encoded_target.gff3` and
`tests/test_features.py::test_encoded_record_id_matches_literal_row` — a row
`ID=gene:My%20gene` resolved by the decoded target `gene:My gene`, which outcome
2 would call `not-found` and outcome 3 calls `found`.

Two consequences of decoding both sides, both intended:

- Identifiers that differ **only** by escape spelling collapse onto one key
  (`a%2Fb` and `a/b` are the same identifier), so a layer that carries both now
  yields `duplicate-row`. Ambiguity surfaces as a scored rejection of the
  pointer rather than as a silent first match.
- A malformed escape (`%zz`, `%2`) is left as written by `urllib.parse.unquote`
  instead of raising: identifiers are data, and a target that carries the same
  broken escape matches the row that carries it.

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
gff3-validate --feature-id 'gene:My%20gene' annotation.gff3      # one K4 predicate
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

(Added with the implementation: the same fixtures scored by
`FAIR-bioHeaders-Tools-JavaScript` `src/features.js` on `main` and by
`gff3_validator.features`, and the disagreements found.)
