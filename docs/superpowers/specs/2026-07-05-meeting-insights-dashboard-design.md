# Meeting Insights Dashboard — Design

**Date:** 2026-07-05
**Status:** Approved (pending spec review)

## Problem

The meeting pipeline (Drive → `transcribe.py` → Gemini transcription → `meeting-processor` → Slack summary) produces rich structured data — participants, decisions, learnings, themes — and then throws the structure away: transcripts are git commits, summaries are ephemeral Slack messages. Consequences:

- `reconcile.py` must scan Slack message history to detect which transcripts lack summaries (brittle, capped at 100 messages).
- No way to browse, search, or analyze 179+ meetings: who we met, which themes recur, how discovery is trending.
- The nanoclaw git repo absorbs every transcript as a `feat(transcription)` commit — the repo is becoming a database.

## Goal

Promote meetings (transcripts + summaries + extracted structure) to first-class data in a real store, and serve a dashboard with three jobs, chosen explicitly:

1. **Browse & search meetings** — chronological, filterable index; click through to summary + full transcript.
2. **People & pipeline tracking** — who we met (practitioners, VCs, founders), role/company, meeting history per person.
3. **Cross-meeting insights** — theme frequency over time, meeting volume/type trends.

(Action-item tracking was considered and explicitly deferred.)

## Decisions made during brainstorming

| Decision | Choice |
|---|---|
| Store | Supabase Postgres (existing project; exact project confirmed at setup) |
| Dashboard hosting | GitHub Pages, static site, like `fishbone-ai/cyber-mindmap` |
| Auth | None for now — anon read access; RLS makes auth a later config change, not a migration |
| Data exposure | Everything published, including full transcripts |
| Git's role | Supabase only. `transcribe.py` stops committing transcripts; `calls/meetings/` becomes a frozen archive |
| Backfill | Import existing summaries from Slack history where they exist; regenerate only the missing ones |

## Architecture

```
Drive recordings
      │
transcribe.py (cron */10) ──INSERT──▶ Supabase: meetings (transcript row, summary_md NULL)
      │ NEW_TRANSCRIPTS
      ▼
meeting-processor (agent) ──UPDATE──▶ + summary_md, title, type, participants, themes, slack_ts
      │
      └──▶ Slack #meeting-summaries post (unchanged)

reconcile.py (cron */15): SELECT id FROM meetings WHERE summary_md IS NULL
      └──▶ PENDING_TRANSCRIPTS → meeting-processor

GitHub Pages dashboard (fishbone-ai/meeting-insights)
      └── supabase-js + anon key ──▶ live reads (no rebuild/redeploy per meeting)
```

## Schema (Supabase, `public` schema)

```sql
create table meetings (
  id            text primary key,        -- filename stem, e.g. 2026-07-05-bxw-faqy-yqf-2026-07-05-15-47-gmt-3
  date          date not null,
  title         text,
  type          text,                    -- discovery-call | vc-meeting | internal-strategy | phone-call | weekly-retro | weekly-kickoff | other
  language      text,                    -- he | en | mixed
  source        text,                    -- meet | phone | whatsapp | voice
  transcript_md text,
  summary_md    text,                    -- NULL = summary pending
  slack_ts      text,
  imported_from text,                    -- 'slack' for backfilled summaries, NULL otherwise
  created_at    timestamptz default now(),
  updated_at    timestamptz default now()
);

create table participants (
  meeting_id text references meetings(id) on delete cascade,
  name       text not null,
  category   text,                       -- founder | practitioner | vc | advisor | other
  role       text,
  company    text,
  primary key (meeting_id, name)
);

create table themes (
  meeting_id text references meetings(id) on delete cascade,
  theme      text not null,
  primary key (meeting_id, theme)
);
```

**RLS:** enabled on all three tables. Anon role: SELECT only. Writes require the service role key (pipeline only). Adding auth later = replace the anon SELECT policy with an authenticated one; no data migration.

**Idempotency:** all pipeline writes are upserts keyed on `id` (participants/themes: delete-and-reinsert for the meeting). A failed or repeated run converges to the same state.

## Component changes

### `groups/global/skills/meeting-transcriber/transcribe.py`
- After successful transcription: upsert the meeting row (`id`, `date`, `language`, `source`, `transcript_md`) via Supabase REST (`requests`, service key).
- Remove git commit/push of transcript files and stop writing local `.md` transcripts entirely — Supabase is the only destination. `.transcriber-state.json` remains the Drive-side dedup state (moved out of `calls/meetings/` to the skill directory).

### `groups/global/skills/meeting-transcriber/reconcile.py`
- Replace Slack-history scanning with one query: `GET /rest/v1/meetings?summary_md=is.null&select=id`.
- Emits `PENDING_TRANSCRIPTS` as today; delete `summary_exists_for()` and Slack pagination logic.

### `groups/global/skills/meeting-processor/SKILL.md`
- Step 0 dedup check becomes: fetch the meeting row; if `summary_md` is non-null, stop. (Replaces Slack search.)
- Step 1 reads the transcript from the Supabase row (fallback: local file for legacy paths).
- New step after the Slack post: UPDATE the row with `summary_md`, `title`, `type`, `slack_ts`; replace participants and themes rows.
- Slack post format unchanged.

### Secrets
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` added to the transcriber group's container env — same mechanism as `GEMINI_API_KEY` today. Anon key is public by design and lives in the dashboard bundle.

### Dashboard — new repo `fishbone-ai/meeting-insights`
- Static Vite + TypeScript app on GitHub Pages (cyber-mindmap pattern). `supabase-js` with anon key; no backend.
- **Meetings view:** chronological list; client-side text search; filters: type, theme, participant, date range. Detail view renders `summary_md` and `transcript_md` (transcript fetched per-meeting on open, not with the index).
- **People view:** aggregation over `participants`: name, company, category, meeting count, first/last met, links to meetings.
- **Insights view:** theme frequency over time (by week), meetings per week, breakdown by type, most-met people.
- Index query selects everything except `transcript_md` to keep initial load small.

### Backfill (one-time script, run inside the transcriber group container)
1. For each of the ~179 files in `calls/meetings/*.md`: parse stem/date/language from filename + header, upsert transcript rows.
2. Paginate the full `#meeting-summaries` Slack history (cursor-based, not `limit=100`), parse the known post format (`*Meeting: <title>* | date`, participants block, sections), match to meeting `id` by filename stem, attach `summary_md`, `title`, participants, `slack_ts`, `imported_from='slack'`.
3. Batch inference pass (agent) fills `type` and `themes` from summary text only — not transcripts — to keep cost low.
4. Meetings still lacking summaries surface via the new `reconcile.py` automatically and flow through meeting-processor in batches.
5. Importer never overwrites a non-null `summary_md`.

## Error handling

- Supabase write failures: script exits nonzero with the error in output; the agent reports to the Slack log channel (`C0ALJGPQSL8`), and the next cron cycle retries (upserts make this safe).
- Malformed Slack summaries during backfill: skipped and listed in the script report; those meetings fall through to regeneration.
- Dashboard: if Supabase is unreachable, show an explicit error state, not a blank page.

## Testing

- Unit tests for the Slack-summary parser (backfill) against real captured message samples, including malformed ones.
- Unit tests for the Supabase write module with mocked HTTP (upsert payload shape, idempotent re-run).
- RLS verification: anon-key write attempt must fail; anon-key read must succeed.
- Dashboard: smoke test that index query renders a list from a seeded fixture project; the rest manual.

## Out of scope (explicit)

- Auth on the dashboard (later; RLS design keeps the path open).
- Action-item/decision tracking views.
- Editing meetings from the dashboard (read-only v1).
- Migrating the git history of existing transcripts (archive stays as-is).

## Open items for implementation

- Which existing Supabase project to use (only known candidate today: the FitBot project `iejvqtvnrthvhxemonlz`); user provides URL + service key at setup.
- GitHub Pages deployment details for the new repo (public repo, or private + Pages if the org plan allows).
