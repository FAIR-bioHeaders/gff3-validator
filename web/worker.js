/*
 * The page's Web Worker: loads Pyodide and the validator, then validates the
 * files the page sends. It is started from a blob: URL so that it inherits
 * the page's Content-Security-Policy (a worker loaded from an ordinary URL
 * would take its policy from HTTP headers, which GitHub Pages does not set).
 * Files are read here with FileReaderSync, in slices; nothing is sent
 * anywhere.
 */
/* global importScripts, loadPyodide, FileReaderSync, GFF3Glue */
"use strict";

var pyodide = null;

function post(message) {
  self.postMessage(message);
}

async function fetchChecked(url, integrity) {
  var response = await fetch(url, {
    integrity: integrity,
    mode: "cors",
    credentials: "omit",
    referrerPolicy: "no-referrer",
  });
  if (!response.ok) throw new Error("could not load " + url + " (" + response.status + ")");
  return response;
}

async function init(message) {
  var manifest = message.manifest;
  var cdn = manifest.pyodide.base;
  importScripts(new URL("glue.js", message.base).href);

  post({ type: "progress", phase: "runtime", text: "Downloading the Python runtime (Pyodide " + manifest.pyodide.version + ")" });
  // pyodide.js and pyodide-lock.json are checked with Subresource Integrity;
  // the lock file in turn pins the sha256 of PyYAML.
  var script = await (await fetchChecked(cdn + "pyodide.js", manifest.pyodide.integrity["pyodide.js"])).text();
  var lock = await (await fetchChecked(cdn + "pyodide-lock.json", manifest.pyodide.integrity["pyodide-lock.json"])).text();
  var scriptUrl = URL.createObjectURL(new Blob([script], { type: "text/javascript" }));
  try {
    importScripts(scriptUrl);
  } finally {
    URL.revokeObjectURL(scriptUrl);
  }
  post({ type: "progress", phase: "runtime", text: "Starting Python" });
  pyodide = await loadPyodide({ indexURL: cdn, lockFileContents: lock, packageBaseUrl: cdn });

  post({ type: "progress", phase: "runtime", text: "Installing gff3-validator" });
  var wheel = await fetch(new URL(manifest.wheel, message.base).href, { credentials: "omit" });
  if (!wheel.ok) throw new Error("could not load " + manifest.wheel + " (" + wheel.status + ")");
  var facts = await GFF3Glue.install(pyodide, await wheel.arrayBuffer(), manifest.wheel_sha256, crypto.subtle);
  post({ type: "ready", facts: facts });
}

function slices(file) {
  var reader = new FileReaderSync();
  return {
    name: file.name,
    size: file.size,
    readAt: function (offset, length) {
      return reader.readAsArrayBuffer(file.slice(offset, offset + length));
    },
  };
}

function validate(message) {
  var last = 0;
  var started = Date.now();
  function onProgress(phase, done, total) {
    var now = Date.now();
    if (done < total && now - last < 150) return;
    last = now;
    post({ type: "progress", phase: phase, done: done, total: total });
  }
  var genome = message.genome ? slices(message.genome) : null;
  var result = GFF3Glue.validate(pyodide, slices(message.file), genome, message.options, onProgress);
  result.seconds = (Date.now() - started) / 1000;
  post({ type: "result", result: result });
}

self.onmessage = async function (event) {
  var message = event.data;
  try {
    if (message.type === "init") await init(message);
    else if (message.type === "validate") validate(message);
  } catch (error) {
    post({ type: "error", during: message.type, message: String((error && error.message) || error) });
  }
};
