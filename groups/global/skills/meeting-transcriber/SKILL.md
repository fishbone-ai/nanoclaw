---
name: meeting-transcriber
description: Poll Google Drive for new Meet recordings, transcribe via Gemini 2.5, store in the Supabase meeting store
env:
  - GEMINI_API_KEY
  - GOOGLE_SERVICE_ACCOUNT_JSON
  - SUPABASE_URL
  - SUPABASE_SERVICE_KEY
bins:
  - python3
  - git
cron: "*/10 * * * *"
---

# Meeting Transcriber

Automatically transcribes Google Meet recordings from Drive into the Supabase meeting store (`meetings` table).

## How it works

1. Polls the configured Drive folder for new video files
2. Downloads unprocessed recordings to a temp directory
3. Uploads audio to Gemini 2.5 Flash for verbatim Hebrew transcription
4. Upserts the meeting row (transcript, date, owner, source, duration) into the Supabase `meetings` table
5. Prints NEW_TRANSCRIPTS meeting ids for the agent to summarize (via meeting-processor)

## Usage

**Cron (default):** runs every 10 minutes automatically.

**Manual:** `python3 ops/skills/meeting-transcriber/transcribe.py`

## Silence Rule

**If no new recordings are found, post NOTHING to Slack.** Do not summarize, do not announce "nothing to do", do not confirm the run. Silence is the correct response when there's nothing to process.

## State

Processed recordings are tracked in `skills/meeting-transcriber/.transcriber-state.json` (runtime state, not committed). A recording is only marked processed after its transcript row is successfully stored in Supabase. `calls/meetings/` is a frozen archive of pre-Supabase transcripts.

## Setup

1. Create Google Cloud project, enable Drive API
2. Create service account, download JSON key file
3. Share the "Meet Recordings" Drive folder with the service account email
4. `pip install -r ops/skills/meeting-transcriber/requirements.txt`
5. Set env vars: `GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON` (path to JSON key file)
6. Set `drive_folder_id` in `config.json` (from the Drive folder URL)
