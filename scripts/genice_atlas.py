#!/usr/bin/env python3
"""Specificity atlas over the GenIce polymorph library.

GenIce (Matsumoto, Yagasaki, Tanaka) generates hydrogen-disordered ice
structures for a named lattice. This script runs the per-molecule
classifiers of the comparison suite over that library, ideal and under
positional noise, and reports what each one calls the structure. Ice I
(both polymorphs, and stacking-disordered ice I) is the positive set;
every other polymorph, the empty clathrate frameworks and the amorphous
networks are the negative set: a cage-based label on ice VI is a false
positive, however confidently it is assigned.

Per structure and noise level the output lists the oxygen count, the
fraction of molecules each method labels cubic, hexagonal, mixed and
clathrate, the number of HC and DDC cages, and the primitive ring
census of the cutoff graph. Output is key=value lines.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sota_compare import (  # noqa: E402
    CUTOFF,
    chill_plus,
    dseams_lists,
    dseams_topo,
    dseams_topo_seeded,
)
from pydseams import yoda  # noqa: E402

# name -> (GenIce type, class). Classes: ice1 (positive), dense (high
# pressure polymorph), clathrate (empty hydrate framework), porous
# (hypothetical low-density ice), amorphous.
STRUCTURES = {
    "Ih": ("1h", "ice1"),
    "Ic": ("1c", "ice1"),
    "Isd": ("one", "ice1"),
    "XI": ("11", "ice1"),
    "0": ("0", "dense"),
    "II": ("2", "dense"),
    "III": ("3", "dense"),
    "IV": ("4R", "dense"),
    "V": ("5R", "dense"),
    "VI": ("6", "dense"),
    "VII": ("7", "dense"),
    "VIII": ("8", "dense"),
    "IX": ("9", "dense"),
    "XII": ("12", "dense"),
    "XIII": ("13", "dense"),
    "XIV": ("14", "dense"),
    "XVI": ("16", "clathrate"),
    "XVII": ("17", "porous"),
    "sI": ("CS1", "clathrate"),
    "sII": ("CS2", "clathrate"),
    "sH": ("DOH", "clathrate"),
    "sT": ("T", "clathrate"),
    "HS1": ("HS1", "ice1"),
    "iceA": ("A", "porous"),
    "iceB": ("B", "porous"),
    "FAU": ("FAU", "porous"),
    "RHO": ("RHO", "porous"),
    "EMT": ("EMT", "porous"),
    "SOD": ("SOD", "porous"),
    "CRN1": ("CRN1", "amorphous"),
    "CRN2": ("CRN2", "amorphous"),
    "CRN3": ("CRN3", "amorphous"),
}
MIN_EDGE = 16.0  # Angstrom; every box edge above 4 cutoffs
NOISE = [0.0, 5.0, 10.0]  # GenIce --add_noise, percent of a molecular diameter


def genice(exe: str, kind: str, rep, noise: float, seed: int):
    cmd = [exe, kind, "--rep", *map(str, rep), "--format", "gromacs", "--seed", str(seed)]
    if noise > 0:
        cmd += ["--add_noise", str(noise)]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    lines = out.splitlines()
    n = int(lines[1])
    pos = []
    for line in lines[2 : 2 + n]:
        if line[10:15].strip().startswith("O"):
            pos.append((float(line[20:28]), float(line[28:36]), float(line[36:44])))
    cell = [float(x) for x in lines[2 + n].split()]
    if len(cell) != 3:
        raise SystemExit(f"{kind}: non-orthogonal cell {cell}; skip")
    box = np.asarray(cell) * 10.0
    return np.asarray(pos) * 10.0 % box, box


def reps_for(exe: str, kind: str):
    _, box = genice(exe, kind, (1, 1, 1), 0.0, 1)
    return tuple(max(1, math.ceil(MIN_EDGE / b)) for b in box)


def fractions(labels):
    c = Counter(labels)
    n = max(1, len(labels))
    return {k: c.get(k, 0) / n for k in ("cubic", "hexagonal", "mixed", "clathrate", "interfacial")}


def cages_and_rings(pos, box):
    cloud, nl, idx = dseams_lists(pos, box)
    rings = yoda.ringNetwork(idx, 8)
    census = Counter(len(r) for r in rings)
    six = [r for r in rings if len(r) == 6]
    n_hc = n_ddc = 0
    if six:
        hc, ddc = yoda.cageAffiliation(six, idx)
        n_hc, n_ddc = int(sum(hc)), int(sum(ddc))
    return census, n_hc, n_ddc


def emit(**kv):
    print(" ".join(f"{k}={v}" for k, v in kv.items()), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genice", default="genice2")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--noise", nargs="*", type=float, default=NOISE)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    scratch = tempfile.mkdtemp(prefix="genice-atlas-")
    for name, (kind, klass) in STRUCTURES.items():
        if args.only and name not in args.only:
            continue
        try:
            rep = reps_for(args.genice, kind)
        except (subprocess.CalledProcessError, SystemExit) as exc:
            emit(structure=name, kind=kind, klass=klass, status=f"skip:{str(exc)[:60]!r}")
            continue
        for noise in args.noise:
            try:
                pos, box = genice(args.genice, kind, rep, noise, args.seed)
            except subprocess.CalledProcessError as exc:
                emit(structure=name, kind=kind, klass=klass, noise=noise, status="genice-failed")
                continue
            census, n_hc, n_ddc = cages_and_rings(pos, box)
            f_cut = fractions(dseams_topo(pos, box))
            f_seed = fractions(dseams_topo_seeded(pos, box, ring_adjacent=True))
            f_chill = fractions(chill_plus(pos, box, scratch))
            emit(
                structure=name, kind=kind, klass=klass, noise=noise, n=len(pos),
                rep="x".join(map(str, rep)),
                rings=",".join(f"{k}:{census[k]}" for k in sorted(census)),
                hc=n_hc, ddc=n_ddc,
                cut_ice=f"{f_cut['cubic'] + f_cut['hexagonal'] + f_cut['mixed']:.3f}",
                cut_c=f"{f_cut['cubic']:.3f}", cut_h=f"{f_cut['hexagonal']:.3f}",
                seed_ice=f"{f_seed['cubic'] + f_seed['hexagonal'] + f_seed['mixed']:.3f}",
                seed_c=f"{f_seed['cubic']:.3f}", seed_h=f"{f_seed['hexagonal']:.3f}",
                chill_ice=f"{f_chill['cubic'] + f_chill['hexagonal']:.3f}",
                chill_c=f"{f_chill['cubic']:.3f}", chill_h=f"{f_chill['hexagonal']:.3f}",
                chill_clath=f"{f_chill['clathrate']:.3f}",
                chill_inter=f"{f_chill['interfacial']:.3f}",
            )


if __name__ == "__main__":
    main()
