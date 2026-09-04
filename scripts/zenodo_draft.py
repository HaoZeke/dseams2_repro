#!/usr/bin/env python3
"""Create or refresh one unpublished Zenodo draft. Never publishes.

  ZENODO_TOKEN=$(pass websites/zenodo/api) \\
    python scripts/zenodo_draft.py dseams2_repro_archive_YYYYMMDD.tar.xz

The token is read from ZENODO_TOKEN or from `pass websites/zenodo/api`.
The script prints the draft HTML URL and the reserved DOI, then exits.
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://zenodo.org/api"


def token() -> str:
    env = os.environ.get("ZENODO_TOKEN", "").strip()
    if env:
        return env
    out = subprocess.check_output(["pass", "websites/zenodo/api"], text=True)
    return out.strip().splitlines()[0]


def request(method: str, url: str, tok: str, data=None, content_type=None):
    headers = {"Authorization": f"Bearer {tok}"}
    body = None
    if data is not None and not isinstance(data, (bytes, bytearray)):
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    elif data is not None:
        body = data
        if content_type:
            headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"{method} {url} -> {exc.code}: {err}") from exc


def metadata(version: str) -> dict:
    return {
        "metadata": {
            "title": (
                "dseams2_repro: reproducibility package for d-SEAMS 2.0 "
                f"({version})"
            ),
            "upload_type": "software",
            "description": (
                "<p>Reproducibility package for d-SEAMS 2.0: the locked "
                "Snakemake campaign, exclusive-node timings, the mW seeding "
                "committor (216 ICE files) and the ice/brine "
                "direct-coexistence COLVARs (24 BRINE files). The archive "
                "contains the tagged <code>dseams2_repro</code> tree, "
                "<code>pixi.lock</code>, the ecosystem lock (seams-core "
                "v2.9.2), and the measured result files.</p>"
                "<p>This record is the software and the numbers. The "
                "manuscript is not included. The 2020 JCIM article is "
                '<a href="https://doi.org/10.1021/acs.jcim.0c00031">'
                "10.1021/acs.jcim.0c00031</a>. Application trajectories "
                "from that article remain on "
                '<a href="https://figshare.com/projects/d-SEAMS_Datasets/73545">'
                "figshare project 73545</a>.</p>"
                "<p>License: MIT. Reproduce with <code>pixi</code> and the "
                "Snakefile listed in the archive README.</p>"
            ),
            "creators": [
                {
                    "name": "Goswami, Rohit",
                    "orcid": "0000-0002-2393-8056",
                },
                {
                    "name": "Goswami, Amrita",
                    "orcid": "0000-0001-8706-2383",
                },
                {
                    "name": "Goswami, Ruhila",
                    "orcid": "0000-0002-5443-9356",
                },
                {
                    "name": "Singh, Jayant K.",
                    "orcid": "0000-0001-8056-2115",
                },
            ],
            "keywords": [
                "d-SEAMS",
                "ice classification",
                "CHILL+",
                "cages",
                "committor",
                "brine",
                "reproducibility",
            ],
            "license": "mit",
            "version": version,
            "language": "eng",
            "access_right": "open",
            "communities": [{"identifier": "d-seams"}],
            "related_identifiers": [
                {
                    "identifier": "10.1021/acs.jcim.0c00031",
                    "relation": "isSupplementTo",
                    "scheme": "doi",
                },
                {
                    "identifier": "https://github.com/d-SEAMS/dseams2_repro",
                    "relation": "isSupplementTo",
                    "scheme": "url",
                },
                {
                    "identifier": "https://github.com/d-SEAMS/seams-core/releases/tag/v2.9.2",
                    "relation": "references",
                    "scheme": "url",
                },
                {
                    "identifier": "https://figshare.com/projects/d-SEAMS_Datasets/73545",
                    "relation": "references",
                    "scheme": "url",
                },
            ],
        }
    }


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    archive = pathlib.Path(argv[0])
    if not archive.is_file():
        raise SystemExit(f"missing archive {archive}")
    version = os.environ.get("ZENODO_VERSION", "2.7.0")
    tok = token()
    status, drafts = request(
        "GET",
        f"{API}/deposit/depositions?status=draft&size=50",
        tok,
    )
    title_want = metadata(version)["metadata"]["title"]
    dep = None
    for item in drafts:
        if item.get("title") == title_want or item.get("metadata", {}).get(
            "title"
        ) == title_want:
            dep = item
            break
    if dep is None:
        status, dep = request("POST", f"{API}/deposit/depositions", tok, data={})
        print("created deposition", dep["id"], "state", dep.get("state"))
    else:
        print("reusing draft", dep["id"], "state", dep.get("state"))
    dep_id = dep["id"]
    bucket = dep["links"]["bucket"]
    status, dep = request(
        "PUT",
        f"{API}/deposit/depositions/{dep_id}",
        tok,
        data=metadata(version),
    )
    print("metadata", status, "state", dep.get("state"), "submitted", dep.get("submitted"))
    sha = archive.with_suffix(archive.suffix + ".sha256")
    for path in (archive, sha if sha.is_file() else None):
        if path is None:
            continue
        print("uploading", path.name, path.stat().st_size, "bytes")
        with path.open("rb") as fh:
            body = fh.read()
        status, info = request(
            "PUT",
            f"{bucket}/{path.name}",
            tok,
            data=body,
        )
        print("uploaded", info.get("key"), info.get("checksum"), info.get("size"))
    status, dep = request("GET", f"{API}/deposit/depositions/{dep_id}", tok)
    html = dep["links"]["html"]
    doi = dep.get("metadata", {}).get("prereserve_doi", {}).get("doi")
    print("draft", html)
    print("reserved_doi", doi)
    print("state", dep.get("state"), "submitted", dep.get("submitted"))
    if dep.get("submitted") or dep.get("state") == "done":
        raise SystemExit("refusing to leave a published record from this script")


if __name__ == "__main__":
    main()
