/*
 * gff3-validator in Pyodide: the code shared by the page's Web Worker
 * (worker.js) and the Node.js parity test (web/test/parity.mjs).
 *
 * It installs the gff3-validator wheel and PyYAML into a loaded Pyodide and
 * runs gff3_validator.web.run() on a file given as (size, readAt), where
 * readAt(offset, length) returns the bytes at offset. The GFF3 file is read
 * in 1 MiB slices on demand and is never copied whole into memory. An
 * optional genome FASTA is copied into Pyodide's in-memory file system,
 * because the engine reads it by random access.
 */
(function (root) {
  "use strict";

  var GENOME_DIR = "/tmp/gff3-validator-genome";
  var GENOME_CHUNK = 8 * 1024 * 1024;

  function hex(buffer) {
    return Array.prototype.map
      .call(new Uint8Array(buffer), function (b) {
        return b.toString(16).padStart(2, "0");
      })
      .join("");
  }

  /* Install PyYAML (from Pyodide's own packages, checked against the
   * sha256 in pyodide-lock.json) and the gff3-validator wheel (checked
   * against the sha256 in the page's manifest). Returns engine facts. */
  async function install(pyodide, wheelBytes, wheelSha256, subtle) {
    await pyodide.loadPackage("pyyaml", {
      checkIntegrity: true,
      messageCallback: function () {},
    });
    if (wheelSha256) {
      var digest = hex(await subtle.digest("SHA-256", wheelBytes));
      if (digest !== wheelSha256) {
        throw new Error(
          "the gff3-validator wheel does not match its sha256 in manifest.json"
        );
      }
    }
    var site = pyodide.runPython("import site; site.getsitepackages()[0]");
    pyodide.unpackArchive(wheelBytes, "wheel", { extractDir: site });
    var facts = pyodide.runPython(
      [
        "import json",
        "import gff3_validator",
        "from gff3_validator import codons, load_catalogue",
        "_c = load_catalogue()",
        "json.dumps({",
        "  'version': gff3_validator.__version__,",
        "  'catalogue': _c.version,",
        "  'tables': [[n, codons.TABLES[n][0]] for n in sorted(codons.TABLES)],",
        "  'default_table': codons.DEFAULT_TABLE,",
        "  'so': _c.sources['so']['title'],",
        "})",
      ].join("\n")
    );
    return JSON.parse(facts);
  }

  function copyIntoFS(pyodide, path, size, readAt, onProgress) {
    var FS = pyodide.FS;
    var stream = FS.open(path, "w");
    try {
      for (var offset = 0; offset < size; ) {
        var length = Math.min(GENOME_CHUNK, size - offset);
        var data = new Uint8Array(readAt(offset, length));
        if (data.length === 0) throw new Error("the genome file ended early");
        FS.write(stream, data, 0, data.length);
        offset += data.length;
        if (onProgress) onProgress("genome", offset, size);
      }
    } finally {
      FS.close(stream);
    }
  }

  /* Validate one file. options: {headerMode: "auto"|"require"|"skip",
   * translationTable: number|undefined}. genome: {size, readAt}|null.
   * Returns {ok, error} or {ok, valid, counts, summary, json, sarif, html,
   * text}, as gff3_validator.web.run. */
  function validate(pyodide, file, genome, options, onProgress) {
    options = options || {};
    var web = pyodide.pyimport("gff3_validator.web");
    var genomePath;
    var stream, result, kwargs;
    try {
      if (genome) {
        pyodide.FS.mkdirTree(GENOME_DIR);
        genomePath = GENOME_DIR + "/genome.fa";
        copyIntoFS(pyodide, genomePath, genome.size, genome.readAt, onProgress);
      }
      stream = web.open_callback(file.size, file.readAt, function (done, size) {
        if (onProgress) onProgress("gff3", done, size);
      });
      kwargs = { header_mode: options.headerMode || "auto" };
      if (genomePath) kwargs.genome = genomePath;
      if (options.translationTable !== undefined && options.translationTable !== null) {
        kwargs.translation_table = Number(options.translationTable);
      }
      result = web.run.callKwargs(stream, file.name, kwargs);
      return result.toJs({ dict_converter: Object.fromEntries });
    } finally {
      if (result) result.destroy();
      if (stream) {
        stream.close();
        stream.destroy();
      }
      web.destroy();
      if (genomePath) {
        try {
          pyodide.FS.unlink(genomePath);
        } catch (e) {
          /* already gone */
        }
      }
    }
  }

  var api = { install: install, validate: validate, GENOME_DIR: GENOME_DIR };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.GFF3Glue = api;
})(typeof self !== "undefined" ? self : globalThis);
