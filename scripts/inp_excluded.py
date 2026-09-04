#!/usr/bin/env python3
"""Substrate-excluded ice count on an INP (or any mixed) dump.

  python scripts/inp_excluded.py DUMP --water-type 1 --out results/inp/counts.txt

Ions, protein atoms and other substrate types stay out of the neighbour
graph. The ice count is cage membership on the remaining water. Needs
pydseams and the dump. When the dump is absent, dump_status.py writes
the dated note and this script is not run.
"""
from __future__ import annotations

import argparse
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--water-type", type=int, default=1)
    ap.add_argument("--cutoff", type=float, default=3.5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    dump = pathlib.Path(args.dump)
    if not dump.is_file():
        raise SystemExit(f"dump absent: {dump}")
    try:
        from pydseams.features import IceFeaturizer
        from pydseams.frame import Trajectory
    except ImportError as exc:
        raise SystemExit(f"pydseams absent: {exc}") from exc
    traj = Trajectory(str(dump), atom_type=args.water_type, cutoff=args.cutoff)
    feat = IceFeaturizer(traj)
    X, S = feat.transform()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    names = feat.feature_names
    lines = [
        f"# dump={dump} water_type={args.water_type} frames={X.shape[0]} "
        f"molecules={S.shape[1]}",
        "# frame " + " ".join(names),
    ]
    for i, row in enumerate(X, start=1):
        lines.append(str(i) + " " + " ".join(f"{v:.4g}" for v in row))
    out.write_text("\n".join(lines) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
