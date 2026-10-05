# TinyFish Rate Limits & Hermes Fallback Behavior (verified 2026-08-28)

Answers "what happens when we hit the rate limit?" for the enforced TinyFish web backend.

## Free tier limits + billing

- **Search**: ~30 req/min. **Fetch**: ~150 urls/min. Per-minute windows; exceeding them returns **429 RATE_LIMIT_EXCEEDED** ("Too many requests in a short period"), then recovers on its own.
- **Billing split (official docs, authentication.md)**: "Search and Fetch are free. Agent and Browser draw from your wallet as they run." The signup credit (~$12) is ONLY consumed by Agent/Browser automation — daily search/fetch usage never touches it.
- Wallet accounts can also see `INSUFFICIENT_CREDITS` when Agent/Browser credits run out; that is NOT a search/fetch error.

## What Hermes does on a 429 (verified in source, not guessed)

Dispatch path: `tools/web_tools.py` `web_search_tool` / `web_extract_tool` → provider returns `{"success": False, "error": <body>}` (the tinyfish provider raises `ValueError(body)` on >=400, caught into the error dict).

1. `_rescue_eligible(provider)` (web_tools.py) — True unless `web.keyless_rescue: false` or `web.keyless_fallback: false` in config. **All profiles here leave both unset → rescue ON.**
2. One-shot keyless rescue: `_rescue_search` → `search_with_failover` (`plugins/web/keyless_mcp.py`) routes THIS call through the free-tier ring: `_KEYLESS_RING = (exa, parallel, tavily, firecrawl, keenable)`, starting at the round-robin cursor.
3. Rate-limit-shaped errors (`_is_rate_limitish` — matches "429"/RATE_LIMIT etc.) advance to the next ring vendor; non-throttle errors (e.g. malformed query) stop the walk immediately.
4. Success comes back annotated `data.served_by: <vendor>` + `data.backend_error` ("Configured backend 'tinyfish' failed this call ...; result served by the keyless free tier. The next call will use 'tinyfish' again.").
5. Whole ring throttled → original TinyFish error with "(all keyless vendors throttled: ...)" appended.
6. **Stateless**: the NEXT web_search call attempts the configured backend again. Explicit config (`web.search_backend: tinyfish`) still wins in resolution — a 429 never permanently switches backends.

Extract (`_rescue_extract`): fires only when EVERY url in the batch failed with rate-limit-shaped errors; partial failures are page problems and pass through. Website-policy blocks are never rescued.

Practical consequence: 429s are invisible in normal operation — one call rides the free ring, next is back on TinyFish. Only visible when the whole ring is throttled too (rare), or via `served_by`/`backend_error` annotations in results.

## Reading TinyFish docs (JS-rendered site)

- `docs.tinyfish.ai` pages are JS-rendered — plain curl returns only the nav skeleton.
- Append `.md` to any page URL → raw markdown over plain HTTP: e.g. `https://docs.tinyfish.ai/search-api/reference.md`, `https://docs.tinyfish.ai/authentication.md`. Full index: `https://docs.tinyfish.ai/llms.txt`.
- Works with curl or the TinyFish fetch API itself.

## Usage introspection

- `GET https://api.search.tinyfish.ai/usage` with `X-API-Key` header → `{"items": [{query, status_code, result_count, results[]...}]}` request history (list-search-usage). Useful to confirm requests actually landed after a 429 scare; no wallet/limit totals in the response.