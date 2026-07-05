# Meeting Insights Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move meeting transcripts + summaries out of git/Slack into Supabase Postgres, and serve a live GitHub Pages dashboard (Meetings / People / Insights) reading via supabase-js.

**Architecture:** `transcribe.py` upserts transcript rows into a Supabase `meetings` table; the meeting-processor agent fills in `summary_md` + participants + themes; `reconcile.py` finds pending meetings with one SQL filter. A static Vite/React dashboard (`fishbone-ai/meeting-insights`) reads live with the anon key. A one-time backfill imports 179 existing transcripts and attaches summaries parsed from Slack history.

**Tech Stack:** Python 3.12 stdlib-only for new modules (`urllib.request`, `unittest` — host has no `requests`/`pytest`); Supabase REST (PostgREST); Vite + React 19 + TypeScript + `@supabase/supabase-js` + vitest for the dashboard; GitHub Actions Pages deploy (cyber-mindmap pattern).

**Spec:** `docs/superpowers/specs/2026-07-05-meeting-insights-dashboard-design.md`

## Global Constraints

- New Python modules import **stdlib only** (`urllib.request`, `json`, `os`, `re`, `pathlib`, `datetime`, `unittest`). Do NOT import `requests` in new files (host Python lacks it; existing files that already use it are fine).
- Python tests run with `python3 -m unittest` (no pytest anywhere).
- Env var names: `SUPABASE_URL` (e.g. `https://<ref>.supabase.co`), `SUPABASE_SERVICE_KEY` (service role), `SUPABASE_ANON_KEY` (dashboard only, baked into the bundle — public by design).
- Meeting `id` = transcript filename stem, e.g. `2026-07-05-bxw-faqy-yqf-2026-07-05-15-47-gmt-3` (no `.md`).
- Meeting `type` enum strings: `discovery-call | vc-meeting | internal-strategy | phone-call | weekly-retro | weekly-kickoff | other`. Participant `category`: `founder | practitioner | vc | advisor | other`.
- Dashboard repo name: `fishbone-ai/meeting-insights`; site URL `https://fishbone-ai.github.io/meeting-insights/`; Vite `base: '/meeting-insights/'`.
- All pipeline writes are idempotent upserts keyed on `id` — re-running any script must converge to the same state.
- Never overwrite a non-null `summary_md` (backfill and processor both check first).
- Commit after every green test cycle. Nanoclaw-repo commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Files under `groups/global/` follow workspace conventions: lowercase-hyphen filenames, ISO dates, no em-dashes in prose.
- The user must supply the Supabase project URL + keys at Task 1 — STOP and ask if not provided; everything else is blocked on it.

---

### Task 1: Supabase schema, RLS, and credential wiring

**Files:**
- Create: `groups/global/skills/meeting-transcriber/schema.sql`
- Modify: `/share/nanoclaw/.env` (add 2 keys)
- Modify: `src/container-runner.ts:375-382` (passthrough list)

**Interfaces:**
- Produces: tables `meetings`, `participants`, `themes` live in the user's Supabase project; env vars `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` available inside agent containers; anon read verified working, anon write verified failing.

- [ ] **Step 1: Get project credentials from the user**

Ask the user (this is the one blocking input):

> Which Supabase project should this use? I need: the project URL (`https://<ref>.supabase.co`), the **service role** key, and the **anon** key (Dashboard → Settings → API). The only project I found referenced in this workspace is the FitBot one (`iejvqtvnrthvhxemonlz`) — is it that one, or another?

Do not proceed until you have all three values.

- [ ] **Step 2: Write `schema.sql`**

```sql
-- Meeting Insights store. Apply in Supabase SQL Editor (idempotent).
create table if not exists meetings (
  id               text primary key,
  date             date not null,
  title            text,
  type             text check (type in ('discovery-call','vc-meeting','internal-strategy','phone-call','weekly-retro','weekly-kickoff','other')),
  language         text,
  source           text check (source in ('meet','phone','whatsapp','voice')),
  owner            text,
  duration_seconds numeric,
  transcript_md    text,
  summary_md       text,
  slack_ts         text,
  imported_from    text,
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);

create table if not exists participants (
  meeting_id text not null references meetings(id) on delete cascade,
  name       text not null,
  category   text check (category in ('founder','practitioner','vc','advisor','other')),
  role       text,
  company    text,
  primary key (meeting_id, name)
);

create table if not exists themes (
  meeting_id text not null references meetings(id) on delete cascade,
  theme      text not null,
  primary key (meeting_id, theme)
);

create index if not exists meetings_date_idx on meetings (date desc);
create index if not exists meetings_pending_idx on meetings (id) where summary_md is null;

alter table meetings     enable row level security;
alter table participants enable row level security;
alter table themes       enable row level security;

drop policy if exists anon_read_meetings     on meetings;
drop policy if exists anon_read_participants on participants;
drop policy if exists anon_read_themes       on themes;
create policy anon_read_meetings     on meetings     for select to anon using (true);
create policy anon_read_participants on participants for select to anon using (true);
create policy anon_read_themes       on themes       for select to anon using (true);

create or replace function set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end;
$$ language plpgsql;

drop trigger if exists meetings_updated_at on meetings;
create trigger meetings_updated_at before update on meetings
  for each row execute function set_updated_at();
```

- [ ] **Step 3: Apply the schema**

Have the user paste `schema.sql` into the Supabase SQL Editor (Dashboard → SQL Editor → Run), or apply it yourself if they give you a direct Postgres connection string. Confirm "Success" output.

- [ ] **Step 4: Verify RLS from this machine**

First export the three values from Step 1 in your shell (`export SUPABASE_URL=... SUPABASE_ANON_KEY=... SUPABASE_SERVICE_KEY=...`) — later verification steps in Tasks 2 and 6 assume the same exports.

```bash
# Anon read must succeed (200, empty array):
curl -s -w '\n%{http_code}\n' "$SUPABASE_URL/rest/v1/meetings?select=id&limit=1" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY"
# Expected: []  then  200

# Anon write must FAIL (401 or 403):
curl -s -w '\n%{http_code}\n' -X POST "$SUPABASE_URL/rest/v1/meetings" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" -d '{"id":"rls-probe","date":"2026-01-01"}'
# Expected: RLS violation message, then 401 or 403

# Service write must succeed:
curl -s -w '\n%{http_code}\n' -X POST "$SUPABASE_URL/rest/v1/meetings" \
  -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY" \
  -H "Content-Type: application/json" -H "Prefer: resolution=merge-duplicates" \
  -d '{"id":"rls-probe","date":"2026-01-01"}'
# Expected: 201. Then clean up:
curl -s -X DELETE "$SUPABASE_URL/rest/v1/meetings?id=eq.rls-probe" \
  -H "apikey: $SUPABASE_SERVICE_KEY" -H "Authorization: Bearer $SUPABASE_SERVICE_KEY"
```

- [ ] **Step 5: Wire env into containers**

Append to `/share/nanoclaw/.env` (values from Step 1):

```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<service-role-key>
SUPABASE_ANON_KEY=<anon-key>
```

(The anon key is only read by verification commands and the dashboard build — it is deliberately NOT in the container passthrough list.)

In `src/container-runner.ts`, extend the passthrough list (lines 375–382):

```typescript
  const passthroughEnv = readEnvFile([
    'LINEAR_API_KEY',
    'SLACK_BOT_TOKEN',
    'GEMINI_API_KEY',
    'GOOGLE_SERVICE_ACCOUNT_JSON',
    'META_ADS_TOKEN',
    'META_ADS_ACCOUNT_ID',
    'SUPABASE_URL',
    'SUPABASE_SERVICE_KEY',
  ]);
```

- [ ] **Step 6: Build and verify**

Run: `cd /share/nanoclaw && npm run build`
Expected: clean TypeScript compile, exit 0. (Do NOT restart the service yet — that happens at cutover, Task 9, so the running pipeline keeps working until the new code is fully in place.)

- [ ] **Step 7: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/schema.sql src/container-runner.ts
git commit -m "feat(meetings): Supabase schema + container env passthrough for meeting store

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(`.env` is gitignored — verify with `git status` that it is not staged.)

---

### Task 2: `supabase_store.py` — stdlib Supabase REST client

**Files:**
- Create: `groups/global/skills/meeting-transcriber/supabase_store.py`
- Test: `groups/global/skills/meeting-transcriber/test_supabase_store.py`

**Interfaces:**
- Consumes: env vars `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (Task 1).
- Produces (used by Tasks 3, 4, 6):
  - `upsert_meeting(row: dict) -> None` — POST with merge-duplicates; `row` must contain `id` and `date`.
  - `get_meeting(meeting_id: str, columns: str = "*") -> dict | None`
  - `pending_meetings() -> list[dict]` — `[{"id": ..., "owner": ...}]` where `summary_md` is null.
  - `save_summary(meeting_id: str, summary_md: str, title: str, mtype: str | None, slack_ts: str | None, participants: list[dict], themes: list[str], imported_from: str | None = None) -> None` — PATCH meeting, then delete+reinsert participants/themes rows.
  - `SupabaseError(RuntimeError)` raised on any non-2xx response, message includes status + body.

- [ ] **Step 1: Write the failing tests**

`groups/global/skills/meeting-transcriber/test_supabase_store.py`:

```python
import json
import unittest
from unittest import mock

import supabase_store as ss


def fake_response(status=200, body=b"[]"):
    resp = mock.MagicMock()
    resp.status = status
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = mock.Mock(return_value=False)
    return resp


@mock.patch.dict("os.environ", {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "sk"})
class TestSupabaseStore(unittest.TestCase):
    @mock.patch("supabase_store.urlopen")
    def test_upsert_meeting_posts_merge_duplicates(self, urlopen):
        urlopen.return_value = fake_response(201)
        ss.upsert_meeting({"id": "m1", "date": "2026-07-05", "transcript_md": "hi"})
        req = urlopen.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertIn("/rest/v1/meetings", req.full_url)
        self.assertEqual(req.get_header("Prefer"), "resolution=merge-duplicates")
        self.assertEqual(req.get_header("Authorization"), "Bearer sk")
        self.assertEqual(json.loads(req.data), {"id": "m1", "date": "2026-07-05", "transcript_md": "hi"})

    @mock.patch("supabase_store.urlopen")
    def test_get_meeting_returns_row(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([{"id": "m1"}]).encode())
        row = ss.get_meeting("m1", columns="id,summary_md")
        self.assertEqual(row, {"id": "m1"})
        self.assertIn("id=eq.m1", urlopen.call_args[0][0].full_url)
        self.assertIn("select=id%2Csummary_md", urlopen.call_args[0][0].full_url)

    @mock.patch("supabase_store.urlopen")
    def test_get_meeting_missing_returns_none(self, urlopen):
        urlopen.return_value = fake_response(200, b"[]")
        self.assertIsNone(ss.get_meeting("nope"))

    @mock.patch("supabase_store.urlopen")
    def test_pending_meetings_filters_null_summary(self, urlopen):
        urlopen.return_value = fake_response(200, json.dumps([{"id": "m1", "owner": "ohav"}]).encode())
        rows = ss.pending_meetings()
        self.assertEqual(rows, [{"id": "m1", "owner": "ohav"}])
        self.assertIn("summary_md=is.null", urlopen.call_args[0][0].full_url)

    @mock.patch("supabase_store.urlopen")
    def test_save_summary_patches_then_replaces_children(self, urlopen):
        urlopen.return_value = fake_response(204, b"")
        ss.save_summary(
            "m1", "## Summary\n- x", "Title", "discovery-call", "123.456",
            participants=[{"name": "Dana", "category": "practitioner"}],
            themes=["ai-security"],
        )
        methods = [(c[0][0].get_method(), c[0][0].full_url) for c in urlopen.call_args_list]
        self.assertEqual(methods[0][0], "PATCH")               # meetings row
        self.assertIn("meetings?id=eq.m1", methods[0][1])
        self.assertEqual(methods[1][0], "DELETE")              # old participants
        self.assertIn("participants?meeting_id=eq.m1", methods[1][1])
        self.assertEqual(methods[2][0], "POST")                # new participants
        self.assertEqual(methods[3][0], "DELETE")              # old themes
        self.assertIn("themes?meeting_id=eq.m1", methods[3][1])
        self.assertEqual(methods[4][0], "POST")                # new themes
        posted = json.loads(urlopen.call_args_list[4][0][0].data)
        self.assertEqual(posted, [{"meeting_id": "m1", "theme": "ai-security"}])

    @mock.patch("supabase_store.urlopen")
    def test_save_summary_skips_empty_children_posts(self, urlopen):
        urlopen.return_value = fake_response(204, b"")
        ss.save_summary("m1", "s", "t", None, None, participants=[], themes=[])
        methods = [c[0][0].get_method() for c in urlopen.call_args_list]
        self.assertEqual(methods, ["PATCH", "DELETE", "DELETE"])  # no empty POSTs

    @mock.patch("supabase_store.urlopen")
    def test_non_2xx_raises_supabase_error(self, urlopen):
        import urllib.error
        urlopen.side_effect = urllib.error.HTTPError(
            "https://x.supabase.co/rest/v1/meetings", 401, "unauthorized", {}, None
        )
        with self.assertRaises(ss.SupabaseError):
            ss.upsert_meeting({"id": "m1", "date": "2026-07-05"})


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_supabase_store -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'supabase_store'`

- [ ] **Step 3: Write `supabase_store.py`**

```python
#!/usr/bin/env python3
"""Minimal Supabase PostgREST client for the meeting store. Stdlib only."""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class SupabaseError(RuntimeError):
    pass


def _env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SupabaseError(f"{name} env var not set")
    return value


def _request(method: str, path: str, body=None, prefer: str | None = None):
    url = _env("SUPABASE_URL").rstrip("/") + "/rest/v1/" + path
    key = _env("SUPABASE_SERVICE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
            if resp.status >= 300:
                raise SupabaseError(f"{method} {path} -> {resp.status}: {raw[:300]!r}")
            return json.loads(raw) if raw else None
    except HTTPError as e:
        raise SupabaseError(f"{method} {path} -> {e.code}: {e.read()[:300]!r}") from e
    except URLError as e:
        raise SupabaseError(f"{method} {path} failed: {e}") from e


def upsert_meeting(row: dict) -> None:
    _request("POST", "meetings", body=row, prefer="resolution=merge-duplicates")


def get_meeting(meeting_id: str, columns: str = "*") -> dict | None:
    rows = _request(
        "GET", f"meetings?id=eq.{quote(meeting_id)}&select={quote(columns)}&limit=1"
    )
    return rows[0] if rows else None


def pending_meetings() -> list[dict]:
    return _request("GET", "meetings?summary_md=is.null&select=id,owner&order=date.asc") or []


def save_summary(
    meeting_id: str,
    summary_md: str,
    title: str,
    mtype: str | None,
    slack_ts: str | None,
    participants: list[dict],
    themes: list[str],
    imported_from: str | None = None,
) -> None:
    patch = {"summary_md": summary_md, "title": title}
    if mtype:
        patch["type"] = mtype
    if slack_ts:
        patch["slack_ts"] = slack_ts
    if imported_from:
        patch["imported_from"] = imported_from
    _request("PATCH", f"meetings?id=eq.{quote(meeting_id)}", body=patch)

    _request("DELETE", f"participants?meeting_id=eq.{quote(meeting_id)}")
    if participants:
        _request(
            "POST", "participants",
            body=[{"meeting_id": meeting_id, **p} for p in participants],
        )
    _request("DELETE", f"themes?meeting_id=eq.{quote(meeting_id)}")
    if themes:
        _request(
            "POST", "themes",
            body=[{"meeting_id": meeting_id, "theme": t} for t in themes],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_supabase_store -v`
Expected: `OK` — 7 tests pass.

- [ ] **Step 5: Live smoke test (service key)**

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
set -a; grep -E '^SUPABASE_(URL|SERVICE_KEY)=' /share/nanoclaw/.env; set +a  # visually confirm vars exist
env $(grep -E '^SUPABASE_(URL|SERVICE_KEY)=' /share/nanoclaw/.env | xargs) python3 - <<'EOF'
import supabase_store as ss
ss.upsert_meeting({"id": "smoke-test", "date": "2026-01-01", "transcript_md": "probe"})
print("row:", ss.get_meeting("smoke-test", "id,transcript_md"))
ss.save_summary("smoke-test", "s", "t", None, None, [{"name": "X"}], ["probe-theme"])
print("pending excludes it:", all(r["id"] != "smoke-test" for r in ss.pending_meetings()))
EOF
```
Expected: `row: {'id': 'smoke-test', 'transcript_md': 'probe'}` and `pending excludes it: True`. Then delete the probe row with curl (as in Task 1 Step 4).

- [ ] **Step 6: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/supabase_store.py groups/global/skills/meeting-transcriber/test_supabase_store.py
git commit -m "feat(meetings): stdlib Supabase store client with tests

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `transcribe.py` writes to Supabase, stops writing git/files

**Files:**
- Modify: `groups/global/skills/meeting-transcriber/transcribe.py`
- Modify: `groups/global/skills/meeting-transcriber/SKILL.md`
- Test: `groups/global/skills/meeting-transcriber/test_transcribe_helpers.py`

**Interfaces:**
- Consumes: `supabase_store.upsert_meeting` (Task 2).
- Produces: new pure helpers `meeting_id_for(drive_file: dict) -> str` and `infer_source(filename: str) -> str` in `transcribe.py`; `NEW_TRANSCRIPTS:` stdout lines now list **meeting ids** (not paths): `  <meeting-id> (recorded from <owner>'s Drive)`. State file moves to `SCRIPT_DIR / ".transcriber-state.json"`.

- [ ] **Step 1: Write failing tests for the new helpers**

`groups/global/skills/meeting-transcriber/test_transcribe_helpers.py` — note: `transcribe.py` imports `requests`/`google` which the host lacks, so test the helpers via source extraction is NOT acceptable; instead guard the imports. The test file:

```python
import unittest
from unittest import mock
import sys

# Stub out heavy third-party imports so transcribe.py can be imported on the host.
for name in ("requests", "google", "google.genai", "google.oauth2",
             "google.oauth2.service_account", "googleapiclient",
             "googleapiclient.discovery", "googleapiclient.http"):
    sys.modules.setdefault(name, mock.MagicMock())

import transcribe  # noqa: E402


class TestHelpers(unittest.TestCase):
    def test_meeting_id_for_uses_created_date_and_slug(self):
        f = {"name": "bxw-faqy-yqf (2026-07-05 15:47 GMT+3).mp4",
             "id": "abc", "createdTime": "2026-07-05T12:47:00.000Z"}
        self.assertEqual(
            transcribe.meeting_id_for(f),
            "2026-07-05-bxw-faqy-yqf-2026-07-05-15-47-gmt-3",
        )

    def test_meeting_id_falls_back_to_today_without_created_time(self):
        f = {"name": "call.mp4", "id": "abc"}
        self.assertRegex(transcribe.meeting_id_for(f), r"^\d{4}-\d{2}-\d{2}-call$")

    def test_infer_source(self):
        self.assertEqual(transcribe.infer_source("phone_20260702-090335_0545881339.m4a"), "phone")
        self.assertEqual(transcribe.infer_source("whatsapp_20260629-222345_ohav.ogg"), "whatsapp")
        self.assertEqual(transcribe.infer_source("voice-020_w_20260629.m4a"), "voice")
        self.assertEqual(transcribe.infer_source("bxw-faqy-yqf (2026-07-05).mp4"), "meet")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_transcribe_helpers -v`
Expected: FAIL — `AttributeError: module 'transcribe' has no attribute 'meeting_id_for'`

- [ ] **Step 3: Implement the helpers in `transcribe.py`**

Add after `recording_slug()` (around line 46):

```python
def meeting_id_for(drive_file: dict) -> str:
    """Meeting id = transcript filename stem: YYYY-MM-DD-<slug>."""
    created = drive_file.get("createdTime", "")
    if created:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        date_str = dt.strftime("%Y-%m-%d")
    else:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"{date_str}-{recording_slug(drive_file)}"


def infer_source(filename: str) -> str:
    name = filename.lower()
    if name.startswith("phone_"):
        return "phone"
    if name.startswith("whatsapp_"):
        return "whatsapp"
    if name.startswith("voice-"):
        return "voice"
    return "meet"
```

Add `import supabase_store` next to the other local imports (top of file, after `import requests`).

- [ ] **Step 4: Run helper tests to verify they pass**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_transcribe_helpers -v`
Expected: `OK` — 3 tests pass.

- [ ] **Step 5: Rewire `main()` — Supabase instead of file + git**

In `main()` (currently lines 636–773), make these changes:

a) State path (line 650) becomes the skill dir:

```python
    state_path = SCRIPT_DIR / ".transcriber-state.json"
```

b) Replace the `write_transcript(...)` block (lines 712–714):

```python
            meeting_id = meeting_id_for(rec)
            supabase_store.upsert_meeting({
                "id": meeting_id,
                "date": meeting_id[:10],
                "owner": rec.get("owner"),
                "language": "he",
                "source": infer_source(rec["name"]),
                "duration_seconds": raw_secs,
                "transcript_md": transcript,
            })
            print(f"  Stored meeting {meeting_id} in Supabase")
```

c) In the same loop, replace `new_transcripts.append((rel_transcript, rec.get("owner")))` with `new_transcripts.append((meeting_id, rec.get("owner")))`, and update the Done notification (line 722) to:

```python
            slack_notify(
                f"✅ Done: `{meeting_id}` _{duration_str}_",
                slack_token, thread_ts=thread_ts,
            )
```

d) Delete the whole "Commit and push new transcripts to git" block (lines 738–765) — Supabase is the only destination now.

e) The final stdout block becomes:

```python
    if new_transcripts:
        print("\nNEW_TRANSCRIPTS:")
        for meeting_id, owner in new_transcripts:
            owner_hint = f" (recorded from {owner}'s Drive)" if owner else ""
            print(f"  {meeting_id}{owner_hint}")
    print("\nDone.")
```

f) Delete the now-unused `write_transcript()` function (lines 606–629) and the `output_dir`/`output_dir_rel` variables in `main()` (`config["output_dir"]` stays in config.json harmlessly, but nothing reads it).

- [ ] **Step 6: Migrate the state file (one-time, host)**

```bash
cp /share/nanoclaw/groups/global/calls/meetings/.transcriber-state.json \
   /share/nanoclaw/groups/global/skills/meeting-transcriber/.transcriber-state.json
```

Verify: `python3 -c "import json; s=json.load(open('/share/nanoclaw/groups/global/skills/meeting-transcriber/.transcriber-state.json')); print(len(s['processed']), 'processed ids')"`
Expected: a count ≥ 179. Leave the original in place (frozen archive; reconcile no longer reads it after Task 4).

- [ ] **Step 7: Syntax check + re-run both test files**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m py_compile transcribe.py && python3 -m unittest test_transcribe_helpers test_supabase_store -v`
Expected: compile clean, all tests `OK`. (A live end-to-end run happens at cutover, Task 9, when the container has the new env.)

- [ ] **Step 8: Update `SKILL.md`**

In `groups/global/skills/meeting-transcriber/SKILL.md`: add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to the `env:` frontmatter list; in "How it works" replace steps 4–5 with "4. Upserts the meeting row (transcript, date, owner, source, duration) into the Supabase `meetings` table" and "5. Prints NEW_TRANSCRIPTS meeting ids for the agent"; update the State section to say the state file lives at `skills/meeting-transcriber/.transcriber-state.json` and is no longer committed.

- [ ] **Step 9: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/transcribe.py \
        groups/global/skills/meeting-transcriber/test_transcribe_helpers.py \
        groups/global/skills/meeting-transcriber/SKILL.md
git commit -m "feat(meetings): transcribe.py writes to Supabase, drops git commits and transcript files

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `reconcile.py` — pending = one Supabase query

**Files:**
- Modify: `groups/global/skills/meeting-transcriber/reconcile.py` (full rewrite, it shrinks to ~40 lines)

**Interfaces:**
- Consumes: `supabase_store.pending_meetings()` (Task 2).
- Produces: same stdout contract the cron prompt expects — `PENDING_TRANSCRIPTS:` followed by `  <meeting-id> (recorded from <owner>'s Drive)` lines, or `No pending summaries to reconcile.`

- [ ] **Step 1: Rewrite `reconcile.py`**

Replace the entire file with:

```python
#!/usr/bin/env python3
"""Report meetings in Supabase that have a transcript but no summary yet."""

import fcntl
import os
import tempfile
from pathlib import Path

import supabase_store

LOCK_FILE = Path(tempfile.gettempdir()) / "fishbone-summary-reconciler.lock"


def acquire_lock() -> bool:
    try:
        lock_fd = open(LOCK_FILE, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        acquire_lock._fd = lock_fd  # type: ignore[attr-defined]
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return True
    except OSError:
        return False


def main() -> None:
    if not acquire_lock():
        print("Another reconciler instance is running. Exiting.")
        return

    pending = supabase_store.pending_meetings()
    if not pending:
        print("No pending summaries to reconcile.")
        return

    print(f"Found {len(pending)} meeting(s) without summaries:")
    print("\nPENDING_TRANSCRIPTS:")
    for row in pending:
        owner = row.get("owner")
        owner_hint = f" (recorded from {owner}'s Drive)" if owner else ""
        print(f"  {row['id']}{owner_hint}")


if __name__ == "__main__":
    main()
```

(The old Slack-history scanning, `.transcriber-state.json` records logic, and `summary_exists_for()` are deleted — that was the brittleness this project removes. Note `records` was never even populated by `transcribe.py`.)

- [ ] **Step 2: Syntax check + live run**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m py_compile reconcile.py && env $(grep -E '^SUPABASE_(URL|SERVICE_KEY)=' /share/nanoclaw/.env | xargs) python3 reconcile.py`
Expected before backfill (Task 6): `No pending summaries to reconcile.` (table is empty — that's correct).

- [ ] **Step 3: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/reconcile.py
git commit -m "feat(meetings): reconcile.py queries Supabase instead of scanning Slack history

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `meeting-processor` SKILL.md — Supabase read/write

**Files:**
- Modify: `groups/global/skills/meeting-processor/SKILL.md`

**Interfaces:**
- Consumes: `meetings` row shape (Task 1), `NEW_TRANSCRIPTS`/`PENDING_TRANSCRIPTS` id lines (Tasks 3–4). The agent executes these instructions inside the container, where `SUPABASE_URL`/`SUPABASE_SERVICE_KEY` are set.
- Produces: after each processed meeting, the row has `summary_md`, `title`, `type`, `slack_ts` and fresh `participants`/`themes` rows.

- [ ] **Step 1: Rewrite the affected SKILL.md sections**

Keep sections 3b (assumption mapping), 3c (Linear dedup), 3d (weekly kickoff), 5 (Linear issues), 6 (learnings) as they are. Replace sections 0, 1, 4, add 4b, and trim 7:

Section 0 (replaces the path-extraction + Slack dedup):

````markdown
### 0. Extract meeting id and dedup check
The trigger message contains a meeting id like:
```
Process meeting transcript: `2026-07-05-bxw-faqy-yqf-2026-07-05-15-47-gmt-3`
```
(Legacy triggers may pass a path like `calls/meetings/<id>.md` — the id is the filename stem.)

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
````

Section 1 (replaces "Fetch the transcript"):

```markdown
### 1. Read the transcript
Use `row["transcript_md"]` from step 0. If the row is missing but a legacy file
exists at `/workspace/global/calls/meetings/<id>.md`, read that file, then create
the row first with `supabase_store.upsert_meeting({"id": ..., "date": id[:10], "transcript_md": ...})`.
```

Section 4: keep the posting code as-is, but change the format's second line — the transcript link now points at the dashboard:

```
*Meeting: <title>* | YYYY-MM-DD
_<meeting-id>_ | <https://fishbone-ai.github.io/meeting-insights/#/meeting/<meeting-id>|Open in dashboard>
```

New section 4b (after the Slack post; use the `ts` from the `chat.postMessage` response):

````markdown
### 4b. Save the structured summary to Supabase
This is what makes the meeting a first-class data citizen — never skip it.

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
````

Section 7 becomes learnings-only:

```markdown
### 7. Commit and push learnings
```bash
cd /workspace/project && git add groups/global/learnings/ && git commit -m "docs(learnings): <meeting-title> YYYY-MM-DD" && git push
```
(Transcripts are no longer committed — they live in Supabase.)
```

- [ ] **Step 2: Review the whole SKILL.md top-to-bottom**

Read the full edited file once and check: no remaining references to `calls/meetings/` outside the legacy-fallback note, no remaining Slack-history dedup code, section numbering intact (0, 1, 2, 3, 3b, 3c, 3d, 4, 4b, 5, 6, 7).

- [ ] **Step 3: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-processor/SKILL.md
git commit -m "feat(meetings): meeting-processor reads/writes Supabase, links dashboard

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Backfill — 179 transcripts + Slack summary import

**Files:**
- Create: `groups/global/skills/meeting-transcriber/slack_summary_parser.py`
- Create: `groups/global/skills/meeting-transcriber/backfill.py`
- Test: `groups/global/skills/meeting-transcriber/test_slack_summary_parser.py`

**Interfaces:**
- Consumes: `supabase_store` (Task 2); env `SLACK_BOT_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`; transcripts dir (default `/share/nanoclaw/groups/global/calls/meetings`, override with `MEETINGS_DIR` env var so it also runs in-container against `/workspace/global/calls/meetings`).
- Produces: every transcript file has a `meetings` row; rows matched in Slack history additionally have `summary_md`, `title`, `slack_ts`, participants, `imported_from='slack'`. Function `parse_slack_summary(text: str) -> dict | None` returning `{"stem", "title", "date", "participants": list[str], "summary_md"}`.

- [ ] **Step 1: Write failing parser tests**

`test_slack_summary_parser.py`:

```python
import unittest
from slack_summary_parser import parse_slack_summary

CANONICAL = """*Meeting: Sean × Todd prep* | 2026-06-29
_2026-06-29-sean-todd_ | <https://github.com/fishbone-ai/nanoclaw/blob/main/groups/global/calls/meetings/2026-06-29-sean-todd.md|Transcription>

*Participants*
• Avishay, Sean Murphy (⚠️ Speaker 3 identity unclear — who is this?)

*Summary*
• Discussed partnership scope
• Agreed on next steps

*Decisions*
• Go with option B

*Suggested Linear issues* (reply ✅ to approve all, or list which ones to create)
1. [high] Draft proposal — Send by Friday
"""


class TestParser(unittest.TestCase):
    def test_parses_canonical_format(self):
        r = parse_slack_summary(CANONICAL)
        self.assertEqual(r["stem"], "2026-06-29-sean-todd")
        self.assertEqual(r["title"], "Sean × Todd prep")
        self.assertEqual(r["date"], "2026-06-29")
        self.assertEqual(r["participants"], ["Avishay", "Sean Murphy"])
        self.assertIn("## Summary", r["summary_md"])
        self.assertIn("- Discussed partnership scope", r["summary_md"])
        self.assertIn("## Decisions", r["summary_md"])
        self.assertNotIn("Linear", r["summary_md"])  # suggestions section excluded

    def test_rejects_non_canonical_messages(self):
        self.assertIsNone(parse_slack_summary("📋 *Summary: Or Git × Avishay — May 10, 2026*\nIntro..."))
        self.assertIsNone(parse_slack_summary("random chatter"))
        self.assertIsNone(parse_slack_summary(""))

    def test_missing_participants_section_is_ok(self):
        text = "*Meeting: Quick sync* | 2026-06-01\n_2026-06-01-quick-sync_ | <http://x|T>\n\n*Summary*\n• a\n"
        r = parse_slack_summary(text)
        self.assertEqual(r["participants"], [])
        self.assertIn("- a", r["summary_md"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify failure**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_slack_summary_parser -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'slack_summary_parser'`

- [ ] **Step 3: Write `slack_summary_parser.py`**

```python
#!/usr/bin/env python3
"""Parse canonical #meeting-summaries Slack posts into structured summary data."""

import re

HEADER_RE = re.compile(r"^\*Meeting: (?P<title>.+?)\*\s*\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*$")
STEM_RE = re.compile(r"^_(?P<stem>[\w.\-]+)_\s*\|")
SECTION_RE = re.compile(r"^\*(?P<name>[A-Z][^*]*?)\*")
EXCLUDED_SECTIONS = ("suggested linear issues", "suggested goals.md update")


def parse_slack_summary(text: str) -> dict | None:
    lines = text.splitlines()
    if not lines:
        return None
    header = HEADER_RE.match(lines[0].strip())
    if not header:
        return None
    stem = None
    for line in lines[1:3]:
        m = STEM_RE.match(line.strip())
        if m:
            stem = m.group("stem")
            break
    if not stem:
        return None

    participants: list[str] = []
    md_parts: list[str] = []
    section = None
    for line in lines[1:]:
        stripped = line.strip()
        sec = SECTION_RE.match(stripped)
        if sec:
            section = sec.group("name").strip().lower()
            if section != "participants" and not section.startswith(EXCLUDED_SECTIONS):
                md_parts.append(f"\n## {sec.group('name').strip()}")
            continue
        if not stripped or section is None:
            continue
        if section == "participants":
            names = re.sub(r"\([^)]*\)", "", stripped.lstrip("• ").strip())
            participants.extend(n.strip() for n in names.split(",") if n.strip())
        elif not section.startswith(EXCLUDED_SECTIONS):
            md_parts.append(re.sub(r"^•\s*", "- ", stripped))

    summary_md = "\n".join(md_parts).strip()
    if not summary_md:
        return None
    return {
        "stem": stem,
        "title": header.group("title"),
        "date": header.group("date"),
        "participants": participants,
        "summary_md": summary_md,
    }
```

- [ ] **Step 4: Run parser tests to verify they pass**

Run: `cd /share/nanoclaw/groups/global/skills/meeting-transcriber && python3 -m unittest test_slack_summary_parser -v`
Expected: `OK` — 3 tests pass. If the canonical-format test fails on section handling, fix the parser, not the test — the fixture mirrors the real SKILL.md format.

- [ ] **Step 5: Write `backfill.py`**

```python
#!/usr/bin/env python3
"""One-time backfill: transcript files -> Supabase rows; Slack history -> summaries.

Idempotent: upserts transcripts, never overwrites a non-null summary_md.
Run with: SUPABASE_URL=... SUPABASE_SERVICE_KEY=... SLACK_BOT_TOKEN=... python3 backfill.py
"""

import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import supabase_store
from slack_summary_parser import parse_slack_summary

MEETINGS_DIR = Path(os.environ.get("MEETINGS_DIR", "/share/nanoclaw/groups/global/calls/meetings"))
SUMMARIES_CHANNEL = "C0AQ6D4KPGQ"
STEM_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def infer_source(stem: str) -> str:
    rest = STEM_DATE_RE.sub("", stem)
    if rest.startswith("phone_"):
        return "phone"
    if rest.startswith("whatsapp_"):
        return "whatsapp"
    if rest.startswith("voice-"):
        return "voice"
    return "meet"


def transcript_body(raw: str) -> str:
    marker = "## Transcription\n"
    idx = raw.find(marker)
    return raw[idx + len(marker):].strip() if idx != -1 else raw.strip()


def detect_language(text: str) -> str:
    hebrew = len(re.findall(r"[֐-׿]", text[:4000]))
    return "he" if hebrew > 50 else "en"


def load_transcripts() -> int:
    count = 0
    for path in sorted(MEETINGS_DIR.glob("*.md")):
        stem = path.stem
        m = STEM_DATE_RE.match(stem)
        if not m:
            print(f"  SKIP (no date prefix): {stem}")
            continue
        existing = supabase_store.get_meeting(stem, columns="id")
        if existing:
            continue
        body = transcript_body(path.read_text(encoding="utf-8"))
        supabase_store.upsert_meeting({
            "id": stem,
            "date": m.group(1),
            "language": detect_language(body),
            "source": infer_source(stem),
            "transcript_md": body,
        })
        count += 1
        print(f"  transcript row: {stem}")
    return count


def iter_slack_history():
    token = os.environ["SLACK_BOT_TOKEN"]
    cursor = None
    while True:
        params = {"channel": SUMMARIES_CHANNEL, "limit": 200}
        if cursor:
            params["cursor"] = cursor
        req = Request(
            "https://slack.com/api/conversations.history?" + urlencode(params),
            headers={"Authorization": f"Bearer {token}"},
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        if not data.get("ok"):
            raise RuntimeError(f"Slack error: {data.get('error')}")
        yield from data.get("messages", [])
        cursor = data.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return
        time.sleep(1.2)  # tier-3 rate limit headroom


def attach_summaries() -> tuple[int, int]:
    attached = skipped = 0
    for msg in iter_slack_history():
        parsed = parse_slack_summary(msg.get("text") or "")
        if not parsed:
            continue
        row = supabase_store.get_meeting(parsed["stem"], columns="id,summary_md")
        if row is None:
            print(f"  no transcript row for Slack summary: {parsed['stem']}")
            skipped += 1
            continue
        if row.get("summary_md"):
            continue  # never overwrite
        supabase_store.save_summary(
            parsed["stem"],
            summary_md=parsed["summary_md"],
            title=parsed["title"],
            mtype=None,                       # filled by the inference pass (Step 8)
            slack_ts=msg.get("ts"),
            participants=[{"name": n} for n in parsed["participants"]],
            themes=[],
            imported_from="slack",
        )
        attached += 1
        print(f"  summary attached: {parsed['stem']}")
    return attached, skipped


def main() -> None:
    print(f"Loading transcripts from {MEETINGS_DIR} ...")
    n = load_transcripts()
    print(f"{n} new transcript rows.")
    print("Scanning Slack history for summaries ...")
    attached, skipped = attach_summaries()
    print(f"{attached} summaries attached, {skipped} had no matching transcript row.")
    print(f"Pending (need regeneration): {len(supabase_store.pending_meetings())}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Dry-run sanity check on one file, then run the full backfill**

```bash
cd /share/nanoclaw/groups/global/skills/meeting-transcriber
python3 -m py_compile backfill.py
env $(grep -E '^(SUPABASE_(URL|SERVICE_KEY)|SLACK_BOT_TOKEN)=' /share/nanoclaw/.env | xargs) python3 backfill.py
```
Expected output shape: `~179 new transcript rows`, then `N summaries attached` (expect well over half — the canonical format has been in use since April), and a final pending count = 179 − attached. Rerun the same command once more — expected: `0 new transcript rows`, `0 summaries attached` (idempotency proof).

- [ ] **Step 7: Verify counts in Supabase**

```bash
curl -s "$SUPABASE_URL/rest/v1/meetings?select=id&imported_from=eq.slack" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY" | python3 -c "import json,sys; print(len(json.load(sys.stdin)), 'imported')"
curl -s "$SUPABASE_URL/rest/v1/meetings?select=id" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $SUPABASE_ANON_KEY" | python3 -c "import json,sys; print(len(json.load(sys.stdin)), 'total')"
```
Expected: total = number of `*.md` files with a date prefix in `calls/meetings/` (~179); imported = the attached count from Step 6.

- [ ] **Step 8: Queue the type/theme inference pass (agent task, summaries only)**

Post this as a message to the transcriber Slack channel (`#meeting-transcription-logs`, C0ALJGPQSL8) so the group agent runs it once, or run it directly if executing inside that group:

```
One-time task: classify backfilled meetings in Supabase.
For each row from supabase_store._request("GET", "meetings?type=is.null&summary_md=not.is.null&select=id,title,summary_md"):
read only title + summary_md (NOT transcripts), then update via
supabase_store.save_summary is NOT needed — just PATCH type and insert themes:
  supabase_store._request("PATCH", f"meetings?id=eq.{id}", body={"type": "<type>"})
  supabase_store._request("POST", "themes", body=[{"meeting_id": id, "theme": t} for t in themes])
Types: discovery-call | vc-meeting | internal-strategy | phone-call | weekly-retro | weekly-kickoff | other.
Themes: 2-5 kebab-case tags; reuse existing spellings (GET themes?select=theme first).
Work in batches of 20; report a count summary at the end, no per-meeting messages.
```

Remaining meetings with `summary_md IS NULL` need no action — the reconcile cron (Task 4) will surface them to meeting-processor automatically, a few per cycle.

- [ ] **Step 9: Commit**

```bash
cd /share/nanoclaw
git add groups/global/skills/meeting-transcriber/slack_summary_parser.py \
        groups/global/skills/meeting-transcriber/test_slack_summary_parser.py \
        groups/global/skills/meeting-transcriber/backfill.py
git commit -m "feat(meetings): backfill script — transcript rows + Slack summary import

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Dashboard scaffold, data layer, and Pages deploy

**Files:**
- Create: `groups/global/meeting-insights/` (new nested git repo → `fishbone-ai/meeting-insights`): `package.json`, `vite.config.ts`, `tsconfig.json`, `index.html`, `src/main.tsx`, `src/App.tsx`, `src/lib/supabase.ts`, `src/lib/types.ts`, `.github/workflows/pages.yml`, `.gitignore`
- Modify: `/share/nanoclaw/.gitignore` (add `groups/global/meeting-insights/`)

**Interfaces:**
- Consumes: Supabase tables + anon key (Task 1).
- Produces (used by Task 8): `fetchIndex(): Promise<MeetingIndexRow[]>` (everything except `transcript_md`, with participants + themes joined), `fetchTranscript(id: string): Promise<string | null>`; types `MeetingIndexRow { id; date; title; type; language; source; owner; duration_seconds; summary_md; slack_ts; participants: Participant[]; themes: string[] }`, `Participant { name; category; role; company }`. Deployed site at `https://fishbone-ai.github.io/meeting-insights/`.

- [ ] **Step 1: Scaffold**

```bash
cd /share/nanoclaw/groups/global
npm create vite@latest meeting-insights -- --template react-ts
cd meeting-insights
npm install @supabase/supabase-js
npm install -D vitest
echo 'groups/global/meeting-insights/' >> /share/nanoclaw/.gitignore
```

Set in `vite.config.ts`: `base: '/meeting-insights/'`. Add to `package.json` scripts: `"test": "vitest run"`. Site `<title>`: `Fishbone Meetings`.

- [ ] **Step 2: Write the data layer + a vitest for the join shaping**

`src/lib/types.ts`:

```typescript
export interface Participant {
  name: string;
  category: 'founder' | 'practitioner' | 'vc' | 'advisor' | 'other' | null;
  role: string | null;
  company: string | null;
}

export interface MeetingIndexRow {
  id: string;
  date: string;
  title: string | null;
  type: string | null;
  language: string | null;
  source: string | null;
  owner: string | null;
  duration_seconds: number | null;
  summary_md: string | null;
  slack_ts: string | null;
  participants: Participant[];
  themes: string[];
}
```

`src/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js';
import type { MeetingIndexRow } from './types';

// Anon key is public by design (read-only via RLS).
const SUPABASE_URL = 'https://<ref>.supabase.co';          // value from Task 1
const SUPABASE_ANON_KEY = '<anon-key>';                    // value from Task 1

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const INDEX_COLUMNS =
  'id,date,title,type,language,source,owner,duration_seconds,summary_md,slack_ts,' +
  'participants(name,category,role,company),themes(theme)';

export function shapeIndexRow(raw: any): MeetingIndexRow {
  return { ...raw, participants: raw.participants ?? [], themes: (raw.themes ?? []).map((t: any) => t.theme) };
}

export async function fetchIndex(): Promise<MeetingIndexRow[]> {
  const { data, error } = await supabase
    .from('meetings').select(INDEX_COLUMNS).order('date', { ascending: false });
  if (error) throw error;
  return (data ?? []).map(shapeIndexRow);
}

export async function fetchTranscript(id: string): Promise<string | null> {
  const { data, error } = await supabase
    .from('meetings').select('transcript_md').eq('id', id).single();
  if (error) throw error;
  return data?.transcript_md ?? null;
}
```

`src/lib/supabase.test.ts` (tests the pure shaping only — no network):

```typescript
import { describe, expect, it } from 'vitest';
import { shapeIndexRow } from './supabase';

describe('shapeIndexRow', () => {
  it('flattens themes and defaults empty children', () => {
    const row = shapeIndexRow({ id: 'm1', date: '2026-07-05', themes: [{ theme: 'ai-security' }] });
    expect(row.themes).toEqual(['ai-security']);
    expect(row.participants).toEqual([]);
  });
});
```

- [ ] **Step 3: Run the test**

Run: `cd /share/nanoclaw/groups/global/meeting-insights && npm test`
Expected: 1 test passes. (Vitest imports `supabase.ts`, which calls `createClient` at module load — that is fine offline, createClient does not connect eagerly.)

- [ ] **Step 4: Minimal App proving live reads**

`src/App.tsx`:

```tsx
import { useEffect, useState } from 'react';
import { fetchIndex } from './lib/supabase';
import type { MeetingIndexRow } from './lib/types';

export default function App() {
  const [meetings, setMeetings] = useState<MeetingIndexRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchIndex().then(setMeetings).catch((e) => setError(String(e)));
  }, []);

  if (error) return <p role="alert">Failed to load meetings: {error}</p>;
  if (!meetings) return <p>Loading…</p>;
  return <h1>Fishbone Meetings — {meetings.length} meetings</h1>;
}
```

Run: `npm run dev` then `curl -s http://127.0.0.1:5173 | head -5` to confirm it serves; open in agent-browser if available and confirm the count matches Task 6 Step 7's total. Then `npm run build` — expected: clean build.

- [ ] **Step 5: Create the GitHub repo + Pages workflow**

Copy the deploy workflow from the cyber-mindmap repo and save as `.github/workflows/pages.yml` — build job identical (`node 22`, `npm ci`, `npm run build`, upload `dist`), plus the standard deploy job:

```yaml
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

```bash
cd /share/nanoclaw/groups/global/meeting-insights
git init -b main && git add -A && git commit -m "feat: meeting insights dashboard scaffold"
# Create the repo the same way cyber-mindmap was created. If `gh` is available:
gh repo create fishbone-ai/meeting-insights --public --source . --push
# Otherwise: create it in the GitHub UI, then add a PAT remote (same PAT pattern
# as the nanoclaw origin remote — read it with `git -C /share/nanoclaw remote get-url origin`)
# and `git push -u origin main`.
```

Enable Pages with source "GitHub Actions": repo Settings → Pages → Source → GitHub Actions (or `gh api repos/fishbone-ai/meeting-insights/pages -X POST -f build_type=workflow`).

- [ ] **Step 6: Verify the deployed site**

Wait for the Actions run to finish (`gh run watch` or the Actions tab), then:
Run: `curl -s -o /dev/null -w '%{http_code}' https://fishbone-ai.github.io/meeting-insights/`
Expected: `200`. Open the URL and confirm the meeting count renders (live Supabase read from the browser — this also proves CORS/anon key work from Pages).

---

### Task 8: Meetings list + detail views

**Files:**
- Create: `groups/global/meeting-insights/src/lib/router.ts`, `src/lib/filter.ts`, `src/lib/filter.test.ts`, `src/views/MeetingsList.tsx`, `src/views/MeetingDetail.tsx`, `src/lib/markdown.ts`
- Modify: `src/App.tsx`

**Interfaces:**
- Consumes: `fetchIndex`, `fetchTranscript`, `MeetingIndexRow` (Task 7).
- Produces: hash routes `#/` (list) and `#/meeting/<id>` (detail — the URL format the Slack posts link to, Task 5); `filterMeetings(rows, q: {text?, type?, theme?, person?, from?, to?}): MeetingIndexRow[]`; `useHashRoute(): string` hook; `renderMarkdown(md: string): string` (safe minimal renderer).

- [ ] **Step 1: Write failing tests for `filterMeetings`**

`src/lib/filter.test.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { filterMeetings } from './filter';
import type { MeetingIndexRow } from './types';

const m = (over: Partial<MeetingIndexRow>): MeetingIndexRow => ({
  id: 'x', date: '2026-07-01', title: 'T', type: null, language: null, source: null,
  owner: null, duration_seconds: null, summary_md: null, slack_ts: null,
  participants: [], themes: [], ...over,
});

const rows = [
  m({ id: 'a', title: 'VC chat', type: 'vc-meeting', themes: ['fundraising'], date: '2026-07-01',
      participants: [{ name: 'Dana', category: 'vc', role: null, company: 'Grove' }] }),
  m({ id: 'b', title: 'CISO discovery', type: 'discovery-call', themes: ['ai-security'],
      date: '2026-06-01', summary_md: 'talked about agent security' }),
];

describe('filterMeetings', () => {
  it('matches free text against title and summary, case-insensitive', () => {
    expect(filterMeetings(rows, { text: 'agent SECURITY' }).map(r => r.id)).toEqual(['b']);
  });
  it('filters by type, theme, and participant name', () => {
    expect(filterMeetings(rows, { type: 'vc-meeting' }).map(r => r.id)).toEqual(['a']);
    expect(filterMeetings(rows, { theme: 'ai-security' }).map(r => r.id)).toEqual(['b']);
    expect(filterMeetings(rows, { person: 'dana' }).map(r => r.id)).toEqual(['a']);
  });
  it('filters by date range inclusive', () => {
    expect(filterMeetings(rows, { from: '2026-06-15' }).map(r => r.id)).toEqual(['a']);
    expect(filterMeetings(rows, { to: '2026-06-15' }).map(r => r.id)).toEqual(['b']);
  });
  it('combines filters with AND', () => {
    expect(filterMeetings(rows, { text: 'vc', theme: 'ai-security' })).toEqual([]);
  });
});
```

Run: `npm test` — Expected: FAIL, module `./filter` not found.

- [ ] **Step 2: Implement `src/lib/filter.ts`**

```typescript
import type { MeetingIndexRow } from './types';

export interface MeetingQuery {
  text?: string; type?: string; theme?: string; person?: string; from?: string; to?: string;
}

export function filterMeetings(rows: MeetingIndexRow[], q: MeetingQuery): MeetingIndexRow[] {
  const text = q.text?.toLowerCase();
  const person = q.person?.toLowerCase();
  return rows.filter((r) => {
    if (text && !(`${r.title ?? ''}\n${r.summary_md ?? ''}\n${r.id}`.toLowerCase().includes(text))) return false;
    if (q.type && r.type !== q.type) return false;
    if (q.theme && !r.themes.includes(q.theme)) return false;
    if (person && !r.participants.some((p) => p.name.toLowerCase().includes(person))) return false;
    if (q.from && r.date < q.from) return false;
    if (q.to && r.date > q.to) return false;
    return true;
  });
}
```

Run: `npm test` — Expected: all tests pass.

- [ ] **Step 3: Router hook, markdown renderer, and views**

`src/lib/router.ts`:

```typescript
import { useEffect, useState } from 'react';

export function useHashRoute(): string {
  const [route, setRoute] = useState(window.location.hash.slice(1) || '/');
  useEffect(() => {
    const onChange = () => setRoute(window.location.hash.slice(1) || '/');
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}
```

`src/lib/markdown.ts` — minimal, escape-first (transcripts/summaries are trusted-ish but escape anyway):

```typescript
function escapeHtml(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

export function renderMarkdown(md: string): string {
  return escapeHtml(md)
    .split(/\n{2,}/)
    .map((block) => {
      if (block.startsWith('## ')) return `<h2>${block.slice(3)}</h2>`;
      if (/^[-•] /m.test(block)) {
        const items = block.split('\n').filter(Boolean)
          .map((l) => `<li>${l.replace(/^[-•]\s*/, '')}</li>`).join('');
        return `<ul>${items}</ul>`;
      }
      return `<p>${block.replace(/\n/g, '<br/>')}</p>`;
    })
    .join('\n')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
}
```

`src/views/MeetingsList.tsx` — controlled filter bar over `filterMeetings`; each row shows date, title (fallback: id), type badge, theme chips, participant names, duration (`Math.round(duration_seconds/60)`m); row links to `#/meeting/<id>`. Filter options (types, themes, people) are derived from the loaded rows via `new Set(...)`.

`src/views/MeetingDetail.tsx` — finds the row by id from the index; renders title/date/type/participants/themes header, `renderMarkdown(summary_md)`, a link to the Slack message when `slack_ts` is set (`https://app.slack.com/client/…` optional — skip if workspace id unknown), and a "Load transcript" `<details>` section that calls `fetchTranscript(id)` on first open and renders it in `<pre style={{whiteSpace:'pre-wrap'}}>` (transcripts are speaker-labeled plain text; RTL: set `dir="auto"` on the pre so Hebrew renders correctly).

`src/App.tsx` — routes: `/` → MeetingsList, `/meeting/<id>` → MeetingDetail; fetches the index once at the top and passes it down; nav header with links `Meetings · People · Insights` (People/Insights routes land in Task 9).

- [ ] **Step 4: Verify locally, then deploy**

Run: `npm test && npm run build && npm run dev`
Check in browser (or agent-browser): list renders all meetings, filters narrow it, clicking a meeting shows summary, "Load transcript" pulls the Hebrew transcript and renders RTL. Then:

```bash
git add -A && git commit -m "feat: meetings list + detail views with filters and lazy transcripts" && git push
```
Expected: Actions deploy goes green; spot-check the live URL, including a deep link `https://fishbone-ai.github.io/meeting-insights/#/meeting/<some-id>`.

---

### Task 9: People + Insights views, then cutover

**Files:**
- Create: `groups/global/meeting-insights/src/lib/aggregate.ts`, `src/lib/aggregate.test.ts`, `src/views/People.tsx`, `src/views/Insights.tsx`
- Modify: `src/App.tsx` (add routes)

**Interfaces:**
- Consumes: `MeetingIndexRow` (Task 7).
- Produces: `peopleIndex(rows): PersonAgg[]` where `PersonAgg { name; category; company; meetingCount; firstMet; lastMet; meetingIds: string[] }` (sorted by meetingCount desc); `weeklyCounts(rows): { week: string; count: number }[]` (week = ISO Monday `YYYY-MM-DD`); `themeCounts(rows): { theme: string; count: number }[]`; `typeCounts(rows): { type: string; count: number }[]`.

- [ ] **Step 1: Write failing aggregation tests**

`src/lib/aggregate.test.ts`:

```typescript
import { describe, expect, it } from 'vitest';
import { peopleIndex, themeCounts, typeCounts, weeklyCounts } from './aggregate';
import type { MeetingIndexRow } from './types';

const m = (over: Partial<MeetingIndexRow>): MeetingIndexRow => ({
  id: 'x', date: '2026-07-01', title: null, type: null, language: null, source: null,
  owner: null, duration_seconds: null, summary_md: null, slack_ts: null,
  participants: [], themes: [], ...over,
});

const rows = [
  m({ id: 'a', date: '2026-06-30', type: 'discovery-call', themes: ['ai-security'],
      participants: [{ name: 'Dana', category: 'vc', role: null, company: 'Grove' }] }),
  m({ id: 'b', date: '2026-07-02', type: 'discovery-call', themes: ['ai-security', 'dbsc'],
      participants: [{ name: 'dana', category: null, role: null, company: null },
                     { name: 'Guy', category: 'practitioner', role: null, company: null }] }),
];

describe('aggregations', () => {
  it('peopleIndex merges case-insensitively, keeps first non-null metadata, tracks range', () => {
    const dana = peopleIndex(rows).find((p) => p.name === 'Dana')!;
    expect(dana.meetingCount).toBe(2);
    expect(dana.company).toBe('Grove');
    expect(dana.category).toBe('vc');
    expect(dana.firstMet).toBe('2026-06-30');
    expect(dana.lastMet).toBe('2026-07-02');
    expect(dana.meetingIds).toEqual(['a', 'b']);
  });
  it('sorts people by meeting count desc', () => {
    expect(peopleIndex(rows)[0].name).toBe('Dana');
  });
  it('weeklyCounts buckets by ISO Monday', () => {
    // 2026-06-30 is a Tuesday, 2026-07-02 a Thursday — same week starting Mon 2026-06-29
    expect(weeklyCounts(rows)).toEqual([{ week: '2026-06-29', count: 2 }]);
  });
  it('counts themes and types', () => {
    expect(themeCounts(rows)).toEqual([{ theme: 'ai-security', count: 2 }, { theme: 'dbsc', count: 1 }]);
    expect(typeCounts(rows)).toEqual([{ type: 'discovery-call', count: 2 }]);
  });
});
```

Run: `npm test` — Expected: FAIL, `./aggregate` not found.

- [ ] **Step 2: Implement `src/lib/aggregate.ts`**

```typescript
import type { MeetingIndexRow } from './types';

export interface PersonAgg {
  name: string; category: string | null; company: string | null;
  meetingCount: number; firstMet: string; lastMet: string; meetingIds: string[];
}

export function peopleIndex(rows: MeetingIndexRow[]): PersonAgg[] {
  const byKey = new Map<string, PersonAgg>();
  const sorted = [...rows].sort((a, b) => a.date.localeCompare(b.date));
  for (const r of sorted) {
    for (const p of r.participants) {
      const key = p.name.trim().toLowerCase();
      const agg = byKey.get(key);
      if (!agg) {
        byKey.set(key, {
          name: p.name.trim(), category: p.category, company: p.company,
          meetingCount: 1, firstMet: r.date, lastMet: r.date, meetingIds: [r.id],
        });
      } else {
        agg.meetingCount += 1;
        agg.lastMet = r.date;
        agg.meetingIds.push(r.id);
        agg.category ??= p.category;
        agg.company ??= p.company;
      }
    }
  }
  return [...byKey.values()].sort((a, b) => b.meetingCount - a.meetingCount);
}

function isoMonday(date: string): string {
  const d = new Date(date + 'T00:00:00Z');
  const day = (d.getUTCDay() + 6) % 7; // Mon=0
  d.setUTCDate(d.getUTCDate() - day);
  return d.toISOString().slice(0, 10);
}

export function weeklyCounts(rows: MeetingIndexRow[]): { week: string; count: number }[] {
  const map = new Map<string, number>();
  for (const r of rows) map.set(isoMonday(r.date), (map.get(isoMonday(r.date)) ?? 0) + 1);
  return [...map.entries()].map(([week, count]) => ({ week, count }))
    .sort((a, b) => a.week.localeCompare(b.week));
}

function counted(values: string[]): { key: string; count: number }[] {
  const map = new Map<string, number>();
  for (const v of values) map.set(v, (map.get(v) ?? 0) + 1);
  return [...map.entries()].map(([key, count]) => ({ key, count }))
    .sort((a, b) => b.count - a.count || a.key.localeCompare(b.key));
}

export function themeCounts(rows: MeetingIndexRow[]): { theme: string; count: number }[] {
  return counted(rows.flatMap((r) => r.themes)).map(({ key, count }) => ({ theme: key, count }));
}

export function typeCounts(rows: MeetingIndexRow[]): { type: string; count: number }[] {
  return counted(rows.map((r) => r.type).filter((t): t is string => !!t))
    .map(({ key, count }) => ({ type: key, count }));
}
```

Run: `npm test` — Expected: all tests pass.

- [ ] **Step 3: Build the two views**

**IMPORTANT: read the `dataviz` skill before writing any chart markup** (it governs colors, axes, bar specs). Keep charts dependency-free inline SVG:

- `src/views/People.tsx` — table of `peopleIndex(rows)` (name, category badge, company, count, first/last met); clicking a person filters an inline list of their meetings (links to `#/meeting/<id>`). Exclude the two founders from the top of the table by default with a "show founders" toggle (they attend everything, so they drown the signal).
- `src/views/Insights.tsx` — stat tiles (total meetings, total hours from `duration_seconds`, people met, active themes) + three charts: meetings per week (bar, `weeklyCounts`), top 12 themes (horizontal bar, `themeCounts`), type breakdown (horizontal bar, `typeCounts`).
- `src/App.tsx` — add routes `/people` → People, `/insights` → Insights.

- [ ] **Step 4: Verify, deploy, and check live**

Run: `npm test && npm run build`, check locally with `npm run dev`, then:

```bash
git add -A && git commit -m "feat: people and insights views" && git push
```
Expected: deploy green; live site shows all three views with real backfilled data.

- [ ] **Step 5: Cutover — restart nanoclaw with the new code**

The nanoclaw service restart picks up the `container-runner.ts` env passthrough (Task 1) so the *next* agent containers get Supabase creds. This is an HA addon — restart via the addon, not systemctl:

```bash
# from the HA host / addon supervisor context used previously:
docker restart addon_29dff93f_nanoclaw
```

Then watch one full cycle in `/tmp/nanoclaw-debug.log` (the transcriber cron fires every 10 min): confirm `transcribe.py` runs clean (or exits with "No new recordings"), and `reconcile.py` prints pending ids from Supabase. If a new recording lands, verify the full flow: row inserted → summary posted to Slack with the dashboard link → `summary_md` filled → meeting visible on the live dashboard.

- [ ] **Step 6: Update workspace docs + commit**

In `groups/global/CLAUDE.md`, update the skills table row for meeting-transcriber ("transcribes to Supabase meeting store") and meeting-processor ("summarizes into Supabase + Slack; dashboard: https://fishbone-ai.github.io/meeting-insights/"). Add a `groups/global/calls/meetings/README.md` one-liner: "Frozen archive as of 2026-07. New transcripts live in the Supabase meeting store; browse at https://fishbone-ai.github.io/meeting-insights/."

```bash
cd /share/nanoclaw
git add groups/global/CLAUDE.md groups/global/calls/meetings/README.md .gitignore
git commit -m "docs(meetings): point workspace docs at the Supabase meeting store + dashboard

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Post-plan verification checklist

- [ ] `python3 -m unittest` green across all three test files in `skills/meeting-transcriber/`.
- [ ] `npm test` green in `meeting-insights` (filter + aggregate + shaping suites).
- [ ] Live dashboard shows ≈179 meetings; a spot-checked meeting renders summary + transcript.
- [ ] Anon write to Supabase still fails (rerun Task 1 Step 4's negative probe).
- [ ] Next real recording flows end-to-end without touching git (`git -C /share/nanoclaw log --oneline -3` shows no new `feat(transcription)` commits).
- [ ] Run the `verify` skill on the pipeline changes before declaring done.
