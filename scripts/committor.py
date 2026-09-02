#!/usr/bin/env python3
"""Committor and growth rates from the ICE files of a seeding campaign.

  committor.py RESULTS_DIR --nc-cage NC --nc-chill NC_CHILL > committor.txt

Each replica directory holds ICE (PLUMED PRINT of DSEAMS_CAGES) and a
run.json with temperature, seed size and polymorph. A replica "grows" under
a label when the label's largest cluster ends above its starting value and
above the threshold, and "melts" when it ends below the melt basin. The
committor per (temperature, seed size) is the grown fraction; the same
replicas are scored with the cage cluster (column nmax) and with the CHILL+
cluster (chillmax), which is the comparison the paper makes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import statistics


def read_ice(path):
    rows = []
    cols = None
    for line in path.read_text().splitlines():
        if line.startswith("#! FIELDS"):
            cols = line.split()[2:]
            continue
        if line.startswith("#") or not line.strip():
            continue
        rows.append(dict(zip(cols, map(float, line.split()))))
    return rows


def fate(series, melt, grow):
    last = series[-1]
    if last >= grow:
        return "grow"
    if last <= melt:
        return "melt"
    return "open"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results")
    ap.add_argument("--melt", type=int, default=20)
    ap.add_argument("--grow", type=int, default=None, help="default: twice the seed size")
    a = ap.parse_args()
    groups = {}
    for run in sorted(pathlib.Path(a.results).glob("*/run.json")):
        meta = json.loads(run.read_text())
        ice = run.parent / "ICE"
        if not ice.is_file():
            continue
        rows = read_ice(ice)
        if len(rows) < 2:
            continue
        grow = a.grow or 2 * meta["seed_size"]
        key = (meta["temperature"], meta["seed_size"], meta["polymorph"])
        g = groups.setdefault(key, {"cage": [], "chill": [], "slope_cage": [], "slope_chill": []})
        cage = [r["ice.nmax"] for r in rows]
        chill = [r["ice.chillmax"] for r in rows]
        g["cage"].append(fate(cage, a.melt, grow))
        g["chill"].append(fate(chill, a.melt, grow))
        t = [r["time"] for r in rows]
        if t[-1] > t[0]:
            g["slope_cage"].append((cage[-1] - cage[0]) / (t[-1] - t[0]))
            g["slope_chill"].append((chill[-1] - chill[0]) / (t[-1] - t[0]))
    print("# T seed polymorph n  p_grow_cage p_grow_chill  open_cage open_chill  slope_cage slope_chill  nmax0_cage nmax0_chill")
    for (T, s, poly), g in sorted(groups.items()):
        n = len(g["cage"])
        pc = sum(f == "grow" for f in g["cage"]) / n
        ph = sum(f == "grow" for f in g["chill"]) / n
        oc = sum(f == "open" for f in g["cage"]) / n
        oh = sum(f == "open" for f in g["chill"]) / n
        sc = statistics.fmean(g["slope_cage"]) if g["slope_cage"] else float("nan")
        sh = statistics.fmean(g["slope_chill"]) if g["slope_chill"] else float("nan")
        print(f"{T} {s} {poly} {n}  {pc:.3f} {ph:.3f}  {oc:.3f} {oh:.3f}  {sc:.4f} {sh:.4f}")


if __name__ == "__main__":
    main()
