# Both conditions install to one neutral skill path

The original plan placed the conditions at `.claude/skills/l2_permissive.md` and `.claude/skills/l5_emphatic.md`. Claude Code only discovers skills at `.claude/skills/<name>/SKILL.md`, and a skill's name and description are always in the agent's context. So each Run instead installs one condition to `pilot/.claude/skills/quixbugs-fix/SKILL.md`, with frontmatter byte-identical across conditions. This keeps the skills loadable, stops the skill name from revealing the condition, and confines the manipulation to the skill body. The condition sources live in `pilot/conditions/l2_permissive/SKILL.md` and `pilot/conditions/l5_emphatic/SKILL.md`.

## Consequences

- The body is read only if the agent invokes the skill, so `skill_loaded` is recorded per Run. Results are reported over all Runs and over loaded-only Runs.
