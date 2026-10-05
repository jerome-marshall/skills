# TinyFish Setup — connect flow, doctor, API shapes, key handling

Reach for this when wiring up, repairing, or proving TinyFish integration for any harness, or when the MCP tools are missing.
TinyFish = hosted search/fetch/agent/browser suite. MCP server: `https://agent.tinyfish.ai/mcp`. CLI: `tinyfish` (v0.34.0 as of 2026-08-28).

## Key handling (never echo the key)

- Source: `MCP_TINYFISH_API_KEY` in `/home/machine0/.hermes/profiles/tech/.env`.
- Stage it in a 0600 temp file for scripts; **never** type it into argv (it lands in process listings and logs).
- Never print it in agent output. Refer to the env var by name.

## Connect flow

1. `tinyfish auth login --source openclaw` or set `TINYFISH_API_KEY` (CLI reads it from the keychain/config).
2. Register the MCP server in each harness. Hermes: config.yaml `mcp.servers.tinyfish.url` = `https://agent.tinyfish.ai/mcp?...` (already set).
3. **Tools only load in NEW sessions.** A harness that started before registration won't show `mcp_tinyfish_*` tools — restart the session, do not retry the install.
4. Verify with `tinyfish doctor`.

**Completion criterion:** `tinyfish doctor` shows `ok_harnesses: true` and every installed harness reports `pass` for `harness-registration`.

## Reading `tinyfish doctor`

- `cli-version` pass — CLI is current; server reports staleness via `X-TF-Notice` header.
- `mcp-connectivity` pass — endpoint reachable.
- `harness-registration` per harness:
  - `pass` = registered AND reach proven (api-key verified against the API).
  - `warn` = registered but reach unproven (e.g. codex: `$TINYFISH_API_KEY` not set in its env).
  - `skip` = harness not installed (grok/openclaw) — fine.
- `cli-auth-call` pass — an authenticated call succeeded (listRuns).

## API shapes (verified)
### Search
```
GET https://api.search.tinyfish.ai?query=<q>&domain_type=web|news&location=US&language=en
Header: X-API-Key: <key>
```
Response: `{query, results[], total_results, page}`. Each result: `{date, position, publisher, site_name, snippet, title, url}`. Hard cap 10 results.
**Trap:** `domain_type=news` returns Google News redirect URLs (`google.com/goto?url=...`) and drifts off-topic for non-news queries. Use `domain_type=web` for general queries; `news` only for dated headline sweeps (fetch the redirect URL anyway — it resolves).

**Config-driven upgrades (web.tinyfish.*):**
- `web.tinyfish.purpose` (str) — search intent hint, improves ranking. Sent on both search + fetch.
- `web.tinyfish.recency_minutes` (int, 1-5256000) — freshness window. Search only.
- Set per-profile via `hermes config set web.tinyfish.purpose "..."` etc. Read by the provider's `_tinyfish_config()`.

**Fetch**
```
POST https://api.fetch.tinyfish.ai
{"urls": ["https://..."], "format": "markdown"}
Header: X-API-Key: <key>
```
Response: `{results: [{url, final_url, title, language, published_date, text, latency_ms}], errors: []}`.
- Field is `urls` (array), NOT `url`. Content field is `text`, NOT `markdown`/`data`.
- Errors come back as `results: []` + `errors[]` with `{url, error, status}` (e.g. `page_not_found` / 404).
- Free tier: search 30 req/min, fetch 150 urls/min. No wallet needed for search+fetch.

### Agent / browser (heavier)
- `tinyfish agent run --url <url> "<goal>"` — real browser, returns `resultJson` on `COMPLETE`. Use for bot-protected/JS pages the fetch APIs can't read.
- `tinyfish browser session create --url <url>` — CDP WebSocket URL for programmatic control.

## Per-harness notes

| Harness | Status (2026-08-28) | Note |
|---|---|---|
| claude-code | pass | api-key verified |
| cursor | pass | api-key verified |
| hermes | pass | api-key verified; MCP in config.yaml |
| opencode | pass | registered, doesn't report headers |
| codex | warn | registered; needs `$TINYFISH_API_KEY` in its env to prove reach |
| grok / openclaw | skip | not installed |

If a harness flips to `warn`/fail after working, re-run `tinyfish install` for that harness and re-check doctor. The free-tier limits are generous enough for agent workloads — rate-limit errors are rare; treat them as "wait a second and retry", not a config problem.