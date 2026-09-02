#!/usr/bin/env python3
"""Where the seeded assignment loses molecules under jitter, and why.

Reuses the lattice generators and label functions of sota_compare.py. For
each sigma and seed it labels the jittered Ic and Ih lattices with the
seeded assignment, then classifies every missed molecule:

  star_in_ice      all four nearest neighbours (mutual graph) accepted ice
  strict_rings     six-rings through the molecule on the strict graph
  perm_rings       six-rings through it on the permissive (union) graph
  adjacent_ring    it lies on a six-ring sharing an edge with an accepted ring
  degree_mutual    degree in the mutual four-nearest graph

and evaluates two completions that keep the null structurally at zero:
  embedded   accept a molecule whose four nearest neighbours are all accepted
             ice in one component
  adjacent   accept the vertices of a six-ring that shares an edge with an
             affiliated ring of a seeded component

Output is key=value lines per (sigma, seed, system) plus per-missed-atom
diagnostics on stderr with --verbose.
"""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys

import numpy as np
from pydseams import yoda

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sota_compare", HERE / "sota_compare.py")
sc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sc)


def seeded_state(pos, box, permissive_k=4):
    n = len(pos)
    cloud = sc.make_cloud(pos, box)
    strict = yoda.neighbourListByIndex(
        cloud, yoda.kNearestNeighbourList(cloud, 4, 5.0, 1, True)
    )
    perm = yoda.neighbourListByIndex(
        cloud, yoda.kNearestNeighbourList(cloud, permissive_k, 5.0, 1, False)
    )
    six_s = [r for r in yoda.ringNetwork(strict, 7) if len(r) == 6]
    six_p = [r for r in yoda.ringNetwork(perm, 7) if len(r) == 6]
    hc, ddc = yoda.seededCageAffiliation(six_s, strict, six_p, perm)
    ice = np.array([bool(h or d) for h, d in zip(hc, ddc)])
    return cloud, strict, perm, six_s, six_p, ice


def rings_through(rings, n):
    count = np.zeros(n, dtype=int)
    for r in rings:
        for a in r:
            count[a] += 1
    return count


def ring_edges(r):
    k = len(r)
    return {frozenset((r[i], r[(i + 1) % k])) for i in range(k)}


def complete_embedded(ice, strict):
    """Accept a molecule whose four mutual neighbours are all accepted."""
    out = ice.copy()
    for i, row in enumerate(strict):
        if out[i]:
            continue
        nb = [j for j in row[1:]]
        if len(nb) == 4 and all(out[j] for j in nb):
            out[i] = True
    return out


def complete_adjacent(ice, six_p):
    """Accept vertices of a six-ring that shares an edge with a ring whose
    vertices are all accepted ice (the ring is then part of the network)."""
    accepted_edges = set()
    for r in six_p:
        if all(ice[a] for a in r):
            accepted_edges |= ring_edges(r)
    out = ice.copy()
    for r in six_p:
        if all(out[a] for a in r):
            continue
        if ring_edges(r) & accepted_edges:
            for a in r:
                out[a] = True
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sigmas", type=float, nargs="+", default=[0.25, 0.30, 0.35, 0.40])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    ic_pos, ic_box = sc.cubic_diamond(4)
    ih_pos, ih_box = sc.lonsdaleite(5, 3, 3)
    rng = np.random.default_rng(sc.SEED)
    null_pos = sc.dense_null(360, ic_box, rng)
    systems = [("ic", ic_pos, ic_box), ("ih", ih_pos, ih_box)]

    for sigma in args.sigmas:
        for seed in range(args.seeds):
            for name, pos0, box in systems:
                pos = sc.jitter(pos0, box, sigma,
                                np.random.default_rng(sc.SEED + int(sigma * 1000) + 7919 * seed))
                cloud, strict, perm, six_s, six_p, ice = seeded_state(pos, box)
                n = len(pos)
                missed = np.where(~ice)[0]
                ts = rings_through(six_s, n)
                tp = rings_through(six_p, n)
                emb = complete_embedded(ice, strict)
                adj = complete_adjacent(ice, six_p)
                both = complete_adjacent(emb, six_p)
                print(f"system={name} sigma={sigma:.2f} seed={seed} n={n} "
                      f"seeded={ice.sum()/n:.4f} embedded={emb.sum()/n:.4f} "
                      f"adjacent={adj.sum()/n:.4f} embedded+adjacent={both.sum()/n:.4f} "
                      f"missed={len(missed)} "
                      f"missed_star_in_ice={sum(1 for i in missed if len(strict[i]) == 5 and all(ice[j] for j in strict[i][1:]))} "
                      f"missed_no_strict_ring={int((ts[missed] == 0).sum())} "
                      f"missed_no_perm_ring={int((tp[missed] == 0).sum())}")
                if args.verbose:
                    for i in missed:
                        print(f"  {name} sigma={sigma:.2f} seed={seed} atom={i} deg_mutual={len(strict[i]) - 1} "
                              f"strict_rings={ts[i]} perm_rings={tp[i]} "
                              f"nb_ice={sum(1 for j in strict[i][1:] if ice[j])}", file=sys.stderr)
        # the null must stay at zero under every completion
        cloud, strict, perm, six_s, six_p, ice = seeded_state(null_pos, ic_box)
        emb = complete_embedded(ice, strict)
        adj = complete_adjacent(ice, six_p)
        both = complete_adjacent(emb, six_p)
        print(f"system=null sigma={sigma:.2f} seeded_false={ice.mean():.4f} "
              f"embedded_false={emb.mean():.4f} adjacent_false={adj.mean():.4f} "
              f"embedded+adjacent_false={both.mean():.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
