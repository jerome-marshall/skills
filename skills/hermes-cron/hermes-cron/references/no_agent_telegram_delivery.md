Session: 2026-06-03

User ran `hermes cron run 2182c97e2a31` (daily-service-health-check).

Job config:
- no_agent: true
- script: service_health_check.sh
- deliver: telegram:-1004283478948:43

Error observed after run:
last_delivery_error: "delivery error: python-telegram-bot not installed. Run: pip install python-telegram-bot"

Key discovery:
- The script itself executed successfully (report generated, all services ✅).
- Delivery failed because the cron delivery layer uses `~/.hermes/hermes-agent/venv/bin/python`, which did not have python-telegram-bot.
- Normal `send_message` tool calls succeeded because they use the main gateway process.

Fix applied:
`uv pip install python-telegram-bot --python ~/.hermes/hermes-agent/venv/bin/python`

After fix:
last_delivery_error became None on next run.

Also noted: `hermes cron run` only schedules — does not force immediate execution.