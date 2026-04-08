# Codex Customization In This Repo

This repository now follows the Codex customization model described in the official OpenAI Codex docs:

- `AGENTS.md` for durable project guidance
- repo-specific skills in `.agents/skills`

## What was added

### Root guidance

- `AGENTS.md`

Use this for repo-wide rules, routing, validation commands, and documentation expectations.

### Directory-specific guidance

- `src/AGENTS.md`
- `static/AGENTS.md`

These keep backend and frontend instructions close to where they apply.

### Repo skills

- `.agents/skills/manual-qa/SKILL.md`
- `.agents/skills/release-version/SKILL.md`

These cover the two repeatable workflows that happen often in this project:

- manual QA / regression planning
- versioning / release publication

## How to use this in future Codex sessions

Ask Codex to start by reading:

1. `AGENTS.md`
2. the relevant directory `AGENTS.md`
3. the relevant skill when the task matches it

Examples:

- "Use the repo guidance and update the UI safely."
- "Use the `manual-qa` skill and refresh the test checklist."
- "Use the `release-version` skill and publish `v1.1.1`."

## Notes

- Keep `AGENTS.md` small and high-signal.
- When the agent makes the same repo-specific mistake twice, add or refine a rule in the nearest `AGENTS.md`.
- When a workflow becomes repetitive, promote it into a repo skill.
