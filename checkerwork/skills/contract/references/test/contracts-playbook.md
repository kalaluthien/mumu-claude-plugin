# Contracts

A test drives the app as its user does and asserts a contract or a path, never a bare equality:

| a bare equality | a contract or a path |
| --- | --- |
| `add("")` returns `None` | every blank title (empty, spaces, a tab) exits non-zero with a message, and the stored list is unchanged |
| the refund call returns 200 | a refund reaches the payment gateway once, before the order reads refunded, and never for an unpaid order |

- An acceptance test drives the app as its user does (the CLI, the HTTP API, the screen: a screen in a browser, asserting what it shows); an integration test runs one module against its real infrastructure (the database, the filesystem, the network).
- A value rule - a threshold, a colour, a size - lives once as a named constant where the code reads it, and its test states the literal: `isFlat(5.0f)`, never `isFlat(TOLERANCE)`.
- A rule the code breaks, when the change is not to fix it, is a code gap: file an issue quoting the check's command and failing output, and land the witness disabled, or the check `expect 1`, with `gap #<issue>` on its line; `verify.sh` counts each.
