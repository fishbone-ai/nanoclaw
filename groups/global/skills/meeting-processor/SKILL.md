---
name: meeting-processor
description: >
  Process a meeting transcript from the workspace. Given a file path (e.g. calls/meetings/2026-03-15-standup.md),
  reads the transcript, infers participants, extracts summary/action items/decisions/blockers/learnings,
  posts a summary to Slack #meeting-summaries, and suggests Linear issues for approval before creating them.
---

# meeting-processor

## Workflow

### 0. Extract path and dedup check
The trigger message contains a path like:
```
Process meeting transcript: `calls/meetings/2026-03-16-cpw-tmrf-adq-....md`
```

1. **Extract the exact path** from the backtick-quoted portion. Only process the explicitly specified file.

2. **Dedup check** — search Slack channel `C0AQ6D4KPGQ` (#meeting-summaries) for a message containing both "Meeting:" and the filename stem. If a summary already exists, stop.

```python
import json, os, urllib.request
from urllib.parse import urlencode
token = os.environ["SLACK_BOT_TOKEN"]
stem = "FILENAME_STEM_HERE"
params = urlencode({"channel": "C0AQ6D4KPGQ", "limit": 100})
req = urllib.request.Request(
    f"https://slack.com/api/conversations.history?{params}",
    headers={"Authorization": f"Bearer {token}"},
)
msgs = json.loads(urllib.request.urlopen(req).read()).get("messages", [])
already_posted = any("Meeting:" in (m.get("text") or "") and stem in (m.get("text") or "") for m in msgs)
```

### 1. Fetch the transcript
Read the file directly from `/workspace/global/<path>` using the Read tool.

### 2. Infer participants
Transcripts use `[Speaker Name]` or `[דובר N]` tags. Avishay (אבישי) and Ohav (אוהב) are always the known team members. If owner hint is given ("recorded from Ohav's Drive"), use that.

### 3. Analyze (output in English, transcript may be Hebrew)
Extract:
- **Summary** — 3-5 concise bullets
- **Action items** — verb-led, each with assignee and priority
- **Decisions** — things explicitly decided
- **Blockers/risks** — anything flagged as blocking
- **Learnings** — insights relevant to AI agents, e-commerce, catalog enrichment

### 3b. Map action items to assumptions
Classify each action item before suggesting a Linear issue:

**Type A — Assumption validator:** Directly moves confidence on an active assumption.
- Set as sub-issue of the assumption's parent issue
- Note: *Sub-issue of FB-XXX (assumption #N)*

**Type B — Sub-issue of existing issue**

**Type C — Enabler:** Necessary but doesn't validate any assumption.
- Flag: *Enabler — not assumption-linked*

**Type D — Unclear:** Flag and ask before suggesting.

Active assumptions (check `linear.sh team FB` for latest):
- FB-121: #1 — Catalog optimization → AI visibility
- FB-122: #2 — Fishbone beats DIY/PIM
- FB-123: #3 — Competitive whitespace exists
- FB-124: #4 — Can automate into platform
- FB-125: #5 — Retailers recognize gap + seeking solutions
- FB-128: #6 — ChatGPT apps as real channel

### 3c. Linear dedup check (run before suggesting each issue)
Search Linear for open issues that might already cover the proposed work.
- Full overlap: reference the existing issue ID, don't suggest a new one.
- Partial overlap: frame the new suggestion to cover only the non-overlapping scope; note the existing issue and explain why the new one isn't redundant.

### 4. Post summary to Slack (channel C0AQ6D4KPGQ)
Use Python urllib directly — do NOT use the `message` tool (it posts as a reply) and do NOT use curl (shell variable expansion mangles multi-line text).

```python
import json, os, urllib.request
token = os.environ["SLACK_BOT_TOKEN"]
text = """..."""  # full summary text
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps({"channel": "C0AQ6D4KPGQ", "text": text}).encode(),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST",
)
resp = json.loads(urllib.request.urlopen(req).read())
assert resp["ok"], resp
```

Format:
```
*Meeting: <title>* | YYYY-MM-DD

*Participants*
• Name 1, Name 2 (⚠️ Speaker 3 identity unclear — who is this?)

*Summary*
• bullet 1
• bullet 2

*Decisions* (omit if none)
• ...

*Blockers* (omit if none)
• ...

*Suggested Linear issues* (reply ✅ to approve all, or list which ones to create)
1. [high] Title — Description
   _Validates assumption #N (FB-XXX) — <rationale> / Sub-issue of FB-XXX / Enabler_
```

### 5. Create approved Linear issues
Use `LINEAR_API_KEY` env var. For each approved item, create via the Linear API or curl:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation{issueCreate(input:{teamId:\"TEAM_ID\",title:\"TITLE\",description:\"DESC\",priority:PRIORITY}){success issue{id identifier url}}}"}'
```

For Type A/B, set parent via:
```bash
curl -s -X POST https://api.linear.app/graphql \
  -H "Authorization: $LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation{issueUpdate(id:\"ISSUE_UUID\",input:{parentId:\"PARENT_UUID\"}){success}}"}'
```

### 6. Append learnings
Add to `/workspace/global/learnings/YYYY-MM.md` (create if not exists):
```markdown
## YYYY-MM-DD - Meeting: <title>
- learning 1
- learning 2
```
Use the Edit/Write tools directly.

### 7. Commit to git
After writing the transcript and learnings, commit them:
```bash
cd /workspace/project && git add groups/global/calls/meetings/ groups/global/learnings/ && git commit -m "feat(transcription): <meeting-title> YYYY-MM-DD"
```
