---
name: hermes-cron
description: Reliable cron job creation, delivery troubleshooting, and debugging the cronjob tool in Hermes Agent. Covers workarounds for parameter passing bugs, no_agent script delivery issues (especially Telegram), and direct create_job usage.
---

# Hermes Cron Job Management

## Creating Jobs When the `cronjob` Tool Fails

The `cronjob` tool (especially `action=create`) sometimes fails to accept `prompt` and `schedule` parameters due to schema/function-calling issues with certain models.

### Direct Python Workaround

Call `create_job` directly:

```python
from cron.jobs import create_job

result = create_job(
    prompt="Your full agent prompt here...",
    schedule="0 7 * * *",
    name="daily-brief",
    deliver="origin",
    enabled_toolsets=["web", "x_search"],
    profile="default",
    repeat=0
)
```

### Delivery Context (Critical)

- `deliver="origin"` only works when the job is created from within an active messaging session (Telegram, etc.).
- Direct Python calls leave `origin=None`, causing the job to run but produce no output in chat.
- Always verify `origin` after creation using `cronjob action=list`.

### Verification Steps

1. Check output: `~/.hermes/cron/output/{job_id}/`
2. Confirm via tool: `cronjob action=list`
3. If delivery is missing, either update the job with explicit delivery target or re-create inside the target chat.

## Debugging the cronjob Tool (Parameter Passing Bugs)

See `references/parameter-passing-bug.md` for the June 2026 diagnosis of cases where `schedule` and `prompt` parameters are dropped by the function-calling layer before reaching the Python implementation in `cronjob_tools.py`.

Common symptoms:
- "schedule is required for create"
- "create requires either prompt or at least one skill"
- `list` action works, but `create` fails.

Workarounds:
- Use `no_agent=True` + `script` path when possible.
- Fall back to raw system crontab + a small Python script in `~/.hermes/scripts/`.
- Retry creation after a gateway restart or model change.

## Troubleshooting Health-Monitor Cron Jobs

When a cron health report says a service is down, verify at the same seam the cron uses before changing service code:

1. List the job in the correct profile, including disabled jobs: `hermes --profile <profile> cron list --all`.
2. Read the job prompt and latest saved output under `$HERMES_HOME/cron/jobs.json` and `$HERMES_HOME/cron/output/<job_id>/` to identify the exact script/check that failed.
3. Re-run the underlying health script directly with host-safe env, not with the current agent profile's synthetic home: `HOME=/home/machine0 XDG_RUNTIME_DIR=/run/user/$(id -u) bash /home/machine0/.hermes/scripts/service_health_check.sh`.
4. For user systemd services, set the user bus before inspection or restart: `export XDG_RUNTIME_DIR=/run/user/$(id -u); export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus; systemctl --user status <unit> --no-pager -l`.
5. If a user service exists but is inactive/disabled, prefer the reversible fix `systemctl --user enable --now <unit>`; then verify the listening port and HTTP health endpoint.
6. Trigger the cron job only after the service-level check is green. `hermes cron run <id>` schedules it for the next scheduler tick; wait long enough for the tick and agent run, then confirm `last_run_at`, `last_status`, and the newest output file.

Pitfall: running `bash ~/.hermes/scripts/...` from a profile-scoped gateway session may expand `~` to a profile home such as `~/.hermes/profiles/tech/home`, not `/home/machine0`; use absolute `/home/machine0/.hermes/...` paths for default-profile host scripts.

## Troubleshooting no_agent Script Delivery (Especially Telegram)

See `references/no_agent_telegram_delivery.md` for session-specific reproduction of delivery failures when using `no_agent: true` + `script:` jobs.

Key issue: The delivery layer uses `~/.hermes/hermes-agent/venv/bin/python` which may lack packages like `python-telegram-bot` that exist in the main gateway environment.

Fix:
```bash
uv pip install python-telegram-bot --python ~/.hermes/hermes-agent/venv/bin/python
```

Also noted:
- `hermes cron run <id>` only advances the scheduler tick; does not execute immediately.
- For Discord: use `discord:CHANNEL_ID` (root) or `discord:CHANNEL_ID:THREAD_ID`; confirm exact target with user.
- Prefer normal agent mode (no `no_agent` flag) for delivery to messaging platforms.

## References

- `references/direct-create-job.md` — detailed reproduction and gotchas from June 2026 session.
- `references/parameter-passing-bug.md` — parameter passing diagnosis.
- `references/no_agent_telegram_delivery.md` — Telegram delivery fix for no_agent jobs.