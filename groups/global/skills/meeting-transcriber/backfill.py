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
            mtype=None,                       # filled by the inference pass
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
