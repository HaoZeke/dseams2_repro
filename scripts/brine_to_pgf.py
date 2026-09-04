#!/usr/bin/env python3
"""pgfplots figure from brine_summary.py output.

  python scripts/brine_summary.py results/brine > results/brine/summary.txt
  python scripts/brine_to_pgf.py results/brine/summary.txt results/brine/brine.tex
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


def load(path):
    rows = []
    for line in pathlib.Path(path).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        w = line.split()
        if len(w) < 13:
            continue
        rows.append(
            {
                "T": int(w[0]),
                "pairs": int(w[1]),
                "replica": int(w[2]),
                "n": int(w[3]),
                "nice0": float(w[4]),
                "nice1": float(w[5]),
                "nmax0": float(w[6]),
                "nmax1": float(w[7]),
                "chill0": float(w[8]),
                "chill1": float(w[9]),
                "slope": float(w[10]),
                "ionice": float(w[11]),
                "ionfront": float(w[12]),
                "ionliq": float(w[13]) if len(w) > 13 else 0.0,
            }
        )
    return rows


def mean_by(rows, key_fields, value):
    groups = {}
    for r in rows:
        k = tuple(r[f] for f in key_fields)
        groups.setdefault(k, []).append(r[value])
    return {k: sum(v) / len(v) for k, v in groups.items()}


def figure_tex(rows):
    temps = sorted({r["T"] for r in rows})
    dn = mean_by(rows, ("T", "pairs"), "nmax1")
    d0 = mean_by(rows, ("T", "pairs"), "nmax0")
    liq = mean_by(rows, ("T", "pairs"), "ionliq")
    pairs = sorted({r["pairs"] for r in rows})
    styles = (
        r"teal!80!black, very thick, mark=square*",
        r"teal!50!black, thick, mark=*",
        r"coral!80!red, very thick, mark=o",
    )
    parts = [
        r"\begin{tikzpicture}",
        rf"""\begin{{groupplot}}[
  group style={{group size=2 by 1, horizontal sep=1.6cm}},
  width=0.48\textwidth, height=0.42\textwidth,
  xlabel={{NaCl pairs}},
{STYLE}]""",
        r"\nextgroupplot[title={largest cage cluster, last stride}, "
        r"ylabel={molecules}, legend to name=appbrineleg, legend columns=3]",
    ]
    for T, style in zip(temps, styles):
        pts = " ".join(f"({p},{dn[(T, p)]:.1f})" for p in pairs if (T, p) in dn)
        parts.append(f"\\addplot[{style}] coordinates {{{pts}}};")
        parts.append(f"\\addlegendentry{{${T}\\,\\mathrm{{K}}$}}")
    parts.append(r"\nextgroupplot[title={ions in liquid, last stride}, ylabel={ions}]")
    for T, style in zip(temps, styles):
        pts = " ".join(f"({p},{liq[(T, p)]:.2f})" for p in pairs if (T, p) in liq)
        parts.append(f"\\addplot[{style}] coordinates {{{pts}}};")
    parts.append(r"\end{groupplot}")
    parts.append(
        r"\node at ($(group c1r1.south)!0.5!(group c2r1.south)$) "
        r"[below=1.15cm] {\pgfplotslegendfromname{appbrineleg}};"
    )
    parts.append(r"\end{tikzpicture}")
    parts.append("")
    _ = d0
    return "\n".join(parts)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(argv[0])
    out = pathlib.Path(argv[1])
    rows = load(src)
    if not rows:
        raise SystemExit(f"no brine summary rows in {src}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(figure_tex(rows))
    print("wrote", out)


if __name__ == "__main__":
    main()
