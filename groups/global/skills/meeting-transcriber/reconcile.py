#!/usr/bin/env python3
"""Reconcile transcript summaries: find transcripts without posted summaries and report them."""

import fcntl
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

SLACK_LOG_CHANNEL = "C0ALJGPQSL8"
SLACK_SUMMARIES_CHANNEL = "C0AQ6D4KPGQ"
LOCK_FILE = Path(tempfile.gettempdir()) / "fishbone-summary-reconciler.lock"
WORKSPACE = Path("/workspace/global")


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


def get_slack_token() -> str | None:
    return os.environ.get("SLACK_BOT_TOKEN")


def load_state(state_path: Path) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text())
    return {"processed": [], "records": {}}


def normalize_state(state: dict) -> dict:
    if "records" not in state or not isinstance(state["records"], dict):
        state["records"] = {}
    if "processed" not in state or not isinstance(state["processed"], list):
        state["processed"] = []
    return state


def summary_exists_for(rel_path: str) -> bool:
    token = get_slack_token()
    if not token:
        return False
    stem = Path(rel_path).stem
    params = urlencode({"channel": SLACK_SUMMARIES_CHANNEL, "limit": 100})
    try:
        resp = requests.get(
            f"https://slack.com/api/conversations.history?{params}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        data = resp.json()
        if not data.get("ok"):
            return False
        for msg in data.get("messages", []):
            text = msg.get("text") or ""
            if "Meeting:" in text and stem in text:
                return True
    except Exception:
        pass
    return False


def main() -> None:
    if not acquire_lock():
        print("Another reconciler instance is running. Exiting.")
        return

    output_dir = WORKSPACE / "calls" / "meetings"
    state_path = output_dir / ".transcriber-state.json"
    state = normalize_state(load_state(state_path))
    records = state["records"]

    pending = []
    for file_id, record in records.items():
        rel_path = record.get("transcript_path")
        if not rel_path:
            continue
        if record.get("transcript_status") != "done":
            continue
        transcript_file = WORKSPACE / rel_path
        if not transcript_file.exists():
            continue
        if record.get("summary_status") == "done":
            continue
        if summary_exists_for(rel_path):
            record["summary_status"] = "done"
            record["summary_posted_at"] = datetime.now(timezone.utc).isoformat()
            continue
        owner = record.get("owner")
        pending.append((rel_path, owner))

    # Save state updates
    state_path.write_text(json.dumps(state, indent=2) + "\n")

    if not pending:
        print("No pending summaries to reconcile.")
        return

    print(f"Found {len(pending)} transcript(s) without summaries:")
    print("\nPENDING_TRANSCRIPTS:")
    for rel_path, owner in pending:
        owner_hint = f" (recorded from {owner}'s Drive)" if owner else ""
        print(f"  {rel_path}{owner_hint}")


if __name__ == "__main__":
    main()
