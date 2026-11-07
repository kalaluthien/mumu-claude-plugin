# Handoff

How a manager adds to the owner's words before passing them on, so a worker gets a finished task, a prompt that steers it and a judge a way to score it, with no owner re-decision after the routing.

## Domain

- **addition**: what the next reader cannot get from the words alone, one of the rows below.
- **routing decision**: the task's own properties, written once in the routing `DECIDED:`: its outcomes, a `Why:` line, the guesses, `Never:` lines, the context the worker lacks with its url, what done is, and the `Judge note:`. The worker reads it with `use-board.py read <issue> --as worker`.
- **worker prompt**: the lines after the kick-off arguments that steer the worker's attitude and way of working on this task, at most 100 words besides urls and the owner's quoted words, empty when the default attitude of [worker.md](worker.md) fits. It holds no goal, outcome, criterion or constraint, since the task holds those.
- **judge note**: a `Judge note:` paragraph in the routing `DECIDED:`, which the judge reads among the binding decisions and a worker's `read --as worker` omits: the cases to try against each outcome, at most 120 words.
- **guess**: an outcome or edge the words leave open and you fill in, marked `(guess)` for the worker to confirm.

Task properties, for the routing decision:

| the words or work are | add |
| --- | --- |
| short or vague | `Why:` the purpose in your own words, then the outcomes the words imply as guesses |
| open on an edge: an order, a scope, whether to remove, what a term means | a guess when one choice is plain, else one question to the owner, since choices that lead to different work are the owner's |
| a research ask | `Never:` each change the ask does not request, with the command that shows it held; done when each claim is counted or probed by a script and shown with the probe's output, never by reading; the scope lists every folder and file kind the repository keeps that can hold the thing studied, not only the obvious ones |
| a change a person sees | done when the owner sees a drawn sample of the changed rows; the owner's layout words, quoted |
| a measuring task | done when it is measured and reported, whatever the result |
| touching files another open task touches | the order link and that task's url, under `Context you lack:` |
| the base may already meet an outcome | a probe to report first, not an outcome to build |
| a change to a playbook or rule | every file that states the rule |

Steering lines, for the worker prompt; take a row only when the task is that case:

| the task is | the line |
| --- | --- |
| a research ask | Count by script, start from the raw material and check each idea as new against the repository and its prior work. |
| a change a person sees | Show the owner a drawn sample of the changed rows before you build. |
| holding files another open task touches | `BLOCKED:` at once, and start the part whose files that task never touches. |
| using a mechanism new to the repository | Read its official docs before you design. |
| a `[check]` that pipes a producer into a tool | Run `run-criteria.py` with `--pass <n>=<sample-file>`, since the base run never reaches its pass path. |
| leaving the worker a choice the words do not settle | `Free:` the choice to make unasked; `Ask first:` the choice that is the owner's. |

## Steps

1. Read the words for the purpose, the implied outcomes, the open edges and the kind of work.
2. Take the rows of the first table that fit; take the situation rows only where the words leave the case open.
3. Write the routing `DECIDED:` with its outcomes, a `Why:` line, the guesses, the properties the rows add and the `Judge note:`.
4. Write the worker prompt from the steering rows that fit, each line as short as it can be; with no row, send the kick-off arguments alone.
5. Count the worker prompt with `wc -w` after deleting its urls and the owner's quoted words; over 100, cut each line that changes no reader's next action and count again.

## Rules

- **Quote beside, never instead**: the owner's words stay verbatim; your purpose and guesses sit beside them.
- **Mark every guess**: a guess unmarked reads as the owner's word.
- **Properties in the task, steering in the prompt**: a goal, a constraint, a criterion or a judge case never goes in the prompt, since the worker finds the path and the judge's cases are probes of its criteria.
- **Judge note**: a way to score (`yes`, `no` or `Unknown`) and the cases to try; not the worker's reasoning or the manager's history.

## Example

The owner says "내보내기가 너무 느려". The routing `DECIDED:` holds the outcome "exporting a 10k-row table takes under 5 seconds", `Why:` the owner exports before every meeting, the guesses "slow" means over 5 seconds at 10k rows (guess) and csv and xlsx both count (guess), `Never:` change the file format, and done when a timed export of the 10k-row sample prints under 5 seconds, base over.

The worker prompt, 15 words:

> Free: how to speed it up. Ask first: anything that changes the output a reader opens.

The `Judge note:`, 35 words:

> Score each outcome `yes`, `no` or `Unknown`. Run the timed export at head, base and a mutant that puts the slow step back. Try 0 rows and 100k rows. Open the output in both readers.
