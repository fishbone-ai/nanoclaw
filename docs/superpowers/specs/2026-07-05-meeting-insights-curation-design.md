# Meeting Insights — Curation Feature Design

**Date:** 2026-07-05
**Status:** Approved (pending spec review)
**Builds on:** `2026-07-05-meeting-insights-dashboard-design.md` (the Supabase store + dashboard)

## Problem

Meetings have summaries, but the valuable cross-meeting *insights* (signals, learnings, risks,
opportunities, quotable moments) aren't captured as first-class, curated data. We want the pipeline
to propose insights per meeting, a human to accept/reject/edit them, and a way to hand-create insights
by highlighting transcript text and adding a note. Accepted insights should surface both on the meeting
page and in a dedicated Insights feed.

## Goal

1. `meeting-processor` extracts **candidate** insights from each meeting.
2. The dashboard lets us **accept / reject / edit** them, and **create** insights by highlighting
   transcript text + adding a note.
3. **Accepted** insights appear on the meeting page and in a repurposed **Insights** feed.
4. Backfill candidate insights for the **20 most recent** summarized meetings (from their summaries).

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Write path | **Open anon writes, scoped**: RLS lets the `anon` role INSERT/UPDATE the `insights` table only — no DELETE, no writes to other tables. Same openness as reads today; real auth deferred. |
| Insight shape | Text + one **category** (`signal`/`learning`/`risk`/`opportunity`/`quote`/`note`). |
| Insights page | The existing charts **Insights** tab becomes the accepted-insights **feed**; charts move to a new **Stats** tab. |
| Backfill | The **20 most recent** summarized meetings, extracting from each **summary** (not transcript). |
| Manual insight | Highlight transcript → add note → submit = one manual insight (`quote`=selection, `content`=note). |

## Data model — `insights` table

```sql
create table insights (
  id          uuid primary key default gen_random_uuid(),
  meeting_id  text not null references meetings(id) on delete cascade,
  content     text not null,                       -- insight text; the user's note for manual insights
  category    text not null default 'note' check (category in ('signal','learning','risk','opportunity','quote','note')),
  status      text not null default 'candidate' check (status in ('candidate','accepted','rejected')),
  source      text not null check (source in ('extracted','manual')),
  quote       text,                                -- optional supporting transcript excerpt
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists insights_meeting_idx on insights (meeting_id);
create index if not exists insights_feed_idx on insights (status, created_at desc);

alter table insights enable row level security;
create policy anon_read_insights   on insights for select to anon using (true);
create policy anon_insert_insights on insights for insert to anon with check (true);
create policy anon_update_insights on insights for update to anon using (true) with check (true);
-- deliberately NO delete policy for anon.

drop trigger if exists insights_updated_at on insights;
create trigger insights_updated_at before update on insights
  for each row execute function set_updated_at();   -- reuses the store's existing trigger fn
```

**Constraints:** the CHECK clauses above enforce `category` (six values), `status`, and `source` at the
database, in addition to app-level validation.

**Blast radius:** anon can add/edit insight rows and soft-reject them. Anon cannot delete any row, and
cannot write `meetings`/`participants`/`themes`. A malicious visitor could tamper with insights only.

## Lifecycle

```
meeting-processor ──insert──▶ insights (source=extracted, status=candidate)
dashboard accept  ──update──▶ status=accepted
dashboard reject  ──update──▶ status=rejected        (hidden; retained, never deleted)
transcript highlight+note ──insert──▶ (source=manual, status=accepted, quote=selection, content=note)
dashboard edit    ──update──▶ content / category / quote
```

Feeds show `status=accepted` only. Candidates appear solely on their meeting page for triage.

## Component changes

### `groups/global/skills/meeting-transcriber/schema.sql`
Append the `insights` table + policies + trigger above (idempotent, re-runnable).

### `groups/global/skills/meeting-transcriber/supabase_store.py`
Add:
- `insert_insights(meeting_id, items)` — bulk insert; `items` = `[{content, category, quote?, source, status}]`.
- `meeting_has_extracted_insights(meeting_id) -> bool` — for idempotent backfill.

### `groups/global/skills/meeting-processor/SKILL.md`
New section **4c. Extract candidate insights** (after 4b saves the summary): produce 3–7 insights,
each `{content, category, quote?}`, insert via `supabase_store.insert_insights(id, items)` with
`source='extracted'`, `status='candidate'`. Guidance on what qualifies as an insight (a reusable
signal/learning/risk/opportunity/quote worth carrying across meetings — not a restatement of the
summary) and how to pick a category. Skip if the meeting already has extracted insights.

### `groups/global/skills/meeting-transcriber/backfill_insights.py` (new, one-time)
For the 20 most-recent meetings with a non-null `summary_md`, ordered by `date desc`: if the meeting has
no extracted insights yet, read `title` + `summary_md` (not the transcript), derive 3–7 candidate
insights, insert as candidates. Idempotent; logs a per-meeting count. Run as an agent task (LLM judgment
needed), same pattern as the classification pass — a scripted loop that hands each summary to the agent.

### Dashboard (`groups/global/meeting-insights/`)
- `src/lib/insights.ts` — types (`Insight`, `Category`, `Status`), `CATEGORIES` constant, and pure
  helpers: `buildManualInsight(meetingId, quote, note, category)`, `groupByMeeting(insights)`.
- `src/lib/supabase.ts` — `fetchInsights(): Promise<Insight[]>` (all rows), plus write helpers
  `insertInsight(row)`, `updateInsight(id, patch)` via the anon client (RLS-permitted).
- `src/views/MeetingDetail.tsx` — new **Insights** section: candidates with Accept/Reject, accepted with
  Edit; transcript selection (`window.getSelection()` inside the `<pre>`) raises a small "＋ Add insight"
  popover → note textarea + category select → submit. Optimistic local update, refetch on error.
- `src/views/Insights.tsx` — **repurposed** to the accepted-insights feed: list grouped/filterable by
  category and meeting, each item links to `#/meeting/<id>`, inline Edit.
- `src/views/Stats.tsx` — **new**, holds the current stat tiles + per-week / theme / type charts moved
  out of the old Insights view.
- `src/App.tsx` — routes/nav: Calendar · List · Insights · People · Stats (`#/insights`, `#/stats`).
- App fetches insights once alongside the meeting index and passes them down; writes update that state.

## Error handling

- Write failure (network / RLS): revert the optimistic change and show an inline error on the affected
  insight; never lose the user's typed note (keep the form open on failure).
- Extraction failure in meeting-processor: log to the Slack log channel; the summary/pipeline still
  succeeds (insights are additive, never block a summary).
- Backfill: per-meeting try/scope; a failed meeting is logged and skipped, others proceed.

## Testing

- **RLS probes** (curl, anon key): INSERT insights → 201; UPDATE insights → 204; DELETE insights → 403;
  INSERT meetings → 403 (unchanged).
- **Dashboard unit tests (vitest):** `buildManualInsight` payload shape; `groupByMeeting`; the
  accept/reject/edit state-transition reducer (candidate→accepted, →rejected, edit content/category);
  `CATEGORIES` completeness; feed filter excludes non-accepted.
- **Extraction:** verified on the backfill run (counts per meeting) and the next live meeting.
- **Manual:** highlight a transcript span, add a note, confirm it appears accepted on the meeting page
  and in the feed; edit it; reject a candidate and confirm it disappears from both.

## Out of scope (explicit)

- Real auth on writes (deferred; RLS is scoped so the blast radius is insight-only).
- Deleting insights (reject is a soft status; hard delete not exposed).
- Insight-to-Linear or insight-to-learnings-journal syncing (the git learnings journal continues
  independently for now).
- Character-offset transcript anchoring — we store the quoted text, not positions.

## Open items for implementation

- Exact insight-extraction prompt wording in SKILL.md (what qualifies, category rubric).
