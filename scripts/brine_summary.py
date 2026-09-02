#!/usr/bin/env python3
"""Digest the BRINE files of the ice/brine campaign.

One line per run: temperature, pairs, replica, rows, the cage count and
largest cluster at the first and last stride, the CHILL+ count at both,
the growth rate of the largest cluster (molecules per row, least squares),
and the ion classes at the last stride: in ice, at the front, in liquid.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

COLS = ["time", "nice", "nmax", "nclus", "nic", "nih", "nmixed", "chillice", "chillmax",
        "chillinterfacial", "sixrings", "nionice", "nionfront", "nionliq"]


def read_brine(path):
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith("#") or not line.strip():
            continue
        rows.append([float(x) for x in line.split()])
    return np.asarray(rows)


def main():
    root = pathlib.Path(sys.argv[1])
    print("# T pairs replica rows nice0 nice1 nmax0 nmax1 chill0 chill1 slope_nmax ionice ionfront ionliq")
    for run in sorted(root.glob("T*_m*_r*/BRINE")):
        T, m, r = run.parent.name.split("_")
        data = read_brine(run)
        if data.size == 0:
            print(f"{T[1:]} {m[1:]} {r[1:]} 0")
            continue
        c = {name: data[:, i] for i, name in enumerate(COLS) if i < data.shape[1]}
        slope = np.polyfit(np.arange(len(data)), c["nmax"], 1)[0] if len(data) > 1 else 0.0
        print(
            f"{T[1:]} {m[1:]} {r[1:]} {len(data)} "
            f"{c['nice'][0]:.0f} {c['nice'][-1]:.0f} {c['nmax'][0]:.0f} {c['nmax'][-1]:.0f} "
            f"{c['chillice'][0]:.0f} {c['chillice'][-1]:.0f} {slope:.4f} "
            f"{c['nionice'][-1]:.0f} {c['nionfront'][-1]:.0f} {c['nionliq'][-1]:.0f}"
        )


if __name__ == "__main__":
    main()
