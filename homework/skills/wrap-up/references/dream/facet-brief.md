# Facet brief

You read digests of Claude Code sessions and write one facet per digest: what the owner objected to (friction), and what the owner's words show of how they want the agent to work with them (habits). A digest's lines are `[OWNER L<n>]`, the owner's own words at transcript line `<n>`; `[ANSWER L<n>]`, the owner's answer to a question the agent asked, with its options, the recommended one marked in its name; `[Agent L<n>]`, the agent's text; and `[Tool: <name>]`, a tool call.

## Steps

1. For each digest path you are given, `Read` it, then `Write` `<facets>/<session>.json`, where `<facets>` is the folder you are given and `<session>` is the digest's file name without `.txt`, holding only this JSON, a habit's `kind` one of `"instruct"`, `"ask"`, `"answer"`, `"feedback"` or `"rule"`:

   ```json
   {
     "friction": [
       {"quote": "the owner's words, verbatim, from one [OWNER] or [ANSWER] line", "line": 123,
        "what_went_wrong": "one line: what the agent did or said that the owner objected to"}
     ],
     "habits": [
       {"kind": "ask", "quote": "the owner's words, verbatim, from one [OWNER] or [ANSWER] line", "line": 123,
        "before": "one line: what the agent did, said or asked just before",
        "preference": "one line: what the agent should do the first time, as `when <situation>, <do>`"}
     ]
   }
   ```

2. Reply with one line: how many facets you wrote.

## Rules

- **Friction**: an owner line or answer that objects to a result or an action already done: wrong, missing, too narrow, beyond the request, unchecked, or against a rule. A new request, a new instruction, a question or an approval is not friction.
- **Habit kinds**:
  - `instruct`: a request the agent read otherwise than the owner meant, as a later owner line shows, or a short form the owner uses for a request; its `quote` is the request line, never the later line, which is friction when it objects;
  - `ask`: the owner asks what something the agent wrote or made means, or why, such as a term, a name, a number or a choice;
  - `answer`: an `[ANSWER]` line where the owner did not pick the recommended option, or wrote their own words;
  - `feedback`: the owner corrects or approves how the agent explained, proposed, asked or reported;
  - `rule`: a rule the owner set for future work, such as "always …" or "never …"; not a one-off request.
- **Boundary**: a line that objects to a result or action already done is friction, not a habit, even when it also sets a rule; an objection to a proposal, an option, a question or an explanation, such as its cost or its words, is `feedback`; a plain pick of the recommended option, a new request read right and a thanks are neither.
- **No guess**: for a quote under 4 words, name the agent's preceding action in `what_went_wrong` or `before` only when the digest shows it; a `preference` follows from the quote and `before` alone.
- **Line**: `line` is the `<n>` of that `[OWNER L<n>]` or `[ANSWER L<n>]` line.
- **Empty**: an empty list for a kind with none, and a file for every digest, even `{"friction": [], "habits": []}`.
