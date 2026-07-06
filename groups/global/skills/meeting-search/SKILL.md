---
name: meeting-search
description: >
  Search and refer to past meetings and notes. Use when asked to find a meeting, recall what
  was discussed/decided about a topic, check whether we've talked to someone or heard an
  objection/idea before, or pull notes on a person, company, theme, or date range. Searches
  meeting summaries, transcripts, and curated insights in the Supabase store. Dashboard:
  https://meetings.getfishbone.ai/
---

# meeting-search

Keyword search over the meeting store (summaries + transcripts + insights). Read-only —
never mutate anything here.

## Workflow

### 1. Parse the ask into a query + filters
- **person / company** → `participant` (name substring, case-insensitive)
- **month / quarter / "last week" / date range** → `date_from` / `date_to` (compute ABSOLUTE
  YYYY-MM-DD dates from today's date; e.g. "in June" → 2026-06-01..2026-06-30)
- **meeting kind** → `mtype`, one of: `discovery-call | vc-meeting | internal-strategy |
  phone-call | weekly-retro | weekly-kickoff | other`
- **topic words** → `query`
- A purely structured ask ("VC calls in June", "meetings with Dana") passes `query=None`.

### 2. Run the search
```python
import sys
sys.path.insert(0, "/workspace/global/skills/meeting-transcriber")
import supabase_store

hits = supabase_store.search_meetings(
    query="audit trail",          # or None for filters-only
    participant=None,             # e.g. "Michael Colao"
    mtype=None,                   # e.g. "vc-meeting"
    date_from=None, date_to=None, # e.g. "2026-06-01", "2026-06-30"
    limit=20,
)
```
Each hit: `{source, meeting_id, title, date, snippet, rank, url}` where `source` is
`summary` | `transcript` | `insight`. Results are already ranked (summary > insight >
transcript). Matched terms in `snippet` are wrapped in `*...*`.

### 3. Reply in Slack (top ~5)
The `snippet` already uses `*term*` bolding — keep it. Format:
```
*<title>* · <date> · <type-label>
> <snippet>
<https://meetings.getfishbone.ai/#/meeting/<meeting_id>|Open>
```
- Prefix insight hits with `💡 insight`.
- Collapse multiple hits from the same meeting (e.g. summary + transcript) into one entry;
  keep the highest-ranked snippet.
- If several meetings match, list up to 5 and note the total.
- **No hits** → say so plainly and offer to broaden: drop a filter, widen the date range, or
  include transcripts (`sources=['summary','transcript','insight']`).

## Rules
- Read-only. Never write, update, or delete.
- Prefer summaries/insights for "what did we conclude"; reach into transcripts only when the
  ask wants the exact wording of an exchange.
- Always include the dashboard link so the user can open the full meeting.
