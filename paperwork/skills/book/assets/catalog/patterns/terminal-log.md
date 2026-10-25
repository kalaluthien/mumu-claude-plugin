# terminal-log: monospaced output the reader scans line by line, with the line that decides drawn apart
family: visual
elements: raw, alt
differs: the exhibit is a stream of lines (output, errors, codes) whose order and channel matter. mock-screen is a drawn interface of parts; table is a grid; neither shows sequence of text lines
Hand markup: drawn with `raw` and `alt`; show the lines as the tool prints them.

## Why it works
Output that mixes streams or hides its result in noise teaches the reader what to look for. Showing the exact lines, with the deciding line marked, lets the text point at one of them. It prevents describing a log in words the reader cannot check.

## Parts
- raw: the lines in order, in monospace, with the deciding line drawn apart (a box or tone, not only colour).
- alt: names the tool, the stream and the line the point rests on.

## Examples
Source book: the UX book (ids are its card or figure ids, with the unit in parentheses).
- fig-plat-cli-streams (u-platform): progress, result and error drawn first in one channel, then piped, split, given an exit code 3 and a --json form. Essential content: a spinner piped into the next program breaks a script that reads the result; separate channels and a code fix it.
- fig-plat-three (u-platform): one incident as a phone notification, a web page and a terminal output ending in an exit code. Essential content: the terminal form is read by a script as well as a person, so the code carries the outcome.
- fig-str-log-demo (u-structure): a log panel opened from a map point, with its label and message text. Essential content: the raw line is the evidence the map position is checked against.
Elsewhere: A build log with warnings above one failing step, the failing line boxed and its exit code shown.

## Compose and vary
- Combines with: frames (output at successive moments), annotated-exhibit (numbered lines), read-exhibit (a card asks about the log).
- Vary: change the tool (build, deploy, query) and the stream (output, error, exit code); keep the lines real, not paraphrased.
- Usual failure: a decorative terminal with invented output that no line of the text refers to.

## Seed
Which single line must the reader find, and is it drawn apart?
