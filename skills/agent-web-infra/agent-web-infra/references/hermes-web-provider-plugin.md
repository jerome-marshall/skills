# Writing / Debugging a Custom Hermes Web Provider Plugin

Class-level guide for adding a new `web.search_backend` / `web.extract_backend` to Hermes, or debugging why a provider isn't registering. Worked example: the TinyFish plugin at `hermes-agent/plugins/web/tinyfish/` (backup `~/.hermes/web-tools/tinyfish-web-provider/`).

## Why this exists
Hermes' `web_search` / `web_extract` tools are backend-driven. `web.search_backend` / `web.extract_backend` / `web.backend` in config.yaml name a provider registered in the `agent.web_search_registry`. There is NO built-in `tinyfish` provider — the plugin registers it. To add ANY new web vendor (or restore the tinyfish plugin after a Hermes update), you need this recipe.

## Plugin layout (3 files, bundled auto-load)
Under `<repo>/plugins/web/<name>/`:
- `plugin.yaml` — manifest: `name: web-<name>`, `kind: backend`, `provides_web_providers: [<name>]`. Bundled backends auto-load (no `plugins.enabled` opt-in needed, unlike user plugins).
- `__init__.py` — `def register(ctx): ctx.register_web_search_provider(<Name>WebSearchProvider())`.
- `provider.py` — subclass `agent.web_search_provider.WebSearchProvider` (the ABC).

## The provider contract (from `agent/web_search_provider.py`)
- `name` (property, lowercase, config key value), `display_name`.
- `is_available()` — typically `bool(get_provider_env("<KEY>"))`.
- `is_keyless_available()` — False if the vendor needs a key.
- `supports_search()` / `supports_extract()` — capability flags; a provider can advertise both.
- `search(query, limit=5) -> {"success": True, "data": {"web": [{"title","url","description","position"}, ...]}}` or `{"success": False, "error": str}`.
- `extract(urls, **kwargs) -> [{"url","title","content","raw_content","metadata"}]` — per-URL failures become items with `error`, never raise the whole call.
- `get_setup_schema()` — for `hermes tools` UI.

Mirror the smallest existing provider (`plugins/web/tavily/provider.py`) as the template. Response-shape contract is preserved bit-for-bit from the legacy wrapper — don't invent new shapes.

## Config resolution (the two gotchas that cost real time)
1. **`get_provider_env(name)`** reads env via Hermes' config-aware lookup (os.environ → profile `.env`). Use it for the API key.
2. **Per-profile config**: `load_config().get("web")` reads from `$HERMES_HOME/config.yaml`. For profile `tech`, HERMES_HOME must be `/home/machine0/.hermes/profiles/tech` (where config.yaml lives) — NOT `profiles/tech/home` (that's the simulated $HOME, has no config.yaml). Wrong HERMES_HOME → you silently read the default profile's config and get the wrong backend.
3. **Provider-level tuning**: read a sub-dict like `web.tinyfish.*` via `load_config().get("web", {}).get("tinyfish", {})` so users can `hermes config set web.tinyfish.<key> <val>` per profile. (Used for `purpose` / `recency_minutes`.)

## Debugging "provider not registered" (the exact path that worked)
1. `hermes plugins list` — confirm the plugin shows as bundled.
2. `hermes plugins doctor <path-to-plugin-dir>` — validates discovery, manifest, import, registration ("OK: runtime discovery, manifest parsing, import, and registration passed").
3. In a venv python: `from hermes_cli.plugins import discover_plugins; discover_plugins()` then `from agent.web_search_registry import list_providers` / `get_provider('<name>')`.
4. `HERMES_PLUGINS_DEBUG=1` — verbose discovery logs to stderr (shows parsed manifests, skipped dirs, registration lines).
5. Registry is populated at **process boot**. A session that started before the plugin existed will error "no registered web search provider has that name" even though fresh processes resolve fine. Restart the session — don't chase a phantom config bug.

## Verification after writing
- Fresh-boot test: `discover_plugins()` → `get_provider('<name>')` → `is_available()` → live `search()` + `extract()`.
- `hermes plugins doctor web/<name>` → OK.
- Run `scripts/check-tinyfish-provider.py` (in this skill) as a quick probe.
- If the plugin lives in the Hermes source tree, keep a backup copy under `~/.hermes/web-tools/<name>-web-provider/` and restore after Hermes updates wipe it.

## Pitfalls
- `enabled: true` is NOT a valid engine key for SearXNG — `disabled: false` is (see searxng-admin.md). Unrelated to plugins, but easy to conflate.
- Bundled backends show "not enabled" in `hermes plugins list` — that's normal (they auto-load), don't try to enable them.
- `plugins doctor` needs the path or full key (`web/tinyfish`), not the bare plugin name.