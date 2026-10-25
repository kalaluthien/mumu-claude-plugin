# computed-plot: a curve or points drawn from the model's own numbers, so the figure is evidence
family: visual
elements: axes, series, alt

## Why it works
Values come from a script, so the figure and the prose cannot disagree (fig-data). The reader reads position along a common scale, the channel that is most accurate (fig-channel).
The figure shows its uncertainty or counts when an estimate is plotted (fig-uncertainty); a threshold or crossing is marked and named in the prose.

## Parts
- axes: `x`, `y` with `field`, `label`, `unit`, `scale`; bars start at zero (fig-scale).
- series: data or `compute: figs/U.py:fn`; direct labels on lines (fig-label); `uncertainty` as interval or counted dots.
- alt: chart type, variables, the take-away.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-per-contrast (u-percept): contrast ratio against the grey value of text on a light and a dark background. Essential content: the threshold 4.5:1 is crossed at 118 on white and 137 on a dark ground.
- fig-human-fitts-curve (u-human): time to press a target against its width for a hand with a=0.1 s, b=0.15 s/bit at 600 px. Essential content: time rises by an even step each time the width halves.
- fig-idm-spread (u-idiom): seed spread, a 95% interval for the mean and the standard error on one axis. Essential content: the three measure different things at 0.40.
Elsewhere: Savings against months for two fee plans; the lines cross at month 14, labelled at the crossing.
# Compose and vary
- Combines with: estimate, frames (the plot grows), demo.
- Vary: choose the relationship the unit claims; plot only that, with the threshold the card will ask about.
- Usual failure: dual axes, a legend for ≤5 series, no interval on an estimate (axes check).

## Seed
Does the figure compute its numbers from the script that the prose cites, with units on both axes?
