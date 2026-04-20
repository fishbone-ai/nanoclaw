---
name: meeting-transcriber
description: Poll Google Drive for new Meet recordings, transcribe via Gemini 2.5, commit to repo
env:
  - GEMINI_API_KEY
  - GOOGLE_SERVICE_ACCOUNT_JSON
bins:
  - python3
  - git
cron: "*/10 * * * *"
---

# Meeting Transcriber

Automatically transcribes Google Meet recordings from Drive and commits them to `calls/meetings/`.

## How it works

1. Polls the configured Drive folder for new video files
2. Downloads unprocessed recordings to a temp directory
3. Uploads audio to Gemini 2.5 Flash for verbatim Hebrew transcription
4. Saves transcripts as `calls/meetings/YYYY-MM-DD-filename.md`
5. Commits and pushes transcripts + state file

## Usage

**Cron (default):** runs every 10 minutes automatically.

**Manual:** `python3 ops/skills/meeting-transcriber/transcribe.py`

## Silence Rule

**If no new recordings are found, post NOTHING to Slack.** Do not summarize, do not announce "nothing to do", do not confirm the run. Silence is the correct response when there's nothing to process.

## State

Processed recordings are tracked in `calls/meetings/.transcriber-state.json` (committed to repo). A recording is only marked processed after its transcript is successfully committed.

## Setup

1. Create Google Cloud project, enable Drive API
2. Create service account, download JSON key file
3. Share the "Meet Recordings" Drive folder with the service account email
4. `pip install -r ops/skills/meeting-transcriber/requirements.txt`
5. Set env vars: `GEMINI_API_KEY`, `GOOGLE_SERVICE_ACCOUNT_JSON` (path to JSON key file)
6. Set `drive_folder_id` in `config.json` (from the Drive folder URL)
