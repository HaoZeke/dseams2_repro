#!/usr/bin/env python3
"""pgfplots figure from hydrate_occupancy.py output.

  python scripts/hydrate_occupancy.py > results/hydrate_occupancy.txt
  python scripts/hydrate_occupancy_to_pgf.py results/hydrate_occupancy.txt \\
      results/hydrate_occupancy.tex
"""
from __future__ import annotations

import pathlib
import sys

STYLE = r"""  grid=major,
  grid style={gray!18},
  tick label style={font=\sffamily\small},
  label style={font=\sffamily\small},
  title style={font=\sffamily\small},
  legend style={font=\sffamily\footnotesize, draw=none, fill=white,
    fill opacity=0.88, text opacity=1},
  legend cell align=left,
"""

SIG_TEX = {
    "512": r"$5^{12}$",
    "51262": r"$5^{12}6^{2}$",
    "5:12,6:4": r"$5^{12}6^{4}$",
    "all": "all",
}


def parse(path):
    rows = []
    for line in pathlib.Path(path).read_text().splitlines():
        if "signature=" not in line:
            continue
        kv = {}
        for tok in line.split():
            if "=" in tok:
                k, v = tok.split("=", 1)
                kv[k] = v
        if kv.get("signature") == "all":
            continue
        rows.append(
            {
                "structure": kv["structure"],
                "signature": kv["signature"],
                "cages": int(kv["cages"]),
                "expected": int(kv["expected"]),
                "occupied": int(kv["occupied"]),
                "multiple": int(kv["multiple"]),
                "free": int(kv["free"]),
                "filled": float(kv["filled"]),
            }
        )
    return rows


def figure_tex(rows):
    # symbolic x coords with slashes/braces is fragile; use numeric ticks
    labels = [
        f"{r['structure'].replace('+CH4', '')} {SIG_TEX.get(r['signature'], r['signature'])}"
        for r in rows
    ]
    occ_pts = " ".join(f"({i},{r['occupied']})" for i, r in enumerate(rows))
    exp_pts = " ".join(f"({i},{r['expected']})" for i, r in enumerate(rows))
    xtick = ",".join(str(i) for i in range(len(rows)))
    xticklabels = ",".join(labels)
    return "\n".join(
        [
            r"\begin{tikzpicture}",
            rf"""\begin{{axis}}[
  ybar,
  bar width=9pt,
  width=0.92\textwidth, height=0.42\textwidth,
  ylabel={{cages}},
  xtick={{{xtick}}},
  xticklabels={{{xticklabels}}},
  x tick label style={{rotate=20, anchor=east, font=\sffamily\footnotesize}},
  enlarge x limits=0.15,
  ymin=0,
  legend to name=apphydleg, legend columns=2,
{STYLE}]""",
            rf"\addplot[teal!80!black, fill=teal!55!white] coordinates {{{occ_pts}}};",
            r"\addlegendentry{occupied}",
            rf"\addplot[coral!80!red, fill=coral!30] coordinates {{{exp_pts}}};",
            r"\addlegendentry{enumerated}",
            r"\end{axis}",
            r"\node at (current bounding box.south) [below=0.55cm] "
            r"{\pgfplotslegendfromname{apphydleg}};",
            r"\end{tikzpicture}",
            "",
        ]
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(argv[0])
    out = pathlib.Path(argv[1])
    rows = parse(src)
    if not rows:
        raise SystemExit(f"no occupancy rows in {src}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(figure_tex(rows))
    print("wrote", out)


if __name__ == "__main__":
    main()
