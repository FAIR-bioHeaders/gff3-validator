/*
 * The page: reads manifest.json, starts the validator worker and shows the
 * report. Validation happens in worker.js; no file content leaves the page.
 */
"use strict";

(function () {
  var $ = function (id) {
    return document.getElementById(id);
  };
  var state = { worker: null, ready: false, busy: false, file: null, genome: null, result: null, facts: null };
  var GENOME_WARN_BYTES = 300 * 1024 * 1024;

  function formatBytes(n) {
    if (n < 1024) return n + " B";
    var units = ["KB", "MB", "GB"];
    var i = -1;
    do {
      n /= 1024;
      i++;
    } while (n >= 1024 && i < units.length - 1);
    return n.toFixed(n < 10 ? 1 : 0) + " " + units[i];
  }

  function status(text, done, total) {
    $("status-text").textContent = text;
    var bar = $("progress");
    if (total) {
      bar.max = total;
      bar.value = done;
    } else {
      bar.removeAttribute("value"); // indeterminate
    }
  }

  function updateButton() {
    $("run").disabled = !(state.ready && state.file && !state.busy);
  }

  function chooseFile(file) {
    state.file = file || null;
    $("gff3-chosen").textContent = file ? file.name + " (" + formatBytes(file.size) + ")" : "";
    updateButton();
  }

  function chooseGenome(file) {
    state.genome = file || null;
    var text = "";
    if (file) {
      text = file.name + " (" + formatBytes(file.size) + ")";
      if (file.size > GENOME_WARN_BYTES) {
        text += ": large genome; the tab may run out of memory.";
      }
    }
    $("genome-chosen").textContent = text;
    $("genome-chosen").classList.toggle("alert", !!file && file.size > GENOME_WARN_BYTES);
    $("table").disabled = !file;
  }

  function startWorker() {
    var base = new URL(".", location.href).href;
    return fetch("manifest.json", { cache: "no-cache" })
      .then(function (r) {
        if (!r.ok) throw new Error("manifest.json: " + r.status);
        return r.json();
      })
      .then(function (manifest) {
        return fetch("worker.js").then(function (r) {
          if (!r.ok) throw new Error("worker.js: " + r.status);
          return r.text().then(function (source) {
            // A blob: worker inherits this page's Content-Security-Policy.
            var url = URL.createObjectURL(new Blob([source], { type: "text/javascript" }));
            var worker = new Worker(url);
            URL.revokeObjectURL(url);
            worker.onmessage = onMessage;
            worker.onerror = function (event) {
              fail("The validator stopped: " + (event.message || "unknown error"));
            };
            worker.postMessage({ type: "init", base: base, manifest: manifest });
            state.worker = worker;
          });
        });
      })
      .catch(function (error) {
        fail("Could not start the validator: " + error.message);
      });
  }

  function fail(text) {
    state.busy = false;
    $("status-text").textContent = text;
    $("status-text").classList.add("alert");
    $("progress").hidden = true;
    updateButton();
  }

  function onMessage(event) {
    var m = event.data;
    if (m.type === "progress") {
      if (m.phase === "runtime") status(m.text);
      else if (m.phase === "genome") status("Copying the genome into memory: " + formatBytes(m.done) + " of " + formatBytes(m.total), m.done, m.total);
      else status("Validating: read " + formatBytes(m.done) + " of " + formatBytes(m.total), m.done, m.total);
    } else if (m.type === "ready") {
      state.ready = true;
      state.facts = m.facts;
      var select = $("table");
      select.textContent = "";
      m.facts.tables.forEach(function (entry) {
        var option = document.createElement("option");
        option.value = String(entry[0]);
        option.textContent = entry[0] + ": " + entry[1];
        if (entry[0] === m.facts.default_table) option.selected = true;
        select.appendChild(option);
      });
      $("engine-version").textContent = m.facts.version + " (catalogue " + m.facts.catalogue + ")";
      status("Ready. Choose a GFF3 file.", 1, 1);
      $("progress").hidden = false;
      updateButton();
    } else if (m.type === "result") {
      state.busy = false;
      showResult(m.result);
      updateButton();
    } else if (m.type === "error") {
      fail((m.during === "init" ? "Could not load the validator: " : "Validation failed: ") + m.message);
    }
  }

  function showResult(result) {
    if (!result.ok) {
      state.result = null;
      $("results").hidden = true;
      fail("The file could not be read completely: " + result.error);
      return;
    }
    state.result = result;
    status("Done in " + result.seconds.toFixed(1) + " s.", 1, 1);
    var verdict = $("verdict");
    verdict.textContent = state.file.name + ": " + result.summary;
    verdict.className = result.valid ? "ok" : "bad";
    $("report").srcdoc = result.html;
    $("results").hidden = false;
    $("results-title").focus();
  }

  function download(kind) {
    if (!state.result) return;
    var types = { html: "text/html", json: "application/json", sarif: "application/sarif+json" };
    var suffix = { html: ".report.html", json: ".report.json", sarif: ".sarif" };
    var blob = new Blob([state.result[kind]], { type: types[kind] + ";charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = state.file.name.replace(/\.gz$/i, "") + suffix[kind];
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () {
      URL.revokeObjectURL(a.href);
    }, 10000);
  }

  function submit(event) {
    event.preventDefault();
    if (!state.ready || !state.file || state.busy) return;
    state.busy = true;
    updateButton();
    $("status-text").classList.remove("alert");
    $("progress").hidden = false;
    status("Starting...");
    var form = $("form");
    var options = { headerMode: form.elements.header.value };
    if (state.genome) options.translationTable = Number($("table").value);
    state.worker.postMessage({ type: "validate", file: state.file, genome: state.genome, options: options });
  }

  document.addEventListener("DOMContentLoaded", function () {
    $("gff3").addEventListener("change", function () {
      chooseFile(this.files[0]);
    });
    $("genome").addEventListener("change", function () {
      chooseGenome(this.files[0]);
    });
    $("clear-genome").addEventListener("click", function () {
      $("genome").value = "";
      chooseGenome(null);
    });
    var drop = $("drop");
    ["dragenter", "dragover"].forEach(function (name) {
      drop.addEventListener(name, function (event) {
        event.preventDefault();
        drop.classList.add("over");
      });
    });
    ["dragleave", "drop"].forEach(function (name) {
      drop.addEventListener(name, function (event) {
        event.preventDefault();
        drop.classList.remove("over");
      });
    });
    drop.addEventListener("drop", function (event) {
      var files = event.dataTransfer && event.dataTransfer.files;
      if (files && files.length) chooseFile(files[0]);
    });
    $("form").addEventListener("submit", submit);
    document.querySelectorAll("[data-download]").forEach(function (button) {
      button.addEventListener("click", function () {
        download(button.getAttribute("data-download"));
      });
    });
    $("results-title").tabIndex = -1;
    status("Loading the Python runtime...");
    startWorker();
  });
})();
