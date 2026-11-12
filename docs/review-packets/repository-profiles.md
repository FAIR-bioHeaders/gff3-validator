# Review packet — repository profiles beyond AgBioData

Prepared for [#20](https://github.com/FAIR-bioHeaders/gff3-validator/issues/20)
(Refs #20; consumes the placement outcome of #18/#19 and the merged INSDC
review of [#28](https://github.com/FAIR-bioHeaders/gff3-validator/pull/28)).
Draft packet, 2026-11-11. It authorizes no contact and claims no review,
adoption or endorsement — of AgBioData by its working group, or of anything
by NCBI, Ensembl or the Alliance. Every external citation below was checked
**on 2026-11-11** and is described only as far as the fetched text supports.

## 1. The shipped-profile mechanism (as implemented today)

A profile is `profiles/ID.yaml` (`profile_format: 1`) layered on the core
rules; findings stay separate and **never change core validity**
(spec 009 FR-011; [docs/profiles.md](../profiles.md)). What the loader and
the tests actually enforce (`gff3_validator/profiles/__init__.py`,
`tests/test_profiles.py`):

| Surface | Enforced constraint |
| --- | --- |
| Metadata | `profile_format, id, name, version, description, review, source, prefix, rules` required; unknown top-level fields rejected; `id` lowercase pattern, `prefix` 2–6 capitals, rule ids must match the prefix |
| `source` | **required: `title`, `url`, `license`** (`SOURCE_REQUIRED`); optional `commit`, `date`. A profile without a license string cannot load |
| `review` | required free text; policy (AGENTS.md, docs/profiles.md step 6): it may record only a review that has happened |
| `levels` | may name only **implemented** catalogue rules, may only **raise** levels (info→warning/error, warning→error), never lower or silence |
| `rules` | a rule marked `implemented` requires a shipped checks module (`gff3_validator/profiles/ID.py`) and emits findings; planned rules must report as not checked |
| `guidance` | everything of the source not checked, each with the reason; `covered_by` ids are validated |
| Reporting | core findings/`valid` identical with or without the profile; profile verdict is separate (`compliant` = valid GFF3 **and** no profile errors); JSON `profile` object, HTML section, SARIF tool extension; exit status 1 on profile errors |
| Shipping | adding `profiles/ID.yaml` means, **in the same commit**: `tests/test_profiles.py::test_shipped_profiles` is updated (`builtin_ids()` currently pins exactly `["agbiodata"]`), the conformance manifest gains a mirrored entry (`test_conformance_manifest_agrees_with_the_profile` checks name/version/source/**license**), and `scripts/render_rules.py` writes the packaged copy plus `docs/profiles/ID.md` plus the mapping table — a profile cannot ship half-wired |

**AgBioData state (never say "endorsed"):** `agbiodata` 0.1.0-draft is
*implemented and delivered* — 13 rules (AGB-001…013), 2 raised core rules
(SO-001→error, BIO-008→error), 19 guidance entries — pinned to the
recommendations at commit `32c8a386d3bca504e61cb6f7d9b9b038b7f7b0f8`
(2021-12-29, CC0-1.0; raw file verified HTTP 200 today), and its `review`
field says, honestly: *"not reviewed by the AgBioData GFF3 working group."*
Working-group review is an open acceptance item of #20; new profiles may be
researched while it is pending.

## 2. Candidate rule sources — verification results (2026-11-11)

### NCBI

| | |
| --- | --- |
| Source 1 | *Annotating Genomes with GFF3 or GTF files* — https://www.ncbi.nlm.nih.gov/genbank/genomes_gff/ — fetched HTTP 200; page stamp **"Last updated: 2024-03-08T13:58:42Z"** |
| Source 2 | *Eukaryotic Genome Annotation Guide* — https://www.ncbi.nlm.nih.gov/genbank/eukaryotic_genome_submission_annotation/ — fetched HTTP 200; page stamp **"Last updated: 2025-03-21T17:20:47Z"** |

What the fetched text says that a profile could translate (section
references as the pages give them; nothing beyond this is supported):

- Source 1, *GenBank-specific requirements*: seqid must match the FASTA/ASN.1
  seqids ([1]); landmark features "not required and will be ignored" ([2]);
  multi-exon RNA shapes allowed ([3], incl. the deviation that eukaryotic
  multiple CDS rows sharing a **Parent** are assumed one CDS); "GFF3 ID
  attributes are required for interpreting parent-child feature relationships
  and that is their only role here" ([4]); "GFF3 Name attributes are ignored"
  ([5]).
- Source 1, *Changes that occur during processing*: partialness is computed
  automatically and "any attributes that are sometimes used to specify
  partialness, such as start_range or end_range, will be ignored" ([3]) —
  direct evidence for question 19 (a major consumer reads **no** GFF3
  partiality marker); product on the CDS or the CDS is named
  "hypothetical protein" ([4]).
- Source 1, *Attributes/Annotation features*: type conversions and drops,
  e.g. specific gene types "should be converted to use gene instead" and
  `misc_RNA` "is not a recognized SO term" ([1]); "pseudogenes should be
  flagged with pseudogene=<TYPE> qualifier … on the gene feature" ([2]);
  "annotate with pseudo=true any genes that are 'broken' but are not thought
  to be pseudogenes" ([3]); "gene features require locus_tag qualifiers" ([4]);
  mRNA/CDS "require transcript_id and protein_id qualifiers" ([5]); product
  naming per GenBank guidelines, comma rules, %2C encoding ([6]); INSDC
  qualifiers usable as column-9 attributes, "multiple values … as a
  comma-separated list" ([7]).
- Source 2, *locus_tag*: prefixes "must be registered and … unique", 3–12
  alphanumeric characters, first character not a digit, one underscore
  separator, one prefix per genome — the checkable half of draft INSDC-010's
  form, and the registry half that stays guidance (no network).
- Source 2, *Gene fragments*: "/pseudo … does NOT mean that the gene is a
  pseudogene"; /pseudo vs /pseudogene as distinct claims — question 20
  evidence on the NCBI side.
- Source 2, *Transpliced Genes*: `exception trans-splicing` on gene and tRNA —
  the marker question 18 proposed to exempt, confirmed in NCBI practice
  (the validator still does not implement the exemption; no rule was
  changed by this packet).

Licensing note: US-government pages; the fetched pages themselves carry no
licence statement beyond the NLM site policies footer — record URL +
"Last updated" stamp as the pin, and keep rule text paraphrased (§4 option
C) so no redistribution question arises.

### Ensembl

| | |
| --- | --- |
| Source | *GFF3 File Format — Definition and supported options* — https://www.ensembl.org/info/website/upload/gff3.html — fetched HTTP 200 on 2026-11-11, served from the **jun2026 archive ("Ensembl release 116 – June 2026")**, permanent link recorded on the page |
| Scope caveat | the page documents **custom-track upload** into the Ensembl display, not Ensembl's internal gene-build policy; a profile must say so and translate only this page |

What the fetched text says: first line must be `##gff-version 3`; fields
"must be tab-separated" and "all but the final field … must contain a value;
'empty' columns should be denoted with a '.'"; **seqid** "must be one used
within Ensembl, i.e. a standard chromosome name or an Ensembl identifier …
without any additional content such as species or assembly"; **type** "Must
be a term or accession from the **SOFA** sequence ontology"; **strand**
"defined as + (forward) or − (reverse)" (the page names no `.`/`?`);
**phase** "One of '0', '1' or '2'" (it does not mention `.`); `Parent`
identifiers are used to join features into blocks.

Profile translation (all *levels-raising / guidance* candidates against
implemented core rules — nothing new is needed in the catalogue): SOFA-only
types (raise SO-001/SO-003 behaviour within profile findings; note this is
also question-13/14 evidence *for* SO), Ensembl seqid matching (profile rule
or guidance), strand restricted to `+`/`-` (raise GFF-SYN-017), phase values
without `.` on CDS (raise GFF-SYN-019/020 — careful: the page's phrasing
describes required values, it does not itself state severities; the profile
must record how it read it).

### Alliance of Genome Resources

| | |
| --- | --- |
| Checked 2026-11-11 | https://www.alliancegenome.org/faq (fetched in full), /downloads (fetched in full), /submit-data (fetched in full): HTTP 200 — **none contains GFF3 format conventions**; /downloads lists aggregate TSV/JSON/VCF products; /submit-data states submissions "are pulled in from the individual Model Organism Databases" |
| Not reachable from this workstation | `docs.alliancegenome.org`, `ftp.alliancegenome.org`, `kb.alliancegenome.org` — DNS resolution failed on every network path available here (curl, web fetch, headless browser); their content is therefore **unverified today** and is not cited |
| What is citable now | the AgBioData GFF3 recommendations (already pinned in-repo, CC0-1.0, commit `32c8a38`) list AgBioData, **the Alliance of Genome Resources and NCBI** as the recommending bodies — Alliance's public GFF3 position of record is that document |

Consequence for #20: an "Alliance profile" should not be drafted from memory
of docs.alliancegenome.org. Either (a) re-verify the Alliance user docs from
a network that resolves them before writing any `AGR-*` rule, or (b) treat
Alliance adoption as a `review:`-field outcome on the existing `agbiodata`
profile once the working-group review happens — the honest default today.

### INSDC (the draft that is waiting on this packet)

`docs/insdc-rule-placement.md` (merged state of #28) carries **16 draft
profile entries, INSDC-001…INSDC-016**, all `status: planned`, none shipped,
all citing *Annotation Minimum Specification v1.0* at
`insdc/minimum-specifcations` commit `41f0dc424748c9f7e50a8b6bda9b888218c4b65e`
(`Annotations/Current version/Annotation Minimum Specification v1.0.docx.pdf`,
blob verified HTTP 200 today; file SHA-256 `bb7b8992…d20d`, 185312 bytes,
6 pages, re-verified by the reviewer on 2026-11-11). Only **GFF-STR-015**
remained in the core catalogue, re-cited to GFF3 itself. The document states
the **update gate**: INSDC is revising the specification; rule numbers,
thresholds, table 2e exceptions and the partial-marker vocabulary may move;
**INSDC outreach is deferred until the update lands** (maintainer decision on
the PR). Questions 19/20 of `docs/questions-for-SO.md` gate INSDC-001/004/
005/007/012/016 regardless of licensing.

## 3. Open policy decisions #20 owns (beyond licensing)

From the merged review doc's "Review items for the maintainers" — listed here
so the packet reviewer sees the whole blocker set:

1. One INSDC/NCBI profile or two (split by source document, not subject).
2. Whether a profile's **own** rule may require `--genome` (INSDC-012);
   today only raised core biology rules declare that dependency, and a
   skipped check must report as skipped, never as passed.
3. How a file declares context the format cannot carry — "this is a genome
   submission" (INSDC-009), "this is prokaryote" (INSDC-012): profile
   options, a CLI flag, or documented non-checks.
4. Profile severities for the moved candidates (INSDC-014's level,
   INSDC-015's placement, INSDC-016's 5'-end reading) — after the INSDC
   update and the SO answers.

## 4. Licence decision memo — the INSDC profiles

**The blocker, re-verified today.** `profiles/insdc.yaml` cannot ship because
the mechanism and the policy meet at one field:

- the loader requires `source.license` (`SOURCE_REQUIRED` in
  `gff3_validator/profiles/__init__.py`) — no profile file loads without it;
- [AGENTS.md](../../AGENTS.md) ("Do not invent … metadata"; licensing
  policy: preserve third-party licences/notices) and
  [docs/profiles.md](../profiles.md) step 1 ("check that its licence allows
  quoting it") forbid filling that field by guess;
- the source has **no licence**: `GET /repos/insdc/minimum-specifcations`
  answers `"license": null` (checked 2026-11-11) and the tree at `41f0dc4`
  contains no LICENSE file (category READMEs only — also checked today);
- and the source text is **in flux** (the #28 update gate), independent of
  licensing.

Note that the repo already stores short verbatim sentences of the INSDC PDF
in `docs/insdc-rule-placement.md` — a review document merged deliberately
(#28), where quotation is the evidence of a faithful translation. Shipping a
*packaged* `profiles/insdc.yaml` (installed data, redistributed with every
wheel, its licence mirrored into the conformance manifest by
`test_conformance_manifest_agrees_with_the_profile`) is a higher bar, and it
is the bar this memo decides.

**Options.**

| | Option | What it satisfies concretely | What it costs |
| --- | --- | --- | --- |
| A | **Document-as-citation-only**: the profile ships with `source.license` stating the fact — "no licence declared at commit 41f0dc4…" — and the profile file contains **no text from the source at all**: rule `title`/`description`/`fix` in our own words, `reference.section` only as a locator | the loader requirement is met truthfully (the field describes the licence situation, it does not grant a licence); zero redistribution exposure | weakest auditability: the "translate only what the document says" check moves out of the shipped file into `docs/insdc-rule-placement.md`, which must then stay in the repo as the evidence file (it is already there); indistinguishable from C in practice except that C keeps short quotations of *facts* (thresholds, rule numbers) which are the non-copyrightable core |
| B | **Vendor-terms review**: ask INSDC (via the maintainers, alongside the deferred outreach on the update) for a written statement of reuse/quotability; ship with whatever it grants, verbatim notes included | the only option that fully clears both the loader and step 1 of docs/profiles.md without interpretation | blocked on an external actor twice over: maintainer-authorized contact **and** the INSDC update; timeline is #20's to accept, not to assume |
| C | **Paraphrase rules without verbatim sentences**: rule text restated in the validator's own words; numbers, rule identifiers and section locators kept as factual citations; the *draft* review doc retains the quotations as review evidence; `source.license` records the factual status as in A | keeps rules testable and reviewable (a reviewer can still compare each paraphrase against the pinned PDF page cited in `reference.section`); copyright protects expression, not the requirements themselves; no permission needed to state "b.v.1: complete CDSs, 30 aa threshold" | every drafted entry must have its quoted clauses rewritten before shipping (the §2 "Draft profile entries" block currently quotes verbatim in `description`/`notes`); a maintenance rule: future profile PRs restate, never paste |

**Recommended default: C, with A's `source.license` wording, and B pursued
in parallel once outreach is authorized.** Concretely: ship no
`profiles/insdc.yaml` before (i) the INSDC update lands (update gate), (ii)
questions 19/20 have SO answers for the six blocked drafts, and (iii) each
shipped rule text has been converted from the draft block's quotations to
paraphrase with section citations. Until then the 16 entries stay exactly
where they are — documentation under #20, engine silent, conformance status
`extension:insdc` reserved but unused. The NCBI candidate rules do **not**
share this blocker (US-government pages, factual restatement as in §2), but
they are equally gated on the maintainer's one-vs-two-profile decision.

## 5. Review asks, ready to route (not sent)

1. **AgBioData GFF3 working group**: review of the 0.1.0-draft profile
   (rules, the two raises, the two wording conflicts recorded in
   docs/profiles.md) — only their reply may change the `review` field.
2. **INSDC** (after its update is published): licence/reuse statement
   (option B) and confirmation whether the rule placement survived the
   revision.
3. **NCBI**: confirmation that the NCBI-specific paraphrases (§2) match
   current guidance, once an `NCBI-*` profile is drafted.
4. **Ensembl**: confirmation of the custom-track scope caveat and of the
   SOFA/seqid/strand/phase readings before any `ENS-*` rule ships.
5. **Alliance**: re-verification of the user docs from a network that
   reaches them, or explicit routing to the AgBioData review as the
   Alliance position of record.

Nothing above was contacted by this packet; the AgBioData profile remains
"delivered, unreviewed", and no profile ships on the strength of these notes.

Companion packets: [catalogue-review.md](catalogue-review.md) (#18) and
[term-parent-rules.md](term-parent-rules.md) (#19).
