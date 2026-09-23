# Synthetic inputs

Make test inputs when real ones are missing or too uniform, aimed at where the system is expected to fail. They feed [error analysis](error-analysis.md); they are not a suite on their own.

Skip this when about 100 representative real inputs exist (sample those instead), or when nobody can tell a realistic input from an unrealistic one — specialised legal or medical documents, a language the model writes poorly.

## 1. Dimensions

Name three axes along which inputs differ and failures are likely, each with a few values. For a plugin skill:

```
request: asks for the skill's job directly | describes the need without naming it | a near miss the skill should not take
context: empty repo | repo with the layout the skill expects | repo with a competing layout
user: precise | vague | contradicts itself
```

Add an axis only when traces show failures along it.

## 2. Tuples

Write about 20 combinations (one value per axis) and have the owner strike the unrealistic ones. Then let a model propose more, without duplicates.

## 3. Inputs

Turn each tuple into a natural input in a **separate** call from the one that made the tuple; generating both at once repeats phrasing. Give the call one hand-written example. Drop inputs that read awkwardly, miss their tuple, or near-duplicate another.

Generate inputs only, never the outputs: the system under test writes those, or the traces show the generator's habits instead of the system's.

For a skill, include inputs that should **not** trigger it: a trigger eval needs both sides.

## 4. Run

Run each input through the whole system and keep the full trace. Then read them: [error analysis](error-analysis.md).
