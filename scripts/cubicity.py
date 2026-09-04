#!/usr/bin/env python3
"""Last-frame nic, nih, nmixed from the ICE files of a seeding campaign.

  cubicity.py RESULTS_DIR > cubicity.txt

Cubicity is (nic + nmixed) / nice on the last PRINT row. The same ICE
files feed committor.py; this digest is the polymorph split of that
campaign, not a second run.
"""
from __future__ import annotations

import json
import pathlib
import statistics
import sys

from committor import read_ice


def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    groups = {}
    for run in sorted(root.glob("*/run.json")):
        meta = json.loads(run.read_text())
        ice = run.parent / "ICE"
        if not ice.is_file():
            continue
        rows = read_ice(ice)
        if not rows:
            continue
        key = (meta["temperature"], meta["seed_size"], meta["polymorph"])
        g = groups.setdefault(
            key,
            {
                "nic": [],
                "nih": [],
                "nmixed": [],
                "nice": [],
                "nmax": [],
                "chillice": [],
                "chillmax": [],
                "nic0": [],
                "nih0": [],
                "nmixed0": [],
            },
        )
        first, last = rows[0], rows[-1]
        g["nic"].append(last.get("ice.nic", 0.0))
        g["nih"].append(last.get("ice.nih", 0.0))
        g["nmixed"].append(last.get("ice.nmixed", 0.0))
        g["nice"].append(last.get("ice.nice", 0.0))
        g["nmax"].append(last.get("ice.nmax", 0.0))
        g["chillice"].append(last.get("ice.chillice", 0.0))
        g["chillmax"].append(last.get("ice.chillmax", 0.0))
        g["nic0"].append(first.get("ice.nic", 0.0))
        g["nih0"].append(first.get("ice.nih", 0.0))
        g["nmixed0"].append(first.get("ice.nmixed", 0.0))
    print(
        "# T seed polymorph n  nic nih nmixed nice nmax cubicity  "
        "nic0 nih0 nmixed0  chillice chillmax"
    )
    for (T, s, poly), g in sorted(groups.items()):
        n = len(g["nic"])

        def mean(name):
            return statistics.fmean(g[name]) if g[name] else float("nan")

        nic, nih, nmixed, nice = mean("nic"), mean("nih"), mean("nmixed"), mean("nice")
        cub = (nic + nmixed) / nice if nice else 0.0
        print(
            f"{T} {s} {poly} {n}  {nic:.2f} {nih:.2f} {nmixed:.2f} {nice:.2f} "
            f"{mean('nmax'):.2f} {cub:.3f}  {mean('nic0'):.2f} {mean('nih0'):.2f} "
            f"{mean('nmixed0'):.2f}  {mean('chillice'):.2f} {mean('chillmax'):.2f}"
        )


if __name__ == "__main__":
    main()
