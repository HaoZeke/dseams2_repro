#!/usr/bin/env python3
"""pgfplots figure and latex table from a committor.txt.

  python scripts/committor_to_pgf.py results/production/committor.txt \\
      results/production/committor.tex results/production/committor-table.tex
"""
from __future__ import annotations

import pathlib
import sys

CAGE = r"teal!80!black, very thick, mark=square*"
CHILL = r"coral!80!red, very thick, mark=o"
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
        rows.append(
            {
                "T": int(w[0]),
                "seed": int(w[1]),
                "poly": w[2],
                "n": int(w[3]),
                "p_cage": float(w[4]),
                "p_chill": float(w[5]),
                "open_cage": float(w[6]),
                "open_chill": float(w[7]),
                "slope_cage": float(w[8]),
                "slope_chill": float(w[9]),
            }
        )
    return rows


def coords(rows, key):
    return " ".join(f"({r['seed']},{r[key]:.3f})" for r in rows)


def figure_tex(rows):
    temps = sorted({r["T"] for r in rows})
    n = len(temps)
    parts = [
        r"\begin{tikzpicture}",
        rf"""\begin{{groupplot}}[
  group style={{group size={n} by 1, horizontal sep=1.3cm, ylabels at=edge left}},
  width=0.33\textwidth, height=0.42\textwidth,
  xmin=0, xmax=750, ymin=-0.05, ymax=1.08,
  xlabel={{seed size $N$}}, ylabel={{grown fraction $p$}},
  xtick={{50,200,450,700}},
{STYLE}]""",
    ]
    for i, T in enumerate(temps):
        sub = [r for r in rows if r["T"] == T]
        extra = ", legend to name=appcommleg, legend columns=2" if i == 0 else ""
        parts.append(f"\\nextgroupplot[title={{${T}\\,\\mathrm{{K}}$}}{extra}]")
        parts.append(f"\\addplot[{CAGE}] coordinates {{{coords(sub, 'p_cage')}}};")
        if i == 0:
            parts.append(r"\addlegendentry{cage $n_{\max}$}")
        parts.append(f"\\addplot[{CHILL}] coordinates {{{coords(sub, 'p_chill')}}};")
        if i == 0:
            parts.append(r"\addlegendentry{CHILL+ $n_{\max}$}")
    parts.append(r"\end{groupplot}")
    parts.append(
        r"\node at ($(group c1r1.south)!0.5!(group c"
        + str(n)
        + r"r1.south)$) [below=1.15cm] {\pgfplotslegendfromname{appcommleg}};"
    )
    parts.append(r"\end{tikzpicture}")
    parts.append("")
    return "\n".join(parts)


def table_tex(rows):
    lines = [
        r"\begin{tabular}{rrrrrrrr}",
        r"\hline",
        r"$T$ (K) & $N$ & $n$ & $p_{\mathrm{cage}}$ & $p_{\mathrm{CHILL+}}$ & "
        r"open$_{\mathrm{cage}}$ & open$_{\mathrm{CHILL+}}$ & "
        r"$\mathrm{d}n_{\max}/\mathrm{d}t$ (cage) \\",
        r"\hline",
    ]
    for r in rows:
        lines.append(
            f"{r['T']} & {r['seed']} & {r['n']} & {r['p_cage']:.3f} & "
            f"{r['p_chill']:.3f} & {r['open_cage']:.3f} & {r['open_chill']:.3f} & "
            f"{r['slope_cage']:.2f} \\\\"
        )
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append("")
    return "\n".join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(argv[0])
    fig = pathlib.Path(argv[1])
    tab = pathlib.Path(argv[2]) if len(argv) > 2 else fig.with_name("committor-table.tex")
    rows = load(src)
    if not rows:
        raise SystemExit(f"no committor rows in {src}")
    fig.parent.mkdir(parents=True, exist_ok=True)
    tab.parent.mkdir(parents=True, exist_ok=True)
    fig.write_text(figure_tex(rows))
    tab.write_text(table_tex(rows))
    print("wrote", fig)
    print("wrote", tab)


if __name__ == "__main__":
    main()
