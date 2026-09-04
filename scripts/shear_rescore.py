#!/usr/bin/env python3
"""Re-score a shear dump with cage membership (same walk as walk_compare).

  python scripts/shear_rescore.py DUMP --out results/shear/DUMP.txt

Needs the walk_compare binary (SEAMS_BUILD/tests/walk_compare) or
pydseams IceFeaturizer. When the dump is absent, dump_status.py writes
the dated note and this script is not run.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--out", required=True)
    ap.add_argument("--type", type=int, default=1)
    ap.add_argument("--stride", type=int, default=1)
    args = ap.parse_args()
    dump = pathlib.Path(args.dump)
    if not dump.is_file():
        raise SystemExit(f"dump absent: {dump}")
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    build = os.environ.get("SEAMS_BUILD", "")
    walker = pathlib.Path(build) / "tests" / "walk_compare" if build else None
    if walker and walker.is_file():
        text = subprocess.check_output(
            [str(walker), str(dump), "0", str(args.type), str(args.stride)],
            text=True,
        )
        out.write_text(text)
        print("wrote", out)
        return
    try:
        from pydseams.features import IceFeaturizer
        from pydseams.frame import Trajectory
    except ImportError as exc:
        raise SystemExit(f"walk_compare and pydseams absent: {exc}") from exc
    traj = Trajectory(str(dump), atom_type=args.type)
    X, _ = IceFeaturizer(traj).transform()
    names = IceFeaturizer(traj).feature_names
    lines = [f"# dump={dump} via IceFeaturizer", "# frame " + " ".join(names)]
    for i, row in enumerate(X, start=1):
        lines.append(str(i) + " " + " ".join(f"{v:.4g}" for v in row))
    out.write_text("\n".join(lines) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
