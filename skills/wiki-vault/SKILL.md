---
name: wiki-vault
description: "Save, document, log, note, or query the wiki vault. Trigger whenever the user says save/document this, log/note it, look up/query/read/write anything in the vault, wiki, or vault — the persistent markdown knowledge base at $WIKI_PATH (Daily/ timeline, System/Assistant/ reference, People/, Work/, Personal/)."
version: 2.1.0
author: Curator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [vault, wiki, obsidian, notes, memory, daily-notes, second-brain]
    category: productivity
---

# Wiki Vault

The persistent markdown knowledge base at `$WIKI_PATH` (currently `/home/machine0/wiki`).
Plain markdown the agent reads and writes directly; open in Obsidian for graph view, Dataview, backlinks.

**The vault is the timeline.** It records what happened and what was decided, day by day, plus
operational reference. It is *not* a durable-fact store — that's Mnemosyne's job.

## Memory division of labor

A fact lives in exactly **one layer**. Do not copy facts across layers — a fact in two places drifts.
When in doubt, route durable facts to Mnemosyne; the vault keeps only what its own layer holds.

| Layer | What lives there | Where |
|---|---|---|
| Hot memory | active prefs, corrections, quirks | Hermes memory (MEMORY.md/USER.md) + Mnemosyne |
| Durable facts | stable identity/profile facts | Mnemosyne |
| Vault Tier 2 | operational state, environment, stable reference | `System/Assistant/*.md` |
| Vault Tier 3 | daily timeline | `Daily/YYYY-MM-DD.md` |

"Save it / log it / document this" means the timeline (Tier 3) — never a durable fact without first
checking Mnemosyne.

## Vault structure

```
<vault>/
├── Daily/                    # YYYY-MM-DD.md append-only daily notes (the timeline)
├── System/Assistant/
│   ├── context.md           # family/work overview — read first for advice
│   ├── preferences.md       # how things are done, delivery rules
│   ├── environment.md       # hardware, services, key paths, known issues
│   └── logs/issues-fixes-log.md   # symptom → root cause → fix → status
├── Work/                    # work documents, reports
├── Personal/                # projects, personal tracking
├── People/                  # people MOC + per-person notes
├── Inbox/                   # unclassified incoming
├── Raw/                      # research reserves (not for daily use): Articles/, Papers/, Transcripts/, Assets/
├── Entities/
├── Concepts/
├── Comparisons/
└── Queries/
```

## Naming convention

Top-level folders stay Title-Case single word. Sub-topic folders and files use kebab-case lowercase. Daily notes keep `Daily/YYYY-MM-DD.md`. Example: `Personal/pregnancy/anomaly-scan-10-aug-2026.md`.

## Content routing (the core operation)

When the user says **save it / document this / log it / note it / write that down** — or asks to **look
up / query / read** anything in the vault, wiki, or vault — or when an event, decision, or fix happens —
route it by type. Completion: every event you witnessed or were told about lands in exactly one
destination.

| What happened | Where it goes |
|---|---|
| Operational events (meetings, calls, decisions, errands) | `Daily/YYYY-MM-DD.md` → ## Log |
| System issues / fixes | `System/Assistant/logs/issues-fixes-log.md` (symptom → root cause → fix → status) |
| Learned corrections / preferences | Mnemosyne (durable) — or a vault living file if it's stable reference |
| Recurring workflows | a skill file — never the vault |
| Unclassified incoming | `Inbox/` until classified; file it in the same session when possible |

## Daily notes

- Create `Daily/YYYY-MM-DD.md` at session start if missing (or via the morning check-in).
- Frontmatter: `date: YYYY-MM-DD`, `type: daily`, `tags: [daily]`.
- Sections in order: `## Tasks`, `## Schedule`, `## Log`, `## Wins`, `## Context`.
- Log entries: `- HH:MM — what happened` — use the real clock time, never a placeholder.
- Tasks: `- [ ] desc (p2/p3/p4)`; Wins: `- ✅ desc`.
- **Append-only**: daily notes grow. A correction is a new log line, never an edit to an old one.

## Reading the vault

- "What happened on <date>?" → read `Daily/<date>.md` (and scan `log.md`-style entries if needed).
- "What does the assistant know about <area>?" → read `System/Assistant/context.md`
  first, then the relevant living file.
- Use `[[wikilinks]]` to connect every person, decision, and file mentioned in a daily note;
  flag orphan notes (no inbound links) unprompted.

## Backlinks (mandatory)

Every new or edited note must leave no relation unlinked. Link with `[[wikilinks]]` in both
directions whenever any of these is true: a new relation exists between two documents, an
existing relation is extended, or any relation between two documents is touched at all.
Concretely: when you create a note, add its `[[link]]` to every related note and add their
`[[link]]`s back into the new note (a `Related:` line at the top works). When you edit a note
and the edit creates or extends a relation, update the other side in the same session. Before
finishing, verify both sides resolve to real files and no new orphan is left.

## Guardrails

- **Deletions only after explicit user confirmation.** Otherwise leave content in place and
  supersede it — the user reviews before destructive actions.
- **Research folders are reserve.** `Raw/`, `Entities/`, `Concepts/`, `Comparisons/`, `Queries/` (with `Raw/Articles|Papers|Transcripts|Assets/`) exist
  for a future research-ingest need; create pages there only when that need actually appears.
  The vault is operations-first; `llm-wiki` is the research layer and already points at this directory.
- **The architecture is settled.** Daily-notes pattern over llm-wiki, decided 2026-08-30. Do not
  re-open the debate without a new need; the reasoning is in `references/reddit-obsidian-memory-approach.md`
  and the daily log of that date.

## Scaffolding

If the vault is missing or needs re-scaffolding: run `templates/scaffold-vault.sh`
(defaults to `/home/machine0/wiki`; creates structure + core assistant files + today's daily note),
then verify with `ls <vault>/Daily/`.

## Support files

- `references/reddit-obsidian-memory-approach.md` — source design + adaptations.
- `templates/scaffold-vault.sh` — bash scaffold for structure + core assistant files.