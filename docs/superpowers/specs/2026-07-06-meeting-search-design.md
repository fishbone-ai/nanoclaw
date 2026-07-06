# Meeting & Notes Search for the Slack Agent

Status: approved (2026-07-06)
Related: [meeting-insights-dashboard](2026-07-05-meeting-insights-dashboard-design.md), [meeting-insights-curation](2026-07-05-meeting-insights-curation-design.md)

## Problem

FishboneClaw (the Slack agent) should be able to easily search and refer to past
meetings and notes — "what did we discuss with Michael Colao?", "have we heard the
audit-trail objection?", "VC calls in June". Today it has no search: it can only
fetch a meeting by exact id or fire ad-hoc PostgREST queries, which is token-heavy,
inconsistent, and can't rank across sources.

## Decisions (locked during brainstorming)

- **Search style: keyword / structured**, not semantic. Postgres full-text search
  (FTS), no embeddings, ships now. Designed so semantic (pgvector) could be layered
  onto the same tool later without changing the agent-facing surface.
- **Corpus: meeting summaries + transcripts + curated insights** — all already in
  Supabase. The `learnings/*.md` journal is explicitly out of scope (being
  superseded by the insights table).
- **Approach C**: a Postgres FTS function does the search + ranking; a thin Python
  wrapper exposes it; a skill teaches the agent to call and format it. Chosen over
  raw DB access (A, not actually *easy*) and a Python-only tool (B, multiple
  round-trips + client-side merge).

## Architecture

```
Slack msg → FishboneClaw (container) → meeting-search SKILL
   parse NL → query + filters → supabase_store.search_meetings(...)
      → POST /rest/v1/rpc/search_meetings  (SERVICE_KEY, bypasses RLS)
        → Postgres search_meetings(q, filters): FTS + rank + snippet
      ← ranked rows → agent formats → Slack (title · date · snippet · dashboard link)
```

The only new persistent DB objects: three generated `tsvector` columns, their GIN
indexes, and one SQL function — all appended idempotently to
`groups/global/skills/meeting-transcriber/schema.sql`.

## Component 1 — FTS columns & indexes (schema.sql)

Generated `tsvector` columns (stored, so GIN-indexable):

- `meetings.summary_vec` = `setweight(to_tsvector('english', coalesce(title,'')), 'A') || setweight(to_tsvector('english', coalesce(summary_md,'')), 'B')`
- `meetings.transcript_vec` = `to_tsvector('simple', coalesce(transcript_md,''))`
  — `simple` config so Hebrew transcript tokens still match (no English stemming
  applied to Hebrew); English exact tokens still match.
- `insights.search_vec` = `setweight(to_tsvector('english', coalesce(content,'')), 'A') || setweight(to_tsvector('english', coalesce(quote,'')), 'B')`

GIN index on each. All `create ... if not exists` / `add column if not exists` so
the migration is idempotent.

**Language note:** summaries/insights/titles are English (pipeline output) → `english`.
Transcripts are mixed Hebrew/English → `simple` (best-effort; summaries are the
primary hit target). If Hebrew transcript recall proves insufficient, a future
change can add a Hebrew dictionary or a `simple`-config summary vector — not now.

## Component 2 — The SQL function

```sql
create or replace function search_meetings(
  q           text default null,                     -- free text; null = filters-only
  sources     text[] default array['summary','transcript','insight'],
  participant text default null,                      -- name ILIKE '%participant%'
  mtype       text default null,                      -- meetings.type
  date_from   date default null,
  date_to     date default null,
  max_results int  default 20
) returns table(source text, meeting_id text, title text, date date, snippet text, rank real)
language sql stable
```

Behavior:

- Builds `websearch_to_tsquery('english', q)` for summary/insight sources and
  `websearch_to_tsquery('simple', q)` for transcript.
- UNION ALL across the requested `sources`:
  - **summary**: `meetings` where `summary_vec @@ query_en`; `snippet =
    ts_headline('english', coalesce(summary_md, title), query_en, 'StartSel=*,StopSel=*,MaxWords=35,MinWords=15')`; `rank = ts_rank(summary_vec, query_en) * 1.0`.
  - **transcript**: `meetings` where `transcript_vec @@ query_simple`; snippet via
    `ts_headline('simple', transcript_md, query_simple, ...)`; `rank = ts_rank(...) * 0.4` (boost down — noisier).
  - **insight**: `insights` join `meetings` for title/date; where `search_vec @@
    query_en`; `snippet = coalesce(quote, content)`; `rank = ts_rank(...) * 0.8`.
- Structured filters apply to every meeting-based row:
  `participant` → `exists (select 1 from participants p where p.meeting_id = m.id and p.name ilike '%'||participant||'%')`;
  `mtype` → `m.type = mtype`; `date_from`/`date_to` → `m.date` bounds.
- **`q` is null** → skip the `@@` predicate entirely; return filter matches ordered
  `date desc` with `rank = 0` (handles "meetings with Dana in June").
- Final: `order by rank desc, date desc limit max_results`.
- `grant execute on function search_meetings(...) to anon;` so the dashboard can
  reuse the identical search later (not built now).

Applied via the pooler `psql` (`docker run --rm -i postgres:18-alpine psql "$POOLER_URL" -f schema.sql`) or the Supabase SQL editor. Idempotent.

## Component 3 — The Python tool (supabase_store.py)

```python
def search_meetings(query=None, sources=None, participant=None, mtype=None,
                    date_from=None, date_to=None, limit=20) -> list[dict]:
    args = {"q": query, "sources": sources, "participant": participant,
            "mtype": mtype, "date_from": date_from, "date_to": date_to,
            "max_results": limit}
    rows = _request("POST", "rpc/search_meetings",
                    body={k: v for k, v in args.items() if v is not None}) or []
    for r in rows:
        r["url"] = f"https://meetings.getfishbone.ai/#/meeting/{r['meeting_id']}"
    return rows
```

- Uses existing `_request` (SERVICE_KEY, so RLS-exempt). PostgREST maps SQL
  functions to `POST /rest/v1/rpc/<name>` with JSON args.
- Drops `None` args so Postgres defaults apply.
- Returns `[{source, meeting_id, title, date, snippet, rank, url}]`.

## Component 4 — The skill (skills/meeting-search/SKILL.md)

Registered in `groups/global/CLAUDE.md` skills table. Triggers: "search meetings",
"what did we discuss/decide about…", "have we talked to/heard from…", "find the
meeting where…", "notes on X", references to past people/meetings.

Instructs the agent to:
1. **Parse NL → args**: person → `participant`; month/quarter/"last week" →
   `date_from`/`date_to` (compute absolute dates); kind ("VC calls", "retros") →
   `mtype`; remaining topic words → `query`. Structured-only asks pass `query=None`.
2. **Call** `supabase_store.search_meetings(...)` (sys.path insert to the
   meeting-transcriber skill dir, same pattern as meeting-processor).
3. **Format for Slack** (top ~5 hits):
   ```
   *<title>* · 2026-06-30 · Discovery
   > …matched *snippet* (terms already bolded by ts_headline)…
   <https://meetings.getfishbone.ai/#/meeting/<id>|Open>
   ```
   Label insight hits with `💡 insight`. If empty → say so, offer to broaden
   (drop a filter / include transcripts).
4. **Guardrail**: read/reference only — never mutate.

## Component 5 — Testing

- **Python** (`test_supabase_store.py`, existing stdlib `unittest` + `mock.patch`
  urlopen style): `search_meetings` POSTs to `rpc/search_meetings`; `None` args are
  dropped from the body; `sources`/`participant`/date filters pass through; returned
  rows get the dashboard `url`. RED→GREEN.
- **SQL / integration** (checklist item, not unit-testable without a DB): apply the
  migration, then run three real probes and confirm ranked hits:
  1. keyword only — e.g. `search_meetings('audit trail')`
  2. person filter — `search_meetings(None, participant='Michael Colao')`
  3. structured-only — `search_meetings(None, mtype='vc-meeting', date_from='2026-06-01', date_to='2026-06-30')`

## Out of scope (YAGNI)

- Semantic / vector search (pgvector, embeddings).
- Dashboard search box (the SQL function is granted to `anon` so it's a later
  drop-in, but no UI now).
- Searching the `learnings/*.md` journal.
- Any write/curation path — search is read-only.

## Success criteria

FishboneClaw answers "what did we discuss with <person>?" / "have we heard <topic>?"
/ "<kind> calls in <month>?" in one tool call, returning ranked, snippet-highlighted
hits with dashboard links, formatted for Slack — no hand-crafted queries, consistent
across runs.
