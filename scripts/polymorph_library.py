#!/usr/bin/env python3
"""A topology key library over the GenIce polymorphs, and what it names.

Every GenIce lattice that fits an orthorhombic cell contributes the local
keys of its molecules (rooted bonded neighbourhood within HOPS bonds on
the mutual four-nearest graph) under its own label. The library is then
read against the jittered Ic and Ih lattices of the accuracy sweep and
against the noisy atlas structures: a molecule is named when its local
graph is, up to relabelling, one of a reference polymorph's. This is the
polymorph identifier that the two ice I cages cannot be: it names ice VI,
sII or sT with the same machinery, and it stays exact under permutation.

Output is key=value lines: the library census (labels and key counts,
ambiguous keys), then per test structure and noise level the fraction of
molecules named with the true label, with another label, or unnamed.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from genice_atlas import STRUCTURES, genice, reps_for  # noqa: E402
from sota_compare import cubic_diamond, jitter, lonsdaleite  # noqa: E402
from pydseams import yoda  # noqa: E402
from pydseams.frame import Frame  # noqa: E402

HOPS = 2
LIBRARY_STRUCTURES = ["Ih", "Ic", "XI", "0", "III", "IV", "V", "VI", "VII", "VIII", "IX",
                      "XII", "XIV", "XVI", "XVII", "sI", "sT", "sIV", "iceA", "iceB", "FAU",
                      "RHO", "SOD"]
# ice I under any name is one class for the accuracy test
ICE1 = {"Ih": "Ih", "Ic": "Ic", "XI": "Ih"}


def mutual_rows(pos, box, cut=5.0):
    frame = Frame.from_arrays(pos, list(box), cutoff=3.5)
    knn = yoda.kNearestNeighbourList(frame.cloud, 4, cut, frame.atom_type, True)
    return frame, yoda.neighbourListByIndex(frame.cloud, knn)


def keys_of(pos, box):
    _, rows = mutual_rows(pos, box)
    return yoda.topologyFingerprint(rows, HOPS, 7, [])


def emit(**kv):
    print(" ".join(f"{k}={v}" for k, v in kv.items()), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genice", default="genice2")
    ap.add_argument("--sigmas", nargs="*", type=float, default=[0.0, 0.1, 0.2, 0.3])
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--library-out", default=None)
    args = ap.parse_args()

    lib = yoda.KeyLibrary()
    ideal = {}
    for name in LIBRARY_STRUCTURES:
        spec = STRUCTURES[name]
        kind, guests = spec[0], (spec[2] if len(spec) > 2 else ())
        try:
            rep = reps_for(args.genice, kind)
            pos, box = genice(args.genice, kind, rep, 0.0, 1, guests)
        except (subprocess.CalledProcessError, SystemExit):
            emit(library=name, status="skip")
            continue
        ideal[name] = (pos, box)
        fp = keys_of(pos, box)
        yoda.addToLibrary(lib, fp, ICE1.get(name, name))
        emit(library=name, label=ICE1.get(name, name), n=len(pos), classes=len(fp.classes))
    text = yoda.writeLibrary(lib)
    if args.library_out:
        with open(args.library_out, "w") as fh:
            fh.write(text)
    labels = {}
    for key, label in lib.labelOf.items():
        labels[label] = labels.get(label, 0) + 1
    emit(library="census", method=lib.method, hops=lib.hops, keys=len(lib.labelOf),
         ambiguous=labels.get("ambiguous", 0),
         perlabel=",".join(f"{k}:{v}" for k, v in sorted(labels.items())))

    # the jitter sweep lattices of the accuracy comparison
    rng0 = 88172645463325252
    ic_pos, ic_box = cubic_diamond(4)
    ih_pos, ih_box = lonsdaleite(5, 3, 3)
    for truth, pos0, box in (("Ic", ic_pos, ic_box), ("Ih", ih_pos, ih_box)):
        for sigma in args.sigmas:
            correct = other = unnamed = 0
            for seed in range(args.seeds if sigma > 0 else 1):
                pos = jitter(pos0, box, sigma, np.random.default_rng(rng0 + int(sigma * 1000) + 7919 * seed))
                fp = keys_of(pos, box)
                match = yoda.matchLibrary(fp, lib)
                for lab in match.labels:
                    if lab == truth:
                        correct += 1
                    elif lab == "":
                        unnamed += 1
                    else:
                        other += 1
            tot = max(1, correct + other + unnamed)
            emit(test=truth, sigma=f"{sigma:.2f}", n=len(pos0), correct=f"{correct / tot:.3f}",
                 other=f"{other / tot:.3f}", unnamed=f"{unnamed / tot:.3f}")

    # the atlas at rest and under noise: does the library name each polymorph as itself
    for name, (pos, box) in ideal.items():
        spec = STRUCTURES[name]
        kind, guests = spec[0], (spec[2] if len(spec) > 2 else ())
        rep = reps_for(args.genice, kind)
        for noise in (0.0, 1.0, 2.0):
            try:
                p, b = genice(args.genice, kind, rep, noise, 1, guests)
            except subprocess.CalledProcessError:
                continue
            match = yoda.matchLibrary(keys_of(p, b), lib)
            truth = ICE1.get(name, name)
            n = max(1, len(match.labels))
            correct = sum(1 for lab in match.labels if lab == truth) / n
            unnamed = sum(1 for lab in match.labels if lab == "") / n
            emit(atlas=name, noise=noise, n=len(p), correct=f"{correct:.3f}",
                 unnamed=f"{unnamed:.3f}", other=f"{1 - correct - unnamed:.3f}")


if __name__ == "__main__":
    main()
