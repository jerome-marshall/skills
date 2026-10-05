#!/usr/bin/env bash
# Scaffold the wiki vault (Obsidian-compatible markdown structure).
# Based on u/Jonathan_Rivera's Obsidian + AI Assistant starter template
# (https://www.reddit.com/r/hermesagent/comments/1stz6gd/), adapted for this setup.
# Default vault path matches $WIKI_PATH in the Hermes env config (/home/machine0/wiki).
set -euo pipefail

VAULT_PATH="${VAULT_PATH:-/home/machine0/wiki}"

mkdir -p "$VAULT_PATH"/{Daily,System/Assistant/logs,Work,Personal,People,Inbox}
# llm-wiki research layers (reserve — keep for future research-ingest needs)
mkdir -p "$VAULT_PATH"/{Raw/{Articles,Papers,Transcripts,Assets},Entities,Concepts,Comparisons,Queries}

cat > "$VAULT_PATH/System/Assistant/context.md" << 'EOF'
# Assistant — Context

Current life situation, health protocols, and active things to track.
Read when context matters for decisions or advice.

---

## Operations

- Describe your main work or business here
- Note any secondary projects or side operations

## Health

- Goals and baselines
- Any recurring protocols or reminders

## Family

- Key people and relationships
- Link to People/ folder for details

## Work Dependencies

- Who you wait on for approvals or sign-offs
- Blockers and their schedules

## Location & Timezone

- Home address (optional)
- Timezone: Asia/Kolkata (IST, UTC+05:30)

---

*Last updated: YYYY-MM-DD*
EOF

cat > "$VAULT_PATH/System/Assistant/preferences.md" << 'EOF'
# Assistant — Preferences

How you like things done. Read this when unsure about tone, format, or approach.

---

## Communication

- Concise, direct. Dry wit welcome. Never sycophantic.
- One clear sentence beats three hedged ones.
- When something is urgent, say so plainly.

## Operations Separation

- Keep work and personal clearly separated
- Never mix contexts without explicit labeling

## Agenda & Briefings

- Priority ordering: Due today > Active/P1 > Bills > Upcoming
- Morning brief: always read from actual daily note. Never show template placeholders.

## Task Management

- Every task completion paired with a log entry in daily note
- EOD wrap-ups sourced from daily note log

## Delivery Preferences

- Where should scheduled summaries go? (email, messaging app, etc.)

## Session Style

- Continuous same-session conversations or fresh starts each day?

---

*Last updated: YYYY-MM-DD*
EOF

cat > "$VAULT_PATH/System/Assistant/environment.md" << 'EOF'
# Assistant — Environment & Technical Setup

Hardware, tools, quirks, and gotchas. Read when troubleshooting or configuring.

---

## Hardware

- Primary machine and specs
- Any secondary devices or servers

## Services

- Key services, ports, and endpoints
- API configurations

## Key Paths

 Row | Path
-----|------
 Vault | /home/machine0/wiki
 Daily notes | /home/machine0/wiki/Daily/YYYY-MM-DD.md

## Known Issues & Patterns

- Document any recurring problems and their fixes here

---

*Last updated: YYYY-MM-DD*
EOF

cat > "$VAULT_PATH/System/Assistant/logs/issues-fixes-log.md" << 'EOF'
# Issues & Fixes Log

Append-only record of system issues, technical failures, and their resolutions.

Format: Symptom → Root Cause → Fix → Status

---

*No entries yet.*
EOF

cat > "$VAULT_PATH/People/MOC.md" << 'EOF'
# People — Map of Content

Contacts and relationships. Each person gets their own note in this folder.

---

## Family

- [[People/Jerome]] — user of this assistant; husband of Venolia; office 3 days/week, WFH 2.
- [[People/Venolia]] — wife (formal names: Avantikka / Allyn); health and pregnancy details in System/Assistant/context.md.
- Parents (both sides) — nearby (1–2 km); add individual notes as they come up.
- Sister-in-law — visiting to help; add note when known.

## Work

- [[People/Colleague]] — key colleagues

## Personal

- [[People/Friend]] — friends and acquaintances

---

*Last updated: YYYY-MM-DD*
EOF

# Create today's daily note (skipped if it already exists)
TODAY=$(date +%F)
if [ ! -f "$VAULT_PATH/Daily/$TODAY.md" ]; then
cat > "$VAULT_PATH/Daily/$TODAY.md" << EOF
---
date: $TODAY
type: daily
tags: [daily]
---

## Tasks — $TODAY

### Work

### Personal

### Overdue

## Schedule

## Log

## Wins

## Context
EOF
fi

echo "Vault scaffolded at $VAULT_PATH"
