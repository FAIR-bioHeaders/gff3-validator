"""Build the in-browser validator page into web/dist.

Run from anywhere, with poetry on PATH:

    python scripts/build_web.py                 # build the wheel and web/dist
    python scripts/build_web.py --wheel X.whl   # use an existing wheel
    python scripts/build_web.py --pin 314.0.8   # bump Pyodide (downloads, then rebuild)

web/dist then holds index.html (with the Content-Security-Policy filled in),
app.js, worker.js, glue.js, style.css, the gff3-validator wheel and
manifest.json (wheel file name and sha256, and the pinned Pyodide version,
CDN base URL and Subresource Integrity hashes from web/pyodide.json). Serve
it with any static web server, for example
``python -m http.server -d web/dist``.

``--pin VERSION`` downloads pyodide.js and pyodide-lock.json of that Pyodide
release from jsDelivr, computes their sha384 SRI hashes and rewrites
web/pyodide.json. Check that PyYAML is still in the release's packages, then
update the pyodide version in web/test/package.json (``npm install
pyodide@VERSION --save-exact`` there) so that the parity test uses the same
release.
"""

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gff3_validator import __version__  # noqa: E402
from gff3_validator.report import SCRIPT_HASH, STYLE_HASH  # noqa: E402

WEB = ROOT / "web"
PIN = WEB / "pyodide.json"
STATIC = ("app.js", "worker.js", "glue.js", "style.css")
CDN = "https://cdn.jsdelivr.net/pyodide/v{version}/full/"
PINNED_FILES = ("pyodide.js", "pyodide-lock.json")


def sri(data):
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def pin(version):
    base = CDN.format(version=version)
    integrity = {}
    for name in PINNED_FILES:
        with urllib.request.urlopen(base + name, timeout=60) as response:
            data = response.read()
        integrity[name] = sri(data)
        if name == "pyodide-lock.json":
            packages = json.loads(data)["packages"]
            if "pyyaml" not in packages:
                raise SystemExit(f"Pyodide {version} has no pyyaml package")
    pinned = {"version": version, "base": base, "integrity": integrity}
    PIN.write_text(json.dumps(pinned, indent=2) + "\n", encoding="utf-8")
    print(f"pinned Pyodide {version} in {PIN.relative_to(ROOT)}")


def build_wheel(directory):
    subprocess.run(
        ["poetry", "build", "--format", "wheel", "--output", str(directory)],
        cwd=ROOT,
        check=True,
    )
    (wheel,) = Path(directory).glob("gff3_validator-*.whl")
    return wheel


def build(out, wheel=None):
    pinned = json.loads(PIN.read_text(encoding="utf-8"))
    if pinned["base"] != CDN.format(version=pinned["version"]):
        raise SystemExit(f"{PIN}: base does not match version")
    with tempfile.TemporaryDirectory() as scratch:
        wheel = Path(wheel) if wheel else build_wheel(scratch)
        data = wheel.read_bytes()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    target = out / wheel.name
    target.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    page = (WEB / "index.html").read_text(encoding="utf-8")
    for key, value in (
        ("{{PYODIDE_BASE}}", pinned["base"]),
        ("{{REPORT_SCRIPT_HASH}}", SCRIPT_HASH),
        ("{{REPORT_STYLE_HASH}}", STYLE_HASH),
    ):
        if key not in page:
            raise SystemExit(f"web/index.html has no {key}")
        page = page.replace(key, value)
    (out / "index.html").write_text(page, encoding="utf-8")
    for name in STATIC:
        shutil.copyfile(WEB / name, out / name)
    manifest = {
        "version": __version__,
        "wheel": target.name,
        "wheel_sha256": digest,
        "pyodide": pinned,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {out} ({target.name}, Pyodide {pinned['version']})")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=WEB / "dist")
    parser.add_argument("--wheel", help="use this wheel instead of building one")
    parser.add_argument("--pin", metavar="VERSION", help="pin a Pyodide release")
    args = parser.parse_args(argv)
    if args.pin:
        pin(args.pin)
        return 0
    build(args.out.resolve(), args.wheel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
