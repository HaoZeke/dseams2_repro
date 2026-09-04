#!/usr/bin/env python3
"""Dated note when a campaign dump directory is empty.

  python scripts/dump_status.py --name shear --dumps data/shear --out results/shear/status.txt
  python scripts/dump_status.py --name inp --dumps data/inp --out results/inp/status.txt
  python scripts/dump_status.py --name brine --dumps results/brine --need summary.txt \\
      --out results/brine/status.txt

Exit 0 in every case: an absent dump is a product (the dated note), not
a failed rule. A present dump is listed; scoring is a separate rule.
"""
from __future__ import annotations

import argparse
import datetime as dt
import pathlib


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--dumps", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--need", default="")
    ap.add_argument("--glob", default="*.lammpstrj")
    args = ap.parse_args()
    root = pathlib.Path(args.dumps)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    day = dt.date.today().isoformat()
    lines = [f"name={args.name}", f"date={day}", f"dumps={root}"]
    if args.need:
        needed = root / args.need
        lines.append(f"need={needed}")
        lines.append(f"need_present={needed.is_file()}")
        if needed.is_file():
            lines.append(f"need_bytes={needed.stat().st_size}")
        else:
            lines.append("status=absent")
            lines.append(
                f"note={args.need} is not in the package on {day}; "
                "no figure numbers are taken from an unfinished run."
            )
            out.write_text("\n".join(lines) + "\n")
            print("wrote", out)
            return
    found = sorted(root.glob(args.glob)) if root.is_dir() else []
    lines.append(f"n_dumps={len(found)}")
    if found:
        lines.append("status=present")
        for p in found:
            lines.append(f"dump={p}")
    else:
        lines.append("status=absent")
        lines.append(
            f"note=no {args.glob} under {root} on {day}; "
            "the rule is the consumer, not a substitute dump."
        )
    out.write_text("\n".join(lines) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
