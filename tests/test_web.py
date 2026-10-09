"""The in-browser page: build output, CSP and the Pyodide pin.

The page itself is tested in Pyodide by web/test/parity.mjs (CI job "web").
"""

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT / "scripts"))

import build_web  # noqa: E402

from gff3_validator.report import SCRIPT_HASH, STYLE_HASH  # noqa: E402

PIN = json.loads((WEB / "pyodide.json").read_text(encoding="utf-8"))


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_pyodide_pin_is_consistent():
    version = PIN["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), "pin an exact release"
    assert PIN["base"] == f"https://cdn.jsdelivr.net/pyodide/v{version}/full/"
    assert set(PIN["integrity"]) == {"pyodide.js", "pyodide-lock.json"}
    for value in PIN["integrity"].values():
        assert re.fullmatch(r"sha384-[A-Za-z0-9+/]{64}", value)
    package = json.loads((WEB / "test" / "package.json").read_text(encoding="utf-8"))
    assert package["dependencies"]["pyodide"] == version
    lock = json.loads((WEB / "test" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/pyodide"]["version"] == version


def test_build_fills_in_the_csp_and_manifest(tmp_path):
    wheel = tmp_path / "gff3_validator-0.0.0-py3-none-any.whl"
    wheel.write_bytes(b"not really a wheel")
    out = tmp_path / "dist"
    build_web.build(out, wheel)
    names = {path.name for path in out.iterdir()}
    assert names == {
        "index.html",
        "manifest.json",
        ".nojekyll",
        wheel.name,
        *build_web.STATIC,
    }
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["wheel"] == wheel.name
    assert manifest["wheel_sha256"] == hashlib.sha256(wheel.read_bytes()).hexdigest()
    assert manifest["pyodide"] == PIN

    page = (out / "index.html").read_text(encoding="utf-8")
    assert "{{" not in page
    parser = Tags()
    parser.feed(page)
    (csp,) = [
        attrs["content"]
        for tag, attrs in parser.tags
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy"
    ]
    directives = {
        part.split()[0]: part.split()[1:] for part in csp.split(";") if part.strip()
    }
    assert directives["default-src"] == ["'none'"]
    # Network access: this site and the pinned Pyodide release only.
    assert directives["connect-src"] == ["'self'", PIN["base"]]
    assert set(directives["script-src"]) == {
        "'self'",
        "blob:",
        PIN["base"],
        "'wasm-unsafe-eval'",
        SCRIPT_HASH,
    }
    assert directives["style-src"] == ["'self'", STYLE_HASH]
    assert directives["worker-src"] == ["blob:"]
    assert "'unsafe-inline'" not in csp and "'unsafe-eval'" not in csp
    # No inline scripts and nothing loaded from elsewhere.
    for tag, attrs in parser.tags:
        if tag == "script":
            assert attrs.get("src") == "app.js"
        for key in ("src", "href"):
            value = attrs.get(key, "")
            if tag != "a" and value:
                assert "//" not in value, (tag, value)
