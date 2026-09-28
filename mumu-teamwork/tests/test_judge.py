"""The `judge` agent judges each criterion by its kind against a rubric the worker never sees,
and the kickoff skill, the lead's Filing and the worker's playbook carry the rules it rests on (#299).

Run: uvx pytest mumu-teamwork/tests -q
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
JUDGE = ROOT / "agents" / "judge.md"
SKILL = ROOT / "skills" / "kickoff" / "SKILL.md"
LEAD = ROOT / "skills" / "kickoff" / "references" / "lead-goal.md"
WORK = ROOT / "skills" / "kickoff" / "references" / "work-task.md"
KINDS = ("`[exists]`", "`[test]`", "`[quality]`")


def section(path, heading):
    """The text under `## <heading>` up to the next heading of that level or above."""
    match = re.search(rf"^## {heading}\n(.*?)(?=^#{{1,2}} |\Z)", path.read_text(), re.M | re.S)
    return match.group(1) if match else ""


def step(n):
    """Numbered step `n` of the judge's body."""
    match = re.search(rf"^{n}\. (.*)$", JUDGE.read_text(), re.M)
    return match.group(1) if match else ""


class Rename(unittest.TestCase):
    def test_the_agent_is_named_judge_and_no_file_names_the_old_one(self):
        _, front, _ = JUDGE.read_text().split("---\n", 2)
        self.assertIn("name: judge", front.splitlines())
        for path in [*ROOT.rglob("*"), ROOT.parent / ".claude-plugin" / "marketplace.json"]:
            if path.is_file() and path.suffix in {".md", ".py", ".json"}:
                with self.subTest(path=path):
                    self.assertNotRegex(path.read_text(), r"(?i)review(?:er)")


class Kind(unittest.TestCase):
    def test_the_domain_defines_a_criterion_kind_as_its_first_token(self):
        row = next((line for line in SKILL.read_text().splitlines() if line.startswith("| kind |")), "")
        self.assertIn("first token", row)
        for kind in KINDS:
            self.assertIn(kind, row)

    def test_the_criteria_table_gains_an_on_main_column_for_test_rows(self):
        rule = next((line for line in SKILL.read_text().splitlines() if line.startswith("- A pull request body is")), "")
        self.assertRegex(rule, r"`on main` column, filled for a `\[test\]` row with the new test's failing line run against the default branch")

    def test_filing_has_the_lead_write_a_kind_on_each_new_criterion(self):
        filing = section(LEAD, "Filing")
        self.assertRegex(filing, r"each criterion of a new task with its kind")
        for kind in KINDS:
            self.assertIn(kind, filing)


class Judge(unittest.TestCase):
    def test_it_may_write_its_rubric_file_and_never_posts_it(self):
        _, front, body = JUDGE.read_text().split("---\n", 2)
        self.assertIn("Write", re.search(r"^tools: (.*)$", front, re.M)[1].split(", "))
        self.assertIn("`/tmp/claude-<uid>/mumu-teamwork/rubric-<repo>-<n>.md`", body)
        self.assertRegex(body, r"never posted to GitHub")
        self.assertRegex(body, r"3-6 weighted lenses.*50 = the result the default branch has now and 100 = the ideal expert's")
        self.assertRegex(body, r"3-5 code-review criteria picked from the default list")
        self.assertIn("\nDefault code-review list: ", body)

    def test_plan_review_finds_a_criterion_without_kind_failure_or_score(self):
        plan = step(2)
        self.assertRegex(plan, r"a criterion with no kind, a `\[test\]` that cannot fail on the default branch, or a `\[quality\]` with nothing to score is a finding")
        self.assertIn("write the rubric file", plan)

    def test_pull_request_review_judges_each_kind_against_the_rubric(self):
        review = step(3)
        self.assertRegex(review, r"writing it first as in 2 when missing, and reuse it when present")
        self.assertRegex(review, r"`\[test\]` passes only when its `on main` line .*fails for the reason the task names")
        self.assertRegex(review, r"weighted total of 80 or more with no lens under 50")

    def test_a_finding_quotes_the_criterion_missed_and_names_none_met(self):
        post = step(5)
        self.assertRegex(post, r"the criterion quoted, the gap, and the direction of the fix")
        self.assertIn("name no criterion met", post)

    def test_only_a_lead_decision_changes_the_rubric(self):
        self.assertRegex(JUDGE.read_text(), r"Only a lead's `DECIDED:` on the task newer than the file changes it")


class Worker(unittest.TestCase):
    def test_a_finding_is_closed_at_its_cause(self):
        self.assertRegex(WORK.read_text(), r"A finding is closed by fixing the cause of the gap it names, never by rewording, "
                                           r"loosening a test or editing a criterion; a criterion you think wrong is .*`BLOCKED:`")


if __name__ == "__main__":
    unittest.main()
