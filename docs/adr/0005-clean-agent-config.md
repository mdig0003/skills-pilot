# The agent uses the experimenter's login, isolated by flags

Runs use the experimenter's normal Claude Code login, launched with `--setting-sources project --strict-mcp-config --no-chrome` and an explicit `--effort high`. The experimenter's user settings enable plugins such as superpowers, whose SessionStart hook injects emphatic "you ABSOLUTELY MUST invoke the skill" text. That text would raise skill loading and add emphatic wording to the L2 condition. Dropping the user setting source stops those plugins and hooks from loading. On 2026-09-30 a test session with these flags showed no superpowers text, no hook events, no MCP servers and none of the user's personal skills. Only `quixbugs-fix` and Claude Code's built-in skills were visible.

A separate, empty `CLAUDE_CONFIG_DIR` with its own token was tried first and rejected. `setup-token` needs an interactive browser login, and the flags already give the same isolation. `--bare` was rejected because it only resolves skills via `/skill-name`, which could prevent the agent from discovering the skill on its own.

## Consequences

- Each Run's `init` event (visible skills, plugins, MCP servers) is saved in its record. A change in the account's built-in skills would show up there.
- Claude Code's built-in skills (e.g. `verify`, `debug`) are visible in both conditions and could compete with `quixbugs-fix`.
