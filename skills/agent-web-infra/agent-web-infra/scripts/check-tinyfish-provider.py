#!/usr/bin/env python3
"""Probe the TinyFish web provider registration + live search/extract.

Usage:
  HERMES_HOME=/home/machine0/.hermes/profiles/<profile> python3 check-tinyfish-provider.py

Checks: plugin discovers, provider registers, is_available, live search
returns results, live extract returns content. Exit 0 = all good.
"""
import os
import sys

REPO = "/home/machine0/.hermes/hermes-agent"
sys.path.insert(0, REPO)


def main() -> int:
    from hermes_cli.plugins import discover_plugins
    from agent.web_search_registry import get_provider

    discover_plugins()
    p = get_provider("tinyfish")
    if p is None:
        print("FAIL: tinyfish provider not registered after discover_plugins()")
        return 1
    print(f"OK: provider={type(p).__name__}")

    if not p.is_available():
        print("FAIL: provider not available (MCP_TINYFISH_API_KEY missing?)")
        return 1
    print("OK: is_available()")

    r = p.search("openai gpt-5", limit=3)
    if not r.get("success"):
        print(f"FAIL: search error: {r.get('error')}")
        return 1
    n = len(r.get("data", {}).get("web", []))
    print(f"OK: search -> {n} results")
    if n:
        print("  top:", r["data"]["web"][0].get("title", "")[:60])

    d = p.extract(["https://en.wikipedia.org/wiki/GPT-5"])
    if not d or d[0].get("error") or not d[0].get("content"):
        print(f"FAIL: extract error: {d[0].get('error') if d else 'no result'}")
        return 1
    print(f"OK: extract -> {len(d[0].get('content', ''))} chars, title={d[0].get('title', '')[:40]}")
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())