"""Update the Sequence Ontology release bundled in the package (question 13).

Standard library only. Writes two files into ``gff3_validator/data/``:

- ``so.json.gz``: a compact, deterministic file derived from ``so.obo`` with
  only what the SO rules use (id, label, obsolete flag with replaced_by and
  consider, EXACT synonyms, is_a and part_of parents, subsets);
- ``so-release.json``: the release's data-version and date, the source URL
  and SO-Ontologies commit, and the sha256 of ``so.obo`` and of the derived
  file.

SO has not published a GitHub release since v3.1 (2018); its releases are the
dated ``data-version`` of ``Ontology_Files/so.obo`` on the default branch. The
script therefore takes the latest commit that changed that file:

    python scripts/update_so.py                  # latest so.obo from GitHub
    python scripts/update_so.py --commit SHA     # so.obo at a given commit
    python scripts/update_so.py --obo so.obo --source URL   # a local copy
    python scripts/update_so.py --check          # exit 1 if SO has a newer so.obo
                                                 # (2 if GitHub cannot be reached)

The network is used only by this script, never during validation. After an
update, run the tests, update the expected outputs that name the release and
note the new release in CHANGELOG.md.
"""

import argparse
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_ontology_module():
    """gff3_validator/ontology.py on its own (standard library only), without
    importing the package, whose engine needs PyYAML."""
    path = ROOT / "gff3_validator" / "ontology.py"
    spec = importlib.util.spec_from_file_location("gff3_validator_ontology", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ontology = _load_ontology_module()

REPOSITORY = "The-Sequence-Ontology/SO-Ontologies"
PATH = "Ontology_Files/so.obo"
API = f"https://api.github.com/repos/{REPOSITORY}"
RAW = f"https://raw.githubusercontent.com/{REPOSITORY}/{{commit}}/{PATH}"
DATA = ROOT / "gff3_validator" / ontology.DATA
MAX_OBO = 64 << 20


def fetch(url):
    request = urllib.request.Request(
        url, headers={"User-Agent": "gff3-validator update_so.py"}
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read(MAX_OBO + 1)
    if len(data) > MAX_OBO:
        raise SystemExit(f"{url}: larger than {MAX_OBO} bytes")
    return data


def latest_commit():
    """The latest commit on the default branch that changed so.obo."""
    commits = json.loads(fetch(f"{API}/commits?path={PATH}&per_page=1"))
    if not commits:
        raise SystemExit(f"no commits found for {PATH}")
    return commits[0]["sha"], commits[0]["commit"]["committer"]["date"]


def bundled_release():
    path = DATA / ontology.RELEASE_FILE
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write(obo_path, source, commit=None):
    header, terms, digest = ontology.read_obo(obo_path)
    derived = ontology.derived_bytes(terms)
    # The derived file must load and keep every term.
    ontology.Ontology(json.loads(gzip.decompress(derived))["terms"], {})
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / ontology.TERMS_FILE).write_bytes(derived)
    release = {
        "ontology": "Sequence Ontology (so.obo)",
        "data_version": header.get("data-version"),
        "date": header.get("date"),
        "source": source,
        "commit": commit,
        "sha256": digest,
        "terms": len(terms),
        "obsolete_terms": sum(1 for term in terms.values() if term.get("obsolete")),
        "derived_file": ontology.TERMS_FILE,
        "derived_sha256": hashlib.sha256(derived).hexdigest(),
        "generated_by": "scripts/update_so.py",
    }
    (DATA / ontology.RELEASE_FILE).write_text(
        json.dumps(release, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"bundled so.obo data-version {release['data_version']} "
        f"({len(terms)} terms; {len(derived)} bytes derived)"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--obo", help="read this so.obo instead of downloading")
    parser.add_argument("--source", help="source URL recorded with --obo")
    parser.add_argument("--commit", help="SO-Ontologies commit to download")
    parser.add_argument(
        "--check",
        action="store_true",
        help="only report whether SO has a newer so.obo (exit 1 if so)",
    )
    args = parser.parse_args(argv)
    if args.check:
        try:
            sha, date = latest_commit()
        except (OSError, ValueError, KeyError) as error:
            print(f"cannot check SO-Ontologies: {error}", file=sys.stderr)
            return 2
        current = bundled_release()
        if current.get("commit") == sha:
            print(f"up to date: so.obo data-version {current.get('data_version')}")
            return 0
        print(
            f"newer so.obo: commit {sha} ({date}); bundled: commit "
            f"{current.get('commit')} data-version {current.get('data_version')}"
        )
        return 1
    if args.obo:
        if not args.source:
            parser.error("--obo needs --source (the URL the file came from)")
        write(args.obo, args.source, args.commit)
        return 0
    commit = args.commit or latest_commit()[0]
    url = RAW.format(commit=commit)
    data = fetch(url)
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "so.obo"
        path.write_bytes(data)
        write(path, url, commit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
