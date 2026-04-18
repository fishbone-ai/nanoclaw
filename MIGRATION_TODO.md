# OpenClaw → NanoClaw Migration TODO

Source: `fishbone-ai/fishbone-claw` | Target: `/share/nanoclaw`

---

## ✅ Already Migrated

- **Identity / persona** — FishboneClaw soul, both users (Avishay + Ohav), timezone, formatting rules in `groups/global/CLAUDE.md`
- **GOALS.md** — current week (2026-04-12) in `groups/global/`
- **Slack channel** — all active channels registered, `SLACK_IS_MAIN=true`, `isMain` promoted
- **LINEAR_API_KEY** — present in `.env`
- **daily-standup skill** — `standup.sh` present in `groups/global/skills/daily-standup/`, cron task registered at `0 10 * * 0-5`
- **learnings/2026-04.md** — present in `groups/global/`

---

## 🔴 High Priority

### 1. Add missing credentials to `.env`
- `GEMINI_API_KEY` — required for meeting-transcriber
- `GOOGLE_SERVICE_ACCOUNT_JSON` — path to service account key file (meeting-transcriber)
- `AGENTVITAMINS_TOKEN` — for agent-vitamins-daily cron

### 2. Migrate `MEMORY.md`
Copy from `fishbone-claw` root to `/share/nanoclaw/groups/global/MEMORY.md`.
This is the most important business-context file — product clarity, bias corrections, contact notes, methodology.

### 3. Migrate meeting-transcriber
OpenClaw runs two crons: `*/10 * * * *` (transcribe) and `*/15 * * * *` (reconcile summaries).
- Port `skills/meeting-transcriber/transcribe.py`, `reconcile_summaries.py`, `requirements.txt`
  (deps: `google-genai`, `google-api-python-client`, `google-auth`, `requests`)
- Install Python deps into the NanoClaw container image (`container/Dockerfile`)
- Drive folder IDs: Ohav `1gd7Ted3J4b3w8nBbAJ4KEewLSbiFfNAA`, Avishay `1WID47DofY4bmXL-2oykKIJnqXIQYjqTS`
- Schedule two cron tasks for the `slack_main` group

### 4. Verify daily-standup cron
The DB shows the task was recording script failures. The NanoClaw version reads `LINEAR_API_KEY`
and `SLACK_BOT_TOKEN` from env (correct), but needs end-to-end verification.
Target channel: `#daily-tasks-check` (`C0AP1M0J7FF`).

### 5. Schedule agent-vitamins-daily
- Prompt-only task (no script), daily at `09:00` Sofia time
- Posts to `C0AKP55CTM3`
- Needs `AGENTVITAMINS_TOKEN` in `.env` first

---

## 🟡 Medium Priority

### 6. Create `HEARTBEAT.md`
OpenClaw had two heartbeat routines in `HEARTBEAT.md`:
1. **Goals check** (>22h interval): Check Linear statuses, flag stuck items Wed+, draft Sunday goals, archive Monday goals → post to `C0AP1M0J7FF`
2. **RSS digest** (>2h interval): Fetch nekuda + agentcommerce substacks, post to `#news-digest` (`C0ALG8V1J2U`)

OpenClaw used `blogwatcher` CLI — replace with a `curl`/`python3` RSS fetch script.
Create `/share/nanoclaw/groups/global/HEARTBEAT.md` and schedule a ~30-min heartbeat
task for the main Slack group.

### 7. Migrate `FISHBONE.md`
Copy from `fishbone-claw` root to `/share/nanoclaw/groups/global/FISHBONE.md`.
Contains startup context and RSS feed URLs used by heartbeat.

### 8. Migrate meeting-processor skill
Prompt-only skill (no scripts) — add `skills/meeting-processor/SKILL.md` to the global
skills directory. Critical for the meeting pipeline (dedup, participant inference, Linear
issue suggestions, learnings append).

### 9. Migrate `learnings/2026-03.md`
March learnings file is missing from `groups/global/learnings/`. Copy from the fishbone-claw repo.

### 10. Add `#ventures-evaluations` standing order
Channel: `C0AT7BN408G`. Auto-run venture-evaluation skill on every new top-level message
(Stage 1 Quick Filter → wait for opt-in to Stage 2).
- Create group folder for that channel if not already registered
- Add venture-evaluation skill SKILL.md to global skills
- Add standing order to that group's CLAUDE.md

---

## 🟢 Lower Priority

### 11. Mount fishbone-claw workspace into NanoClaw container
Historical business content is only in the `fishbone-claw` git repo:
`calls/meetings/` (~50 transcripts), `strategy/`, `experiments/`, `memory/`, `outreach/`, `prospects/`

Options:
- **(a) Mount the repo dir** into the container via `additionalMounts` in the group config — simplest
- **(b) Clone into global workspace** — portable but duplicates data
- **(c) GitHub API access from container** — on-demand but slower

Without this, FishboneClaw can't access historical transcripts, competitive research, etc.

### 12. Strategy/assumptions CLI
`strategy/assumptions/cli.py` + `gws` CLI + Google Sheets credentials.
Only needed if FishboneClaw should be able to update assumptions from inside NanoClaw
containers (currently works from Claude Code on the host only).

### 13. daily-self-eval cron
Was **disabled** in OpenClaw. If desired, re-enable using NanoClaw's `store/messages.db`
sessions table (vs OpenClaw's `.jsonl` session files). Low urgency.

---

## ❌ Not Applicable (skip)

- **Git worktree isolation** — OpenClaw used worktrees per session; NanoClaw uses container isolation. The `worktree-init.sh` / `worktree-merge.sh` scripts reference `/config/clawd` and have no equivalent.
- **worktree-cleanup cron** — OpenClaw-specific, not relevant.
- **retail-tech-report-2026 cron** — One-time job that already fired (2026-03-18).
- **Telegram channel** — OpenClaw had Telegram as primary; NanoClaw uses Slack. Confirm whether Telegram is still needed; if yes run `/add-telegram`.
