"""Tiny deterministic tree tests; no external solver or raw NL2 hands required."""
import importlib.util
import pathlib
import sys
import unittest

PY = pathlib.Path(__file__).resolve().parents[1] / "py"
sys.path.insert(0, str(PY))
from strategy_report import board_bucket, cards, hand_group, summarize
from multistreet_batch import extraction, sampled_runouts, SIZES


class ToyTree(unittest.TestCase):
    def test_flop_texture(self):
        self.assertEqual(board_bucket("As7s2s"), ["A_high", "monotone"])
        self.assertEqual(board_bucket("9c9d2h"), ["low_9", "paired"])
        self.assertEqual(board_bucket("KcQd3h"), ["KQ_high"])

    def test_hand_buckets(self):
        self.assertEqual(hand_group("As7h2c", "AdAh"), "two_pair_plus")
        self.assertEqual(hand_group("As7h2c", "AcKh"), "top_pair_good")
        self.assertEqual(hand_group("As7h2c", "Ac4h"), "top_pair_weak")
        self.assertEqual(hand_group("As7h2c", "7c3d"), "middle_low_pair")
        self.assertEqual(hand_group("9s8s2h", "JsTs"), "strong_draw")
        self.assertIsNone(hand_group("As7h2c", "AsKd"))

    def toy(self, unreachable=False):
        # Two private hands, two action blocks (action-major).
        root = dict(line="x", board="As7h2c", player=1,
                    acts=["x", "b33"],
                    w=[[1., 1.], [1., 0. if unreachable else 1.]],
                    strat=[0.4, 1., 0.6, 0.])
        child = dict(line="x b33", board="As7h2c", player=0,
                     acts=["f", "c", "r"],
                     w=[[0.2, 1.], [1., 1.]],
                     strat=[0.2, 0.7, 0.7, 0.3, 0.1, 0.])
        # Root is IP; child OOP. Two villain holdings always reachable.
        return dict(hands=[["AcKh", "7c3d"], ["AcKh", "7c3d"]],
                    nodes=[root, child], info={"gto_expl_pct": .2, "gto_converged": True})

    def test_export_no_ghost_hand(self):
        data = self.toy(unreachable=True)
        rows, issues = summarize(data)
        self.assertFalse(issues, issues)
        self.assertTrue(rows)
        root = [r for r in rows if r["line"] == "x"]
        self.assertFalse(any(r["hand_class"] == "middle_low_pair" for r in root))
        self.assertEqual(sum(r["frequency"] for r in root if r["hand_class"] == "top_pair_good"), 1.0)

    def test_reach_violation(self):
        data = self.toy()
        # Same player parent and child; banned combo reappears.
        data["nodes"][0]["player"] = 0
        data["nodes"][0]["w"][0] = [1., 0.]
        rows, issues = summarize(data)
        self.assertTrue(any("unreachable hand" in x for x in issues), issues)

    def test_deterministic_runouts(self):
        a = list(sampled_runouts("As7h2c", 3, 2))
        self.assertEqual(a, list(sampled_runouts("As7h2c", 3, 2)))
        self.assertEqual(len(a), 3)
        self.assertTrue(all(len(x[1]) == 2 and x[0] not in x[1] for x in a))
        ex = extraction("As7h2c", 2, 1)
        self.assertEqual(len(ex), 5)
        self.assertEqual(ex[0]["prefix"], [])
        self.assertEqual(ex[1]["prefix"][:2], ["x", "x"])

    def test_presets(self):
        self.assertIn("150%", SIZES["full"])
        self.assertIn(",a", SIZES["full"])


if __name__ == "__main__":
    unittest.main()
