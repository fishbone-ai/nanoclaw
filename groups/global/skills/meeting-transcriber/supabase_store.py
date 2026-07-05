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


def pending_meetings(limit: int | None = None) -> list[dict]:
    path = "meetings?summary_md=is.null&select=id,owner&order=date.asc"
    if limit:
        path += f"&limit={limit}"
    return _request("GET", path) or []


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
