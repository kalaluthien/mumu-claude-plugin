---
max_turns: 15
timeout_seconds: 240
allowed_tools: [Skill, Read, Bash]
runs: 3
---

Remember this for future sessions: in this project the test suite must be run with `make check`, never `make test`, because `make test` skips the integration tests.
