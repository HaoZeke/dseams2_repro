#!/usr/bin/env python3
"""pgfplots figure and latex table from cubicity.txt.

  python scripts/cubicity.py results/production > results/production/cubicity.txt
  python scripts/cubicity_to_pgf.py results/production/cubicity.txt \\
      results/production/cubicity.tex results/production/cubicity-table.tex
"""
from __future__ import annotations

import pathlib
import sys

NIC = r"teal!80!black, very thick, mark=square*"
NIH = r"olive!70!black, very thick, mark=triangle*"
MIX = r"coral!80!red, very thick, mark=o"
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
                "nic": float(w[4]),
                "nih": float(w[5]),
                "nmixed": float(w[6]),
                "nice": float(w[7]),
                "nmax": float(w[8]),
                "cubicity": float(w[9]),
                "nic0": float(w[10]),
                "nih0": float(w[11]),
                "nmixed0": float(w[12]),
                "chillice": float(w[13]),
                "chillmax": float(w[14]),
            }
        )
    return rows


def coords(rows, key):
    return " ".join(f"({r['seed']},{r[key]:.1f})" for r in rows)


def figure_tex(rows):
    temps = sorted({r["T"] for r in rows})
    n = len(temps)
    parts = [
        r"\begin{tikzpicture}",
        rf"""\begin{{groupplot}}[
  group style={{group size={n} by 1, horizontal sep=1.3cm, ylabels at=edge left}},
  width=0.33\textwidth, height=0.42\textwidth,
  xmin=0, xmax=750, ymin=0,
  xlabel={{seed size $N$}}, ylabel={{molecules}},
  xtick={{50,200,450,700}},
{STYLE}]""",
    ]
    for i, T in enumerate(temps):
        sub = [r for r in rows if r["T"] == T]
        extra = ", legend to name=appcubleg, legend columns=3" if i == 0 else ""
        parts.append(f"\\nextgroupplot[title={{${T}\\,\\mathrm{{K}}$}}{extra}]")
        parts.append(f"\\addplot[{NIC}] coordinates {{{coords(sub, 'nic')}}};")
        if i == 0:
            parts.append(r"\addlegendentry{$n_{\mathrm{Ic}}$}")
        parts.append(f"\\addplot[{NIH}] coordinates {{{coords(sub, 'nih')}}};")
        if i == 0:
            parts.append(r"\addlegendentry{$n_{\mathrm{Ih}}$}")
        parts.append(f"\\addplot[{MIX}] coordinates {{{coords(sub, 'nmixed')}}};")
        if i == 0:
            parts.append(r"\addlegendentry{$n_{\mathrm{mixed}}$}")
    parts.append(r"\end{groupplot}")
    parts.append(
        r"\node at ($(group c1r1.south)!0.5!(group c"
        + str(n)
        + r"r1.south)$) [below=1.15cm] {\pgfplotslegendfromname{appcubleg}};"
    )
    parts.append(r"\end{tikzpicture}")
    parts.append("")
    return "\n".join(parts)


def table_tex(rows):
    lines = [
        r"\begin{tabular}{rrrrrrrr}",
        r"\hline",
        r"$T$ (K) & $N$ & $n$ & $n_{\mathrm{Ic}}$ & $n_{\mathrm{Ih}}$ & "
        r"$n_{\mathrm{mixed}}$ & $n_{\mathrm{ice}}$ & cubicity \\",
        r"\hline",
    ]
    for r in rows:
        lines.append(
            f"{r['T']} & {r['seed']} & {r['n']} & {r['nic']:.1f} & "
            f"{r['nih']:.1f} & {r['nmixed']:.1f} & {r['nice']:.1f} & "
            f"{r['cubicity']:.3f} \\\\"
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
    tab = pathlib.Path(argv[2]) if len(argv) > 2 else fig.with_name("cubicity-table.tex")
    rows = load(src)
    if not rows:
        raise SystemExit(f"no cubicity rows in {src}")
    fig.parent.mkdir(parents=True, exist_ok=True)
    tab.parent.mkdir(parents=True, exist_ok=True)
    fig.write_text(figure_tex(rows))
    tab.write_text(table_tex(rows))
    print("wrote", fig)
    print("wrote", tab)


if __name__ == "__main__":
    main()
