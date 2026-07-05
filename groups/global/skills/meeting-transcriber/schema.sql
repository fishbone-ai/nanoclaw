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
