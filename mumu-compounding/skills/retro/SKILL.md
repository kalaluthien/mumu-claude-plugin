---
name: retro
description: Use when writing or editing a SKILL.md, an agents/*.md file, a script, or a hook of the harness or of git, and when something learned should outlive the session - a memory, learning turned on, a stop's harvest. Not for settings.json permissions or env (update-config).
user-invocable: false
---

# retro

## Arm

Run this first, every time but one case, silently; tell the owner only when it fails:

```sh
"${CLAUDE_PLUGIN_ROOT}/scripts/takeaway.py" arm "${CLAUDE_PLUGIN_DATA}"
```

To write or edit a skill, an agent or a hook with no lesson behind it, skip
Arm and Harvest and follow the playbook its row below links.

## Route

Match one row, open its playbook, and copy its steps verbatim into the todo
list, a step not done staying as `skip: <reason>`; a lesson that fits a later
row belongs there.

| when | playbook |
| --- | --- |
| one lesson to keep, handed over or found by a harvest: "remember this", a fact, a trap, the user's preference, a procedure that worked once; a stop's harvest, learning turned on, going over the work for what should outlive the session | [references/lesson.md](references/lesson.md) |
| writing or editing a SKILL.md or an `agents/*.md` file; a lesson that is a procedure auto-memory already holds and has now worked again, or how a delegate should work | [references/skill-authoring.md](references/skill-authoring.md) |
| writing or editing a hook or its script; a lesson that is something a check could decide | [references/hook-authoring.md](references/hook-authoring.md) |
| nothing above fits | [references/lesson.md](references/lesson.md) |

File nothing the repository or its history already states.
