# small-multiples: the same case at several settings in a row of panels with one shared scale
family: visual
elements: panels, axes, alt

## Why it works
Panels drawn at the same size and scale let the eye compare by position, so the difference is the data and not the drawing (fig-scale, fig-channel). It prevents overlaid series that need a legend to decode (fig-label).
Each panel is one case; the one thing that varies between panels is named in the caption.

## Parts
- panels: one per case; `domain` is declared once and shared by all.
- axes: unit on each axis; panels share limits, or say so on each panel.
- alt: names the variable that changes across panels and the take-away.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-cmd-styles (u-command): one intent shown in five screens (menu, form, command line, plain language, direct move). Essential content: the same goal at five costs of expressing it.
- fig-idm-six-panels (u-idiom): six learning-rate panels on one vertical axis 0 to 3, one of them diverging. Essential content: a shared scale makes the endpoints 0.45, 0.41, 0.43, 0.44, 0.47 comparable and the divergence visible.
- fig-idm-multiples (u-idiom): three loss curves drawn on one axis, then as three panels on a shared scale. Essential content: separate panels remove the colour matching and keep the comparison.
Elsewhere: Four months of a clinic's waiting times in four panels on one shared time-axis.
# Compose and vary
- Combines with: computed-plot (each panel is a plot), mock-screen (panels are screens), annotated-exhibit.
- Vary: choose the one varied setting; panel count 3 to 6; keep order meaningful (time, size).
- Usual failure: panels autoscale, so equal heights stand for different values (fig-scale).

## Seed
Do all panels share one scale and differ in exactly the one named setting?
