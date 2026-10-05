# Reddit Obsidian-as-Memory Approach (source of this design)

Source: https://www.reddit.com/r/hermesagent/comments/1stz6gd/how_i_use_obsidian_as_the_longterm_memory/ (u/Jonathan_Rivera, ~1mo before 2026-08-30)

## Three-Tier Memory System

- Tier 1 — Hot Memory: injected every turn (~6-9K chars). Prefs, active projects, recent corrections, procedural quirks. Promote out when full (~67% capacity).
- Tier 2 — Vault Living Files: stable reference read on-demand (environment configs, operational context, known failure patterns).
- Tier 3 — Daily Notes: dated note per day, searchable timeline of decisions and actions.

## Morning Briefing Pipeline (their setup, weekday)

- 06:50 — Collection cron: fetch Todoist tasks by project, Google Calendar events (filter noise), create/update Daily/YYYY-MM-DD.md with Tasks/Schedule/Log/Wins/Context sections.
- 07:00 — Delivery cron: read cached data, deliver formatted briefing to Telegram (bullets, overdue count).

## Finance Briefing (their setup, 09:00)

- Navigate Yahoo Finance for tracked tickers; extract price/change/headlines; sentiment classify (bullish/neutral/bearish); summary table to Telegram.

## Vault Structure (original)

```
Vault/
├── Daily/                    # YYYY-MM-DD.md
├── System/Assistant/
│   ├── context.md        # operations, health, family overview
│   ├── preferences.md    # communication style, delivery rules
│   └── environment.md    # hardware, services, known issues
├── Work/                   # per-business folders
├── Personal/               # Finance/, Health/
├── People/                 # contacts MOC
└── Inbox/                  # unclassified incoming
```

## Filing Rules (from the post)

- Operational events -> daily log
- System issues -> separate troubleshooting log
- Learned corrections -> hot memory (or vault if stable)
- Recurring workflows -> skill files

## Why Obsidian (their stated reasons)

1. Plain text markdown — AI reads/writes without plugins or APIs.
2. Backlinks + graph view — connections visible and navigable.
3. Searchable history — every daily note timestamped.
4. Works without the AI — still a full PKM system, no vendor lock-in.

## Adaptations Made for This Setup

- Vault path: /home/machine0/wiki (WIKI_PATH already set in the Hermes env config).
- Hot-memory promotion rule (67%) NOT adopted literally — Hermes memory model differs; intent only.
- Mnemosyne remains the primary durable-fact store; vault is timeline + operational docs.
- llm-wiki (bundled) kept in reserve as a research layer on the same directory.
- No cloud sync/obsidian-headless needed yet (single machine); revisit if multi-device.

## Starter Template Highlights (their Part 1 prompt)

- Vault access rules: daily notes append-only with frontmatter `date/type/tags`; sections Tasks->Schedule->Log->Wins->Context; tasks as `- [ ] (p2/p3/p4)`; log `- HH:MM — what happened`; wins `✅`.
- Content routing block: "log it" -> route by type (see SKILL.md Content Routing).
- Hygiene: wikilinks `[[People/Name]]`, flag orphans, never delete without user confirmation, absolute paths.
- Persona files: context.md / preferences.md / environment.md (see templates/scaffold-vault.sh for full contents).
- Hot memory files: MEMORY.md (personal notes, § separator, compact) / USER.md (who the user is).
