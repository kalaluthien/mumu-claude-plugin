# Changelog

Each version of the grammar, [assets/rubric-schema.json](assets/rubric-schema.json), newest first. A rubric names the version it is written in.

## 1

- First version, from the owner's `rubric-authoring` skill: binary criteria in tiers, exchange records, judge calibration.
- Verdicts are 0 or 1 only; a 2/1/0 question is two criteria.
- Each criterion cites its provenance.
- No tier or criterion carries a weight; `check-spec.py weights` derives each tier's.
- The verdict file a scoring script reads is `$defs/verdicts`.
- The grades file `make-page.py` reads is `$defs/grades`: one target's verdicts with their evidence, reasons and fixes, or `null` for a criterion not judged (added 2026-10-28; a rubric needs no change).
