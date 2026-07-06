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

-- ── Full-text search (see 2026-07-06-meeting-search-design.md) ──────────────
-- Generated tsvector columns (explicit regconfig => IMMUTABLE => allowed as STORED).
-- NOTE: add-column-if-not-exists won't update an existing column's generation
-- expression. To change a vector definition later, drop the column first.
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
  select 'summary'::text as source, m.id as meeting_id, m.title, m.date,
         case when qe.tsq is null
              then left(regexp_replace(coalesce(m.summary_md, m.title, ''), '\s+', ' ', 'g'), 160)
              else ts_headline('english', coalesce(m.summary_md, m.title, ''), qe.tsq,
                               'StartSel=*, StopSel=*, MaxWords=35, MinWords=15, ShortWord=2') end as snippet,
         (case when qe.tsq is null then 0 else ts_rank(m.summary_vec, qe.tsq) end * 1.0)::real as rank
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
         ts_headline('english', coalesce(i.content, i.quote, ''), qe.tsq,
                     'StartSel=*, StopSel=*, MaxWords=35, MinWords=15, ShortWord=2'),
         (case when qe.tsq is null then 0 else ts_rank(i.search_vec, qe.tsq) end * 0.8)::real
  from insights i join meetings m on m.id = i.meeting_id, qe
  where 'insight' = any(sources)
    and qe.tsq is not null and i.search_vec @@ qe.tsq
    and (mtype is null or m.type = mtype)
    and (date_from is null or m.date >= date_from)
    and (date_to   is null or m.date <= date_to)
    and (participant is null or exists (
          select 1 from participants p where p.meeting_id = m.id and p.name ilike '%'||participant||'%'))
  order by rank desc, date desc
  limit max_results;
$func$;

grant execute on function search_meetings(text, text[], text, text, date, date, int) to anon;
