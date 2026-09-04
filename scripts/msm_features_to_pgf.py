#!/usr/bin/env python3
"""pgfplots figure of cage n_max and CHILL+ n_max on the Niu pair.

  python scripts/msm_features.py results/walks results/msm_features.csv
  python scripts/msm_features_to_pgf.py results/msm_features.csv results/msm_features.tex
"""
from __future__ import annotations

import csv
import pathlib
import sys

CAGE = r"teal!80!black, very thick"
CHILL = r"coral!80!red, very thick, densely dashed"
STYLE = r"""  grid=major,
  grid style={gray!18},
  tick label style={font=\sffamily\small},
  label style={font=\sffamily\small},
  title style={font=\sffamily\small},
  legend style={font=\sffamily\footnotesize, draw=none, fill=white,
    fill opacity=0.88, text opacity=1},
  legend cell align=left,
"""
TITLES = {
    "niu-critical-growing": r"growing member",
    "niu-critical-melting": r"melting member",
}


def load(path):
    rows = []
    with pathlib.Path(path).open() as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "dump": r["dump"],
                    "frame": int(r["frame"]),
                    "n_max": float(r["n_max"]),
                    "chill_max": float(r["chill_max"]),
                }
            )
    return rows


def series(rows, dump, key):
    return " ".join(f"({r['frame']},{r[key]:.1f})" for r in rows if r["dump"] == dump)


def figure_tex(rows):
    dumps = [d for d in TITLES if any(r["dump"] == d for r in rows)]
    n = len(dumps)
    parts = [
        r"\begin{tikzpicture}",
        rf"""\begin{{groupplot}}[
  group style={{group size={n} by 1, horizontal sep=1.4cm, ylabels at=edge left}},
  width=0.48\textwidth, height=0.42\textwidth,
  xlabel={{stored frame}}, ylabel={{$n_{{\max}}$}},
  ymin=0,
{STYLE}]""",
    ]
    for i, dump in enumerate(dumps):
        extra = ", legend to name=appmsmleg, legend columns=2" if i == 0 else ""
        parts.append(f"\\nextgroupplot[title={{{TITLES[dump]}}}{extra}]")
        parts.append(f"\\addplot[{CAGE}] coordinates {{{series(rows, dump, 'n_max')}}};")
        if i == 0:
            parts.append(r"\addlegendentry{cage $n_{\max}$}")
        parts.append(
            f"\\addplot[{CHILL}] coordinates {{{series(rows, dump, 'chill_max')}}};"
        )
        if i == 0:
            parts.append(r"\addlegendentry{CHILL+ $n_{\max}$}")
    parts.append(r"\end{groupplot}")
    parts.append(
        r"\node at ($(group c1r1.south)!0.5!(group c"
        + str(n)
        + r"r1.south)$) [below=1.15cm] {\pgfplotslegendfromname{appmsmleg}};"
    )
    parts.append(r"\end{tikzpicture}")
    parts.append("")
    return "\n".join(parts)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        raise SystemExit(__doc__)
    src = pathlib.Path(argv[0])
    out = pathlib.Path(argv[1])
    rows = load(src)
    if not rows:
        raise SystemExit(f"no MSM feature rows in {src}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(figure_tex(rows))
    print("wrote", out)


if __name__ == "__main__":
    main()
