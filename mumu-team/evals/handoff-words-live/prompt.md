---
append_system_prompt: "Facts this session already gathered, still current: the project is kalaluthien/mumu-claude-plugin, checkout /Users/hyungmokim/workspace/plugins, and it has scope: labels, one per plugin folder; herdr agent list shows mumu-paperwork-lead live, agent_status idle."
max_turns: 8
timeout_seconds: 240
allowed_tools: [Skill, Read, Glob, Grep, Bash]
runs: 3
---

/mumu-team:handoff mumu-paperwork 플러그인의 문서 작성 체계를 토큰 비용과 결과 품질 관점에서 레드팀 검토해서 채팅으로 알려 줘
