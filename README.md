# jerome-skills

My personal collection of agent skills.

Each skill lives in its own directory under `skills/` and is defined by a `SKILL.md` file. A skill packages reusable instructions (and optionally supporting scripts and resources) that an AI coding agent can load on demand to perform a specific task.

---

## Skills

| Skill | Description |
| --- | --- |
| [`bro`](skills/bro/SKILL.md) | Restate the last message in plain human language, with no jargon. |
| [`caveman`](skills/caveman/SKILL.md) | Ultra-compressed communication mode. Cuts output tokens ~65% by speaking like a smart caveman while keeping full technical accuracy. Intensity levels: lite, full, ultra. Manually invoked only. |
| [`jira-cli`](skills/jira-cli/SKILL.md) | Interact with Jira from the terminal via [`jira-cli`](https://github.com/ankitpokhrel/jira-cli) — view, search, create, edit, transition, comment, and manage epics/sprints. Agent-friendly (plain output, non-interactive) and covers Cloud and Server/Data Center auth. |
