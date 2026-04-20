---
name: daily-standup
description: Posts daily async standup check-ins to Slack for each team member. Fetches their open Linear tasks and asks for status + blockers. Runs via cron on weekdays (Sunday–Thursday) at 10 AM GMT+2.
---

# Daily Standup

Posts personalized standup messages to #daily-standup (C0AP1M0J7FF) every weekday morning.

## What it does

For each team member (Avishay + Ohav):
1. Fetches all open (non-completed, non-cancelled) Linear issues assigned to them
2. Posts a message to the standup channel listing their tasks and asking for status + blockers

## Script

```bash
~/clawd/skills/daily-standup/scripts/standup.sh
```

No arguments needed. Reads credentials from `/config/.openclaw/openclaw.json`.

## Config (hardcoded in script)

| Person  | Linear ID                              | Slack ID      |
|---------|----------------------------------------|---------------|
| Avishay | 8f197062-380b-4fa4-98e0-acd0fc08ed55   | U0AKCGVSHS8   |
| Ohav    | 68135dc9-ea68-43d3-940d-fa319b99412d   | U0AJTFLERPZ   |

Slack channel: `C0AP1M0J7FF`

## Cron

Scheduled via OpenClaw cron — weekdays Sunday–Thursday at 10:00 AM GMT+2 (08:00 UTC).
See `~/clawd/crons/jobs-def.json` for the job definition.
