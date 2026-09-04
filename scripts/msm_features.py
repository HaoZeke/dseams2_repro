#!/usr/bin/env python3
"""Feature table of the Niu committor pair from walk_compare output.

  python scripts/msm_features.py results/walks > msm_features.csv

Columns follow IceFeaturizer names where the walk records them: n_ice,
n_max, n_clusters, n_ic, n_ih, n_mixed, cubicity, chill_cubic,
chill_hexagonal, chill_interfacial, chill_clathrate,
chill_interclathrate, chill_water, chill_max. This is a feature
series, not a fitted MSM and not a rate.
"""
from __future__ import annotations

import csv
import pathlib
import sys

WALK_COLS = (
    "frame",
    "nop",
    "chill_cubic",
    "chill_hex",
    "chill_interfacial",
    "chill_clathrate",
    "chill_interclathrate",
    "chill_water",
    "chill_ice",
    "chill_max",
    "chill_clus",
    "cut_ice",
    "cut_max",
    "cut_clus",
    "seed_ih",
    "seed_ic",
    "seed_both",
    "seed_ice",
    "seed_max",
    "seed_clus",
)
OUT_COLS = (
    "dump",
    "frame",
    "n_ice",
    "n_max",
    "n_clusters",
    "n_ic",
    "n_ih",
    "n_mixed",
    "cubicity",
    "chill_cubic",
    "chill_hexagonal",
    "chill_interfacial",
    "chill_clathrate",
    "chill_interclathrate",
    "chill_water",
    "chill_max",
)
PAIR = ("niu-critical-growing", "niu-critical-melting")


def load_walk(path: pathlib.Path):
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        w = line.split()
        rows.append({name: float(w[i]) for i, name in enumerate(WALK_COLS)})
    return rows


def features(dump: str, rows):
    out = []
    for r in rows:
        n_ice = r["seed_ice"]
        n_ic = r["seed_ic"]
        n_ih = r["seed_ih"]
        n_mixed = r["seed_both"]
        cub = (n_ic + n_mixed) / n_ice if n_ice else 0.0
        out.append(
            {
                "dump": dump,
                "frame": int(r["frame"]),
                "n_ice": n_ice,
                "n_max": r["seed_max"],
                "n_clusters": r["seed_clus"],
                "n_ic": n_ic,
                "n_ih": n_ih,
                "n_mixed": n_mixed,
                "cubicity": cub,
                "chill_cubic": r["chill_cubic"],
                "chill_hexagonal": r["chill_hex"],
                "chill_interfacial": r["chill_interfacial"],
                "chill_clathrate": r["chill_clathrate"],
                "chill_interclathrate": r["chill_interclathrate"],
                "chill_water": r["chill_water"],
                "chill_max": r["chill_max"],
            }
        )
    return out


def collect(walks: pathlib.Path):
    out = []
    for name in PAIR:
        path = walks / f"{name}.txt"
        if not path.is_file():
            continue
        out.extend(features(name, load_walk(path)))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        raise SystemExit(__doc__)
    walks = pathlib.Path(argv[0])
    dest = pathlib.Path(argv[1]) if len(argv) > 1 else None
    data = collect(walks)
    if dest is None:
        w = csv.DictWriter(sys.stdout, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(data)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=OUT_COLS)
        w.writeheader()
        w.writerows(data)
    print("wrote", dest, "rows", len(data))


if __name__ == "__main__":
    main()
