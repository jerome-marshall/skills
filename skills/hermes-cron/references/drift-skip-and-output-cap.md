# Cron Drift-Skip Guard & Output-Cap Truncation (Aug 2026 session)

Both failures hit the tech profile's cron jobs (daily-ai-tech-brief 84748651fcc5,
mnemosyne-nightly-sleep 3f2bd3b0433c) after the profile default moved from
opencode-zen/muse-spark-1.2-contributor-free to custom/glm-5.3-flash.

## 1. Drift-skip fail-closed guard (#44585)

### Symptom
Job output `.md` is only the prompt + an error block:

```
RuntimeError: [drift_skip] Skipped to prevent unintended spend: global inference
config drifted since this job was created (provider 'opencode-zen' -> 'custom';
model 'muse-spark-1.2-contributor-free' -> 'glm-5.3-flash'), and this job is
unpinned. No inference call was made. ... the job stays skipped until the config
is pinned or restored.
```

Alert fires once (jobs.json `drift_alerted: true`); job keeps failing until fixed.

### Mechanism (source-verified)
- `cron/jobs.py::_compute_provider_model_snapshots` — for non-`no_agent` jobs,
  snapshots the resolved runtime provider + default model into
  `provider_snapshot` / `model_snapshot` at create/edit time. `no_agent` script
  jobs carry no snapshots.
- `hermes_cli/config.py::cron_model_drift_axes` — for each axis (provider,
  model), if the job has no pin (job.provider/job.model empty) AND the snapshot
  is non-empty AND differs from the live default (lowercased compare) → axis
  drifted → the scheduler fails closed instead of silently spending on the new
  config.
- Guard default is ON; only literal YAML `false` for the guard key disables it.
  Missing/malformed stays fail-closed.
- Jobs created AFTER the config change have `*_snapshot: null` → never drift.
  This is why default/finance/health jobs "behaved well" while tech skipped.
- `cron/jobs.py::update_job` recomputes snapshots ONLY when
  `inference_fields_changed` (provider/model/base_url/no_agent actually differ)
  — a no-op `hermes cron edit` does NOT refresh them. There is no CLI flag to
  clear a snapshot.

### Fix (user policy: never pin — clear snapshots)
```bash
cd /home/machine0/.hermes/hermes-agent
HERMES_HOME=/home/machine0/.hermes/profiles/tech python - <<'PY'
import sys; sys.path.insert(0, "/home/machine0/.hermes/hermes-agent")
from cron.jobs import load_jobs, save_jobs
jobs = load_jobs()
for j in jobs:
    if j.get("id") in {"84748651fcc5", "3f2bd3b0433c"}:
        j["provider_snapshot"] = None
        j["model_snapshot"] = None
        j.pop("drift_alerted", None)   # re-arm once-only alert if drift recurs
save_jobs(jobs)
PY
```
Pitfalls:
- `cron.jobs` resolves its store via `get_hermes_home()` → must set
  `HERMES_HOME=/home/machine0/.hermes/profiles/<profile>` or you edit the wrong
  profile's cron store (worst case: default profile).
- Never hand-edit `jobs.json` — `save_jobs` does the atomic replace + field
  invariants.

### Verify
```python
from hermes_cli.config import cron_model_drift_axes, load_config
from cron.jobs import load_jobs
cfg = load_config()
# current_provider/current_model = live values (config.yaml model.provider / model.default)
for j in load_jobs():
    print(j["id"], cron_model_drift_axes(
        j, current_provider="custom", current_model="glm-5.3-flash", config=cfg))
# expect [] for every job
```

### Re-run
- `cronjob` tool action=run executes immediately in the background
  (`execution_mode: background`, delegation_id) — the outcome re-enters the
  conversation. Don't poll.
- CLI `hermes cron run <id>` only schedules for the next scheduler tick
  (existing skill note).

## 2. Response truncated due to output length limit

### Symptom
After the drift fix, the job ran (all searches completed per agent.log) but
failed; cron output `.md` has only prompt + error when the FIRST assistant
response truncated. agent.log shows:

```
ERROR cron.scheduler: Job 'daily-ai-tech-brief' failed: RuntimeError: Response truncated due to output length limit
... [cron_84748651fcc5...] agent.conversation_loop: API call #4: ... in=32295 out=739 ...
```

The small `out=` right before the failure = output cap hit, not a provider
failure (latency/cache were normal).

### Mechanism (source-verified)
- `agent/chat_completion_helpers.py` ~line 1868:
  `max_tokens=agent.max_tokens or 4096` → with `model.max_tokens` unset in
  config.yaml the effective cap is 4096.
- `agent.max_tokens` comes from `model.max_tokens` in config (cli.py:
  `_model_config.get("max_tokens")`, env override `HERMES_MAX_TOKENS`).
- Reasoning models (glm-5.3-flash, `reasoning_effort: medium`) spend reasoning
  tokens inside that budget; long tool-heavy turns exhaust it on the final
  wrap-up response (title + 10 items + links for the brief).

### Fix (profile-wide, no per-job pin)
```bash
hermes --profile tech config set model.max_tokens 8192
```
Verify: `load_config()["model"]["max_tokens"] == 8192`. All jobs (and
interactive sessions) in the profile inherit it. Don't exceed the provider's
model output cap — the agent errors with "max_tokens exceeds the provider's
output cap" and advises lowering config.yaml.

## User policy (durable)
- Cron jobs are NEVER pinned to a model/provider unless explicitly requested.
- When a profile's default model changes, unpinned jobs must keep following it —
  fix drift-skip by clearing snapshots, not by pinning.
- Don't offer "pin this job" remediation; he treats it as noise. One profile-wide
  `model.max_tokens` knob is preferred over per-job config.