#!/usr/bin/env python3
"""Ice classification in the presence of ions.

Monatomic ions replace water molecules at lattice sites of GenIce ice Ih,
ice Ic and the empty sI framework. The substitution is done here rather
than through GenIce's --anion/--cation, whose site indices name unit-cell
positions and replicate with the cell (one pair per cell is already a
12% dopant fraction in ice Ih); a seeded draw of distinct sites gives
the dilute range a brine-rejecting ice front sees. Ions are not part of
the hydrogen-bond network, so they are removed before the water graph is
built; the questions are what the water around a substitutional ion is
called, and what the ion sees.

Per host, pair count and draw the output lists the water and ion counts,
the fraction of water labelled ice I by the seeded cages with completion,
by the cutoff cages and by CHILL+, the mean ice fraction of the ions'
first water shells (within CUTOFF) under each method, and the fraction of
ions whose first shell is entirely ice under the seeded assignment.
Output is key=value lines.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile

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
PAIRS = [0, 1, 2, 4, 8, 16]
SEED = 20260902


def genice(exe, kind, rep):
    cmd = [exe, kind, "--rep", *map(str, rep), "--format", "gromacs"]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    lines = out.splitlines()
    n = int(lines[1])
    pos = [
        (float(l[20:28]), float(l[28:36]), float(l[36:44]))
        for l in lines[2 : 2 + n]
        if l[10:15].strip().startswith("O")
    ]
    cell = [float(x) for x in lines[2 + n].split()]
    if len(cell) != 3:
        raise SystemExit(f"{kind}: non-orthogonal cell")
    box = np.asarray(cell) * 10.0
    return np.asarray(pos) * 10.0 % box, box


def reps_for(exe, kind):
    _, box = genice(exe, kind, (1, 1, 1))
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
    ap.add_argument("--pairs", nargs="*", type=int, default=PAIRS)
    ap.add_argument("--draws", type=int, default=3)
    args = ap.parse_args()
    scratch = tempfile.mkdtemp(prefix="ion-atlas-")
    for name, kind in HOSTS.items():
        rep = reps_for(args.genice, kind)
        sites, box = genice(args.genice, kind, rep)
        n_sites = len(sites)
        for n_pairs in args.pairs:
            for draw in range(args.draws if n_pairs else 1):
                rng = np.random.default_rng(SEED + 1000 * n_pairs + draw)
                chosen = rng.choice(n_sites, size=2 * n_pairs, replace=False)
                mask = np.ones(n_sites, dtype=bool)
                mask[chosen] = False
                water, ions = sites[mask], sites[~mask]
                seeded = ice_mask(dseams_topo_seeded(water, box, ring_adjacent=True))
                cutoff = ice_mask(dseams_topo(water, box))
                chill = ice_mask(chill_plus(water, box, scratch))
                shells = first_shell(water, ions, box, CUTOFF)
                sizes = [len(s) for s in shells]
                f_seed = [seeded[s].mean() if len(s) else 0.0 for s in shells]
                f_cut = [cutoff[s].mean() if len(s) else 0.0 for s in shells]
                f_chill = [chill[s].mean() if len(s) else 0.0 for s in shells]
                emit(
                    host=name, kind=kind, pairs=n_pairs, draw=draw,
                    rep="x".join(map(str, rep)), n_water=len(water), n_ion=len(ions),
                    ion_frac=f"{len(ions) / n_sites:.4f}",
                    seeded_ice=f"{seeded.mean():.3f}", cutoff_ice=f"{cutoff.mean():.3f}",
                    chill_ice=f"{chill.mean():.3f}",
                    shell_mean=f"{np.mean(sizes) if sizes else 0:.2f}",
                    shell_seeded=f"{np.mean(f_seed) if f_seed else 0:.3f}",
                    shell_cutoff=f"{np.mean(f_cut) if f_cut else 0:.3f}",
                    shell_chill=f"{np.mean(f_chill) if f_chill else 0:.3f}",
                    ions_all_ice=f"{np.mean([x >= 1.0 for x in f_seed]) if f_seed else 0:.3f}",
                )


if __name__ == "__main__":
    main()
