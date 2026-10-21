# Recheck

Bring a Schema document read from code back in line once the code has moved on, and say for each rule whether a
failure is drift in the document or a defect in the code. A document that no longer describes the code can keep
passing; that pass is the dangerous case, because it looks like a proof.

## Language

The document is written in the grammar, [../schema/assets/schema.json](../schema/assets/schema.json), as
[../schema/authoring.md](../schema/authoring.md) says; its commit is the sha in its own top-level `meta.evidence`,
which [interpret.md](interpret.md) writes, and each element's `meta.evidence` names the lines it was read from.

## Outcomes

Give each rule one:

- **in sync**: no change since the commit touches what the rule rests on, and it passes;
- **updated**: the code changed, the document now describes it again, and the rule passes;
- **defect**: the document describes the code, and the code breaks the rule; a finding about the code, not drift;
- **blocked**: the document could not be brought back in line, or the rule could not be proved; say why.

A rule can be both updated and defect. Edit only the document, never the system's code, and never weaken a rule to
pass, as [prove.md](prove.md)'s Findings stay findings says.

## Steps

Command paths are relative to this file.

1. Run `scripts/prove-schema.py doc.json` before changing anything, and keep its lines: a pass here says only that
   the old description still holds.
2. Run `scripts/resolve-pointers.py drift doc.json --root <repo> --sha <commit>`; read each `changed` or `gone`
   pointer's diff and commit messages (`git log -L <a>,<b>:<path> <commit>..`), and look for moved or renamed code and
   for new code that writes what a rule guards. Call each change one of:
   - **no effect**: nothing the document states changed, checked against the document, not the commit message;
   - **no longer describes**: a step split, a branch added or removed, a check moved, a new path, a new range;
   - **promise changed on purpose**: a doc comment, test, changelog or commit message says so; cite it;
   - **promise may be broken**: the code changed and nothing says the promise did.
   `fixtures/pointers-drifted.json`, read at 85fcfa8, prints 3 changed and 2 unchanged up to d4a0802; run it after
   changing the script.
3. Update the document from the code, not from what makes a rule pass: each changed element again cites the line it
   rests on. Change a rule only for a promise changed on purpose, writing its old text, new text and evidence. Run
   `../schema/scripts/check-schema.py check doc.json` until it prints `ok`.
4. Run `scripts/prove-schema.py --mutate doc.json` and judge each line:
   - **pass**: it must end `fails without`, so the updated document can still fail;
   - **counterexample**: replay the trace on the code step by step. A step the code cannot take is drift: fix the
     document and say what was wrong. Every step possible is a defect: name the commit that brought it, retell the
     trace in the code's words and the harm in one sentence.
   A rule that passed in step 1 and fails now passed on a stale description; say so.
5. Move the document's commit to the one you checked only when no rule is blocked; else keep it and say why.
6. Hand over each rule's outcome, the commits read, each document change with its reason, each defect, and what the
   document still does not cover. Put the document's update in a change of its own, apart from any fix to the code.
