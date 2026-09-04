#!/usr/bin/env python3
"""Frame-level cage and CHILL+ labels from seeding ICE files.

  python scripts/ml_labels.py RESULTS_DIR > ml_labels.csv

Each PRINT row of DSEAMS_CAGES is one training example. Columns are
temperature, seed_size, polymorph, replica, time, nice, nmax, nclus,
nic, nih, nmixed, chillice, chillmax, chillinterfacial, sixrings.
Those are the frame-level targets. Per-molecule states (water, Ic, Ih,
mixed) come from IceFeaturizer on the dump; see ml_molecule_labels.py.
"""
from __future__ import annotations

import csv
import json
import pathlib
import sys

from committor import read_ice

COLS = (
    "temperature",
    "seed_size",
    "polymorph",
    "replica",
    "time",
    "nice",
    "nmax",
    "nclus",
    "nic",
    "nih",
    "nmixed",
    "chillice",
    "chillmax",
    "chillinterfacial",
    "sixrings",
)
def rows_from(root: pathlib.Path):
    out = []
    for run in sorted(root.glob("*/run.json")):
        meta = json.loads(run.read_text())
        ice = run.parent / "ICE"
        if not ice.is_file():
            continue
        for r in read_ice(ice):
            out.append(
                {
                    "temperature": meta["temperature"],
                    "seed_size": meta["seed_size"],
                    "polymorph": meta["polymorph"],
                    "replica": meta["replica"],
                    "time": r.get("time", 0.0),
                    "nice": r.get("ice.nice", 0.0),
                    "nmax": r.get("ice.nmax", 0.0),
                    "nclus": r.get("ice.nclus", 0.0),
                    "nic": r.get("ice.nic", 0.0),
                    "nih": r.get("ice.nih", 0.0),
                    "nmixed": r.get("ice.nmixed", 0.0),
                    "chillice": r.get("ice.chillice", 0.0),
                    "chillmax": r.get("ice.chillmax", 0.0),
                    "chillinterfacial": r.get("ice.chillinterfacial", 0.0),
                    "sixrings": r.get("ice.sixrings", 0.0),
                }
            )
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    root = pathlib.Path(argv[0])
    dest = pathlib.Path(argv[1]) if len(argv) > 1 else None
    data = rows_from(root)
    if dest is None:
        w = csv.DictWriter(sys.stdout, fieldnames=COLS)
        w.writeheader()
        w.writerows(data)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(data)
    print("wrote", dest, "rows", len(data))


if __name__ == "__main__":
    main()
