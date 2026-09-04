#!/usr/bin/env python3
"""Figures and tables from cubicity, occupancy, MSM features and labels."""
from __future__ import annotations

import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
CUB = ROOT / "results" / "reference" / "elja-production" / "cubicity.txt"
HYD = ROOT / "results" / "reference" / "terra-2026-09-02" / "hydrate_occupancy.txt"
MSM = ROOT / "results" / "reference" / "elja-production" / "msm_features.csv"
LAB = ROOT / "results" / "reference" / "elja-production" / "ml_labels.csv"


class CubicityPgf(unittest.TestCase):
    def test_load_and_figure(self):
        from cubicity_to_pgf import figure_tex, load, table_tex

        rows = load(CUB)
        self.assertEqual(len(rows), 18)
        self.assertEqual({r["T"] for r in rows}, {205, 215, 225})
        tex = figure_tex(rows)
        self.assertIn(r"$n_{\mathrm{Ic}}$", tex)
        self.assertIn(r"$n_{\mathrm{Ih}}$", tex)
        self.assertIn(r"$n_{\mathrm{mixed}}$", tex)
        tab = table_tex(rows)
        self.assertIn("cubicity", tab)
        grow = next(r for r in rows if r["T"] == 205 and r["seed"] == 700)
        self.assertGreater(grow["cubicity"], 0.8)
        melt = next(r for r in rows if r["T"] == 225 and r["seed"] == 50)
        self.assertLess(melt["cubicity"], 0.3)


class HydratePgf(unittest.TestCase):
    def test_filled_unit(self):
        from hydrate_occupancy_to_pgf import figure_tex, parse

        rows = parse(HYD)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r["filled"] == 1.0 for r in rows))
        self.assertTrue(all(r["occupied"] == r["expected"] for r in rows))
        tex = figure_tex(rows)
        self.assertIn("occupied", tex)
        self.assertIn(r"$5^{12}$", tex)


class MsmFeatures(unittest.TestCase):
    def test_pair_and_figure(self):
        from msm_features_to_pgf import figure_tex, load

        rows = load(MSM)
        dumps = {r["dump"] for r in rows}
        self.assertEqual(dumps, {"niu-critical-growing", "niu-critical-melting"})
        grow = [r for r in rows if r["dump"] == "niu-critical-growing"]
        melt = [r for r in rows if r["dump"] == "niu-critical-melting"]
        self.assertGreater(grow[-1]["n_max"], grow[0]["n_max"])
        self.assertLess(melt[-1]["n_max"], melt[0]["n_max"])
        tex = figure_tex(rows)
        self.assertIn("growing member", tex)
        self.assertIn("melting member", tex)
        self.assertIn(r"cage $n_{\max}$", tex)


class MlLabels(unittest.TestCase):
    def test_columns_and_rows(self):
        import csv

        with LAB.open() as fh:
            reader = csv.DictReader(fh)
            cols = reader.fieldnames
            rows = list(reader)
        for name in (
            "temperature",
            "seed_size",
            "replica",
            "time",
            "nic",
            "nih",
            "nmixed",
            "chillice",
            "chillmax",
        ):
            self.assertIn(name, cols)
        self.assertGreaterEqual(len(rows), 216)
        temps = {int(r["temperature"]) for r in rows}
        self.assertEqual(temps, {205, 215, 225})


class DumpStatus(unittest.TestCase):
    def test_absent_note(self):
        from dump_status import main

        with tempfile.TemporaryDirectory() as td:
            out = pathlib.Path(td) / "status.txt"
            import sys

            sys.argv = [
                "dump_status.py",
                "--name",
                "shear",
                "--dumps",
                str(pathlib.Path(td) / "missing"),
                "--out",
                str(out),
            ]
            main()
            text = out.read_text()
            self.assertIn("status=absent", text)
            self.assertIn("date=", text)


if __name__ == "__main__":
    unittest.main()
