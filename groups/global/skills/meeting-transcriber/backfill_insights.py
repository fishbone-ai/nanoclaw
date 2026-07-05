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
