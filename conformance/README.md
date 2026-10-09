# GFF3 conformance suite

Small GFF3 files with the outcome a conforming validator should give for
each, against the
[GFF3 specification 1.26](https://github.com/The-Sequence-Ontology/Specifications/blob/fe73505276dd324bf6a55773f3413fe2bed47af4/gff3.md).
Use them to test any GFF3 validator or parser, in any language. The suite
is not tied to gff3-validator: a tool passes a case by accepting or
rejecting the file correctly. Rule ids and findings are extra detail for tools
that report them.

The suite was built for
[FHR-Specification #68](https://github.com/FAIR-bioHeaders/FHR-Specification/issues/68)
(spec 009 FR-012). It covers every implemented rule in the
[rule catalogue](../docs/rules.md) at least once, plus representative valid
files.

## Layout

- `valid/`: files a validator must accept (no errors). Some carry a warning
  or note, which is listed in the manifest and does not make the file invalid.
- `invalid/`: files a validator must reject. Each breaks one rule and has no
  other error.
- `genomes/genome.fa` (and a gzip copy): a 180 bp synthetic genome for the
  cases that compare features with sequence (the `BIO-*` rules).
- `manifest.json`: the expected outcome of every case.
- `*.gz`: gzip or BGZF copies. Validate the decompressed bytes.

Every file is byte-exact. [`.gitattributes`](../.gitattributes) turns off
line-ending conversion for this directory, so the CRLF, byte-order-mark and
Latin-1 cases stay unchanged in every checkout. Don't open and re-save them in
an editor; change the generator instead.

## Manifest

Top level: `manifest_version` (1), `specification` (title and pinned URL),
`rule_catalogue` and `questions` (where rule ids and open questions are
defined), `statuses` and `levels` (the meanings below), `rules` (the rule ids
the cases target) and `cases`. Each case has:

| Field | Meaning |
| --- | --- |
| `id` | Stable case name; the file is named after it |
| `file` | Path relative to this directory; the first part is `valid` or `invalid` |
| `expected` | `valid` (no errors) or `invalid` (at least one error) |
| `rule` | The catalogue rule the case targets, or `null` for a plain valid file |
| `findings` | Every finding the case produces, as `{rule, level, line}`; `line` is 1-based in the decompressed file, or `null` for a finding about the whole file. Empty for a clean valid file |
| `section` | The GFF3 1.26 section the case tests |
| `status` | `spec`, `proposed`, `extension:fhgff3` or `extension:insdc` (below) |
| `open_question` | `proposed` cases only: a question in [questions-for-SO.md](../docs/questions-for-SO.md) (`Q4`), an issue (`SO-Ontologies#658`) or a catalogue rule whose notes record the open point (`GFF-ATT-007`) |
| `compression` | Compressed cases only: `gzip` or `bgzf` |
| `genome` | Cases that need the genome FASTA: its path |
| `options` | Cases that need a validator option: `require_header` or `no_header` (FAIR-bioHeaders header checks) |
| `description` | What the file contains and why it gets its outcome |

Levels: `error` makes a file invalid; `warning` (probably a mistake) and
`info` (a note) do not.

Statuses:

- **`spec`**: the expected verdict follows from the GFF3 1.26 text. Score
  these to compare tools on what the specification settles.
- **`proposed`**: the verdict, or whether a finding is reported at all,
  depends on an open question for the Sequence Ontology group. The case
  follows the proposed answer or the catalogue's current behaviour, and
  `open_question` says which question. Examples: CRLF line endings (Q2), a
  trailing `;` (Q4), partial CDS marked `partial=start`/`partial=end` (Q17,
  [SO-Ontologies#685](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/685)),
  selenocysteine marked by a `recoded_codon` child
  ([SO-Ontologies#658](https://github.com/The-Sequence-Ontology/SO-Ontologies/issues/658)).
- **`extension:fhgff3`**: the optional FAIR-bioHeaders header layer, outside
  GFF3 1.26.
- **`extension:insdc`**: reserved for cases of the INSDC GFF3 extension; none
  yet.

Two choices are deliberate. First, `findings` is complete: an invalid case
has exactly one error rule (its `rule`), a valid case has none, and every
warning and note is listed, so a tool that reports findings can be compared
exactly. Second, for a feature spread over several lines, `line` is where
gff3-validator reports it (for example the last CDS segment for an incomplete
stop codon). Other tools may point elsewhere; compare lines only if you
adopt the same convention.

The canonical gene is checked without a genome. With one, the
specification's own example would get BIO-009 notes (two of its CDS are one
base longer than a whole number of codons; see the suggested corrections in
questions-for-SO.md), so the genome cases use their own small genes.

## Running a validator over the suite

`scripts/check_conformance.py` (Python 3.9 or later, standard library only)
first checks the suite itself, then runs a validator over every case and
prints a table and a summary. It exits 1 if any case fails.

gff3-validator, comparing every finding from its JSON report:

```bash
python scripts/check_conformance.py --gff3-validate gff3-validate
python scripts/check_conformance.py --gff3-validate "poetry run gff3-validate"
```

Any other tool, comparing only the exit status (0 for valid, anything else for
invalid). `{file}` is replaced by the case file and `{genome}`, if present, by
the genome FASTA. Cases that need a genome are skipped when the command has no
`{genome}`; cases that need `options` are always skipped. For example,
GenomeTools:

```bash
python scripts/check_conformance.py --command 'gt gff3validator {file}' --status spec
```

Other options: `--status S` (repeatable) scores only cases with that status,
`--skip-compressed` skips the gzip and BGZF cases, `--markdown` prints a
Markdown table, `--jobs N` sets parallelism and `--no-suite-check` skips the
regeneration check (for a copy of the suite outside this repository, give
`--suite DIR`). Without a validator option the script only checks the suite.

A tool that does not use exit codes, or that stops at the first error, can
still use the files: read `manifest.json` and compare `expected` (and, if the
tool reports rule-like findings, `findings`) with its own output.

## Regenerating

[`scripts/make_conformance.py`](../scripts/make_conformance.py) holds every
case as code: the file's lines, the expected findings and the metadata. The
expected findings come from the GFF3 text and the catalogue, not from running
a validator. It writes the files with exact bytes; compressed files use stored
deflate blocks, mtime 0 and no file name, so the output does not depend on
the local zlib. Rerunning it reproduces identical bytes, and
`check_conformance.py` (and CI) fails if the committed files differ from its
output.

```bash
python scripts/make_conformance.py      # rewrite valid/, invalid/, genomes/, manifest.json
python scripts/check_conformance.py     # check the suite is up to date and consistent
```

## Contributing cases

New cases are welcome, especially from other implementers. Add a `case(...)`
call to `scripts/make_conformance.py` with the file's lines, the expected
outcome and findings, the specification section and a status, rerun the
generator, check the result with `check_conformance.py`, and open a pull
request with the script and its output. Each invalid case should break one
rule and be otherwise correct. Where the specification does not settle the
outcome, mark the case `proposed` and cite the open question; if there is
none yet, add it to [questions-for-SO.md](../docs/questions-for-SO.md).

We would like the suite to become shared ground:

- **INSDC/NCBI**: as the INSDC GFF3 extension takes shape, we will add its
  cases with status `extension:insdc` (partial features with
  `partial=start`/`partial=end`, translation exceptions and the like), and we
  invite you to contribute or review them.
- **The Sequence Ontology group**: each `proposed` case is a concrete
  example of an open question. An answer turns it into a `spec` case, or
  changes its expected outcome. Corrections to `spec` cases are equally
  welcome.

Disagreements are useful: when a tool and the suite differ, open an issue in
[gff3-validator](https://github.com/FAIR-bioHeaders/gff3-validator/issues)
saying which case and why.

## License

The suite (the GFF3, FASTA and manifest files, and the scripts) is under the
repository's [MIT license](../LICENSE), like the rest of gff3-validator. The
test files are small synthetic examples, several transcribed from the GFF3
specification; you may copy them into other test suites freely. Keeping a
note of where they came from is appreciated but, beyond the MIT notice, not
required.
