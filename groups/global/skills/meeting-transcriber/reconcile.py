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
