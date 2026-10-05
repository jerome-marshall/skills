# SearXNG Admin — engine sweep, config pitfalls, verified setup

Reach for this when SearXNG returns empty or degraded results, or when the engine set needs re-tuning.
Source of truth for the current config: `/home/machine0/.hermes/web-tools/searxng/config/settings.yml` (read it whenever this doc and the file disagree — the file wins).

## Health check (30 seconds)

```
curl -s http://127.0.0.1:8080/healthz                      # expect OK
curl -s "http://127.0.0.1:8080/search?q=test&format=json" | python3 -c "import sys,json;d=json.load(sys.stdin);print(len(d['results']),'results',[u[0] for u in d['unresponsive_engines']])"
```

**Completion criterion:** >0 results AND unresponsive list is short. SearXNG returns HTTP 200 with 0 results when throttled — empty results are a silent failure, not a "no match". Treat 0 results as an engine sweep trigger, not an answer.

## The throttled-engine problem

This box's IP is a datacenter IP. Brave/DDG/Startpage/Qwant/Presearch/AOL/Google all CAPTCHA/rate-limit from it. The fix is not fighting the wall — it is sweeping for the engines that DO answer, then pinning the config to them.

## Engine sweep procedure

1. List candidate engines: `docker exec searxng searxng-run ...` or read `/etc/searxng/engines` inside the container (or use the settings.yml `remove` list as the known-bad set).
2. Test each candidate with 2 queries (`openai gpt-5`, `india budget 2026`) and record: results returned, latency, errors.
3. Categorize: **survivor** (returns results), **throttled** (CAPTCHA/403/empty), **dead** (timeout/parse error every run).
4. Keep survivors; remove throttled+dead via `use_default_settings.engines.remove` (see pitfalls).
5. Re-run the health check — the completion criterion above is the gate.

## Editing settings.yml (the sudo dance)

The file is owned by `colord` (the container user); Hermes cannot write it directly.

```
cp /home/machine0/.hermes/web-tools/searxng/config/settings.yml /tmp/settings.yml
# edit /tmp/settings.yml
sudo cp /tmp/settings.yml /home/machine0/.hermes/web-tools/searxng/config/settings.yml
sudo chown colord:colord /home/machine0/.hermes/web-tools/searxng/config/settings.yml
docker compose -f /home/machine0/.hermes/web-tools/searxng/docker-compose.yaml restart
```

**Completion criterion:** `curl -s http://127.0.0.1:8080/healthz` returns OK AND the test query returns results. Back up the working file first (`settings.yml.bak-YYYYMMDD-HHMMSS`).

## Pitfalls (each cost a real debugging session)

1. **`enabled` is not a valid engine key.** `enabled: true` is silently ignored. The correct key is `disabled: false`.
2. **Remove ALL variants of a family together.** Removing `presearch` but not `presearch images/videos/news` crashes startup with `KeyError` in network init. Same for qwant, brave, duckduckgo, baidu, sogou, naver, mojeek, aol, startpage.
3. **Google is dead weight from this IP** — returns empty results (bot wall), not an error. Remove it.
4. **Restart required after every settings change** — edits do not hot-reload.
5. **Cold-start latency ~20s** on first query after restart (engines warm up); warm queries are 1-6s. Not a fault.

## Verified engine set (as of 2026-08-28 sweep)

Enabled with weights in settings.yml — read the file for the live list. Survivors:
bing 1.6, yep 1.6, yandex 1.5, encyclosearch 1.4, mwmbl 1.4, gmx 1.3, wiby 1.3, yacy 1.2, fynd 1.2, searchmysite 1.2, yahoo 1.1, 360search 1.0, boardreader 1.0.

Removed: brave*, duckduckgo*, startpage*, qwant*, presearch*, aol*, seznam, baidu*, sogou*, naver*, mojeek*, wikivoyage, google.

## Working config pattern

```
use_default_settings:
  engines:
    remove: [ <all throttled/dead families, every variant> ]
engines:
  - name: <survivor>
    disabled: false     # NOT enabled: true
    weight: <1.0-1.6>   # higher = more influence on ranking
```

The `use_default_settings` block keeps the rest of SearXNG sane; only engines are overridden. `server.limiter: false` and `search.safe_search: 0` are intentional (agent use, not public).