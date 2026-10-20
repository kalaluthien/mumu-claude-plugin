#!/usr/bin/env python3
"""Writes ../rubric.json from the source rubric, tier by tier; edit here, rerun, then check-spec.py check."""
import json, pathlib
SRC = ".claude/dogfood/litmus-513/source-rubric.md"
def c(id, text, q, check="judge", pol="+", anchors=None, ok=None, miss=None):
    d = {"id": id, "text": text, "polarity": pol, "check": check,
         "provenance": {"kind": "source-rubric", "source": f"{SRC} question {q}"}}
    if anchors: d["anchors"] = anchors
    if ok: d["variants_ok"] = ok
    if miss: d["near_miss"] = miss
    return d
RECOUNT = "Recount from the model files, with a short Python script when a count is large; the hand-back's own numbers are the claim, never the evidence."
t1 = [
 c("no-silent-drop", "Every `slug` in the original model's `scenarios` and `rules` appears as a `slug` in the same array of each improved model, or the hand-back names it as removed.", "1 and 2",
   check="program", anchors="Compare slugs only; a kept slug whose behaviour changed is a change for change-lists-match, not a drop.",
   ok=["Option B keeps all Scenarios and rules.", "Option B drops order-returned and the hand-back lists it under 'removed, awaiting approval'."],
   miss=["Option B lacks rule no-bill-twice and the hand-back says 'all behaviour kept'.", "A Scenario is renamed and its behaviour changed with no mention."]),
 c("change-lists-match", "Every `slug` of `scenarios`, `rules` or `operations` that an improved model has and the original lacks is named as added, every one the original has and the improved model lacks is named as removed, and the hand-back names nothing as added or removed that the files do not show.", "2",
   anchors="Compare slug sets per improved model file; a changed text or signature under a kept slug needs no entry. When no slug was added or removed, a hand-back with no lists meets it. Wording of the entries is free. "+RECOUNT,
   ok=["Additions: none. Removals: none, as a table.", "The same two removals listed in prose in another order."],
   miss=["Lists one addition the model lacks.", "Omits one removed rule from the list.", "No list at all."]),
 c("size-counts-match", "Every economy value, and every nodes, edges, rules or operations count, that the hand-back states for the original or an improved model equals the recount from that model file.", "3",
   check="program", anchors="Recount: nodes is the total length of the `nodes` arrays of `level` and of every node's `opens`; edges likewise from `edges`; rules is the length of `rules`; operations the length of `operations`; economy is nodes + edges + rules + operations. Check every column of every count table, the improved ones too. Equal means exactly; a count never stated passes.",
   ok=["States 8+6+2+4=20 for the original, which the file gives.", "States only the sum, and the sum is right."],
   miss=["States 19 where the file gives 20.", "Gives the improved model's sum under the original's label."]),
 c("metric-counts-match", "Every value the hand-back states for the original or an improved model for cycles, most nodes on a level, nesting depth, or operations that return and change equals the recount from that model file.", "4 to 11",
   anchors="Most nodes on a level: the largest `nodes` array of `level` and of every node's `opens`. Nesting depth: the longest chain of `opens` below `level`. Operations that return and change: those whose `sig` has a type after the arrow other than Nothing, Unit or None, and that change state: a non-empty `modifies`, or a `post` in a model whose operations carry no `modifies`; a hand-back may call their count data/calculation/action. Ratios such as deep modules and coupling are not recounted. A value never stated passes. "+RECOUNT,
   ok=["Most nodes on a level 6 for both models, as the files give.", "Deep modules 1.06 stated and not recounted."],
   miss=["States nesting depth 2 where the longest opens chain is 3.", "States 0 operations that return and change where two return a type and carry a post."]),
]
t2 = [
 c("counts-any-per-option", "The hand-back shows at least one count, in a table or a list, for the original and for every option.", "15",
   anchors="A count is a number the owner can compare between the original and an option; the option count includes a single answer stated as the answer.",
   ok=["A table with one row per option and one column, size.", "Counts in a bullet list under each option."],
   miss=["An option described only in words such as 'smaller'.", "Counts for the original and one option, none for a second option."]),
 c("counts-all-per-option", "For the original and every option, the hand-back gives a value under each of these ten names or the synonym in brackets: economy (size), duplication (repeated texts), one term per entity, deep modules, low coupling (coupling), near-decomposability (most nodes on a level), requisite variety (unhandled triggers), essential state (unused elements), data/calculation/action (mixed elements), four states.", "15 and 3 to 12",
   anchors="A table row with a cell for the original and for the option counts as a value for both. Data/calculation/action may be a stated skip with the reason when the model is not a software or process model.",
   ok=["Every row of the criteria table filled for all columns.", "Mixed elements skipped with 'a trading model, not software', every other cell filled."],
   miss=["Coupling and cycles missing for one option.", "Only a prose paragraph about the criteria."]),
]
t3 = [
 c("option-has-conflict", "Every improved model file after the first that the hand-back offers comes with two named criteria it trades, one better and one worse than in the original or the first option, as a `Pair:` line does; a hand-back that names one improved model file or none meets it.", "13",
   anchors="An option is an improved model file the hand-back names; a proposal in prose with no model file is not an option. Read the option's own text; whether its counts bear the pair out is for other criteria.",
   ok=["Option B trades size (better) against kept behaviour (worse).", "One answer, with 'wins or ties every count'."],
   miss=["Offers three options with no pair named.", "One answer while the counts show size improves and coupling worsens."]),
]
t4 = [
 c("counts-hold", "For the recommended option, every count in the hand-back's own table that is worse than the original's is excused by a criterion the hand-back names for that option as better in exchange, as a `Pair:` line does; a hand-back with no count table fails.", "3 to 11",
   anchors="Worse means higher for every count except deep modules, where lower is worse. Use the stated values; whether they match the files is the top tier's concern.",
   ok=["Every count falls or holds.", "Coupling rises and the hand-back names the size criterion it trades against."],
   miss=["Repeated labels rise from 1 to 2 with no reason."]),
 c("levels-within-seven", "Counting the `nodes` array of `level` and of every node's `opens`, no level of the recommended model holds more than 7 nodes and its longest `opens` chain is no longer than the original's, or the hand-back states the reason.", "8",
   check="program", anchors="With no improved model, the original is the recommended model.",
   ok=["Levels of 3 and 4 nodes, depth held."], miss=["A level of 8 nodes with no reason.", "Depth rises from 2 to 3 with no reason."]),
 c("fewer-bad-states", "For the original and the recommended model, the hand-back states a count of Missing, Illegal, Redundant and Overloaded states, or that there are none, and the recommended count is 0 or below the original's.", "12",
   anchors="A four states row of 0 for both models meets it. Equal counts above 0 do not. Findings: none alone does not state four states.",
   ok=["Original: 1 Redundant; improved: none."], miss=["Not stated.", "Improved has the same Redundant state as the original."]),
 c("recommended-first", "The hand-back marks exactly one option or proposal as recommended, and no other option comes before it.", "14",
   anchors="Recommended means the word recommend or recommended next to it; a hand-back with one proposal meets it when it calls that proposal recommended.", ok=["Option A, recommended, listed first.", "One answer, stated as the answer."], miss=["Recommended option listed second.", "Two options both marked recommended.", "No recommendation."]),
]
tiers = [
 {"id": "matches-models", "name": "Every claim matches the model files, and no behaviour drops unsaid", "delta": 0.1, "judge_error": 0.03, "mask_below": True, "pass": 1, "pass_rate": 0.7, "criteria": t1},
 {"id": "owner-can-compare", "name": "The owner can compare the original and each option by counts", "delta": 0.1, "judge_error": 0.03, "criteria": t2},
 {"id": "options-earn-place", "name": "Each option exists for a stated conflict", "delta": 0.1, "judge_error": 0.1, "criteria": t3},
 {"id": "recommended-improves", "name": "The recommended model improves, and the hand-back leads with it", "criteria": t4},
]
def ex(a, b, r, by, note): return {"a": a, "b": b, "result": r, "by": by, "note": note}
U = "interview answer of the person, 2026-10-21: "
exch = [
 ex("no-silent-drop", "counts-any-per-option", "a_over_b", "user", U+"matching the model files beats everything else"),
 ex("change-lists-match", "counts-any-per-option", "a_over_b", "user", U+"matching the model files beats everything else"),
 ex("size-counts-match", "counts-any-per-option", "a_over_b", "user", U+"matching the model files beats everything else"),
 ex("metric-counts-match", "counts-any-per-option", "a_over_b", "user", U+"matching the model files beats everything else"),
 ex("no-silent-drop", "change-lists-match", "same", "claude", "both are the worst failure named: a Scenario or rule dropped without saying so; one hides the drop, the other a false list"),
 ex("size-counts-match", "metric-counts-match", "same", "claude", "both are the worst failure named: a stated number that is wrong"),
 ex("change-lists-match", "size-counts-match", "same", "claude", "settled by claude: a wrong list and a wrong number each make the hand-back untrustworthy to the owner"),
 ex("counts-any-per-option", "counts-all-per-option", "same", "claude", "settled by claude: a table with one count and one with every count both let the owner compare; the full set refines the any-count case"),
 ex("counts-any-per-option", "option-has-conflict", "a_over_b", "user", U+"any count shown for every option beats a single answer stated in prose"),
 ex("counts-all-per-option", "option-has-conflict", "a_over_b", "claude", "settled by claude: the same ground as counts-any-per-option, a hand-back with the full set but no conflict named still serves the owner"),
 ex("option-has-conflict", "recommended-first", "a_over_b", "user", U+"whether the recommended option is first or the counts improve is lowest"),
 ex("option-has-conflict", "counts-hold", "a_over_b", "user", U+"whether the recommended option is first or the counts improve is lowest"),
 ex("counts-hold", "levels-within-seven", "same", "claude", "settled by claude: both are a recounted count of the recommended model that holds or improves"),
 ex("counts-hold", "fewer-bad-states", "same", "claude", "settled by claude: both state that the recommended model is not worse than the original"),
 ex("levels-within-seven", "recommended-first", "same", "user", U+"whether the recommended option is first or the counts improve is lowest, the two are tied at the bottom"),
 ex("fewer-bad-states", "recommended-first", "same", "user", U+"whether the recommended option is first or the counts improve is lowest, the two are tied at the bottom"),
]
spec = {"version": 1,
 "task": {"instruction": "Grade one hand-back of an 'improve this system model' run: a Markdown hand-back (facts, not verified, undecided, findings, and one or more options with count tables) plus the model files it names, the original and each improved model, as JSON system models with levels, nodes, edges, scenarios, rules and operations.",
  "world": {"as_of": "2026-10-21", "scope": "The hand-back text, the original model and each improved model. A complete answer states what was kept, added and removed, gives counts for the original and every option, names why each extra option exists and recommends one.",
   "deliverable": "The hand-back; its reader is the system's owner, who picks one option from it and must trust every number without recounting."},
  "evidence_goal": "The grade shows whether the owner can trust the hand-back's numbers and lists against the model files, compare the options by counts, and see why each option exists.",
  "use": ["eval"], "source": SRC},
 "group_size": 8, "tiers": tiers, "exchange": exch,
 "judge": {"mode": "full_rubric", "model": "claude-sonnet-5-5",
  "prompt": "Read the hand-back and the model files it names. Recount from the files, with a short Python script when a count is large. Grade each criterion 0 or 1; a stated number is the claim, the files are the evidence.",
  "calibration": {"human_labels": 0, "macro_f1": None, "met_rate_gap": None, "estimated": True}},
 "monitor": ["met rate per criterion, since a criterion always met or never met orders nothing", "judge agreement across the three runs per criterion, against alpha 0.667", "share of answers failing the masked tier", "tier-mean gaps under 0.1 are ties", "weight-tiny note: the bottom tier weighs 5e-4 of the top because the exchange records fix four tiers (matching, comparing, option conflict, improving, lowest last); the person put the bottom pair lowest, so read the bottom tier as a tiebreak only and normalise advantages per group when training"]}
pathlib.Path(__file__).resolve().parents[1].joinpath("rubric.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
