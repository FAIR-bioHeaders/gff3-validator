// Parity test: the in-browser validator (the page's glue.js and the built
// wheel, in Pyodide under Node.js) must give byte-identical JSON, SARIF and
// HTML reports to the CLI, for every fixture in tests/fixtures/expected.yaml,
// plain and gzipped, for the header and translation-table options, and for
// the profile cases of the conformance suite with --profile.
//
// Usage (from the repository root, after scripts/build_web.py):
//   (cd web/test && npm ci)
//   node web/test/parity.mjs [--python "poetry run python"]
//
// The npm pyodide version must be the one pinned in web/pyodide.json; its
// pyodide.js and pyodide-lock.json must match the pinned SRI hashes, so the
// test runs exactly what the page loads from the CDN. PyYAML is fetched from
// the pinned CDN release, as on the page.

import { execFileSync } from "node:child_process";
import { createHash, webcrypto } from "node:crypto";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { gzipSync } from "node:zlib";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const args = process.argv.slice(2);
const pythonOption = args.indexOf("--python");
const python = (pythonOption >= 0 ? args[pythonOption + 1] : process.env.PYTHON || "python").split(" ");

function fail(message) {
  console.error("parity: " + message);
  process.exit(1);
}

// -- the pinned Pyodide -----------------------------------------------------
const pinned = JSON.parse(readFileSync(join(root, "web", "pyodide.json"), "utf8"));
const pyodideDir = dirname(require.resolve("pyodide/package.json"));
const npmVersion = JSON.parse(readFileSync(join(pyodideDir, "package.json"), "utf8")).version;
if (npmVersion !== pinned.version) fail(`npm pyodide ${npmVersion} is not the pinned ${pinned.version}`);
for (const [name, integrity] of Object.entries(pinned.integrity)) {
  const digest = "sha384-" + createHash("sha384").update(readFileSync(join(pyodideDir, name))).digest("base64");
  if (digest !== integrity) fail(`${name} from npm does not match the pinned SRI hash`);
}

// -- the built page -----------------------------------------------------------
const dist = join(root, "web", "dist");
const manifest = JSON.parse(readFileSync(join(dist, "manifest.json"), "utf8"));
// Pyodide takes typed arrays, not Node's Buffer subclass.
const bytes = (buffer) => new Uint8Array(buffer.buffer, buffer.byteOffset, buffer.byteLength);
const wheel = bytes(readFileSync(join(dist, manifest.wheel)));
const glue = require(join(root, "web", "glue.js"));

const { loadPyodide } = await import("pyodide");
const pyodide = await loadPyodide({ packageBaseUrl: pinned.base });
const facts = await glue.install(pyodide, wheel, manifest.wheel_sha256, webcrypto.subtle);
console.log(`gff3-validator ${facts.version} in Pyodide ${pyodide.version} (Python ${pyodide.runPython("import sys; sys.version.split()[0]")})`);

// -- cases ----------------------------------------------------------------------
const fixtures = join(root, "tests", "fixtures");
const names = JSON.parse(
  execFileSync(python[0], [...python.slice(1), "-c",
    "import json, sys, yaml; print(json.dumps(sorted(yaml.safe_load(open(sys.argv[1], encoding='utf-8')))))",
    join(fixtures, "expected.yaml")], { cwd: root, encoding: "utf8" })
);
const scratch = mkdtempSync(join(tmpdir(), "gff3-parity-"));
const genome = relative(root, join(fixtures, "biology", "genome.fa"));
const genomeGz = relative(root, join(fixtures, "biology", "genome.fa.gz"));
const cases = [];
function add(id, path, options = {}) {
  const cli = [];
  if (options.headerMode === "require") cli.push("--require-header");
  if (options.headerMode === "skip") cli.push("--no-header");
  if (options.genome) cli.push("--genome", options.genome);
  if (options.translationTable) cli.push("--translation-table", String(options.translationTable));
  if (options.profile) cli.push("--profile", options.profile);
  cases.push({ id, path, options, args: [...cli, path] });
}
for (const name of names) {
  const path = relative(root, join(fixtures, name));
  const options = name.startsWith("biology/") ? { genome } : {};
  add(name, path, options);
  const gz = join(scratch, name.replace(/\//g, "_") + ".gz");
  writeFileSync(gz, gzipSync(readFileSync(join(root, path))));
  add(name + " (gzip)", gz, options);
}
for (const name of ["valid/fhgff3_header.gff3", "valid/canonical_gene.gff3"]) {
  const path = relative(root, join(fixtures, name));
  add(name + " --require-header", path, { headerMode: "require" });
  add(name + " --no-header", path, { headerMode: "skip" });
}
for (const name of names.filter((n) => n.startsWith("biology/"))) {
  for (const table of [4, 11]) {
    add(`${name} --genome genome.fa.gz --translation-table ${table}`,
      relative(root, join(fixtures, name)), { genome: genomeGz, translationTable: table });
  }
}

const suite = join(root, "conformance");
const conformance = JSON.parse(readFileSync(join(suite, "manifest.json"), "utf8"));
for (const item of conformance.profile_cases || []) {
  const options = { profile: item.profile };
  if (item.genome) options.genome = relative(root, join(suite, item.genome));
  add(`${item.file} --profile ${item.profile}`, relative(root, join(suite, item.file)), options);
}

// -- the CLI, in one Python process -------------------------------------------
const casesFile = join(scratch, "cases.json");
writeFileSync(casesFile, JSON.stringify(cases.map(({ id, args }) => ({ id, args }))));
const expected = JSON.parse(
  execFileSync(python[0], [...python.slice(1), join(here, "cli_reports.py"), casesFile],
    { cwd: root, encoding: "utf8", maxBuffer: 1 << 30 })
);

// -- the page's glue, in Pyodide ----------------------------------------------
function fileOf(path) {
  const data = bytes(readFileSync(resolve(root, path)));
  return { name: path, size: data.length, readAt: (offset, length) => data.subarray(offset, offset + length) };
}
let failures = 0;
const differences = (a, b) => {
  for (let i = 0; i < Math.max(a.length, b.length); i++) if (a[i] !== b[i]) return `first difference at character ${i}`;
  return "";
};
for (const item of cases) {
  const genomeFile = item.options.genome ? fileOf(item.options.genome) : null;
  const got = glue.validate(pyodide, fileOf(item.path), genomeFile, item.options);
  const want = expected[item.id];
  const problems = [];
  if (!got.ok) problems.push("page could not validate: " + got.error);
  else {
    const passed = got.valid && got.compliant !== false;
    if ((want.exit === 0) !== passed || want.exit === 2) problems.push(`exit ${want.exit} but valid=${got.valid} compliant=${got.compliant}`);
    for (const fmt of ["json", "sarif", "html"]) {
      if (got[fmt] !== want[fmt]) problems.push(`${fmt} differs (${differences(got[fmt], want[fmt])})`);
    }
    const rules = (text) => JSON.parse(text).findings.map((f) => `${f.rule}@${f.line}`).join(",");
    if (rules(got.json) !== rules(want.json)) problems.push(`rules/lines: page ${rules(got.json)} cli ${rules(want.json)}`);
  }
  if (problems.length) {
    failures++;
    console.log(`FAIL ${item.id}: ${problems.join("; ")}`);
  }
}
rmSync(scratch, { recursive: true, force: true });
console.log(`${cases.length - failures} of ${cases.length} cases identical to the CLI (JSON, SARIF, HTML, exit status)`);
process.exit(failures ? 1 : 0);
