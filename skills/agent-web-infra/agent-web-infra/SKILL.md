---
name: agent-web-infra
description: "Operate agent web search/fetch infra (SearXNG, TinyFish)."
---

# Agent Web Infrastructure (SearXNG + Firecrawl + TinyFish)

## When to use
- Web search returns empty results, CAPTCHA/rate-limit throttling, engine failures
- Tuning or fixing the SearXNG engine set
- Setting up, repairing, or proving TinyFish MCP integration
- Health-checking the web toolchain for Hermes profiles (tech/health/finance all share it)

## Stack layout (this machine)
- **SearXNG**: Docker container `searxng` on http://127.0.0.1:8080. Config: `/home/machine0/.hermes/web-tools/searxng/config/settings.yml` — owned by `colord` (container user), so edits need a temp file + `sudo cp` + `sudo chown colord:colord`. Redis sidecar `searxng-redis`. Verified engine set as of 2026-08-28: 13 survivors (bing 1.6, yep 1.6, yandex 1.5, encyclosearch 1.4, mwmbl 1.4, gmx 1.3, wiby 1.3, yacy 1.2, fynd 1.2, searchmysite 1.2, yahoo 1.1, 360search 1.0, boardreader 1.0); 40 throttled/dead removed (brave*, ddg*, startpage*, qwant*, presearch*, aol*, seznam, baidu*, sogou*, naver*, mojeek*, wikivoyage, google).
- **Firecrawl**: docker compose at :3002 (api + playwright-service + rabbitmq + redis + postgres). Extract only.
- **Hermes config**: `web.search_backend: tinyfish` + `web.extract_backend: tinyfish` in ALL profiles (tech/health/finance/default) since 2026-08-28. SearXNG/Firecrawl remain as depth/fidelity fallback (still running).
- **TinyFish**: API key in all 4 profile `.env` as `MCP_TINYFISH_API_KEY`. NO tinyfish MCP server on any Hermes profile (removed 2026-08-28 — the web provider plugin is the single path for search/fetch). Other coding agents (Claude Code, Codex, Cursor, OpenCode) keep their own TinyFish MCP registration — that's separate.
- **TinyFish web provider plugin** (the thing that makes `web.search_backend: tinyfish` work): `/home/machine0/.hermes/hermes-agent/plugins/web/tinyfish/` (bundled, auto-loads) with backup at `/home/machine0/.hermes/web-tools/tinyfish-web-provider/`. Direct REST API, NOT MCP. If a Hermes update wipes the source-tree plugin, restore from the backup.
- **`web.tinyfish.*` config (2026-08-28)**: `recency_minutes: 43200` (30d freshness) set on tech/health/finance; tech also has `purpose` (OpenAI-announcement test string). default profile has NO `.env` key (not enforced) and no tinyfish block.

## Quick health check
```
curl -s http://127.0.0.1:8080/healthz   # expect OK
curl -s "http://127.0.0.1:8080/search?q=test&format=json" | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']),'results',[u[0] for u in d['unresponsive_engines']])"
```
0 results + unresponsive engines = engines throttled from this box's IP (common for datacenter IPs). Sweep and re-tune per `references/searxng-admin.md`. Note: SearXNG returns HTTP 200 with empty results when throttled, so Hermes' keyless fallback does NOT trigger — empty results are silent failures.

## Key pitfalls (detail in references/)
1. **SearXNG settings.yml**: `enabled` is NOT a valid engine key — use `disabled: false`. `enabled: true` is silently ignored.
2. **Removing engines**: remove ALL variants of a family (qwant + qwant images/news/videos) or startup crashes with `KeyError` in network init.
3. **TinyFish connect**: stage the API key in a temp file, never type it into argv; tools only load in NEW sessions — don't retry the install if they're missing.
4. **TinyFish Fetch API**: POST `{"urls":[...]}` (array, not `url`); the content field is `text`, not `markdown`/`data`.
5. **TinyFish search**: `domain_type=news` returns Google News redirect URLs + off-topic for non-news queries — use `domain_type=web` for general search.

## Which search to use when (2026-08-28 bake-off + enforcement)
- **Default search + fetch: TinyFish (web)** — ENFORCED as `web.search_backend` + `web.extract_backend` on all 4 profiles. 0.6-1.7s, structured results, strong top-5 relevance.
- **Depth/discovery: SearXNG** — 80-150 results, 19-engine diversity, but ~20s cold start, no dates. Still running at :8080; switch `web.search_backend` back to `searxng` per-profile if a task needs volume.
- **Full-page fidelity + PDFs: Firecrawl** — keeps navbars/infoboxes/refs; TinyFish fetch strips to main content. Still running at :3002.
- **Bot-blocked/403 pages: neither free fetch works** — escalate to TinyFish `agent run` (real browser).

## Rate-limit watchdog (TinyFish)
- Script: `/home/machine0/.hermes/scripts/tinyfish_ratelimit_watch.py` — reads TinyFish usage endpoints (`/usage` on both search+fetch), reports 429s in trailing window (default 24h, `--min-severity 2`). Watchdog pattern: empty stdout = all clear; exit 1 = 429s found; exit 2 = usage API unreachable. Self-resolves the key from `profiles/tech/.env` when the env var is absent (cron runners don't inherit it).
- **Integrated into the daily health check** (2026-08-28): NOT a standalone cron. `service_health_check.sh` runs the watchdog (`--min-severity 1`) in a "TinyFish" section — reachable+clean = ✅, 429s = ⚠️, usage API down = ❌. Runs daily 06:00 via `daily-service-health-check` (default profile) → Discord 1511680119717101678.
- The standalone `tinyfish-ratelimit-monitor` job (061a3639248e) was removed 2026-08-28.
- Usage endpoint shapes: search `/usage` items carry `status_code` (429 = rate-limited); fetch `/usage` items carry `status`/`error`. Timestamps are naive local (IST).
- Free-tier limits (verified): search ~30 req/min, fetch ~150 urls/min. 429s reset within a minute; Hermes auto-falls back to the keyless ring (exa→parallel→tavily→firecrawl→keenable) for that one call, then returns to TinyFish.

## References
- `references/searxng-admin.md` — engine sweep procedure, settings.yml pitfalls, verified engine list, working config pattern
- `references/tinyfish-setup.md` — connect flow, doctor, API shapes, key handling, per-harness notes
- `references/search-fetch-comparison.md` — 2026-08-28 quality bake-off: SearXNG/Firecrawl vs TinyFish verdict (use TinyFish web search default; SearXNG for depth; Firecrawl for page fidelity)