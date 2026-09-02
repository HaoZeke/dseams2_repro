#!/usr/bin/env python3
"""Build a LAMMPS data file: a spherical ice Ic or Ih seed in mW liquid.

  seed_ice.py --n-liquid N --seed-size S --polymorph ic|ih --density RHO \
              --temperature T --out seeded.data [--rng R]

The liquid is a random dense packing at the mW liquid density (relaxed by
the run itself); the seed is cut from the perfect lattices of
sota_compare.py, centred in the box, and every liquid molecule closer than
2.6 A to a seed molecule is removed. Atom ids 1..S are the seed. The data
file records the intended seed size in its header comment.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sota_compare", HERE / "sota_compare.py")
sc = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(sc)
except Exception:  # pydseams may be absent on the login node; only the lattices are needed
    sc = None

BOND = 2.75  # A, O-O in ice


def lattice(polymorph, reps):
    if sc is not None:
        if polymorph == "ic":
            return sc.cubic_diamond(reps)
        return sc.lonsdaleite(reps, reps, reps)
    # cubic diamond fallback without pydseams
    a = BOND * 4.0 / np.sqrt(3.0)
    base = np.array([[0, 0, 0], [0, .5, .5], [.5, 0, .5], [.5, .5, 0],
                     [.25, .25, .25], [.25, .75, .75], [.75, .25, .75], [.75, .75, .25]])
    pts = []
    for i in range(reps):
        for j in range(reps):
            for k in range(reps):
                pts.append((base + [i, j, k]) * a)
    pos = np.vstack(pts)
    return pos, np.array([a * reps] * 3)


def sphere(pos, box, n_target):
    centre = box / 2.0
    d = np.linalg.norm(pos - centre, axis=1)
    order = np.argsort(d)
    return pos[order[:n_target]] - centre


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-liquid", type=int, default=4096)
    ap.add_argument("--seed-size", type=int, default=300)
    ap.add_argument("--polymorph", choices=("ic", "ih"), default="ic")
    ap.add_argument("--density", type=float, default=0.0332, help="molecules per A^3")
    ap.add_argument("--exclusion", type=float, default=2.6)
    ap.add_argument("--rng", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    L = (a.n_liquid / a.density) ** (1.0 / 3.0)
    rng = np.random.default_rng(a.rng)
    # liquid: random insertion with a hard core, good enough for a run that
    # relaxes it at the target temperature before the seed matters
    liquid = []
    tries = 0
    while len(liquid) < a.n_liquid and tries < 200 * a.n_liquid:
        p = rng.random(3) * L
        tries += 1
        if liquid:
            arr = np.asarray(liquid)
            d = arr - p
            d -= L * np.round(d / L)
            if (np.einsum("ij,ij->i", d, d) < 2.4 ** 2).any():
                continue
        liquid.append(p)
    liquid = np.asarray(liquid)
    if len(liquid) < a.n_liquid:
        raise SystemExit(f"packed {len(liquid)} < {a.n_liquid}; lower --density")

    reps = max(3, int(np.ceil((a.seed_size / 8.0) ** (1.0 / 3.0))) + 2)
    lat, lbox = lattice(a.polymorph, reps)
    seed = sphere(lat, lbox, a.seed_size) + L / 2.0
    d = liquid[:, None, :] - seed[None, :, :]
    d -= L * np.round(d / L)
    keep = (np.einsum("ijk,ijk->ij", d, d) >= a.exclusion ** 2).all(axis=1)
    liquid = liquid[keep]
    pos = np.vstack([seed, liquid])
    with open(a.out, "w") as f:
        f.write(f"mW seeded: {a.polymorph} seed {len(seed)} molecules, {len(liquid)} liquid, L={L:.4f}\n\n")
        f.write(f"{len(pos)} atoms\n1 atom types\n\n")
        f.write(f"0.0 {L:.6f} xlo xhi\n0.0 {L:.6f} ylo yhi\n0.0 {L:.6f} zlo zhi\n\n")
        f.write("Masses\n\n1 18.015\n\nAtoms # atomic\n\n")
        for i, (x, y, z) in enumerate(pos, 1):
            f.write(f"{i} 1 {x % L:.6f} {y % L:.6f} {z % L:.6f}\n")
    print(f"seed {len(seed)} liquid {len(liquid)} total {len(pos)} L {L:.3f}")


if __name__ == "__main__":
    main()
