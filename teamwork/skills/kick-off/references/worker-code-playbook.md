# Code

1. Write the failing test or probe first; keep its output on main.
2. Run the repository's or plugin's tests; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
3. A hook, monitor, start script or service: probe the live copy in a new session or on its host, never only its fixture.
