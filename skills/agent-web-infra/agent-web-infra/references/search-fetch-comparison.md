# Search & Fetch Quality Comparison — SearXNG/Firecrawl vs TinyFish (2026-08-28)

## Verdict in one line
**Default search + fetch: TinyFish (domain_type=web).** SearXNG for depth/volume; Firecrawl for full-page fidelity & PDFs; TinyFish agent for bot-blocked pages.

## Search
- TinyFish: 6-10 results, 0.6-1.7s (no warmup), every result carries date/publisher/position, top-5 relevance strong on web queries, canonical URLs with domain_type=web.
- SearXNG: 80-152 results, 1.2-20s (cold ~20s engine warmup), no dates (publishedDate null), diverse 19-engine mix, canonical URLs.
- TRAP: TinyFish domain_type=news returns Google News redirect URLs (google.com/goto?url=...) and off-topic results for non-news queries. Use domain_type=web for general queries; news only for dated headline sweeps.

## Fetch
- Firecrawl: full-page fidelity (Wikipedia 64.9k chars vs TinyFish 22.5k), PDF excellent, ~1-2.8s.
- TinyFish fetch: faster (~1.5-2.1s), strips nav/boilerplate to clean main content, parallel multi-URL server-side, `urls` array + `text` field.
- Bot-protected/403 pages (e.g. NDTV/Akamai): BOTH fail — Firecrawl returns "Access Denied" markdown, TinyFish 404. Escalate to TinyFish agent (real browser) for those.

## API shapes (verified)
- SearXNG: GET http://127.0.0.1:8080/search?q=..&format=json → results[] with url/title/content/engines/score/publishedDate(null mostly). 0 results + unresponsive = throttled (silent failure).
- TinyFish search: GET https://api.search.tinyfish.ai?query=..&domain_type=web|news&location=US&language=en, header X-API-Key → results[] {date, position, publisher, site_name, snippet, title, url}. total_results caps at 10.
- TinyFish fetch: POST https://api.fetch.tinyfish.ai {"urls":[...],"format":"markdown"} → results[].text (NOT markdown/data). Errors: results[] empty + errors[].
- Firecrawl: POST http://127.0.0.1:3002/v1/scrape {"url":"..","formats":["markdown"]} → data.markdown, data.metadata.statusCode.

## Key not in this file
Source from `MCP_TINYFISH_API_KEY` in /home/machine0/.hermes/profiles/tech/.env. Never echo it.