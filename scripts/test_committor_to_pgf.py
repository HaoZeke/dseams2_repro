#!/usr/bin/env python3
"""committor_to_pgf.py emits one series per temperature from committor.txt."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

from committor_to_pgf import figure_tex, load, table_tex

HERE = pathlib.Path(__file__).resolve().parent
SAMPLE = HERE.parent / "results" / "production" / "committor.txt"


class CommittorPgf(unittest.TestCase):
    def test_load_campaign(self):
        rows = load(SAMPLE)
        self.assertEqual(len(rows), 18)
        self.assertEqual({r["T"] for r in rows}, {205, 215, 225})
        self.assertEqual({r["n"] for r in rows}, {12})

    def test_figure_has_three_panels_and_both_labels(self):
        tex = figure_tex(load(SAMPLE))
        self.assertIn(r"$205\,\mathrm{K}$", tex)
        self.assertIn(r"$215\,\mathrm{K}$", tex)
        self.assertIn(r"$225\,\mathrm{K}$", tex)
        self.assertIn(r"cage $n_{\max}$", tex)
        self.assertIn(r"CHILL+ $n_{\max}$", tex)
        self.assertIn("(200,0.917)", tex)
        self.assertIn("(200,0.000)", tex)

    def test_table_carries_p_grow(self):
        tex = table_tex(load(SAMPLE))
        self.assertIn("0.917", tex)
        self.assertIn("1.000", tex)
        self.assertIn(r"p_{\mathrm{cage}}", tex)

    def test_write(self):
        with tempfile.TemporaryDirectory() as td:
            fig = pathlib.Path(td) / "c.tex"
            tab = pathlib.Path(td) / "t.tex"
            from committor_to_pgf import main

            main([str(SAMPLE), str(fig), str(tab)])
            self.assertGreater(fig.stat().st_size, 200)
            self.assertGreater(tab.stat().st_size, 200)


if __name__ == "__main__":
    unittest.main()
