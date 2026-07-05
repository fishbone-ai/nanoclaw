---
name: meeting-processor
description: >
  Process a meeting transcript from the Supabase meeting store. Given a meeting id (e.g. 2026-03-15-standup),
  reads the transcript row, infers participants, extracts summary/action items/decisions/blockers/learnings,
  saves the structured summary back to Supabase, posts a summary to Slack #meeting-summaries,
  and suggests Linear issues for approval before creating them.
---

# meeting-processor

## Workflow

### 0. Extract meeting id and dedup check
The trigger message contains a meeting id like:
```
Process meeting transcript: `2026-07-05-bxw-faqy-yqf-2026-07-05-15-47-gmt-3`
```
(Legacy triggers may pass a path like `calls/meetings/<id>.md` — the id is the filename stem. Only process the explicitly specified meeting.)

Fetch the row and stop if it is already summarized:
```python
import sys
sys.path.insert(0, "/workspace/global/skills/meeting-transcriber")
import supabase_store
row = supabase_store.get_meeting("MEETING_ID", columns="id,owner,summary_md,transcript_md")
if row is None:
    print("No such meeting row — report this to the log channel and stop.")
elif row["summary_md"]:
    print("Already summarized — stop, post nothing.")
```

### 1. Read the transcript
Use `row["transcript_md"]` from step 0. If the row is missing but a legacy file
exists at `/workspace/global/calls/meetings/<id>.md`, read that file, then create
the row first with `supabase_store.upsert_meeting({"id": MEETING_ID, "date": MEETING_ID[:10], "transcript_md": ...})`.

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

### 3d. If weekly kickoff: draft GOALS.md "This Week" section
Detect if the transcript is a **weekly kickoff** (title contains "kickoff" or "weekly kickoff").

If yes, draft a replacement "This Week" section for `/workspace/global/GOALS.md` using the language and decisions from the transcript. Include it at the bottom of the Slack summary under a new heading:

```
*Suggested GOALS.md update* (reply ✅ to apply, or give feedback)
> ## 📅 This Week (YYYY-MM-DD → YYYY-MM-DD)
> ...
```

When the user approves (✅ or explicit confirmation):
1. Update `/workspace/global/GOALS.md`:
   - Move the current "This Week" section's theme + outcome into the archive table
   - Replace "This Week" section with the approved draft
   - Update the North Star if the strategic direction has shifted
2. Commit and push (see step 7)

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
_<meeting-id>_ | <https://meetings.getfishbone.ai/#/meeting/<meeting-id>|Open in dashboard>

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

### 4b. Save the structured summary to Supabase
This is what makes the meeting a first-class data citizen — never skip it.
Use the `ts` returned by `chat.postMessage` in step 4.

```python
import sys
sys.path.insert(0, "/workspace/global/skills/meeting-transcriber")
import supabase_store

supabase_store.save_summary(
    "MEETING_ID",
    summary_md=SUMMARY_MD,      # markdown: ## Summary / ## Decisions / ## Blockers / ## Learnings sections
    title="MEETING_TITLE",
    mtype="discovery-call",     # one of: discovery-call | vc-meeting | internal-strategy | phone-call | weekly-retro | weekly-kickoff | other
    slack_ts=POSTED_TS,         # ts returned by chat.postMessage
    participants=[
        # category: founder | practitioner | vc | advisor | other; role/company optional, omit if unknown
        {"name": "Avishay", "category": "founder"},
        {"name": "Dana Cohen", "category": "practitioner", "role": "CISO", "company": "Acme"},
    ],
    themes=["ai-security", "vc-readiness"],   # 2-5 kebab-case tags
)
```

Theme tags: reuse existing tags when they fit — check current ones with
`supabase_store._request("GET", "themes?select=theme")` and prefer an existing
spelling over inventing a synonym (e.g. use `ai-security`, not `security-for-ai`,
if `ai-security` exists).

### 4c. Extract candidate insights
Insights are the reusable, cross-meeting-valuable nuggets from this meeting — a market **signal**, a
**learning** about a customer/domain, a **risk**, an **opportunity**, or a **quote** worth remembering.
They are NOT a restatement of the summary bullets. Extract 3-7 (fewer if the meeting is thin; zero is
allowed for an empty/accidental recording).

Skip if this meeting already has extracted insights:
```python
import sys
sys.path.insert(0, "/workspace/global/skills/meeting-transcriber")
import supabase_store
if not supabase_store.meeting_has_extracted_insights("MEETING_ID"):
    supabase_store.insert_insights("MEETING_ID", [
        # category: signal | learning | risk | opportunity | quote | note
        {"content": "Enterprise AI security budgets are moving from pilot to line-item in 2026.",
         "category": "signal", "source": "extracted", "status": "candidate"},
        {"content": "CISOs distrust agent autonomy without an audit trail — recurring objection.",
         "category": "risk", "source": "extracted", "status": "candidate",
         "quote": "I can't put an agent in prod if I can't see what it did"},
    ])
```
Rules: `source` always `"extracted"`, `status` always `"candidate"`. `quote` is optional — include a
short verbatim transcript excerpt when one crisply supports the insight. Keep `content` to one sentence.
Never block the summary on this step; if it errors, report to the log channel and move on.

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

### 7. Commit and push learnings
```bash
cd /workspace/project && git add groups/global/learnings/ && git commit -m "docs(learnings): <meeting-title> YYYY-MM-DD" && git push
```
(Transcripts are no longer committed — they live in Supabase.)
