# Meeting Insights Curation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add curated per-meeting insights — extracted by meeting-processor, accepted/rejected/edited and hand-created (transcript highlight + note) in the dashboard, surfaced on the meeting page and a new Insights feed.

**Architecture:** A new Supabase `insights` table with scoped anon RLS (SELECT/INSERT/UPDATE only) lets the public static dashboard write directly via the existing supabase-js anon client — no Worker. meeting-processor inserts candidates; the dashboard triages them; a one-time script backfills the 20 newest meetings from their summaries.

**Tech Stack:** Supabase Postgres + PostgREST; Python 3.12 stdlib (`urllib`, `unittest`) for pipeline; `@supabase/supabase-js` + React 19 + TypeScript + vitest for the dashboard.

**Spec:** `docs/superpowers/specs/2026-07-05-meeting-insights-curation-design.md`

## Global Constraints

- Reuse the existing store project: Supabase `iejvqtvnrthvhxemonlz`. Env vars already wired: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (pipeline), `SUPABASE_ANON_KEY` (verify scripts), and the anon key hardcoded in the dashboard's `src/lib/supabase.ts`.
- Apply SQL via dockerized psql (no host psql): `docker run --rm -i -e PGPASSWORD='<db-pass>' postgres:18-alpine psql -h aws-1-eu-central-1.pooler.supabase.com -p 5432 -U postgres.iejvqtvnrthvhxemonlz -d postgres -v ON_ERROR_STOP=1 -f - < file.sql`. DB password is provided by the user at Task 1.
- New Python modules import **stdlib only** (`urllib.request`, `json`, `os`, `unittest`). Tests run with `python3 -m unittest` from `groups/global/skills/meeting-transcriber/`.
- Enums — `category`: `signal | learning | risk | opportunity | quote | note`; `status`: `candidate | accepted | rejected`; `source`: `extracted | manual`. Enforced by SQL CHECK **and** app validation.
- Anon RLS on `insights`: SELECT + INSERT + UPDATE only. **No DELETE policy.** No new write policy on meetings/participants/themes. Reject = UPDATE status='rejected'.
- Dashboard: TDD with vitest; `npm test` and `npm run build` from `groups/global/meeting-insights/` must stay green. Deploy = commit + push that repo (SSH remote already configured); the Actions Pages deploy may need a `rerun-failed-jobs` past the flaky "try again later".
- nanoclaw-repo commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`. Dashboard-repo commits use `-c user.email=avikillu@gmail.com -c user.name="Fishbone Agent"`.
- No em-dashes in workspace prose files.

---

### Task 1: `insights` table + scoped anon RLS

**Files:**
- Modify: `groups/global/skills/meeting-transcriber/schema.sql` (append)

**Interfaces:**
- Produces: table `insights` in the store; anon can SELECT/INSERT/UPDATE it, cannot DELETE it, cannot write other tables.

- [ ] **Step 1: Append the insights DDL to `schema.sql`**

```sql

-- Curated per-meeting insights (see 2026-07-05-meeting-insights-curation-design.md)
create table if not exists insights (
  id          uuid primary key default gen_random_uuid(),
  meeting_id  text not null references meetings(id) on delete cascade,
  content     text not null,
  category    text not null default 'note' check (category in ('signal','learning','risk','opportunity','quote','note')),
  status      text not null default 'candidate' check (status in ('candidate','accepted','rejected')),
  source      text not null check (source in ('extracted','manual')),
  quote       text,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);
create index if not exists insights_meeting_idx on insights (meeting_id);
create index if not exists insights_feed_idx on insights (status, created_at desc);

alter table insights enable row level security;
drop policy if exists anon_read_insights   on insights;
drop policy if exists anon_insert_insights on insights;
drop policy if exists anon_update_insights on insights;
create policy anon_read_insights   on insights for select to anon using (true);
create policy anon_insert_insights on insights for insert to anon with check (true);
create policy anon_update_insights on insights for update to anon using (true) with check (true);

drop trigger if exists insights_updated_at on insights;
create trigger insights_updated_at before update on insights
  for each row execute function set_updated_at();
```

- [ ] **Step 2: Apply to Supabase**

```bash
docker run --rm -i -e PGPASSWORD='<db-pass>' postgres:18-alpine \
  psql -h aws-1-eu-central-1.pooler.supabase.com -p 5432 -U postgres.iejvqtvnrthvhxemonlz \
  -d postgres -v ON_ERROR_STOP=1 -f - < groups/global/skills/meeting-transcriber/schema.sql
```
Expected: `CREATE TABLE`, `CREATE INDEX`, `CREATE POLICY` x3, `CREATE TRIGGER` (earlier statements say "already exists, skipping" — fine, the file is idempotent).

- [ ] **Step 3: Verify RLS with the anon key**

Export `U=https://iejvqtvnrthvhxemonlz.supabase.co` and `PK=sb_publishable_dqHwjoGswlc3D3jg-a1HLA_OdLw7_NL`, and grab a real meeting id: `MID=$(curl -s "$U/rest/v1/meetings?select=id&limit=1" -H "apikey: $PK" | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["id"])')`.

```bash
# INSERT as anon must succeed (201). Capture the new id.
NID=$(curl -s "$U/rest/v1/insights" -H "apikey: $PK" -H "Authorization: Bearer $PK" \
  -H "Content-Type: application/json" -H "Prefer: return=representation" \
  -d "{\"meeting_id\":\"$MID\",\"content\":\"rls probe\",\"category\":\"note\",\"source\":\"manual\",\"status\":\"accepted\"}" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)[0]["id"])')
echo "inserted $NID"
# UPDATE as anon must succeed (204)
curl -s -o /dev/null -w 'update: %{http_code}\n' -X PATCH "$U/rest/v1/insights?id=eq.$NID" \
  -H "apikey: $PK" -H "Authorization: Bearer $PK" -H "Content-Type: application/json" \
  -d '{"content":"rls probe edited"}'
# DELETE as anon must FAIL (RLS: 0 rows deleted, but no delete policy → 403/empty). Verify row still there:
curl -s -o /dev/null -w 'delete: %{http_code}\n' -X DELETE "$U/rest/v1/insights?id=eq.$NID" -H "apikey: $PK" -H "Authorization: Bearer $PK"
curl -s "$U/rest/v1/insights?id=eq.$NID&select=id" -H "apikey: $PK" | python3 -c 'import json,sys; print("row still present:", len(json.load(sys.stdin))==1)'
# anon write to meetings must still FAIL (401/403)
curl -s -o /dev/null -w 'meetings write: %{http_code}\n' -X POST "$U/rest/v1/meetings" -H "apikey: $PK" -H "Authorization: Bearer $PK" -H "Content-Type: application/json" -d '{"id":"rls-probe-x","date":"2026-01-01"}'
```
Expected: insert 201, update 204, `row still present: True` (delete blocked by absence of policy), meetings write 401/403. Clean up the probe with the **service** key: `curl -s -X DELETE "$U/rest/v1/insights?id=eq.$NID" -H "apikey: $SERVICE" -H "Authorization: Bearer $SERVICE"`.

- [ ] **Step 4: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/schema.sql
git commit -m "feat(insights): insights table with scoped anon RLS (select/insert/update, no delete)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `supabase_store.py` — insights helpers

**Files:**
- Modify: `groups/global/skills/meeting-transcriber/supabase_store.py`
- Modify: `groups/global/skills/meeting-transcriber/test_supabase_store.py`

**Interfaces:**
- Consumes: existing `_request` (Task exists), `SupabaseError`.
- Produces (used by Tasks 3, 4):
  - `insert_insights(meeting_id: str, items: list[dict]) -> None` — bulk POST to `insights`; each item = `{content, category, quote?, source, status}`; injects `meeting_id`. No-op if `items` empty.
  - `meeting_has_extracted_insights(meeting_id: str) -> bool` — GET count of `insights` rows with `source=extracted` for the meeting.

- [ ] **Step 1: Add failing tests to `test_supabase_store.py`**

Insert before the `if __name__` line:

```python
    @mock.patch("supabase_store.urlopen")
    def test_insert_insights_posts_rows_with_meeting_id(self, urlopen):
        urlopen.return_value = fake_response(201)
        ss.insert_insights("m1", [
            {"content": "AI budgets rising", "category": "signal", "source": "extracted", "status": "candidate"},
            {"content": "note", "category": "note", "quote": "q", "source": "manual", "status": "accepted"},
        ])
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("/rest/v1/insights", req.full_url)
        body = json.loads(req.data)
        self.assertEqual(body[0]["meeting_id"], "m1")
        self.assertEqual(body[0]["category"], "signal")
        self.assertEqual(body[1]["quote"], "q")

    @mock.patch("supabase_store.urlopen")
    def test_insert_insights_empty_is_noop(self, urlopen):
        ss.insert_insights("m1", [])
        urlopen.assert_not_called()

    @mock.patch("supabase_store.urlopen")
    def test_meeting_has_extracted_insights(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([{"id": "i1"}]).encode())
        self.assertTrue(ss.meeting_has_extracted_insights("m1"))
        url = urlopen.call_args[0][0].full_url
        self.assertIn("insights?", url)
        self.assertIn("meeting_id=eq.m1", url)
        self.assertIn("source=eq.extracted", url)

    @mock.patch("supabase_store.urlopen")
    def test_meeting_has_extracted_insights_false_when_empty(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        self.assertFalse(ss.meeting_has_extracted_insights("m1"))
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_supabase_store -v`
Expected: FAIL — `AttributeError: module 'supabase_store' has no attribute 'insert_insights'`.

- [ ] **Step 3: Implement in `supabase_store.py`**

Add after `save_summary`:

```python
def insert_insights(meeting_id: str, items: list[dict]) -> None:
    if not items:
        return
    _request("POST", "insights", body=[{"meeting_id": meeting_id, **item} for item in items])


def meeting_has_extracted_insights(meeting_id: str) -> bool:
    rows = _request(
        "GET",
        f"insights?meeting_id=eq.{quote(meeting_id)}&source=eq.extracted&select=id&limit=1",
    )
    return bool(rows)
```

- [ ] **Step 4: Run to verify pass**

Run: `python3 -m unittest test_supabase_store -v`
Expected: `OK` (11 tests).

- [ ] **Step 5: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/supabase_store.py groups/global/skills/meeting-transcriber/test_supabase_store.py
git commit -m "feat(insights): supabase_store insert_insights + meeting_has_extracted_insights

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: meeting-processor extracts candidate insights

**Files:**
- Modify: `groups/global/skills/meeting-processor/SKILL.md`

**Interfaces:**
- Consumes: `supabase_store.insert_insights`, `meeting_has_extracted_insights` (Task 2).
- Produces: after each processed meeting, 3–7 `insights` rows with `source='extracted'`, `status='candidate'`.

- [ ] **Step 1: Add section 4c to `SKILL.md`**

Insert immediately after section "4b. Save the structured summary to Supabase" and before "### 5.":

````markdown
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
````

- [ ] **Step 2: Review the edit**

Read the file region; confirm section order is 4, 4b, 4c, 5 and the code fence is closed.

- [ ] **Step 3: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-processor/SKILL.md
git commit -m "feat(insights): meeting-processor extracts candidate insights per meeting

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Backfill insights for the 20 newest meetings

**Files:**
- Create: `groups/global/skills/meeting-transcriber/backfill_insights.py`

**Interfaces:**
- Consumes: `supabase_store._request`, `insert_insights`, `meeting_has_extracted_insights`.
- Produces: a script that prints, for the 20 newest summarized meetings, either the meeting id + summary for the agent to turn into insights, or a skip line — and a helper the agent calls to write them.

This is an **agent-run** task (LLM judgment), mirroring the classification pass: the script selects and prints work; the agent reads each summary and calls `insert_insights`. Keep the selection deterministic and idempotent in code.

- [ ] **Step 1: Write `backfill_insights.py`**

```python
#!/usr/bin/env python3
"""Print the 20 newest summarized meetings that still lack extracted insights.

Agent workflow: run this, then for each printed meeting read title+summary and call
  supabase_store.insert_insights(meeting_id, [{content, category, quote?, source:'extracted', status:'candidate'}, ...])
Run with: SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python3 backfill_insights.py
"""

import json

import supabase_store


def candidates(limit: int = 20) -> list[dict]:
    rows = supabase_store._request(
        "GET",
        "meetings?summary_md=not.is.null&select=id,title,summary_md&order=date.desc&limit=" + str(limit),
    ) or []
    return [r for r in rows if not supabase_store.meeting_has_extracted_insights(r["id"])]


def main() -> None:
    todo = candidates()
    print(f"MEETINGS_NEEDING_INSIGHTS: {len(todo)}")
    for r in todo:
        print("\n=====")
        print(json.dumps({"id": r["id"], "title": r["title"], "summary_md": r["summary_md"]}))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Compile + dry-run the selector**

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
python3 -m py_compile backfill_insights.py
env $(grep -E '^SUPABASE_(URL|SERVICE_KEY)=' /share/nanoclaw/.env | xargs) python3 backfill_insights.py | head -3
```
Expected: `MEETINGS_NEEDING_INSIGHTS: 20` (all 20 newest lack insights on first run), then the first meeting's JSON.

- [ ] **Step 3: Run the extraction (agent task)**

Dispatch an agent (general-purpose) with: run `backfill_insights.py` with the SUPABASE_* env exported; for each printed meeting, read `title`+`summary_md`, derive 3-7 insights per the section 4c rubric (categories signal/learning/risk/opportunity/quote; `content` one sentence; `quote` optional and only if it appears in the summary), and call `supabase_store.insert_insights(id, items)` with `source='extracted'`, `status='candidate'`. Batch in scripts of ~10. Report per-meeting counts. It must be idempotent — re-running the selector after should print `MEETINGS_NEEDING_INSIGHTS: 0`.

- [ ] **Step 4: Verify**

```bash
env $(grep -E '^SUPABASE_(URL|SERVICE_KEY)=' /share/nanoclaw/.env | xargs) python3 backfill_insights.py | head -1
curl -s "https://iejvqtvnrthvhxemonlz.supabase.co/rest/v1/insights?select=id&status=eq.candidate" -H "apikey: $PK" -H "Range: 0-0" -H "Prefer: count=exact" -o /dev/null -D - | grep -i content-range
```
Expected: selector prints `MEETINGS_NEEDING_INSIGHTS: 0`; candidate count is roughly 60-140 (≈3-7 × 20).

- [ ] **Step 5: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/backfill_insights.py
git commit -m "feat(insights): backfill selector for the 20 newest meetings

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Dashboard insights data layer + write helpers

**Files:**
- Create: `groups/global/meeting-insights/src/lib/insights.ts`
- Create: `groups/global/meeting-insights/src/lib/insights.test.ts`
- Modify: `groups/global/meeting-insights/src/lib/supabase.ts`

**Interfaces:**
- Consumes: the `supabase` client + `insights` table (Task 1).
- Produces (used by Tasks 6-8):
  - Types `Insight`, `Category`, `Status`; const `CATEGORIES: Category[]`.
  - `buildManualInsight(meetingId, note, quote, category): NewInsight` — `{meeting_id, content, quote, category, source:'manual', status:'accepted'}`.
  - `groupByMeeting(insights: Insight[]): Map<string, Insight[]>`.
  - `fetchInsights(): Promise<Insight[]>`, `insertInsight(row: NewInsight): Promise<Insight>`, `updateInsight(id, patch: Partial<Insight>): Promise<void>` (in supabase.ts).

- [ ] **Step 1: Write `insights.ts`**

```typescript
export const CATEGORIES = ['signal', 'learning', 'risk', 'opportunity', 'quote', 'note'] as const;
export type Category = (typeof CATEGORIES)[number];
export type Status = 'candidate' | 'accepted' | 'rejected';

export interface Insight {
  id: string;
  meeting_id: string;
  content: string;
  category: Category;
  status: Status;
  source: 'extracted' | 'manual';
  quote: string | null;
  created_at: string;
  updated_at: string;
}

export type NewInsight = Pick<Insight, 'meeting_id' | 'content' | 'category' | 'quote' | 'source' | 'status'>;

export function buildManualInsight(
  meetingId: string, note: string, quote: string | null, category: Category,
): NewInsight {
  return {
    meeting_id: meetingId,
    content: note.trim(),
    quote: quote?.trim() ? quote.trim() : null,
    category,
    source: 'manual',
    status: 'accepted',
  };
}

export function groupByMeeting(insights: Insight[]): Map<string, Insight[]> {
  const map = new Map<string, Insight[]>();
  for (const i of insights) {
    const list = map.get(i.meeting_id);
    if (list) list.push(i);
    else map.set(i.meeting_id, [i]);
  }
  return map;
}
```

- [ ] **Step 2: Write failing tests `insights.test.ts`**

```typescript
import { describe, expect, it } from 'vitest';
import { buildManualInsight, CATEGORIES, groupByMeeting } from './insights';
import type { Insight } from './insights';

const ins = (over: Partial<Insight>): Insight => ({
  id: 'i', meeting_id: 'm', content: 'c', category: 'note', status: 'accepted',
  source: 'manual', quote: null, created_at: '', updated_at: '', ...over,
});

describe('buildManualInsight', () => {
  it('builds an accepted manual insight, trimming note and quote', () => {
    const n = buildManualInsight('m1', '  a note  ', '  a quote ', 'signal');
    expect(n).toEqual({ meeting_id: 'm1', content: 'a note', quote: 'a quote', category: 'signal', source: 'manual', status: 'accepted' });
  });
  it('nulls an empty quote', () => {
    expect(buildManualInsight('m1', 'note', '   ', 'note').quote).toBeNull();
    expect(buildManualInsight('m1', 'note', null, 'note').quote).toBeNull();
  });
});

describe('groupByMeeting', () => {
  it('buckets insights by meeting_id preserving order', () => {
    const g = groupByMeeting([ins({ id: 'a', meeting_id: 'm1' }), ins({ id: 'b', meeting_id: 'm2' }), ins({ id: 'c', meeting_id: 'm1' })]);
    expect(g.get('m1')!.map((i) => i.id)).toEqual(['a', 'c']);
    expect(g.get('m2')!.map((i) => i.id)).toEqual(['b']);
  });
});

describe('CATEGORIES', () => {
  it('has the six agreed categories', () => {
    expect(CATEGORIES).toEqual(['signal', 'learning', 'risk', 'opportunity', 'quote', 'note']);
  });
});
```

Run: `cd /share/nanoclaw/groups/global/meeting-insights && npm test` — Expected: the insights suite passes (pure functions; written before the view code). If red, it is an import error — fix and rerun.

- [ ] **Step 3: Add fetch/write helpers to `supabase.ts`**

Append:

```typescript
import type { Insight, NewInsight } from './insights';

export async function fetchInsights(): Promise<Insight[]> {
  const { data, error } = await supabase
    .from('insights')
    .select('*')
    .order('created_at', { ascending: false });
  if (error) throw error;
  return (data ?? []) as Insight[];
}

export async function insertInsight(row: NewInsight): Promise<Insight> {
  const { data, error } = await supabase.from('insights').insert(row).select().single();
  if (error) throw error;
  return data as Insight;
}

export async function updateInsight(id: string, patch: Partial<Insight>): Promise<void> {
  const { error } = await supabase.from('insights').update(patch).eq('id', id);
  if (error) throw error;
}
```

- [ ] **Step 4: Typecheck + test**

Run: `npm test && npx tsc -b`
Expected: tests green; no TS errors. (`tsc -b` catches the new imports wiring.)

- [ ] **Step 5: Commit**

```bash
cd /share/nanoclaw/groups/global/meeting-insights
git add src/lib/insights.ts src/lib/insights.test.ts src/lib/supabase.ts
git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(insights): dashboard insights types, helpers, and supabase read/write"
```

---

### Task 6: Insight state-transition reducer (pure, tested)

**Files:**
- Create: `groups/global/meeting-insights/src/lib/insightState.ts`
- Create: `groups/global/meeting-insights/src/lib/insightState.test.ts`

**Interfaces:**
- Consumes: `Insight` (Task 5).
- Produces (used by Tasks 7, 8): `applyInsightChange(list: Insight[], change: InsightChange): Insight[]` where `InsightChange` is `{type:'add', insight} | {type:'accept', id} | {type:'reject', id} | {type:'edit', id, patch}`. Pure; drives optimistic UI in both views.

- [ ] **Step 1: Write failing tests `insightState.test.ts`**

```typescript
import { describe, expect, it } from 'vitest';
import { applyInsightChange } from './insightState';
import type { Insight } from './insights';

const ins = (over: Partial<Insight>): Insight => ({
  id: 'i', meeting_id: 'm', content: 'c', category: 'note', status: 'candidate',
  source: 'extracted', quote: null, created_at: '', updated_at: '', ...over,
});

describe('applyInsightChange', () => {
  const base = [ins({ id: 'a' }), ins({ id: 'b', status: 'accepted' })];
  it('accept flips status to accepted', () => {
    expect(applyInsightChange(base, { type: 'accept', id: 'a' }).find((i) => i.id === 'a')!.status).toBe('accepted');
  });
  it('reject flips status to rejected', () => {
    expect(applyInsightChange(base, { type: 'reject', id: 'a' }).find((i) => i.id === 'a')!.status).toBe('rejected');
  });
  it('edit merges the patch', () => {
    const out = applyInsightChange(base, { type: 'edit', id: 'a', patch: { content: 'new', category: 'risk' } });
    const a = out.find((i) => i.id === 'a')!;
    expect(a.content).toBe('new');
    expect(a.category).toBe('risk');
  });
  it('add prepends the insight', () => {
    const out = applyInsightChange(base, { type: 'add', insight: ins({ id: 'z', source: 'manual', status: 'accepted' }) });
    expect(out[0].id).toBe('z');
    expect(out).toHaveLength(3);
  });
  it('does not mutate the input array', () => {
    const copy = [...base];
    applyInsightChange(base, { type: 'accept', id: 'a' });
    expect(base).toEqual(copy);
  });
});
```

Run: `npm test` — Expected: FAIL, `./insightState` not found.

- [ ] **Step 2: Implement `insightState.ts`**

```typescript
import type { Insight } from './insights';

export type InsightChange =
  | { type: 'add'; insight: Insight }
  | { type: 'accept'; id: string }
  | { type: 'reject'; id: string }
  | { type: 'edit'; id: string; patch: Partial<Insight> };

export function applyInsightChange(list: Insight[], change: InsightChange): Insight[] {
  switch (change.type) {
    case 'add':
      return [change.insight, ...list];
    case 'accept':
      return list.map((i) => (i.id === change.id ? { ...i, status: 'accepted' } : i));
    case 'reject':
      return list.map((i) => (i.id === change.id ? { ...i, status: 'rejected' } : i));
    case 'edit':
      return list.map((i) => (i.id === change.id ? { ...i, ...change.patch } : i));
  }
}
```

- [ ] **Step 3: Run to verify pass**

Run: `npm test` — Expected: all green.

- [ ] **Step 4: Commit**

```bash
cd /share/nanoclaw/groups/global/meeting-insights
git add src/lib/insightState.ts src/lib/insightState.test.ts
git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(insights): pure state-transition reducer for optimistic UI"
```

---

### Task 7: Meeting page — insights section + transcript highlight-to-note

**Files:**
- Create: `groups/global/meeting-insights/src/components/InsightCard.tsx`
- Modify: `groups/global/meeting-insights/src/views/MeetingDetail.tsx`
- Modify: `groups/global/meeting-insights/src/App.tsx` (pass insights + change handler down)
- Modify: `groups/global/meeting-insights/src/index.css` (append insight styles)

**Interfaces:**
- Consumes: `Insight`, `CATEGORIES`, `buildManualInsight` (Task 5); `insertInsight`, `updateInsight` (Task 5); `applyInsightChange`/`InsightChange` (Task 6).
- Produces: `InsightCard` component; `MeetingDetail` renders this meeting's insights and creates manual ones from transcript selection. App owns the insights array + `onChange(change: InsightChange)`.

- [ ] **Step 1: App owns insights state**

In `src/App.tsx`: add `const [insights, setInsights] = useState<Insight[]>([]);`, fetch it alongside the index (`fetchInsights().then(setInsights).catch(() => {})`), define `const onInsightChange = (c: InsightChange) => setInsights((cur) => applyInsightChange(cur, c));`, and pass `insights={insights}` + `onInsightChange={onInsightChange}` to `MeetingDetail`, `Insights`, and (Task 8) the feed. Import `Insight`, `fetchInsights`, `applyInsightChange`, `InsightChange`.

- [ ] **Step 2: Write `InsightCard.tsx`**

```tsx
import { useState } from 'react';
import { CATEGORIES } from '../lib/insights';
import type { Category, Insight } from '../lib/insights';
import { updateInsight } from '../lib/supabase';
import type { InsightChange } from '../lib/insightState';

export default function InsightCard(
  { insight, onChange, showMeetingLink }: { insight: Insight; onChange: (c: InsightChange) => void; showMeetingLink?: boolean },
) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(insight.content);
  const [category, setCategory] = useState<Category>(insight.category);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const persist = async (patch: Partial<Insight>, change: InsightChange) => {
    setBusy(true); setErr(null);
    onChange(change);                                  // optimistic
    try { await updateInsight(insight.id, patch); }
    catch (e) { setErr(String(e)); onChange({ type: 'edit', id: insight.id, patch: insight }); } // revert
    finally { setBusy(false); }
  };

  if (insight.status === 'rejected') return null;

  return (
    <div className={`insight cat-${insight.category}`}>
      <div className="insight-top">
        <span className="insight-cat">{insight.category}</span>
        {insight.status === 'candidate' && <span className="badge">candidate</span>}
        {showMeetingLink && <a className="muted" href={`#/meeting/${insight.meeting_id}`}>{insight.meeting_id}</a>}
      </div>
      {editing ? (
        <div className="insight-edit">
          <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={2} />
          <select value={category} onChange={(e) => setCategory(e.target.value as Category)}>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <button type="button" disabled={busy} onClick={() => persist({ content: content.trim(), category }, { type: 'edit', id: insight.id, patch: { content: content.trim(), category } }).then(() => setEditing(false))}>Save</button>
          <button type="button" className="linklike" onClick={() => { setEditing(false); setContent(insight.content); setCategory(insight.category); }}>Cancel</button>
        </div>
      ) : (
        <p className="insight-content">{insight.content}</p>
      )}
      {insight.quote && <blockquote className="insight-quote" dir="auto">{insight.quote}</blockquote>}
      {!editing && (
        <div className="insight-actions">
          {insight.status === 'candidate' && (
            <>
              <button type="button" disabled={busy} onClick={() => persist({ status: 'accepted' }, { type: 'accept', id: insight.id })}>Accept</button>
              <button type="button" className="linklike" disabled={busy} onClick={() => persist({ status: 'rejected' }, { type: 'reject', id: insight.id })}>Reject</button>
            </>
          )}
          <button type="button" className="linklike" onClick={() => setEditing(true)}>Edit</button>
        </div>
      )}
      {err && <p className="error">{err}</p>}
    </div>
  );
}
```

- [ ] **Step 3: Rewrite `MeetingDetail.tsx` with the insights section + selection-to-note**

Full file (keeps the existing header/summary/lazy-transcript behavior, adds insights + a transcript selection form):

```tsx
import { useRef, useState } from 'react';
import { fetchTranscript, insertInsight } from '../lib/supabase';
import { renderMarkdown } from '../lib/markdown';
import { buildManualInsight, CATEGORIES } from '../lib/insights';
import type { Category, Insight } from '../lib/insights';
import type { InsightChange } from '../lib/insightState';
import type { MeetingIndexRow } from '../lib/types';
import InsightCard from '../components/InsightCard';

export default function MeetingDetail(
  { meetings, id, insights, onInsightChange }:
  { meetings: MeetingIndexRow[]; id: string; insights: Insight[]; onInsightChange: (c: InsightChange) => void },
) {
  const meeting = meetings.find((m) => m.id === id);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const preRef = useRef<HTMLPreElement>(null);

  // selection-to-note form state
  const [sel, setSel] = useState('');        // highlighted quote
  const [note, setNote] = useState('');
  const [cat, setCat] = useState<Category>('note');
  const [saving, setSaving] = useState(false);
  const [addErr, setAddErr] = useState<string | null>(null);

  if (!meeting) return <p className="error">Meeting not found: {id}</p>;

  const loadTranscript = (open: boolean) => {
    if (!open || transcript !== null || loading) return;
    setLoading(true);
    fetchTranscript(id)
      .then((t) => setTranscript(t ?? '(no transcript stored)'))
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  const onSelect = () => {
    const s = window.getSelection();
    const text = s?.toString().trim() ?? '';
    if (text && preRef.current && s && preRef.current.contains(s.anchorNode)) setSel(text);
  };

  const submitManual = async () => {
    if (!note.trim()) return;
    setSaving(true); setAddErr(null);
    try {
      const row = await insertInsight(buildManualInsight(id, note, sel, cat));
      onInsightChange({ type: 'add', insight: row });
      setSel(''); setNote(''); setCat('note');
    } catch (e) { setAddErr(String(e)); }   // keep form + note on failure
    finally { setSaving(false); }
  };

  const mine = insights.filter((i) => i.meeting_id === id);

  return (
    <div>
      <a href="#/">← Calendar</a> · <a href="#/list">All meetings</a>
      <div className="detail-header">
        <h1>{meeting.title ?? meeting.id}</h1>
        <div className="meta">
          <span>{meeting.date}</span>
          {meeting.type && <span className="badge">{meeting.type}</span>}
          {meeting.language && <span>{meeting.language}</span>}
          {meeting.duration_seconds && <span>{Math.round(meeting.duration_seconds / 60)}m</span>}
          {meeting.themes.map((t) => <span className="chip" key={t}>{t}</span>)}
        </div>
        {meeting.participants.length > 0 && (
          <p className="muted">With: {meeting.participants.map((p) => [p.name, p.role, p.company].filter(Boolean).join(', ')).join(' · ')}</p>
        )}
      </div>

      {meeting.summary_md
        ? <div className="summary-md" dangerouslySetInnerHTML={{ __html: renderMarkdown(meeting.summary_md) }} />
        : <p className="muted">Summary pending — the pipeline will fill this in.</p>}

      <section className="insights-section">
        <h2>Insights</h2>
        {mine.filter((i) => i.status !== 'rejected').length === 0 && <p className="muted">No insights yet.</p>}
        {mine.map((i) => <InsightCard key={i.id} insight={i} onChange={onInsightChange} />)}
      </section>

      <details className="transcript" onToggle={(e) => loadTranscript((e.target as HTMLDetailsElement).open)}>
        <summary>Full transcript</summary>
        {loading && <p className="muted">Loading transcript…</p>}
        {error && <p className="error">{error}</p>}
        {transcript !== null && (
          <div className="transcript-wrap">
            {sel && (
              <div className="insight-add">
                <p className="muted">Add insight from selection:</p>
                <blockquote className="insight-quote" dir="auto">{sel}</blockquote>
                <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} placeholder="Your note…" />
                <div className="insight-actions">
                  <select value={cat} onChange={(e) => setCat(e.target.value as Category)}>
                    {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                  <button type="button" disabled={saving || !note.trim()} onClick={submitManual}>Add insight</button>
                  <button type="button" className="linklike" onClick={() => { setSel(''); setNote(''); setAddErr(null); }}>Cancel</button>
                </div>
                {addErr && <p className="error">{addErr}</p>}
              </div>
            )}
            <pre ref={preRef} dir="auto" onMouseUp={onSelect}>{transcript}</pre>
          </div>
        )}
      </details>
    </div>
  );
}
```

- [ ] **Step 4: Append insight styles to `index.css`**

```css

/* Insights */
.insights-section { margin: 20px 0; }
.insight { background: var(--surface-2); border: 1px solid var(--border); border-left: 3px solid var(--type-color, var(--series-1)); border-radius: 8px; padding: 10px 12px; margin: 8px 0; }
.insight.cat-signal { --type-color: var(--type-0); }
.insight.cat-learning { --type-color: var(--type-1); }
.insight.cat-risk { --type-color: var(--type-5); }
.insight.cat-opportunity { --type-color: var(--type-3); }
.insight.cat-quote { --type-color: var(--type-4); }
.insight.cat-note { --type-color: var(--text-muted); }
.insight-top { display: flex; gap: 8px; align-items: center; font-size: 12px; margin-bottom: 4px; }
.insight-cat { color: var(--type-color); font-weight: 600; text-transform: capitalize; }
.insight-content { margin: 2px 0; }
.insight-quote { margin: 6px 0 0; padding-left: 10px; border-left: 2px solid var(--border); color: var(--text-secondary); font-size: 13px; }
.insight-actions, .insight-edit { display: flex; gap: 8px; align-items: center; margin-top: 6px; flex-wrap: wrap; }
.insight-edit textarea { flex: 1 1 240px; }
.insight-add { position: absolute; z-index: 20; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; padding: 8px; box-shadow: 0 4px 14px rgba(0,0,0,0.2); }
.add-insight-btn { position: absolute; z-index: 20; }
.transcript-wrap { position: relative; }
```

- [ ] **Step 5: Test + build + manual check**

Run: `npm test && npm run build`
Expected: all suites green, clean build. Then `npm run dev`, open a meeting with candidate insights, and confirm: accept/reject/edit work and persist (reload shows the change); selecting transcript text shows the add form and submitting creates an accepted insight. (RTL note: quotes render `dir="auto"`.)

- [ ] **Step 6: Commit + deploy**

```bash
cd /share/nanoclaw/groups/global/meeting-insights
git add -A && git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(insights): meeting page insights section + accept/reject/edit + highlight-to-note"
git push
```
Watch the Actions run; if the deploy job fails with "try again later", rerun failed jobs. Confirm `meetings.getfishbone.ai` serves the new hash and a meeting shows its insights.

---

### Task 8: Insights feed + Stats tab + nav

**Files:**
- Modify: `groups/global/meeting-insights/src/views/Insights.tsx` (repurpose to feed)
- Create: `groups/global/meeting-insights/src/views/Stats.tsx` (moved charts)
- Modify: `groups/global/meeting-insights/src/App.tsx` (routes/nav + props)

**Interfaces:**
- Consumes: `Insight`, `CATEGORIES` (Task 5); `InsightCard` (Task 7); `applyInsightChange`/`InsightChange` (Task 6); existing aggregate fns for Stats.
- Produces: `#/insights` = accepted-insights feed; `#/stats` = charts; nav Calendar · List · Insights · People · Stats.

- [ ] **Step 1: Create `Stats.tsx` from the current Insights view**

Move the exact current `Insights.tsx` body (tiles + three charts) into `src/views/Stats.tsx` as `export default function Stats({ meetings }: { meetings: MeetingIndexRow[] })`. No logic change — same imports (`peopleIndex`, `themeCounts`, `typeCounts`, `weeklyCounts`, `HBars`, `VBars`).

- [ ] **Step 2: Rewrite `Insights.tsx` as the feed**

```tsx
import { useMemo, useState } from 'react';
import InsightCard from '../components/InsightCard';
import { CATEGORIES } from '../lib/insights';
import type { Category, Insight } from '../lib/insights';
import type { InsightChange } from '../lib/insightState';
import type { MeetingIndexRow } from '../lib/types';

export default function Insights(
  { meetings, insights, onInsightChange }: { meetings: MeetingIndexRow[]; insights: Insight[]; onInsightChange: (c: InsightChange) => void },
) {
  const [cat, setCat] = useState<Category | ''>('');
  const titleFor = useMemo(() => {
    const m = new Map(meetings.map((x) => [x.id, x.title ?? x.id]));
    return (id: string) => m.get(id) ?? id;
  }, [meetings]);

  const accepted = insights
    .filter((i) => i.status === 'accepted')
    .filter((i) => !cat || i.category === cat);

  return (
    <div>
      <div className="filters">
        <select value={cat} onChange={(e) => setCat(e.target.value as Category | '')}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="muted">{accepted.length} insights</span>
      </div>
      {accepted.length === 0 && <p className="muted">No accepted insights yet. Accept some on a meeting page.</p>}
      {accepted.map((i) => (
        <div key={i.id}>
          <div className="feed-meeting"><a href={`#/meeting/${i.meeting_id}`}>{titleFor(i.meeting_id)}</a></div>
          <InsightCard insight={i} onChange={onInsightChange} />
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 3: Update `App.tsx` routes, nav, and props**

Nav becomes Calendar · List · Insights · People · Stats. Route `#/insights` → `<Insights meetings insights onInsightChange />`; `#/stats` → `<Stats meetings />`. Import `Stats`. `Insights` now needs `insights` + `onInsightChange` (already created in Task 7 Step 1).

- [ ] **Step 4: Small feed style**

Append to `index.css`: `.feed-meeting { font-size: 12px; color: var(--text-muted); margin-top: 10px; } .feed-meeting a { color: var(--text-secondary); }`

- [ ] **Step 5: Test + build + manual check**

Run: `npm test && npm run build`
Expected: green. `npm run dev`: Insights tab lists accepted insights (filter by category, links to meetings, inline edit works); Stats tab shows the old charts; nav has five tabs.

- [ ] **Step 6: Commit + deploy**

```bash
cd /share/nanoclaw/groups/global/meeting-insights
git add -A && git -c user.email=avikillu@gmail.com -c user.name="Fishbone Agent" commit -m "feat(insights): Insights feed + Stats tab + five-tab nav"
git push
```
Watch the deploy (rerun failed jobs if it blips); confirm the live site shows the feed + Stats.

---

## Post-plan verification checklist

- [ ] `python3 -m unittest` green in `skills/meeting-transcriber/` (supabase_store insights tests).
- [ ] `npm test` green in `meeting-insights` (insights, insightState suites) and `npm run build` clean.
- [ ] RLS: anon insert/update insights OK; anon delete blocked; anon write to meetings still blocked (rerun Task 1 Step 3).
- [ ] Backfill: 20 newest meetings have candidate insights; selector re-run prints `0`.
- [ ] Live `meetings.getfishbone.ai`: a meeting shows candidates → accept/reject/edit persists across reload; transcript highlight → note creates an accepted insight; Insights feed and Stats tab both render.
- [ ] Next real meeting (after cutover of the running pipeline picks up the SKILL.md change) produces candidate insights automatically.
