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
