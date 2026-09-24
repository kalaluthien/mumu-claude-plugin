"""What `judge-agreement.py` prints for a labelled csv: fail-positive rates, the guessing margin and the bootstrap interval.

Run: python3 -m unittest discover mumu-verification/tests
"""
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "eval" / "scripts" / "judge-agreement.py"


def csv_of(counts):
    """counts maps (human, judge) to a number of rows."""
    rows = ["trace,human,judge"]
    for (human, judge), n in counts.items():
        rows += [f"t{len(rows)},{human},{judge}" for _ in range(n)]
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    f.write("\n".join(rows) + "\n")
    f.close()
    return f.name


def run(counts, *args):
    return subprocess.run([sys.executable, str(SCRIPT), csv_of(counts), *args],
                          capture_output=True, text=True)


def rates(out):
    m = re.search(r"TPR (\d\.\d+)\s+TNR (\d\.\d+)", out)
    return float(m.group(1)), float(m.group(2))


def interval(out):
    m = re.search(r"corrected (\d\.\d+)\s+95% interval \[(\d\.\d+), (\d\.\d+)\]", out)
    return tuple(float(g) for g in m.groups())


# 40 human fails, 40 human passes; the judge catches 36 fails and passes 32 passes.
GOOD = {("fail", "fail"): 36, ("fail", "pass"): 4, ("pass", "pass"): 32, ("pass", "fail"): 8}


class FailIsPositive(unittest.TestCase):
    def test_tpr_is_the_share_of_human_fails_the_judge_fails(self):
        r = run(GOOD)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rates(r.stdout), (0.9, 0.8))

    def test_a_judge_that_never_fails_has_tpr_zero(self):
        r = run({("fail", "pass"): 10, ("pass", "pass"): 10})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(rates(r.stdout), (0.0, 1.0))


class GuessingMargin(unittest.TestCase):
    def test_rate_printed_when_tpr_plus_tnr_clears_the_margin(self):
        r = run(GOOD, "--observed", "0.6")
        self.assertEqual(r.returncode, 0, r.stderr)
        theta, lo, hi = interval(r.stdout)
        # pass rate = (p_obs + TPR - 1) / (TPR + TNR - 1) = 0.5 / 0.7
        self.assertAlmostEqual(theta, 0.714, places=3)
        self.assertLessEqual(lo, theta)
        self.assertLessEqual(theta, hi)

    def test_rate_refused_when_tpr_plus_tnr_is_within_the_margin_of_one(self):
        # TPR 0.6, TNR 0.55: |TPR + TNR - 1| = 0.15, under the margin, though far from 0
        r = run({("fail", "fail"): 12, ("fail", "pass"): 8, ("pass", "pass"): 11, ("pass", "fail"): 9},
                "--observed", "0.5")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("corrected", r.stdout)
        self.assertIn("margin", r.stderr)


class ObservedSamplingError(unittest.TestCase):
    def test_unlabelled_count_widens_the_interval(self):
        base = interval(run(GOOD, "--observed", "0.6").stdout)
        r = run(GOOD, "--observed", "0.6", "--unlabelled", "30")
        self.assertEqual(r.returncode, 0, r.stderr)
        both = interval(r.stdout)
        self.assertEqual(both[0], base[0])
        self.assertGreater(both[2] - both[1], base[2] - base[1])

    def test_a_huge_unlabelled_count_leaves_the_interval_nearly_unchanged(self):
        base = interval(run(GOOD, "--observed", "0.6").stdout)
        huge = interval(run(GOOD, "--observed", "0.6", "--unlabelled", "10000000").stdout)
        self.assertAlmostEqual(huge[2] - huge[1], base[2] - base[1], delta=0.02)

    def test_unlabelled_without_observed_is_refused(self):
        r = run(GOOD, "--unlabelled", "30")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
