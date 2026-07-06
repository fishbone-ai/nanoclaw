# Meeting & Notes Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Slack agent (FishboneClaw) a one-call keyword search over meeting summaries, transcripts, and curated insights that returns ranked, snippet-highlighted hits with dashboard links.

**Architecture:** A Postgres full-text-search function (`search_meetings`) does the matching, ranking, and snippet extraction across three generated `tsvector` columns; a thin Python wrapper in `supabase_store.py` exposes it via PostgREST RPC; a `meeting-search` skill teaches the agent to parse a natural-language ask into query + filters and format results for Slack.

**Tech Stack:** Supabase Postgres (FTS: `to_tsvector`/`websearch_to_tsquery`/`ts_rank`/`ts_headline`, GIN indexes, PL/pgSQL-free SQL function), stdlib Python (`urllib`, `unittest`), PostgREST `/rpc/`, Slack mrkdwn.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-06-meeting-search-design.md`. Every task's requirements implicitly include it.
- Corpus is meetings (`summary_md`, `transcript_md`, `title`) + `insights` (`content`, `quote`) — all in Supabase. `learnings/*.md` is out of scope.
- Keyword/FTS only — NO embeddings, NO pgvector, NO semantic search.
- Search is READ-ONLY — no task introduces a write/mutation path.
- Python is stdlib-only (host has no `requests`/`pytest`); tests run with `python3 -m unittest`.
- FTS configs: `english` for summary/title/insight (stemming); `simple` for transcript (Hebrew-safe token match).
- Rank source boosts: summary ×1.0, insight ×0.8, transcript ×0.4.
- All schema changes are idempotent (`if not exists` / `create or replace`), appended to `groups/global/skills/meeting-transcriber/schema.sql`.
- Dashboard base URL for links: `https://meetings.getfishbone.ai/#/meeting/<id>`.
- Git commits use trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

## File Structure

- `groups/global/skills/meeting-transcriber/schema.sql` — **modify** (append FTS columns, GIN indexes, `search_meetings` function, grant). Idempotent migration.
- `groups/global/skills/meeting-transcriber/supabase_store.py` — **modify** (append `search_meetings` wrapper).
- `groups/global/skills/meeting-transcriber/test_supabase_store.py` — **modify** (append wrapper tests).
- `groups/global/skills/meeting-search/SKILL.md` — **create** (agent-facing skill).
- `groups/global/CLAUDE.md` — **modify** (register the skill in the skills table).

---

### Task 1: Postgres FTS engine (schema + function)

**Files:**
- Modify: `groups/global/skills/meeting-transcriber/schema.sql` (append at end)

**Interfaces:**
- Consumes: existing tables `meetings(id,title,summary_md,transcript_md,type,date)`, `participants(meeting_id,name)`, `insights(meeting_id,content,quote)`.
- Produces: SQL function `search_meetings(q text, sources text[], participant text, mtype text, date_from date, date_to date, max_results int)` returning rows `(source text, meeting_id text, title text, date date, snippet text, rank real)`, reachable at `POST /rest/v1/rpc/search_meetings`. Generated columns `meetings.summary_vec`, `meetings.transcript_vec`, `insights.search_vec`.

- [ ] **Step 1: Append the FTS columns, indexes, function, and grant to schema.sql**

Append exactly this block to the end of `schema.sql`:

```sql
-- ── Full-text search (see 2026-07-06-meeting-search-design.md) ──────────────
-- Generated tsvector columns (explicit regconfig => IMMUTABLE => allowed as STORED).
alter table meetings add column if not exists summary_vec tsvector
  generated always as (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(summary_md, '')), 'B')
  ) stored;
alter table meetings add column if not exists transcript_vec tsvector
  generated always as (to_tsvector('simple', coalesce(transcript_md, ''))) stored;
alter table insights add column if not exists search_vec tsvector
  generated always as (
    setweight(to_tsvector('english', coalesce(content, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(quote, '')), 'B')
  ) stored;

create index if not exists meetings_summary_vec_idx    on meetings using gin (summary_vec);
create index if not exists meetings_transcript_vec_idx on meetings using gin (transcript_vec);
create index if not exists insights_search_vec_idx     on insights using gin (search_vec);

-- Unified keyword search across summaries, transcripts, and insights.
-- q null/'' => filters-only (no FTS); transcript rows require a query (excluded when q is null).
create or replace function search_meetings(
  q           text    default null,
  sources     text[]  default array['summary','transcript','insight'],
  participant text    default null,
  mtype       text    default null,
  date_from   date    default null,
  date_to     date    default null,
  max_results int     default 20
) returns table(source text, meeting_id text, title text, date date, snippet text, rank real)
language sql stable
as $func$
  with qe as (select case when q is null or q = '' then null else websearch_to_tsquery('english', q) end as tsq),
       qs as (select case when q is null or q = '' then null else websearch_to_tsquery('simple',  q) end as tsq)
  select 'summary'::text, m.id, m.title, m.date,
         case when qe.tsq is null
              then left(regexp_replace(coalesce(m.summary_md, m.title, ''), '\s+', ' ', 'g'), 160)
              else ts_headline('english', coalesce(m.summary_md, m.title, ''), qe.tsq,
                               'StartSel=*, StopSel=*, MaxWords=35, MinWords=15, ShortWord=2') end,
         (case when qe.tsq is null then 0 else ts_rank(m.summary_vec, qe.tsq) end * 1.0)::real
  from meetings m, qe
  where 'summary' = any(sources)
    and (qe.tsq is null or m.summary_vec @@ qe.tsq)
    and (mtype is null or m.type = mtype)
    and (date_from is null or m.date >= date_from)
    and (date_to   is null or m.date <= date_to)
    and (participant is null or exists (
          select 1 from participants p where p.meeting_id = m.id and p.name ilike '%'||participant||'%'))
  union all
  select 'transcript'::text, m.id, m.title, m.date,
         ts_headline('simple', coalesce(m.transcript_md, ''), qs.tsq,
                     'StartSel=*, StopSel=*, MaxWords=35, MinWords=15, ShortWord=2'),
         (ts_rank(m.transcript_vec, qs.tsq) * 0.4)::real
  from meetings m, qs
  where 'transcript' = any(sources)
    and qs.tsq is not null and m.transcript_vec @@ qs.tsq
    and (mtype is null or m.type = mtype)
    and (date_from is null or m.date >= date_from)
    and (date_to   is null or m.date <= date_to)
    and (participant is null or exists (
          select 1 from participants p where p.meeting_id = m.id and p.name ilike '%'||participant||'%'))
  union all
  select 'insight'::text, m.id, m.title, m.date,
         coalesce(i.quote, i.content),
         (case when qe.tsq is null then 0 else ts_rank(i.search_vec, qe.tsq) end * 0.8)::real
  from insights i join meetings m on m.id = i.meeting_id, qe
  where 'insight' = any(sources)
    and (qe.tsq is null or i.search_vec @@ qe.tsq)
    and (mtype is null or m.type = mtype)
    and (date_from is null or m.date >= date_from)
    and (date_to   is null or m.date <= date_to)
    and (participant is null or exists (
          select 1 from participants p where p.meeting_id = m.id and p.name ilike '%'||participant||'%'))
  order by rank desc, date desc
  limit max_results;
$func$;

grant execute on function search_meetings(text, text[], text, text, date, date, int) to anon;
```

- [ ] **Step 2: Apply the migration to Supabase**

The direct DB host is IPv6-only (unreachable from this box) — use the pooler. The pooler connection string is provided at execution time (host `aws-1-eu-central-1.pooler.supabase.com:5432`, user `postgres.iejvqtvnrthvhxemonlz`); do NOT hardcode the password in any committed file. Run:

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
docker run --rm -i postgres:18-alpine psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f schema.sql
```

Expected: no error; `CREATE FUNCTION`, `ALTER TABLE`, `CREATE INDEX` (or `NOTICE ... already exists, skipping`) lines. Re-running must stay clean (idempotent).

- [ ] **Step 3: Integration probe — keyword search**

```bash
docker run --rm -i postgres:18-alpine psql "$SUPABASE_DB_URL" -A -F$'\t' -c \
  "select source, meeting_id, round(rank::numeric,3) from search_meetings('audit trail') limit 5;"
```
Expected: 0+ rows, ordered by rank desc; if any, summary/insight rows outrank transcript rows for comparable matches. (Zero rows is acceptable only if the term genuinely does not appear — try another common term like `security` to confirm the function works.)

- [ ] **Step 4: Integration probe — participant filter (no keyword)**

```bash
docker run --rm -i postgres:18-alpine psql "$SUPABASE_DB_URL" -A -F$'\t' -c \
  "select source, meeting_id, date from search_meetings(null, participant := 'Michael Colao');"
```
Expected: the meeting(s) with that participant, `source='summary'`, `rank=0`, ordered by date desc. No transcript rows (transcript needs a query).

- [ ] **Step 5: Integration probe — structured-only (type + month)**

```bash
docker run --rm -i postgres:18-alpine psql "$SUPABASE_DB_URL" -A -F$'\t' -c \
  "select meeting_id, date from search_meetings(null, mtype := 'vc-meeting', date_from := '2026-06-01', date_to := '2026-06-30');"
```
Expected: only `vc-meeting` rows dated within June 2026 (or empty if none — verify by loosening the date range).

- [ ] **Step 6: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/schema.sql
git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(search): Postgres FTS function + tsvector columns for meeting search

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Python search wrapper (TDD)

**Files:**
- Modify: `groups/global/skills/meeting-transcriber/supabase_store.py` (append `search_meetings`)
- Test: `groups/global/skills/meeting-transcriber/test_supabase_store.py` (append tests)

**Interfaces:**
- Consumes: existing `_request(method, path, body=None, prefer=None)` and the `search_meetings` SQL function from Task 1 (reached at `rpc/search_meetings`).
- Produces: `search_meetings(query=None, sources=None, participant=None, mtype=None, date_from=None, date_to=None, limit=20) -> list[dict]` where each dict is `{source, meeting_id, title, date, snippet, rank, url}`.

- [ ] **Step 1: Write the failing tests**

Append to `test_supabase_store.py` (inside `TestSupabaseStore`, uses the existing `fake_response` helper and `@mock.patch("supabase_store.urlopen")`):

```python
    @mock.patch("supabase_store.urlopen")
    def test_search_meetings_posts_rpc_with_filtered_body(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([
            {"source": "summary", "meeting_id": "m1", "title": "T",
             "date": "2026-06-30", "snippet": "...*audit*...", "rank": 0.51},
        ]).encode())
        rows = ss.search_meetings("audit trail", participant="Dana", date_from="2026-06-01")
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("/rest/v1/rpc/search_meetings", req.full_url)
        body = json.loads(req.data)
        # None args dropped; max_results always sent; q mapped from query
        self.assertEqual(body, {"q": "audit trail", "participant": "Dana",
                                "date_from": "2026-06-01", "max_results": 20})
        self.assertEqual(rows[0]["url"], "https://meetings.getfishbone.ai/#/meeting/m1")

    @mock.patch("supabase_store.urlopen")
    def test_search_meetings_filters_only_omits_q(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        ss.search_meetings(mtype="vc-meeting", limit=5)
        body = json.loads(urlopen.call_args[0][0].data)
        self.assertNotIn("q", body)
        self.assertEqual(body["mtype"], "vc-meeting")
        self.assertEqual(body["max_results"], 5)

    @mock.patch("supabase_store.urlopen")
    def test_search_meetings_empty_returns_list(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        self.assertEqual(ss.search_meetings("nothing matches"), [])
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
python3 -m unittest test_supabase_store -v 2>&1 | tail -6
```
Expected: FAIL — `AttributeError: module 'supabase_store' has no attribute 'search_meetings'`.

- [ ] **Step 3: Implement the wrapper**

Append to `supabase_store.py`:

```python
def search_meetings(query=None, sources=None, participant=None, mtype=None,
                    date_from=None, date_to=None, limit=20) -> list[dict]:
    """Keyword search across meeting summaries, transcripts, and insights.
    Calls the search_meetings SQL function via PostgREST RPC. Returns ranked
    hits, each decorated with a dashboard url. query=None => filters-only."""
    args = {
        "q": query, "sources": sources, "participant": participant,
        "mtype": mtype, "date_from": date_from, "date_to": date_to,
        "max_results": limit,
    }
    rows = _request("POST", "rpc/search_meetings",
                    body={k: v for k, v in args.items() if v is not None}) or []
    for r in rows:
        r["url"] = f"https://meetings.getfishbone.ai/#/meeting/{r['meeting_id']}"
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
python3 -m unittest test_supabase_store -v 2>&1 | tail -6
```
Expected: PASS — all tests OK (13 existing + 3 new = 16).

- [ ] **Step 5: Live end-to-end probe (real DB, real RPC)**

Confirms the wrapper talks to the Task 1 function end to end (needs `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` in env):

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
python3 -c "import supabase_store as s, json; print(json.dumps(s.search_meetings('security', limit=3), ensure_ascii=False, indent=2)[:800])"
```
Expected: a JSON list (possibly empty) of hits, each with `source`, `meeting_id`, `snippet`, `rank`, and a `url` starting `https://meetings.getfishbone.ai/#/meeting/`.

- [ ] **Step 6: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/supabase_store.py \
        groups/global/skills/meeting-transcriber/test_supabase_store.py
git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(search): supabase_store.search_meetings RPC wrapper

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: meeting-search skill + registration

**Files:**
- Create: `groups/global/skills/meeting-search/SKILL.md`
- Modify: `groups/global/CLAUDE.md` (skills table)

**Interfaces:**
- Consumes: `supabase_store.search_meetings(...)` from Task 2.
- Produces: agent-facing skill triggered by search-style asks; no code exports.

- [ ] **Step 1: Create the skill**

Create `groups/global/skills/meeting-search/SKILL.md` with exactly this content:

````markdown
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
````

- [ ] **Step 2: Register the skill in CLAUDE.md**

In `groups/global/CLAUDE.md`, in the Skills table, add this row immediately after the
`meeting-processor` row:

```markdown
| meeting-search | `skills/meeting-search/SKILL.md` | Search & refer to past meetings and notes — find meetings by topic/person/date, recall decisions, check if we've heard something before. Dashboard: https://meetings.getfishbone.ai/ |
```

- [ ] **Step 3: Verify the skill is discoverable and the path resolves**

```bash
cd /share/nanoclaw/groups/global
test -f skills/meeting-search/SKILL.md && echo "SKILL present"
grep -q "meeting-search" CLAUDE.md && echo "registered in CLAUDE.md"
head -8 skills/meeting-search/SKILL.md
```
Expected: both echo lines print; frontmatter `name: meeting-search` shows.

- [ ] **Step 4: End-to-end dry run of the documented call**

Runs the exact snippet the skill tells the agent to run (needs `SUPABASE_URL` +
`SUPABASE_SERVICE_KEY` in env):

```bash
cd /tmp && python3 -c "
import sys; sys.path.insert(0, '/share/nanoclaw/groups/global/skills/meeting-transcriber')
import supabase_store
hits = supabase_store.search_meetings(query='security', limit=3)
for h in hits:
    print(h['source'], h['date'], '-', (h['title'] or h['meeting_id'])[:40], '->', h['url'])
print('total', len(hits))
"
```
Expected: prints up to 3 ranked hits with urls (or `total 0` if the term is absent — try another term to confirm), no traceback.

- [ ] **Step 5: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-search/SKILL.md groups/global/CLAUDE.md
git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(search): meeting-search skill + registration

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- **Spec coverage:** FTS columns/indexes + `english`/`simple` configs + rank boosts + `search_meetings` function + `grant to anon` → Task 1. Python wrapper (`rpc/search_meetings`, drop-None, url decoration) → Task 2. Skill (NL→args parse, Slack formatting, read-only guardrail) + CLAUDE.md registration → Task 3. Testing: Python unit tests → Task 2 Steps 1-4; SQL integration probes → Task 1 Steps 3-5 + live probes Task 2 Step 5 / Task 3 Step 4. Out-of-scope items (semantic, dashboard UI, learnings journal, writes) are absent by construction. ✅
- **Placeholder scan:** no TBD/TODO; every code and SQL step is complete and literal. ✅
- **Type consistency:** return columns `(source, meeting_id, title, date, snippet, rank)` are identical in the SQL function (Task 1), the wrapper's decorated dict (Task 2 adds `url`), and the skill's documented shape (Task 3). Wrapper signature `search_meetings(query, sources, participant, mtype, date_from, date_to, limit)` matches the skill's call site and the SQL params (wrapper maps `query`→`q`, `limit`→`max_results`). ✅
