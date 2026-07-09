---
name: gws
description: "Google Workspace CLI — interact with Drive, Sheets, Docs, Slides, Forms, and Tasks from the terminal using the `gws` command. Use this skill whenever the user wants to read, write, list, upload, or manage any Google Workspace content (spreadsheets, documents, presentations, forms, tasks, or Drive files), even if they don't mention `gws` by name. Also use when the user mentions a Google Sheet URL, a spreadsheet ID, or asks to pull data from Google Sheets."
---

# Google Workspace CLI

Unified reference for the `gws` command-line tool. Covers authentication, global flags, and all enabled Google Workspace products.

## How to use this skill

This skill has a main section (below) for auth, flags, and general patterns, plus per-product reference files in `references/`. Read only the reference file you need for the current task:

| Product | Reference | When to read |
|---------|-----------|--------------|
| Drive | `references/drive.md` | Files, folders, shared drives, uploads, permissions |
| Sheets | `references/sheets.md` | Spreadsheets — read, append, update, delete rows, clear cells, tab-targeted writes |
| Docs | `references/docs.md` | Google Docs — read, create, append text |
| Slides | `references/slides.md` | Google Slides — presentations, pages |
| Forms | `references/forms.md` | Google Forms — create, read, responses |
| Tasks | `references/tasks.md` | Google Tasks — task lists, manage tasks |

## Installation

The `gws` binary must be on `$PATH`. Install via npm:

```bash
npm install -g @googleworkspace/cli
```

## Authentication

```bash
gws auth setup                 # one-time: creates GCP project, enables APIs, logs in (needs gcloud)
gws auth login                 # subsequent OAuth login
gws auth login -s drive,sheets # limit scopes (see gotcha below)

# Service Account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

Unverified (testing-mode) OAuth apps cap consent at ~25 scopes, so the `recommended` preset fails. When login fails on scopes, retry with `-s` listing only the services you need.

## CLI Syntax

```bash
gws <service> <resource> [sub-resource] <method> [flags]
```

## Global Flags

| Flag | Description |
|------|-------------|
| `--format <FORMAT>` | Output format: `json` (default), `table`, `yaml`, `csv` |
| `--dry-run` | Validate locally without calling the API |
| `--sanitize <TEMPLATE>` | Screen responses through Model Armor |

## Method Flags

| Flag | Description |
|------|-------------|
| `--params '{"key": "val"}'` | URL/query parameters |
| `--json '{"key": "val"}'` | Request body |
| `-o, --output <PATH>` | Save binary responses to file |
| `--upload <PATH>` | Upload file content (multipart) |
| `--page-all` | Auto-paginate (NDJSON output) |
| `--page-limit <N>` | Max pages when using --page-all (default: 10) |
| `--page-delay <MS>` | Delay between pages in ms (default: 100) |

## Helper Commands

Some services ship hand-crafted `+` helpers alongside the Discovery-generated API surface. The `+` prefix keeps them distinct from generated method names. They wrap common tasks with friendlier flags — prefer them over the raw API for these actions. Run `gws <service> --help` to see helpers and API methods together.

| Command | Description | Example |
|---------|-------------|---------|
| `drive +upload` | Upload a file with automatic metadata | `gws drive +upload ./report.pdf --name "Q1 Report"` |
| `sheets +read` | Read values from a spreadsheet | `gws sheets +read --spreadsheet ID --range "Sheet1!A1:D10"` |
| `sheets +append` | Append a row to a spreadsheet | `gws sheets +append --spreadsheet ID --values "Alice,95"` |
| `docs +write` | Append text to a document | `gws docs +write --document ID --text "New line"` |

Slides, Forms, and Tasks have no helpers — use their API resources directly.

## Discovering Commands

Before calling any API method, inspect it to see required params, types, and defaults:

```bash
gws <service> --help
gws schema <service>.<resource>.<method>
```

Use `gws schema` output to build your `--params` and `--json` flags.

## Exit Codes

Branch on the exit code to react to failures without parsing error text:

| Code | Meaning | Typical fix |
|------|---------|-------------|
| 0 | Success | — |
| 1 | API error (Google 4xx/5xx) | Inspect the JSON error; often bad IDs/params or a disabled API |
| 2 | Auth error | Re-run `gws auth login` |
| 3 | Validation error | Fix arguments/flags (unknown service, bad flag) |
| 4 | Discovery error | Could not fetch the API schema; retry |
| 5 | Internal error | Unexpected failure |

On a code-1 `accessNotConfigured` error, the required Google API isn't enabled for the project — open the `enable_url` from the error JSON, enable it, wait ~10s, retry.

## Security Rules

- Never output secrets (API keys, tokens) directly
- Confirm with the user before executing write/delete commands
- Prefer `--dry-run` for destructive operations

## Shell Tips

- **zsh `!` expansion:** Sheet ranges like `Sheet1!A1` contain `!` which zsh interprets as history expansion. Use double quotes instead of single quotes:
  ```bash
  # Wrong — zsh will mangle the !
  gws sheets +read --spreadsheet ID --range 'Sheet1!A1:D10'

  # Correct
  gws sheets +read --spreadsheet ID --range "Sheet1!A1:D10"
  ```
- **JSON with double quotes:** Wrap `--params` and `--json` values in single quotes so the shell doesn't interpret the inner double quotes:
  ```bash
  gws drive files list --params '{"pageSize": 5}'
  ```
