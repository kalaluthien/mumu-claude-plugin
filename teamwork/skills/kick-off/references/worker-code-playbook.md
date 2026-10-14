# Code

1. Write the failing test or probe first and keep its output on main.
2. Implement until each criterion passes at head; run the repository's or the plugin's tests; for an eval case, `claude plugin eval ./<plugin>` and read the failing transcript.
3. A hook, monitor, start script or service: probe the live copy in a new session or on its host, never only its fixture.
