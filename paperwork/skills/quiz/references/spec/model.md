# Model

How a spec turns verdicts into an order. The grammar, [assets/rubric.schema.json](assets/rubric.schema.json), says what a spec may hold; this file says what it means, so every script scores it the same way.

## Tier score and reward

A criterion's verdict $c_k(y)\in\{0,1\}$ says whether answer $y$ meets it; a `-` criterion counts as $1-c_k$, since it names an error. Criteria in one tier trade off against each other and share its score equally; tiers never trade off:

$$u_d(y)=\frac{1}{|T_d|}\sum_{k\in T_d}c_k(y),\qquad r(y)=\sum_d \varepsilon_d\,u_d(y)$$

Order is lexicographic on expected tier scores, a utility in the sense of Fishburn's survey of lexicographic orders (*Management Science* 20(11), 1974): a higher tier decides, and a lower tier only orders answers the higher tiers tie. Never compare two answers outcome by outcome at the first differing tier: when a top criterion passes by chance, the lower tiers would buy back a deficit the expected scores keep.

A rubric of 2/1/0 questions is binary too: each question becomes two criteria, meets fully and meets at least partly, so their sum is the old score. A flat rubric is one tier.

## Derivation

The weights come from two numbers per tier: $e_d$, the chance the judge flips one verdict of tier $d$, and $\delta_d$, the smallest expected tier-score difference no lower tier may overturn.

1. A judge that flips each verdict with chance $e_d$ reports $\hat c = c$ with chance $1-e_d$ and $1-c$ with chance $e_d$, so $E[\hat c]=e_d+(1-2e_d)\,c$.
2. Tier scores are means of verdicts, so a true difference $\Delta u_d$ between two answers is seen as $(1-2e_d)\,\Delta u_d$; at the band, $(1-2e_d)\,\delta_d$.
3. Each lower tier's score lies in $[0,1]$, so together they can move the reward by at most $\sum_{j>d}\varepsilon_j$.
4. The tier-$d$ difference outweighs every lower tier at once exactly when

$$\sum_{j>d}\varepsilon_j<\varepsilon_d\,(1-2e_d)\,\delta_d .$$

5. With the last tier's $\varepsilon$ set to 1, the least weight that meets it is $\sum_{j>d}\varepsilon_j/((1-2e_d)\delta_d)$; the inequality is strict, so the script scales it by a 5% margin. `check-spec.py weights` prints each $\varepsilon_d$ beside the $e_d$ and $\delta_d$ it came from; a spec never writes one.

At $e_d=\tfrac12$ the factor $1-2e_d$ is 0: a verdict that is a coin flip carries no order, so no weight can rescue it. A high $e_d$ on a top tier makes the lower weights tiny; rewrite its criteria to be more concrete or program-checked rather than move the tier down.

## Mask

A masked tier that scores below its pass mark sets every lower tier to 0. Use it only when differences among failing answers have no value. A group of $G$ answers whose pass chance is $p$ gets no signal from the masked tier with chance $p^G+(1-p)^G$; `check-spec.py` warns above one half.

## Pairwise tier

An optional last tier scores quality no criterion captures: an answer's share of its group it beats side by side. It is last because nothing it measures is written down, so it may only order what the criteria tie.

## Judge and reliability

The judge grades the whole rubric in one call. A judge's verdicts are trusted only as far as they agree, with each other across runs and with people. Krippendorff's alpha measures that agreement per criterion; his bar for drawing conclusions is 0.800, 0.667 for tentative ones (*Content Analysis*, 2nd ed., 2004, p. 241). A criterion below the bar is rewritten, never reweighted. LLM judges favour a position, a longer answer and their own style (Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", NeurIPS 2023, arXiv:2306.05685); biases within one tier add up, and the tier condition does not remove them, so calibration measures them by perturbation. Checklist rubrics as rewards beat Likert-scale judges in training and narrow the gap between judge sizes (Gunjal et al., "Rubrics as Rewards", arXiv:2507.17746, 2025), which is why each criterion is one binary check.
