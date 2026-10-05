# Cron model-drift guard ([drift_skip], #44585)

Diagnosis + fix proven in Aug 2026 session. Companion: `scripts/clear-cron-snapshots.py`.

## Symptom

- `cronjob action=list` shows `last_status: error`; the run output under
  `$HERMES_HOME/cron/output/<job_id>/<ts>.md` contains:
  `RuntimeError: [drift_skip] Skipped to prevent unintended spend: global inference
  config drifted since this job was created (provider 'A' -> 'B'; model 'C' -> 'D'),
  and this job is unpinned. No inference call was made. ... See #44585.`
- The job shows `model: null, provider: null` (unpinned) — yet still skips.

## Root cause

- Unpinned jobs capture `provider_snapshot`/`model_snapshot` at create/edit time
  (`_compute_provider_model_snapshots` in `cron/jobs.py`, ~L1730).
- At fire time the guard (`cron_model_drift_axes` in `hermes_cli/config.py`, ~L4954)
  checks each axis (provider, model): skip if a fleet default covers the axis, skip
  if the job has an explicit pin (`job[axis]` truthy), else compare the snapshot to
  the current global default — mismatch => drift => fail closed.
- So an UNPINNED job with a STALE snapshot trips it. "Unpinned" means "guarded
  against default changes", not "no guard". The error text only suggests pinning —
  that is the wrong fix when the job should keep following the default.
- Jobs created AFTER a config change carry current/no snapshots, which is why some
  profiles' jobs "follow the default" with zero friction.

## Fix (keep following profile default)

Clear the stale snapshots via the real API — never hand-edit jobs.json:

    HERMES_HOME=/home/machine0/.hermes/profiles/<profile> python3 \
      ~/.hermes/profiles/tech/skills/hermes-cron/scripts/clear-cron-snapshots.py

- `$HERMES_HOME` selects the store: `cron.jobs` resolves `get_hermes_home()`
  (context/env). Default profile = `~/.hermes`, profiles = `~/.hermes/profiles/<name>`.
- Pins (job `model`/`provider`) are left untouched; only snapshots are cleared.
- Keep the guard enabled (`cron_model_drift_guard_enabled`, fails closed unless
  config literally sets `false`) — it still protects explicitly pinned flows.

## Pitfall: `hermes cron edit` does NOT refresh snapshots

- `update_job` (`cron/jobs.py` ~L2121) recomputes snapshots ONLY when
  `inference_fields_changed` is true, i.e. provider/model/base_url/no_agent
  actually CHANGED. A no-op edit leaves stale snapshots in place.
- There is NO CLI flag to clear snapshots. Use the script above.

## Verify

    HERMES_HOME=... python3 -c "
    import sys; sys.path.insert(0, '/home/machine0/.hermes/hermes-agent')
    from hermes_cli.config import cron_model_drift_axes, load_config
    from cron.jobs import load_jobs
    cfg = load_config()
    for j in load_jobs():
        print(j['id'], j['name'], '->', cron_model_drift_axes(
            j, current_provider='<provider>', current_model='<model>', config=cfg))
    "

Expect `[]` per job. Then `hermes cron run <id>` — it dispatches in background via
delegation (does not block); the outcome re-enters the conversation, don't poll.

## Wider check

Scan every profile's `cron/jobs.json` for jobs where
`j.get('provider_snapshot') or j.get('model_snapshot')` is truthy; any that should
follow the default can be cleared the same way. `hermes cron list` (all profiles)
shows `last_status: error` on blocked jobs.