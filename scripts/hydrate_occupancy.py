#!/usr/bin/env python3
"""Cage occupancy of the GenIce methane hydrates.

GenIce fills the 5^12 and 5^12 6^2 cages of sI (12=me, 14=me) and the
5^12 and 5^12 6^4 cages of sII (12=me, 16=me) with one methane each. The
engine enumerates the cages by ring-size signature on the water graph and
places every methane at the nearest periodic cage centroid within a
radius; a correct enumeration and a correct placement fill every cage
once and leave no guest free.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genice_atlas import STRUCTURES, reps_for  # noqa: E402
from pydseams.frame import Frame  # noqa: E402

# structure -> (signature, cages per unit cell)
CAGES = {
    "sI+CH4": (("512", 2), ("51262", 6)),
    "sII+CH4": (("512", 16), ("5:12,6:4", 8)),
}
RADIUS = {"512": 4.0, "51262": 4.4, "5:12,6:4": 4.8}


def genice_with_guests(exe, kind, rep, guests, seed=1):
    cmd = [exe, kind, "--rep", *map(str, rep), "--format", "gromacs", "--seed", str(seed)]
    for g in guests:
        cmd += ["--guest", g]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    lines = out.splitlines()
    n = int(lines[1])
    water, guest = [], []
    for line in lines[2 : 2 + n]:
        name = line[10:15].strip()
        xyz = (float(line[20:28]), float(line[28:36]), float(line[36:44]))
        if name.startswith("O"):
            water.append(xyz)
        elif not name.startswith("H"):
            guest.append(xyz)
    cell = [float(x) for x in lines[2 + n].split()]
    box = np.asarray(cell[:3]) * 10.0
    return np.asarray(water) * 10.0 % box, np.asarray(guest) * 10.0 % box, box


def emit(**kv):
    print(" ".join(f"{k}={v}" for k, v in kv.items()), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genice", default="genice2")
    args = ap.parse_args()
    for name, sigs in CAGES.items():
        kind, _, guests = STRUCTURES[name]
        rep = reps_for(args.genice, kind)
        water, methane, box = genice_with_guests(args.genice, kind, rep, guests)
        ncell = int(np.prod(rep))
        pos = np.vstack([water, methane])
        numbers = [1] * len(water) + [6] * len(methane)
        frame = Frame.from_arrays(pos, list(box), numbers=numbers, cutoff=3.5)
        emit(structure=name, rep="x".join(map(str, rep)), water=len(water), methane=len(methane))
        every = []
        for sig, per_cell in sigs:
            cages = [c["vertices"] for c in frame.cages_by_signature(sig)]
            occ = frame.guest_occupancy(cages, (6,), radius=RADIUS[sig])
            every.extend(cages)
            emit(structure=name, signature=sig, cages=len(cages), expected=per_cell * ncell,
                 occupied=occ.occupied, multiple=occ.multiply, free=occ.free,
                 filled=f"{occ.occupied / max(1, len(cages)):.3f}")
        occ = frame.guest_occupancy(every, (6,), radius=max(RADIUS[s] for s, _ in sigs))
        emit(structure=name, signature="all", cages=len(every), occupied=occ.occupied,
             multiple=occ.multiply, free=occ.free,
             centre_max=f"{max(occ.centreDistance):.3f}",
             centre_mean=f"{float(np.mean(occ.centreDistance)):.3f}")


if __name__ == "__main__":
    main()
