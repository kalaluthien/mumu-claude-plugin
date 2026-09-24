# Transcripts

A Claude Code session's transcript is `~/.claude/projects/<project>/<session>.jsonl`, one record per line. Before adding a hook or a log to label something, read it here: every turn is already recorded.

## Selecting records

- A person's prompt, or one sent by `herdr agent prompt`, has `origin.kind` `human`; another session's has `peer`; hook and cron feedback is `isMeta: true`; a prompt sent mid-turn is an `attachment` of type `queued_command`.
- A compaction is `type: system`, `subtype: compact_boundary`, with `compactMetadata.preTokens` and `postTokens`; a session's name is its last `agent-name` record.
- Records are not in time order within a file, since a resume appends: select by `timestamp`. Count sessions by `sessionId`, not by file.
- A subagent writes `<session>/subagents/agent-<id>.jsonl`, its first user record the brief, beside `agent-<id>.meta.json` with its `agentType`, `description` and `spawnDepth`.
- To find which files a session read, match their content in `tool_result`s, not their paths. Thinking blocks rarely carry text: read `text` and `tool_use`.
- Files expire after `cleanupPeriodDays` (30 by default): a zero count means not in this window.

## Counting tokens

- One API message spans several records, each repeating its `usage`: key on `message.id`, never sum records.
- `output_tokens` is a placeholder until a record whose `usage.iterations` is non-empty, so take the maximum per message id, and a subagent's output as a floor; input and cache fields are exact on every record.
- A limit banner or API error is an assistant record with `model: "<synthetic>"`: skip it. The figure the Agent tool reports is its last turn's context, not the round's spend.
