When the `cronjob` tool's `create` action fails to accept `prompt`/`schedule` parameters (seen with grok-4.3 + Hermes ~June 2026), bypass it by calling `create_job` directly:

```python
from cron.jobs import create_job

create_job(
    prompt="...",
    schedule="0 7 * * *",
    name="job-name",
    deliver="origin",
    enabled_toolsets=["web", "x_search"],
    profile="default",
    repeat=0
)
```

**Critical gotcha**: `deliver="origin"` only works if the job is created inside an active session that has Telegram/Discord/etc context. Direct Python calls result in `origin=None`, causing silent delivery failure even when the job runs successfully.

Always verify after creation:
- Check `~/.hermes/cron/output/{job_id}/` for run logs
- Use `cronjob action=list` to confirm `origin` and `deliver`
- If origin is missing, update the job or re-create inside the target chat.