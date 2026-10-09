"""Text, JSON, HTML and SARIF renderings of a :class:`~gff3_validator.engine.Report`.

The HTML report is one self-contained file: no external stylesheets, scripts,
fonts or images, and a Content-Security-Policy that allows only its own inline
style and sorting script (by hash). Every value taken from the input (file
name, messages) is escaped. The SARIF report follows SARIF 2.1.0.
"""

import base64
import hashlib
import html
import json
import os
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote

from gff3_validator.rules import load_catalogue

REPOSITORY = "https://github.com/FAIR-bioHeaders/gff3-validator"
RULES_URL = REPOSITORY + "/blob/main/docs/rules.md"
SARIF_SCHEMA = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/"
    "sarif-schema-2.1.0.json"
)
SARIF_LEVELS = {"error": "error", "warning": "warning", "info": "note"}
LEVEL_ORDER = {"error": 0, "warning": 1, "info": 2}
LIMITATIONS = (
    "Pre-release: only the catalogue rules marked implemented are checked, and "
    "the rule catalogue is a draft under review with the Sequence Ontology "
    "group; rule ids, levels and this report format may still change. Layers "
    'listed under "Not checked" were not run and have not passed. A '
    "suggested fix is guidance only; the validator never changes the file."
)


def rule_url(rule_id):
    """The rule's section in docs/rules.md on GitHub."""
    return f"{RULES_URL}#{rule_id.lower()}"


def to_json(report):
    return json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"


def to_text(report):
    lines = []
    for finding in report.findings:
        where = report.source
        if finding.line is not None:
            where += f":{finding.line}"
        if finding.field is not None:
            where += f" (column {finding.field})"
        lines.append(f"{where}: {finding.level} {finding.rule}: {finding.message}")
        if finding.fix and finding.level != "info":
            lines.append(f"    fix: {finding.fix}")
    if report.truncated:
        lines.append(f"... {report.truncated} more findings not shown")
    lines.append(f"{report.source}: {summary(report)}")
    for item in report.skipped:
        lines.append(f"  not checked: {item['layer']}: {item['reason']}")
    return "\n".join(lines) + "\n"


def summary(report):
    """One-line verdict, for example "INVALID (1 errors, 0 warnings, ...)"."""
    counts = report.counts
    verdict = "no errors" if report.valid else "INVALID"
    return (
        f"{verdict} ({counts['error']} errors, {counts['warning']} warnings, "
        f"{counts['info']} notes; {report.lines} lines)"
    )


# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

HTML_STYLE = """
body{font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;margin:0;
color:#1b1b1b;background:#fff}
main{max-width:72rem;margin:0 auto;padding:1rem 1.25rem 2rem}
h1{font-size:1.4rem;margin:.2rem 0 .8rem}h2{font-size:1.1rem;margin:1.4rem 0 .5rem}
.verdict{font-weight:600;padding:.6rem .8rem;border-left:.4rem solid;margin:0 0 1rem}
.verdict.ok{border-color:#1a7f37;background:#eaf6ec}
.verdict.bad{border-color:#c62828;background:#fdecea}
dl{display:grid;grid-template-columns:max-content 1fr;gap:.2rem 1rem;margin:0}
dt{font-weight:600}dd{margin:0;overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%;font-size:.92rem}
caption{text-align:left;padding:.3rem 0;color:#555}
th,td{border-bottom:1px solid #ddd;padding:.35rem .5rem;text-align:left;
vertical-align:top}
td{overflow-wrap:anywhere}
th button{font:inherit;font-weight:600;background:none;border:0;padding:0;
cursor:pointer;color:inherit;text-decoration:underline dotted}
th[aria-sort=ascending] button::after{content:" \\2191"}
th[aria-sort=descending] button::after{content:" \\2193"}
.num{text-align:right;font-variant-numeric:tabular-nums}
.lvl{font-weight:600}.error .lvl{color:#b71c1c}.warning .lvl{color:#8a5300}
.info .lvl{color:#285a8f}
a{color:#0b57d0}code{font-size:.95em}
.note{color:#444}
@media (prefers-color-scheme:dark){body{color:#e8e8e8;background:#161616}
th,td{border-color:#333}caption,.note{color:#aaa}a{color:#8ab4f8}
.verdict.ok{background:#14301b}.verdict.bad{background:#3a1717}
.error .lvl{color:#ff8a80}.warning .lvl{color:#ffcc80}.info .lvl{color:#90caf9}}
"""

# Sorts the findings table by line, rule or level. Kept tiny and inline so the
# report stays one file; allowed by its hash in the report's CSP.
HTML_SCRIPT = """
(function(){
var table=document.getElementById("findings");if(!table)return;
var body=table.tBodies[0];
table.querySelectorAll("th button[data-key]").forEach(function(button){
button.addEventListener("click",function(){
var th=button.parentNode,key=button.getAttribute("data-key");
var dir=th.getAttribute("aria-sort")==="ascending"?-1:1;
table.querySelectorAll("th[aria-sort]").forEach(function(o){
o.removeAttribute("aria-sort");});
th.setAttribute("aria-sort",dir===1?"ascending":"descending");
var rows=Array.prototype.slice.call(body.rows);
rows.sort(function(a,b){
var x=a.getAttribute("data-"+key),y=b.getAttribute("data-"+key);
var c=key==="rule"?(x<y?-1:x>y?1:0):Number(x)-Number(y);
return c*dir||Number(a.getAttribute("data-order"))-Number(b.getAttribute("data-order"));
});
rows.forEach(function(r){body.appendChild(r);});
});});
})();
"""


def csp_hash(text):
    """The CSP source expression ('sha256-...') allowing inline ``text``."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return "'sha256-" + base64.b64encode(digest).decode("ascii") + "'"


STYLE_HASH = csp_hash(HTML_STYLE)
SCRIPT_HASH = csp_hash(HTML_SCRIPT)
HTML_CSP = (
    f"default-src 'none'; style-src {STYLE_HASH}; script-src {SCRIPT_HASH}; "
    "base-uri 'none'; form-action 'none'"
)


def to_html(report, catalogue=None):
    """Render ``report`` as one self-contained, accessible HTML page."""
    from gff3_validator import __version__

    catalogue = catalogue or load_catalogue()
    e = html.escape
    counts = report.counts
    out = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        f'<meta http-equiv="Content-Security-Policy" content="{e(HTML_CSP)}">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        f"<title>GFF3 validation report: {e(report.source)}</title>",
        f"<style>{HTML_STYLE}</style>",
        "</head>",
        "<body>",
        "<main>",
        "<h1>GFF3 validation report</h1>",
        f'<p class="verdict {"ok" if report.valid else "bad"}" role="status">'
        f"{e(report.source)}: {e(summary(report))}</p>",
        "<dl>",
        f"<dt>File</dt><dd><code>{e(report.source)}</code></dd>",
        f"<dt>Lines read</dt><dd>{report.lines}</dd>",
        f"<dt>Errors</dt><dd>{counts['error']}</dd>",
        f"<dt>Warnings</dt><dd>{counts['warning']}</dd>",
        f"<dt>Notes</dt><dd>{counts['info']}</dd>",
        f"<dt>FAIR-bioHeaders header lines</dt><dd>{report.header_lines}</dd>",
        f"<dt>Validator</dt><dd>gff3-validator {e(__version__)}</dd>",
        f"<dt>Rule catalogue</dt><dd>{e(report.catalogue_version)} "
        f'(<a href="{e(RULES_URL)}">rules</a>)</dd>',
    ]
    for key, label in (("gff3", "Specification"), ("so", "Sequence Ontology")):
        source = catalogue.sources.get(key)
        if source:
            out.append(
                f'<dt>{label}</dt><dd><a href="{e(source["url"])}">'
                f'{e(source["title"])}</a></dd>'
            )
    out += [
        "</dl>",
        '<section aria-labelledby="not-checked">',
        '<h2 id="not-checked">Not checked</h2>',
    ]
    if report.skipped:
        out.append("<ul>")
        for item in report.skipped:
            out.append(
                f"<li><strong>{e(item['layer'])}</strong>: {e(item['reason'])}</li>"
            )
        out.append("</ul>")
    else:
        out.append("<p>Every layer was checked.</p>")
    out += [
        "</section>",
        '<section aria-labelledby="findings-title">',
        f'<h2 id="findings-title">Findings ({len(report.findings)})</h2>',
    ]
    if report.truncated:
        out.append(
            f'<p class="note">{report.truncated} more findings are not shown '
            "(--max-findings); the counts above are complete.</p>"
        )
    if report.findings:
        out += [
            '<table id="findings">',
            "<caption>Each finding cites a catalogue rule. Use the Line, Level "
            "and Rule headings to sort.</caption>",
            "<thead><tr>",
            '<th scope="col" class="num">'
            '<button type="button" data-key="line">Line</button></th>',
            '<th scope="col" class="num">GFF3 column</th>',
            '<th scope="col"><button type="button" data-key="level">'
            "Level</button></th>",
            '<th scope="col"><button type="button" data-key="rule">'
            "Rule</button></th>",
            '<th scope="col">Message</th>',
            '<th scope="col">Suggested fix</th>',
            "</tr></thead>",
            "<tbody>",
        ]
        for order, finding in enumerate(report.findings):
            # Whole-file findings (no line) sort after every line.
            line_key = finding.line if finding.line is not None else 2**53
            fix = finding.fix if finding.fix and finding.level != "info" else ""
            line = "" if finding.line is None else finding.line
            column = "" if finding.field is None else finding.field
            out.append(
                f'<tr class="{e(finding.level)}" data-order="{order}" '
                f'data-line="{line_key}" data-rule="{e(finding.rule)}" '
                f'data-level="{LEVEL_ORDER.get(finding.level, 3)}">'
                f'<td class="num">{line}</td><td class="num">{column}</td>'
                f'<td class="lvl">{e(finding.level)}</td>'
                f'<td><a href="{e(rule_url(finding.rule))}">'
                f"<code>{e(finding.rule)}</code></a></td>"
                f"<td>{e(finding.message)}</td><td>{e(fix)}</td></tr>"
            )
        out += ["</tbody>", "</table>"]
    else:
        out.append("<p>No findings.</p>")
    out += [
        "</section>",
        '<section aria-labelledby="limitations">',
        '<h2 id="limitations">Limitations</h2>',
        f"<p>{e(LIMITATIONS)}</p>",
        "</section>",
        "</main>",
        f"<script>{HTML_SCRIPT}</script>",
        "</body>",
        "</html>",
    ]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------
# SARIF 2.1.0
# --------------------------------------------------------------------------


def _artifact_location(source):
    """A SARIF artifactLocation for the validated input (None for stdin).

    Absolute paths become file: URIs; relative paths stay relative to the
    %SRCROOT% base, as code-scanning services expect.
    """
    if source == "-":
        return None
    if PureWindowsPath(source).is_absolute():
        return {"uri": PureWindowsPath(source).as_uri()}
    if os.path.isabs(source):
        return {"uri": PurePosixPath(source).as_uri()}
    return {"uri": quote(source.replace(os.sep, "/")), "uriBaseId": "%SRCROOT%"}


def _sarif_rule(rule, catalogue):
    return {
        "id": rule.id,
        "name": rule.id.replace("-", ""),
        "shortDescription": {"text": rule.title},
        "fullDescription": {"text": rule.description},
        "helpUri": rule_url(rule.id),
        "help": {"text": f"Fix: {rule.fix}"},
        "defaultConfiguration": {"level": SARIF_LEVELS[rule.level]},
        "properties": {
            "layer": rule.layer,
            "status": rule.status,
            "review": rule.review,
            "reference": catalogue.reference_url(rule),
            "tags": [rule.layer, rule.category],
        },
    }


def to_sarif_dict(report, catalogue=None):
    """Return ``report`` as a SARIF 2.1.0 log (a dict).

    Locations give the line. The engine reports GFF3 columns (1 to 9), not
    character offsets, so the column is in each result's properties
    (``gff3Column``), not in ``region.startColumn``. Layers that were not
    checked are tool execution notifications and run properties.
    """
    from gff3_validator import __version__

    catalogue = catalogue or load_catalogue()
    rules = list(catalogue)
    index = {rule.id: number for number, rule in enumerate(rules)}
    artifact = _artifact_location(report.source)
    results = []
    for finding in report.findings:
        result = {
            "ruleId": finding.rule,
            "ruleIndex": index[finding.rule],
            "level": SARIF_LEVELS[finding.level],
            "message": {"text": finding.message},
        }
        if artifact is not None:
            location = {"artifactLocation": dict(artifact)}
            if finding.line is not None:
                location["region"] = {"startLine": finding.line}
            result["locations"] = [{"physicalLocation": location}]
        properties = {}
        if finding.field is not None:
            properties["gff3Column"] = finding.field
        if finding.fix and finding.level != "info":
            properties["fix"] = finding.fix
        if properties:
            result["properties"] = properties
        results.append(result)
    notifications = [
        {
            "level": "note",
            "message": {"text": f"not checked: {item['layer']}: {item['reason']}"},
        }
        for item in report.skipped
    ]
    if report.truncated:
        notifications.append(
            {
                "level": "warning",
                "message": {
                    "text": f"{report.truncated} more findings not shown "
                    "(--max-findings)"
                },
            }
        )
    run = {
        "tool": {
            "driver": {
                "name": "gff3-validator",
                "version": __version__,
                "informationUri": REPOSITORY,
                "rules": [_sarif_rule(rule, catalogue) for rule in rules],
                "properties": {"catalogueVersion": report.catalogue_version},
            }
        },
        "invocations": [
            {"executionSuccessful": True, "toolExecutionNotifications": notifications}
        ],
        "results": results,
        "properties": {
            "valid": report.valid,
            "counts": dict(report.counts),
            "lines": report.lines,
            "headerLines": report.header_lines,
            "truncatedFindings": report.truncated,
            "notChecked": list(report.skipped),
        },
    }
    return {"$schema": SARIF_SCHEMA, "version": "2.1.0", "runs": [run]}


def to_sarif(report, catalogue=None):
    log = to_sarif_dict(report, catalogue)
    return json.dumps(log, indent=2, ensure_ascii=False) + "\n"
