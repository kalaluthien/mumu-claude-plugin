"""The `judge` agent judges each criterion by its kind against a rubric the worker never sees,
and the kickoff skill, the lead's Filing and the worker's playbook carry the rules it rests on (#299).

Run: uvx pytest teamwork/tests -q
"""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
JUDGE = ROOT / "agents" / "judge.md"
SKILL = ROOT / "skills" / "kickoff" / "SKILL.md"
LEAD = ROOT / "skills" / "kickoff" / "references" / "lead-playbook.md"
WORK = ROOT / "skills" / "kickoff" / "references" / "worker-playbook.md"
KINDS = ("[check]", "[score]")
RULES = [*(ROOT / "agents").glob("*.md"), *(ROOT / "skills").rglob("*.md")]


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
        self.assertEqual(tuple(re.findall(r"\[\w+\]", row)), KINDS)

    def test_the_criteria_table_fills_on_main_for_every_criterion(self):
        rule = next((line for line in SKILL.read_text().splitlines() if line.startswith("- A pull request body is")), "")
        self.assertRegex(rule, r"`on main` column, filled for every criterion with its check's failing output run against the default branch")

    def test_filing_derives_one_criterion_per_clause_and_runs_each_on_main(self):
        filing = section(LEAD, "Filing")
        self.assertRegex(filing, r"each criterion of a new task with its kind, `\[check\]` or `\[score\]`")
        self.assertRegex(filing, r"Derive the criteria from the Goal and each `DECIDED:`, split into one-sentence clauses, one criterion each")
        self.assertRegex(filing, r"run each criterion's check on main and quote its output")
        self.assertRegex(filing, r"A guard that already passes on main is no criterion")

    def test_only_the_judge_names_the_kinds_before_these(self):
        lines = [f"{path.name}: {line}" for path in RULES for line in path.read_text().splitlines()
                 if re.search(r"\[(exists|test|quality)\]", line)]
        self.assertEqual(len(lines), 1, lines)
        self.assertIn("filed before these kinds", lines[0])


class Judge(unittest.TestCase):
    def test_it_may_write_its_rubric_file_and_never_posts_it(self):
        _, front, body = JUDGE.read_text().split("---\n", 2)
        self.assertIn("Write", re.search(r"^tools: (.*)$", front, re.M)[1].split(", "))
        self.assertIn("`/tmp/claude-<uid>/teamwork/rubric-<repo>-<n>.md`", body)
        self.assertRegex(body, r"never posted to GitHub")
        self.assertRegex(body, r"3-6 weighted lenses.*50 = the result the default branch has now and 100 = the ideal expert's")
        self.assertRegex(body, r"3-5 code-review criteria picked from the default list")
        self.assertIn("\nDefault code-review list: ", body)

    def test_plan_review_finds_a_criterion_passing_on_main_or_a_clause_uncovered(self):
        plan = step(2)
        self.assertRegex(plan, r"a criterion with no kind, a `\[check\]` or `\[score\]` whose check passes on main, .*"
                               r"a clause of the Goal or of a `DECIDED:` no criterion covers, or a `\[score\]` with nothing to score is a finding")
        self.assertNotRegex(plan, r"relabel")
        self.assertIn("write the rubric file", plan)

    def test_plan_review_finds_what_a_later_audit_caught(self):
        plan = step(2)
        for finding in (r"Judge overlap by the files each open task's fixes would touch, .*never from the plans' words",
                        r"a rate or a count of passes with no guard against reaching it by editing its grader or checker",
                        r"decided by an eval, or by a count over runs, that does not write out its literal command, flags and grader included",
                        r"a file read or a test still to be written is none",
                        r"whose main side is quoted from an earlier run instead of measured beside head",
                        r"a gate the plan's files map to in `gates\.json` that the plan or an open task shows failing on main, "
                        r"with no criterion or blocker covering it",
                        r"run each one's check on the default branch as the plan writes it, .*never by a variant of yours",
                        r"each criterion that passes on main or cannot run there gets a finding line of its own, opening with its id"):
            with self.subTest(finding=finding):
                self.assertRegex(plan, finding)

    def test_filing_asks_of_a_plan_what_the_judge_finds(self):
        filing = section(LEAD, "Filing")
        for ask in (r"as its literal command, flags and grader included",
                    r"a guard against reaching it by editing its grader or checker",
                    r"measure main beside head, never quote it from an earlier run",
                    r"list the files its fixes would touch, a shared one included, and `order` it with each open task touching one",
                    r"a gate those files map to in `gates\.json` that fails on main, add a criterion or a blocker covering it"):
            with self.subTest(ask=ask):
                self.assertRegex(filing, ask)

    def test_pull_request_review_judges_each_kind_against_the_rubric(self):
        review = step(3)
        self.assertRegex(review, r"writing it first as in 2 when missing, and reuse it when present")
        self.assertRegex(review, r"`\[check\]` passes when its output at the sha meets its pass condition and its `on main` cell .*fails it for the reason the task names")
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
                                           r"loosening a test or editing a criterion\.")
        self.assertRegex(WORK.read_text(), r"for a criterion you think wrong, .*: `comment` `BLOCKED: <question>`")

    def test_no_rule_file_names_another_plugin(self):
        for path in RULES:
            with self.subTest(path=path):
                self.assertNotRegex(path.read_text(), r"checkerwork|mumu-verification")


if __name__ == "__main__":
    unittest.main()
