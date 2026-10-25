# Contributing

- **Outside pull requests are not accepted**: the owner's sessions run these plugins straight from `main`, so only the owner's sessions change the code; a pull request from anyone else is closed unread.
- **Issues are welcome**: a bug, a question or an idea goes in an issue.
- **Issue first**: open an issue that says what should change and why; the owner's sessions turn it into a change.
- **Comments are discussion**: the team's sessions act only on the owner's and collaborators' `BLOCKED:` and `DECIDED:` comments, so yours never assign or answer work.
- **Security**: a vulnerability goes through [SECURITY.md](SECURITY.md), never an issue.
- **Rules**: [AGENTS.md](AGENTS.md) holds the rules every change follows.

## Local clone install

This is the way the owner of this repository runs the plugins; the marketplace install in the [README](README.md#installation) is the way for everyone else. A clone makes a merged change reach your sessions after a `git pull`, with no reinstall.

1. Clone the repository:

   ```
   git clone https://github.com/kalaluthien/mumu-claude-plugin ~/workspace/plugins
   ```

2. Add the clone as a marketplace, in `~/.claude/settings.json`:

   ```json
   {
     "extraKnownMarketplaces": {
       "mumu-claude-plugin": {
         "source": { "source": "directory", "path": "/Users/<you>/workspace/plugins" }
       }
     }
   }
   ```

3. Enable the plugins per project, in the project's git-ignored `.claude/settings.local.json`:

   ```json
   {
     "enabledPlugins": {
       "teamwork@mumu-claude-plugin": true,
       "homework@mumu-claude-plugin": true,
       "paperwork@mumu-claude-plugin": true
     }
   }
   ```

A merged change reaches a running session as [Repository in AGENTS.md](AGENTS.md#repository) says.
