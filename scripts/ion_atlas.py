#!/usr/bin/env python3
"""Ice classification in the presence of ions.

GenIce substitutes monatomic ions for water molecules at lattice sites
(--anion, --cation), which gives ice Ih and Ic doped with NaCl at
construction-known positions, and the empty sI framework with ions in its
water network. Ions are not part of the hydrogen-bond network, so they are
removed before the water graph is built; the questions are what the water
around a substitutional ion is called, and what the ion sees.

Per structure and ion count the output lists the water and ion counts, the
fraction of water labelled ice I by the seeded cages with completion, by
the cutoff cages and by CHILL+, the fraction of first-shell waters of the
ions (within CUTOFF) that carry an ice label, and the fraction of ions whose
first shell is all ice. Output is key=value lines.
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
    dseams_topo,
    dseams_topo_seeded,
)

HOSTS = {"Ih": "1h", "Ic": "1c", "sI": "CS1"}
MIN_EDGE = 16.0
# Substitution sites are unit-cell indices, replicated with the cell;
# GenIce refuses a site whose hydrogen-bond pattern cannot host the ion at
# the chosen replication, so candidates are tried in order at that
# replication until the requested count is reached
CANDIDATES = list(range(0, 40))


def run_genice(exe, kind, rep, anions, cations, seed):
    cmd = [exe, kind, "--rep", *map(str, rep), "--format", "gromacs", "--seed", str(seed)]
    for i in anions:
        cmd += ["--anion", f"{i}=Cl"]
    for i in cations:
        cmd += ["--cation", f"{i}=Na"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip().splitlines()[-1] if out.stderr else "genice failed")
    lines = out.stdout.splitlines()
    n = int(lines[1])
    water, ions = [], []
    for line in lines[2 : 2 + n]:
        name = line[10:15].strip()
        xyz = (float(line[20:28]), float(line[28:36]), float(line[36:44]))
        if name.startswith("O"):
            water.append(xyz)
        elif name in ("Cl", "Na", "CL", "NA"):
            ions.append(xyz)
    cell = [float(x) for x in lines[2 + n].split()]
    if len(cell) != 3:
        raise RuntimeError("non-orthogonal cell")
    box = np.asarray(cell) * 10.0
    return np.asarray(water) * 10.0 % box, np.asarray(ions).reshape(-1, 3) * 10.0 % box, box


def choose_sites(exe, kind, rep, n_pairs, seed):
    """Pick n_pairs anion sites and n_pairs cation sites GenIce accepts."""
    anions, cations = [], []
    for idx in CANDIDATES:
        if len(anions) < n_pairs:
            try:
                run_genice(exe, kind, rep, anions + [idx], cations, seed)
                anions.append(idx)
                continue
            except RuntimeError:
                pass
        if len(cations) < n_pairs and idx not in anions:
            try:
                run_genice(exe, kind, rep, anions, cations + [idx], seed)
                cations.append(idx)
            except RuntimeError:
                pass
        if len(anions) == n_pairs and len(cations) == n_pairs:
            break
    return anions, cations


def reps_for(exe, kind, seed):
    _, _, box = run_genice(exe, kind, (1, 1, 1), [], [], seed)
    return tuple(max(1, math.ceil(MIN_EDGE / b)) for b in box)


def ice_mask(labels):
    return np.array([lab in ("cubic", "hexagonal", "mixed") for lab in labels])


def first_shell(water, ions, box, cutoff):
    """Indices of the water within cutoff of each ion, periodic."""
    shells = []
    for ion in ions:
        d = water - ion
        d -= box * np.round(d / box)
        r = np.sqrt((d ** 2).sum(axis=1))
        shells.append(np.nonzero(r < cutoff)[0])
    return shells


def emit(**kv):
    print(" ".join(f"{k}={v}" for k, v in kv.items()), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genice", default="genice2")
    ap.add_argument("--pairs", nargs="*", type=int, default=[0, 1, 2, 3])
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    scratch = tempfile.mkdtemp(prefix="ion-atlas-")
    for name, kind in HOSTS.items():
        rep = reps_for(args.genice, kind, args.seed)
        for n_pairs in args.pairs:
            anions, cations = choose_sites(args.genice, kind, rep, n_pairs, args.seed)
            if len(anions) < n_pairs or len(cations) < n_pairs:
                emit(host=name, pairs=n_pairs, status="no-sites")
                continue
            try:
                water, ions, box = run_genice(args.genice, kind, rep, anions, cations, args.seed)
            except RuntimeError as exc:
                emit(host=name, pairs=n_pairs, status=f"genice:{str(exc)[:50]!r}")
                continue
            seeded = ice_mask(dseams_topo_seeded(water, box, ring_adjacent=True))
            cutoff = ice_mask(dseams_topo(water, box))
            chill = ice_mask(chill_plus(water, box, scratch))
            shells = first_shell(water, ions, box, CUTOFF)
            shell_sizes = [len(s) for s in shells]
            shell_ice = [seeded[s].mean() if len(s) else 0.0 for s in shells]
            shell_cut = [cutoff[s].mean() if len(s) else 0.0 for s in shells]
            shell_chill = [chill[s].mean() if len(s) else 0.0 for s in shells]
            emit(
                host=name, kind=kind, pairs=n_pairs, rep="x".join(map(str, rep)),
                n_water=len(water), n_ion=len(ions),
                ion_frac=f"{len(ions) / (len(ions) + len(water)):.3f}",
                seeded_ice=f"{seeded.mean():.3f}", cutoff_ice=f"{cutoff.mean():.3f}",
                chill_ice=f"{chill.mean():.3f}",
                shell_mean=f"{np.mean(shell_sizes) if shell_sizes else 0:.2f}",
                shell_seeded=f"{np.mean(shell_ice) if shell_ice else 0:.3f}",
                shell_cutoff=f"{np.mean(shell_cut) if shell_cut else 0:.3f}",
                shell_chill=f"{np.mean(shell_chill) if shell_chill else 0:.3f}",
                ions_all_ice=f"{np.mean([x == 1.0 for x in shell_ice]) if shell_ice else 0:.3f}",
                sites=f"a{anions}c{cations}".replace(" ", ""),
            )


if __name__ == "__main__":
    main()
