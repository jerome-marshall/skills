---
name: mnemosyne-hermes-ops
description: |
  Mnemosyne Hermes provider: diagnose plugin enable/remove.
trigger: |
  Plugin store shows both hermes-mnemosyne and mnemosyne present/disabled; user asks whether to enable/remove/switch Mnemosyne; memory "isn't remembering"; questions about post-tool-call hooks or auto-capture.
---

# Mnemosyne on Hermes — Ops & Diagnostics

## The one mental model that saves the day

Mnemosyne on Hermes = ONE package, TWO registrations, TWO config gates.

- Package: `mnemosyne-hermes` (plugin wrapper) + `mnemosyne-memory` (core), installed in the Hermes venv.
- Registration 1 (Source: user): `~/.hermes/plugins/mnemosyne/` symlink -> package dir; the manifest `plugin.yaml` gives it the name `hermes-mnemosyne`.
- Registration 2 (Source: entrypoint): pip entry point scanned from the venv; name `mnemosyne`.

Both entries are the SAME code. Two entries in the store != two implementations. Never "remove the custom one" — it IS the official install (upstream mnemosyne-oss docs: pip install `mnemosyne-hermes` + symlink + `hermes config set memory.provider mnemosyne`).

Two config gates, independent:
- `memory.provider: mnemosyne` -> makes it the ACTIVE memory provider (what actually stores/recalls).
- `plugins.enabled: [...]` -> allow-list for the plugin's tools + hooks.

Provider can be fully live while the plugin shows "not enabled" in the store — that is normal, not broken.

## Quick verification (cheapest first)

1. `hermes memory status` — Provider line + Plugin installed/available + active marker. If "Provider: mnemosyne" -> memory layer is live, regardless of store toggle state.
2. `hermes plugins list` — shows both registrations and their enabled state.
3. `hermes plugins doctor <name>` — KEY diagnostic: flags "manifest declares hook X but registration did not add it" and tools-registered-but-not-listed.
4. `grep -n register_hook <venv>/site-packages/mnemosyne_hermes/*.py` — confirms whether lifecycle hooks are actually wired.

## Verified upstream quirk (mnemosyne-hermes 0.5.0)

- `plugin.yaml` DECLARES hooks `pre_llm_call`, `on_session_start`, `post_tool_call`, but the package never calls `ctx.register_hook(...)` for them (grep proves it). Doctor reports them as warnings. Enabling the plugin therefore does NOT switch on post-tool-call auto-capture.
- The real auto-capture lives in `MnemosyneMemoryProvider.sync_turn()` (saves `[USER]` importance 0.5 / `[ASSISTANT]` 0.15, identity-signal capture, auto-sleep every 10 turns) — but nothing in Hermes core calls it (no caller anywhere in hermes-agent). Effectively dormant unless a wrapper/shim invokes it.
- So the honest answer to "how do I get post-tool-call auto-capture?" is a small hook shim / wrapper that calls `mnemosyne_remember` or `sync_turn` on tool results — NOT the plugin toggle. Re-verify with `hermes plugins doctor` after any version bump (hook wiring may change).
- Never `hermes tools disable memory` — it kills all `mnemosyne_*` tools (upstream README warning).

## Clean enable (when actually needed)

- Prefer the entrypoint registration: `hermes plugins enable mnemosyne`.
- If a profile has `plugins.disabled: [hermes-mnemosyne]` (seen in tech), enabling `hermes-mnemosyne` creates an enabled+disabled conflict — clear the disabled entry first, or sidestep by enabling `mnemosyne` instead.
- After any config change: restart the gateway, then re-verify with `hermes memory status` + `<venv>/bin/mnemosyne stats`.

## Pitfalls

- Do NOT delete the venv package or the plugins symlink to "switch to the official plugin" — same package; it breaks the live provider.
- Judge memory health by `hermes memory status`, never by the store toggle.
- Tech profile was observed missing `provider: mnemosyne` yet still active (entrypoint discovery) — keep all profile configs in sync anyway.
- DB locations: `~/.hermes/profiles/<p>/mnemosyne/data/mnemosyne.db` per profile; `~/.hermes/mnemosyne/data/shared/mnemosyne.db` shared surface.

See references/hermes-integration-findings.md for the full command recipe, doctor transcript, and code-location facts.
