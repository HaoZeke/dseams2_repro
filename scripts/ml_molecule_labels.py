#!/usr/bin/env python3
"""Per-molecule states from a dump via IceFeaturizer.

  python scripts/ml_molecule_labels.py DUMP --out labels.npz

Writes X (n_frames, n_features) and S (n_frames, n_molecules) with
STATE_WATER=0, STATE_IC=1, STATE_IH=2, STATE_MIXED=3. Needs pydseams
and the dump. When the dump is absent the caller writes a dated note
instead of inventing states.
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("--out", required=True)
    ap.add_argument("--type", type=int, default=1)
    ap.add_argument("--cutoff", type=float, default=3.5)
    args = ap.parse_args()
    dump = pathlib.Path(args.dump)
    if not dump.is_file():
        raise SystemExit(f"dump absent: {dump}")
    try:
        from pydseams.features import FEATURE_NAMES, IceFeaturizer
        from pydseams.frame import Trajectory
    except ImportError as exc:
        raise SystemExit(f"pydseams absent: {exc}") from exc
    traj = Trajectory(str(dump), atom_type=args.type, cutoff=args.cutoff)
    feat = IceFeaturizer(traj)
    X, S = feat.transform()
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    import numpy as np

    np.savez_compressed(
        out,
        X=X,
        S=S,
        feature_names=np.array(FEATURE_NAMES),
        dump=str(dump),
    )
    print("wrote", out, "frames", X.shape[0], "molecules", S.shape[1])


if __name__ == "__main__":
    main()
