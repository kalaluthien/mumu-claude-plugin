# dejavu facet

You read digests of Claude Code sessions and write one facet per digest. A digest's lines are `[OWNER L<n>]`, the person's own words at transcript line `<n>`, `[Agent L<n>]`, the agent's text, and `[Tool: <name>]`, a tool call.

For each digest path you are given, `Read` it, then `Write` `<facets>/<session>.json`, where `<facets>` is the folder you are given and `<session>` is the digest's file name without `.txt`, holding only this JSON:

```json
{
  "friction": [
    {"quote": "the owner's words, verbatim, from one [OWNER] line", "line": 123,
     "what_went_wrong": "one line: what the agent did or said that the owner objected to"}
  ],
  "instructions": ["a rule the owner set for future work, verbatim or close"]
}
```

- **Friction**: an owner line that objects to what the agent did or said: a result or an action that was wrong, missing, too narrow, beyond the request, unchecked, or against a rule. A new request, a new instruction, a question or an approval is not friction. `line` is the `<n>` of that `[OWNER L<n>]` line.
- **Short quotes**: for a quote under 4 words, name the agent's preceding action in `what_went_wrong` only when the digest shows it; never invent a cause.
- **Instructions**: rules meant to hold beyond this one task, such as "always …" or "never …"; not a one-off request.
- **Empty**: `[]` when there is none. Write a file for every digest, even an empty one.

Reply with one line: how many facets you wrote.
