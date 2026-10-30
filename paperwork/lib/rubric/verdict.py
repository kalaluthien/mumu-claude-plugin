"""A criterion's result from its runs, and a target's rating from its gaps; report.md says why each rule holds."""
import hashlib

RUNS = 3


def rubric_sha(rubric_bytes):
    return hashlib.sha256(rubric_bytes).hexdigest()[:12]


def majority(runs):
    """1 or 0 when more than half the runs say so, else None; a run with no verdict still counts in the whole."""
    return next((value for value in (1, 0) if runs.count(value) * 2 > len(runs)), None)


def split(grade):
    return len(set(grade["runs"])) > 1


def status(criterion, grade):
    """One of met, not met, not settled or not judged; a split on a critical criterion stays unsettled, whatever the
    majority, since a wrong pass there costs the most."""
    if grade["met"] is None:
        return "not judged"
    if criterion.get("critical") and split(grade):
        return "not settled"
    return "met" if grade["met"] else "not met"


def needs_person(grade):
    return split(grade) or grade["met"] is None


def gaps(rubric, grades):
    """(critical gaps, other gaps): every criterion that is not met, since nobody earns what nobody could check."""
    missed = [criterion for criterion in rubric["criteria"] if status(criterion, grades["grades"][criterion["id"]]) != "met"]
    critical = sum(bool(criterion.get("critical")) for criterion in missed)
    return critical, len(missed) - critical


def rating(critical_gaps, other_gaps):
    """AMSTAR 2's pattern of flaws, which is never a score."""
    if critical_gaps:
        return "Low" if critical_gaps == 1 else "Critically low"
    return "High" if other_gaps <= 1 else "Moderate"
