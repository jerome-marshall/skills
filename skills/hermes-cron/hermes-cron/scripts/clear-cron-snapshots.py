#!/usr/bin/env python3
"""Clear stale provider/model snapshots on unpinned cron jobs (drift-skip fix, #44585).

Unpinned cron jobs carry provider_snapshot/model_snapshot captured at create/edit
time. When the profile's default model/provider changes, the drift guard
(cron_model_drift_axes in hermes_cli/config.py) fails closed on those stale
snapshots and skips the job ("[drift_skip] No inference call was made").

This script clears the snapshots so unpinned jobs follow the profile's CURRENT
default at fire time — no pins added, no re-pin nagging on future default changes.

Usage (HERMES_HOME selects the profile store; omit for the default profile):
  HERMES_HOME=/home/machine0/.hermes/profiles/tech python3 clear-cron-snapshots.py
  HERMES_HOME=/home/machine0/.hermes python3 clear-cron-snapshots.py   # default profile

Only stale snapshots are removed; pins (job model/provider) are never touched.
Also drops drift_alerted so a fresh single alert can fire if drift recurs.
"""
import os
import sys

repo = os.environ.get("HERMES_AGENT_REPO") or "/home/machine0/.hermes/hermes-agent"
sys.path.insert(0, repo)

from cron.jobs import load_jobs, save_jobs  # noqa: E402

jobs = load_jobs()
changed = 0
for job in jobs:
    had_p = job.get("provider_snapshot")
    had_m = job.get("model_snapshot")
    if had_p is None and had_m is None:
        continue
    job["provider_snapshot"] = None
    job["model_snapshot"] = None
    job.pop("drift_alerted", None)
    print(f"cleared {job.get('id')} ({job.get('name')}): provider_snapshot={had_p!r}->None, model_snapshot={had_m!r}->None")
    changed += 1

if changed:
    save_jobs(jobs)
print(f"Done. Snapshots cleared on {changed} job(s).")