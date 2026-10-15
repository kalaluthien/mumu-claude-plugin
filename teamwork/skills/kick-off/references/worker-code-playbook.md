# Code

1. Write the failing test or probe first, by the repository's test rules; where they keep none, keep it in the scratchpad, never committed, and run it by [run-on-refs.py](../scripts/run-on-refs.py) `'<command>' origin/<default> <head sha>` until it prints that it fails on main and passes at the head; quote the command in the criterion, so the judge reruns it. A plugin's test runs in its copy: the command copies it into the plugin's folder, then runs `claude plugin test <plugin>`.
2. Run the repository's or plugin's tests; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
3. A hook, monitor, start script or service: probe the live copy in a new session or on its host, never only its fixture; for a change in looks, the owner checks how it looks on the live pane or page.
