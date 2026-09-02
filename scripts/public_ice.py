#!/usr/bin/env python3
"""Fetch the public TIP4P/Ice nucleation dumps of Niu, Yang and Parrinello.

Materials Cloud record 10.24435/materialscloud:2020.0005/v1 holds two
archives of raw LAMMPS dumps: three homogeneous nucleation runs and the
critical-nucleus committor pair (one growing, one melting). This script
downloads both archives, verifies them against the MD5 sums the record
publishes, and unpacks the dumps under one directory.

  public_ice.py fetch <dir>      download, verify, unpack
  public_ice.py list  <dir>      print name, path, atoms per frame, frames
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import urllib.request
import zipfile

BASE = "https://archive.materialscloud.org/records/kc275-mc539/files/"
ARCHIVES = {
    "Nucleation.zip": "bddcd4d35b1fed3353dcc320343907ec",
    "CriticalNucleus.zip": "b02811b02fb00a97b941dbd63b23c165",
}
DOI = "10.24435/materialscloud:2020.0005/v1"

# name -> path inside the unpacked archives
DUMPS = {
    "niu-traj1-extract": "nucleation/Ice_nucleation_trajectory/Nucleation_trajectory-1",
    "niu-traj2-foursite": "nucleation/Ice_nucleation_trajectory/Nucleation_trajectory-2",
    "niu-traj3-oxygen": "nucleation/Ice_nucleation_trajectory/Nucleation_trajectory-3",
    "niu-critical-growing": "critical/Critical-nucleus_analysis-trajectory/Critical-nucleus-analysis-growing",
    "niu-critical-melting": "critical/Critical-nucleus_analysis-trajectory/Critical-nucleus-analysis-melting",
}
UNPACK_DIR = {"Nucleation.zip": "nucleation", "CriticalNucleus.zip": "critical"}


def md5(path: pathlib.Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(root: pathlib.Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, digest in ARCHIVES.items():
        target = root / name
        if not target.exists() or md5(target) != digest:
            urllib.request.urlretrieve(BASE + name + "?download=1", target)
        actual = md5(target)
        if actual != digest:
            raise SystemExit(f"{name}: md5 {actual} != {digest}")
        out = root / UNPACK_DIR[name]
        if not out.is_dir():
            with zipfile.ZipFile(target) as zf:
                zf.extractall(out)
    missing = [k for k, rel in DUMPS.items() if not (root / rel).is_file()]
    if missing:
        raise SystemExit(f"dumps missing after unpack: {missing}")
    (root / "SOURCE.json").write_text(
        json.dumps({"doi": DOI, "archives": ARCHIVES, "dumps": DUMPS}, indent=2)
        + "\n"
    )


def frames_and_atoms(path: pathlib.Path) -> tuple[int, int]:
    frames = 0
    atoms = 0
    with path.open("rb") as fh:
        for line in fh:
            if line.startswith(b"ITEM: TIMESTEP"):
                frames += 1
            elif frames == 1 and line.startswith(b"ITEM: NUMBER OF ATOMS"):
                atoms = int(next(fh))
    return frames, atoms


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in {"fetch", "list"}:
        print(__doc__, file=sys.stderr)
        return 2
    root = pathlib.Path(argv[2])
    if argv[1] == "fetch":
        fetch(root)
        return 0
    for name, rel in DUMPS.items():
        p = root / rel
        f, a = frames_and_atoms(p)
        print(f"{name} {p} atoms_frame1={a} frames={f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
