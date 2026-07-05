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
