---
name: profile-bulk-sync
description: Bulk sync model/provider across all Hermes profiles.
version: 1.0.0
author: Tony (tech)
license: MIT
metadata:
  hermes:
    tags: [hermes, profiles, config, model, provider]
    related_skills: [hermes-agent]
---

# Profile Bulk Sync — fan-out model/provider changes to every Hermes profile

Use this when the user wants one model/provider change applied to **all** profiles, instead of `hermes -p <name> config set` one-by-one.

Profiles are isolated: each has `~/.hermes/profiles/<name>/config.yaml` + `.env` (default is `~/.hermes/` itself). There is no native `--all` flag. This skill is the fan-out.

## Steps

### 1. Discover profiles
Run:
```
hermes profile list
```
Completion: every profile ID collected. On this machine: `default`, `finance`, `health`, `tech` — but always discover dynamically (user may have added a 5th). Never hardcode the list.

### 2. Resolve target configuration from user request
Parse the user's request into:
- `model.default` (e.g. `anthropic/claude-sonnet-4`, `openai/gpt-4o`, `minimax/minimax-m3`)
- Provider-specific secrets: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `MINIMAX_API_KEY`, etc.
- Optional config.yaml keys: `model.provider`, `providers.<id>.base_url`, `model.reasoning_effort`, etc.
- Optional per-profile exceptions if user says "all except X uses Y"

If user says "use anthropic" but no key given, ask for the missing `ANTHROPIC_API_KEY`. If user gives a key without a model, ask which model to set.

Completion: target map is explicit: `KEY=VAL` list with no ambiguity.

Reference for provider→env mapping is in `references/provider-env-map.md`. Load it when resolving.

### 3. Preview plan and confirm (unless --yes)
Print a table:
```
Profile | current model | -> target model | keys to set
default | minimax/...   | -> anthropic/...| ANTHROPIC_API_KEY, model.default
finance | ... | -> ... | ...
```
Ask for confirmation if more than one profile or any secret is involved. Respect the user's standing rule: list first, then act after selection — for config updates, list the planned writes and wait for "go" unless user said dry-run or gave --yes.

Completion: user confirmed or --yes given; or dry-run requested so skip to step 5.

### 4. Apply fan-out
For each profile, run via `terminal`:
```
hermes -p <name> config set <KEY> <VAL>
```
`hermes config set` auto-routes: secrets -> `.env`, others -> `config.yaml`. Never hand-edit `config.yaml` (a stray indent breaks the gateway) and never `echo >> .env`.

- For default profile, `hermes -p default` and plain `hermes` are equivalent; prefer `hermes -p default` for clarity.
- Run sequentially and capture exit_code. If exit says "managed by administrator (/etc/hermes/...)" -> report as blocked, do not retry.
- If `hermes model` OAuth flow is needed (Nous Portal, Anthropic OAuth, Codex), tell user: OAuth cannot be fanned-out non-interactively; run `hermes -p <name> model` per profile interactively.

Completion: `hermes -p <name> config set` succeeded for every requested KEY on every profile; failures collected with reason.

### 5. Verify
For each profile:
```
hermes -p <name> config get model
hermes -p <name> config get model.default
```
And optionally `hermes -p <name> doctor` if user wants health check. Print before/after diff.

Completion: verification output shows target model on every profile; mismatches flagged.

## New-profile defaults (always apply)
Any new Hermes profile gets clean cron output by default:
- `hermes -p <name> config set cron.wrap_response false`
- User preference (2026-09-06): no `Cronjob Response / job_id / -----` header or `To stop or manage...` footer on any cron in any profile.

## Branches

- **Bulk model only**: `update all profiles to openai/gpt-4o` -> only `model.default`
- **Bulk provider + key**: `all profiles to anthropic/claude-sonnet-4 with key sk-...` -> `ANTHROPIC_API_KEY` + `model.default`
- **Mixed config**: `all profiles use minimax but tech uses reasoning_effort high` -> apply base to all, then overlay per-profile exception
- **Dry run**: `preview sync to openai/gpt-4o` -> steps 1-3 + 5 (show what would change, no writes)

## Example prompts that trigger this skill
- "make every profile use anthropic/claude-sonnet-4"
- "sync all profiles to the same model as tech"
- "update the default model in all the profiles to openai/gpt-4o with key sk-..."
- "fan out the new minimax key to all profiles"
