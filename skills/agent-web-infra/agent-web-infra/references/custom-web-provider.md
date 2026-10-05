# Custom Hermes Web Provider Plugin — add a new search/extract backend

Use when wiring a new vendor as `web.search_backend` / `web.extract_backend`, rebuilding the tinyfish plugin after a Hermes update wiped it, or verifying a bundled backend registers. Built 2026-08-28 for TinyFish; recipe generalizes to any HTTP search/fetch API.

## The provider contract (agent.web_search_provider.WebSearchProvider ABC)

Subclass the ABC; the registry dispatches every `web_search` / `web_extract` call to the provider named by config.

- `name` property → the exact value used in `web.search_backend` etc. (lowercase, e.g. `tinyfish`).
- `supports_search()` / `supports_extract()` → capability flags.
- `search(query, limit)` → `{"success": True, "data": {"web": [{"title","url","description","position"}]}}` or `{"success": False, "error": str}`.
- `extract(urls, **kwargs)` → list of `{"url","title","content","raw_content","metadata"}`; per-URL failures become items with `error` (never raise).
- `is_available()` → cheap env check. Use `get_provider_env("VAR")` (config-aware: os.environ then the profile `.env`), not bare os.getenv.
- Smallest full template: `plugins/web/tavily/provider.py`.

## Plugin layout (bundled, auto-loads)

```
plugins/web/<name>/
  plugin.yaml    # name: web-<name>  |  kind: backend  |  provides_web_providers: [<name>]
  __init__.py    # def register(ctx): ctx.register_web_search_provider(<Name>Provider())
  provider.py    # the ABC implementation
```

Bundled backends auto-load (`manifest.source == "bundled" and kind == "backend"`). **"not enabled" in `hermes plugins list` is NORMAL for bundled web backends** — they register regardless (searxng/firecrawl/tavily all show it too).

## Verify (in this order)

1. `HERMES_PLUGINS_DEBUG=1` boot → log line `Parsed manifest: key=web/<name>`.
2. `hermes plugins doctor web/<name>` → `OK: runtime discovery, manifest parsing, import, and registration passed`.
3. Fresh-boot registry test — **use the Hermes venv python**, not system python3 (httpx + hermes modules live there):
   ```
   HERMES_HOME=/home/machine0/.hermes/profiles/<p> /home/machine0/.hermes/hermes-agent/venv/bin/python3 -c "
   import sys; sys.path.insert(0,'/home/machine0/.hermes/hermes-agent')
   from hermes_cli.plugins import discover_plugins; discover_plugins()
   from agent.web_search_registry import get_provider
   p = get_provider('tinyfish'); print(type(p).__name__, p.is_available())"
   ```
4. Live call through the provider: `p.search(...)`, `p.extract([...])`.

## Pitfalls (each cost real debugging time)

1. **HERMES_HOME for a profile is `profiles/<name>/`** — that's where config.yaml lives. `profiles/<name>/home` is the simulated $HOME; pointing HERMES_HOME there reads the WRONG config and silently falls back to the keyless ring (resolves to keenable/whatever), making you think your config didn't take.
2. **Registry is populated at import-time (plugin load at boot).** A session started BEFORE the plugin existed errors `web is configured to use 'tinyfish' but no registered web search provider has that name` until restarted. Expected, not a bug — new sessions pick it up.
3. **`hermes mcp add` is fully interactive** (overwrite confirm, auth prompt, tool-select prompt) — not scriptable. For fan-out, write nested keys directly: `hermes -p <p> config set mcp_servers.<name>.url <url>` / `.headers.Authorization` / `.enabled true` (nested YAML works; env keys auto-route to `.env`).
4. Response shape must match the registry contract exactly or the tool wrapper misbehaves silently.

## Fan-out to all profiles

```
hermes -p <p> config set web.backend <name>
hermes -p <p> config set web.search_backend <name>
hermes -p <p> config set web.extract_backend <name>
hermes -p <p> config set <ENV_VAR> <value>     # auto-routes to .env
```
Then re-run the fresh-boot registry test per profile. Verify `hermes -p <p> mcp list` shows the server enabled.

## Restoring after a Hermes update

The plugin lives in the source tree (`hermes-agent/plugins/web/tinyfish/`) and a git update can wipe it. Backup lives at `/home/machine0/.hermes/web-tools/tinyfish-web-provider/` — copy it back, re-run verification steps 1-4.