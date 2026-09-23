# Audit an existing eval

Say whether an eval suite can be trusted, and what to fix first. Inspect the artifacts themselves — cases, graders, judge prompts, labels, results — never answer from a checklist alone.

## 1. Gather

Cases and graders in `evals/`, judge prompts, labelled data, past results, and the traces behind them: local files, or the observability tool if one is connected.

## 2. Check

| area | a problem when |
| --- | --- |
| error analysis | no notes or failure taxonomy exists; the modes are generic ("hallucination", "toxicity", "coherence") rather than observed in this product ("quotes a price from the wrong listing"); or it predates the last model switch or prompt rewrite |
| grader design | a score scale with no pass line; a judge covering several qualities at once; a judge where a pattern, a parse or an execution would do; similarity metrics (ROUGE, BERTScore, embedding distance) grading generated text |
| judge validation | no TPR and TNR measured against human labels; agreement reported as accuracy or kappa; prompt examples drawn from the data used to measure it; dev rates reported as final |
| human review | reviewers are not domain experts; they see only final outputs, not the whole trace; traces are shown as raw JSON |
| labelled data | fewer than about 100 reviewed traces, or fewer than about 50 of each verdict for a judge; sampled from the first N rather than across what varies |
| runs | one run per case for a non-deterministic system; runs sharing state (files, caches, a session); a regression suite that has passed everything for months and so catches nothing new; nobody reads failing transcripts |

## 3. Report

Findings in order of impact on the product, each as:

```
### <problem>
Status: exists | fine | cannot tell
<one or two sentences on what was found, naming the file>
Fix: <the action, and the reference that does it>
```

Omit areas with nothing found. With no eval artifacts at all, the report is one line: start with [error analysis](error-analysis.md), or [synthetic inputs](synthetic-inputs.md) where no traces exist; recommend no grader before that.
