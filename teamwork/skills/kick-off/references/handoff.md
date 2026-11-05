# Handoff

How a manager adds to the owner's words before passing them on, so a worker gets a finished task and a judge a way to score it, with no owner re-decision after the routing.

## Domain

- **addition**: what the next reader cannot get from the words alone, one of the rows below.
- **worker brief**: the words handed over with the kick-off arguments: the goal and its context, at most 150 words besides urls and the owner's quoted words.
- **judge note**: a `Judge note:` paragraph in the routing `DECIDED:`, which the judge reads among the binding decisions: the cases to try against each outcome, at most 120 words.
- **guess**: an outcome or edge the words leave open and you fill in, marked `(guess)` for the worker to confirm.

| the words or work are | add |
| --- | --- |
| short or vague | `Why:` the purpose in your own words, then the outcomes the words imply as guesses |
| open on an edge: an order, a scope, whether to remove, what a term means | a guess when one choice is plain, else one question to the owner, since choices that lead to different work are the owner's |
| a research ask | `Never: edit a file or call an outside service`, with the command that shows nothing changed; done when each claim is counted or probed by a script and shown with the probe's output, never by reading, and each option is checked as new against the repository and its prior work, not recalled; the scope lists the repository's folders and file kinds that can hold the thing studied, shared libraries and interface code beside the usual scripts |
| a change a person sees | done when the owner sees a drawn sample of the changed rows, before the build; the owner's layout words, quoted |
| a measuring task | done when it is measured and reported, whatever the result |
| touching files another open task touches | the order link and that task's url, under `Context you lack:` |
| the base may already meet an outcome | a probe to report first, not an outcome to build |
| a change to a playbook or rule | every file that states the rule |

## Steps

1. Read the words for the purpose, the implied outcomes, the open edges and the kind of work.
2. Take the rows of the table that fit; take the situation rows only where the words leave the case open.
3. Write the routing `DECIDED:` with its outcomes, a `Why:` line, the guesses and the `Judge note:`: how to score (`yes`, `no` or `Unknown`) and the cases to try, at most 120 words counted as in 5.
4. Write the worker brief in this order, leaving out a slot with nothing to add: goal, why, the owner's words, guesses, never / ask first / free, context you lack with its url, sample, done when, what to return.
5. Count the worker brief with `wc -w` after deleting its urls and the owner's quoted words; over 150, cut each line that changes no reader's next action and count again.

## Rules

- **Quote beside, never instead**: the owner's words stay verbatim; your purpose and guesses sit beside them.
- **Mark every guess**: a guess unmarked reads as the owner's word.
- **Goal, not steps**: the worker brief holds no step, no formatting rule and no judge case, since the worker finds the path and the judge's cases are probes of its criteria.
- **Return doubts**: ask the worker to return its doubts and any departure from the brief with the result.
- **Judge note**: a way to score and the cases to try, with `Unknown` allowed; not the worker's reasoning or the manager's history.

## Example

The owner says "내보내기가 너무 느려". The worker brief, 75 words:

> Goal: exporting a 10k-row table feels instant. Why: the owner exports before every meeting, so a wait blocks them. Owner's words: "내보내기가 너무 느려". Guesses: "slow" means over 5 seconds at 10k rows (guess); csv and xlsx both count (guess). Never: change the file format. Free: how to speed it up. Done when: a timed export of the 10k-row sample prints under 5 seconds, base over. Return: the timings and your doubts.

The `Judge note:`, 45 words:

> Score each outcome `yes`, `no` or `Unknown`. Run the timed export at head, base and a mutant that puts the slow step back. Try 0 rows and 100k rows. Open the output in both readers.
