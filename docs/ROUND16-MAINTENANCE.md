# Round 16 maintenance and audit — 2026-11-20

These corrections are unreleased source changes, not a claim that the existing
0.1.0 wheel changed. No release/tag/publication occurs in this packet.

This packet ports human-only merge guidance, repairs documentation and modern
Black development-tool advisories. It changes no rule IDs, ontology, schemas,
fixtures, runtime dependency range or release version. SO review/endorsement,
profile acceptance, releases and downstream adoption remain separate gates.

Manual review covered streaming/gzip error handling (`reader.py`), indexed genome
access, `engine.py` report/finding limits, feature-ID evidence, optional header
imports, local ontology/profile loading, HTML/SARIF escaping, packaging and all
four workflows. Ordinary validation is offline; core operation does not need the
optional toolkit. Structural/feature indexes grow with data; long lines and large
decompressed inputs need deployment-level CPU/memory/disk/time limits. A finding
limit does not bound all input processing. The validator never edits annotations.

Bandit 1.8.6 on Python 3.13 scanned `gff3_validator` with default rules and zero
parse errors. Two B105 results are literal accepted attribute/biology values,
not passwords. Zizmor 1.16.3 default workflow scan reports zero. Gitleaks 8.30.1
(default rules, redact=100) reports zero for the working tree and `git --all`
history. No suppressions or fixture/history changes hide findings. Commands and
redacted evidence are retained in the shared Round 16 B continuation packet.

Black's modern Python branch is patched to >=26.10.1 with a generated Poetry
2.3.2 lock; only that development package is intentionally refreshed. Python 3.9
retains Black 25.11.0 and pytest 8.4.2 because patched upstream tools require
Python 3.10+. Maintainers own that runtime/tooling decision. Relevant advisories:
GHSA-cg8m-r9f2-5wm2 (Black action, unused here), GHSA-3936-cmfr-pm3m (untrusted
python-cell-magics/cache path, not supplied by CI), and GHSA-6w46-j5rx-g56g
(shared pytest temporary directories). Use isolated development users/containers
or an explicitly private pytest basetemp on multi-user machines. Do not call the
whole development lock advisory-free.

Published validator 0.1.0 and source use different optional-header dependency
ranges; installed core/header behavior must name actual versions. This packet
does not widen support or publish source fixes. The current source and frozen
fixtures remain separate from the already published wheel.

Historical review packets remain evidence of questions, not SO acceptance or
future agent merge permission. Preexisting branches/worktrees are retained:
exclusive ownership, integration and lack of unique/open work cannot all be
proved from this packet. Every PR needs another actual model review (another
family preferred), fixes and current-head CI; a human alone merges. No auto-merge,
merge queue, merge proxy or default-branch bypass is allowed.

Reproducible scan shapes (run from the declared repository/source scope):
`bandit -r SOURCE -f json`, `zizmor --format json .github/workflows`,
`gitleaks dir SCOPE --redact=100 --report-format json` and
`gitleaks git . --log-opts=--all --redact=100 --report-format json`.
Bioconda history additionally restricts log paths to owned FAIR docs/scripts and
recipes; scaffold-inapplicable tools are not claimed as passes.
[Redacted source/finding inventory](audit-2026-11-20.json) records actual coverage
and locations. No raw credential values are committed.

pip-audit 2.9.0 reported no known vulnerabilities on 2026-11-20 for the actual Python 3.13 source install with optional headers (resolved toolkit 0.8.6). This is a current pip resolution, not the distinct locked 0.8.0 environment. Browser-test npm audit of the lockfile also reports zero vulnerabilities.

Exact advisory input is [the dated requirement set](audit-runtime-2026-11-20.txt).
Re-run `pip-audit -r docs/audit-runtime-2026-11-20.txt --no-deps --disable-pip -f json`.
Advisory databases change; an old zero result is not a future warranty.

Independent Qwen3 actual-source review found a mislabeled omitted-row count in
feature text listings: anonymous rows were called ID-carrying. The label and
coordinate/strand spacing are corrected with a two-row regression. No feature
ID predicate, report JSON/SARIF schema, rule or fixture bytes change. Stale
pre-first-release comments and the canonical specification link are corrected.

Manual follow-up of development scripts found destructive output overlap:
`build_web.py --out .` could remove the checkout, and `make_conformance.py
--output .` could remove source `profiles`. A shared stdlib guard now runs
before building/deleting, refuses source/ancestor/Git/worktree/symlink overlaps
and tracked source (except the designated generated conformance tree), and
fails closed on unknown in-checkout tracking. Synthetic-root sentinel tests
never risk the actual checkout. Dedicated untracked scratch outputs remain
replaceable; TOCTOU and external untracked data are not isolation guarantees.
No generated fixture bytes are changed.

The output guard uses physical samefile ancestry plus NFC/casefold indexed-path
prefixes, so case/composition aliases such as DOCS/.GIT or composed/decomposed
Unicode cannot bypass protection on case-insensitive filesystems. Unknown file
identity/tracking fails closed. Synthetic-root tests cover these aliases without
ever deleting the actual checkout.
