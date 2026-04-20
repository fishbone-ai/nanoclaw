# Workflows

How we work with Claude Code and this repo.

## General conventions

- **Write in plain markdown** unless there's a good reason for another format
- **Keep files concise**. Working docs, not polished publications.
- **Use ISO dates** everywhere: 2025-03-05
- **Filenames**: lowercase, hyphens for word separation
- **No em-dashes**. Use -- or rewrite the sentence.

## Common tasks with Claude Code

### Log a learning
After a call or experiment, ask Claude Code to add an entry to the current month's file in `learnings/`. Include the date, source, what we learned, and what it means.

### Draft outreach
Point Claude Code at a prospect and a template in `outreach/templates/`. It fills in the personalization, you review and send. Log the sent version in `outreach/sent/`.

### Update assumptions
When we learn something that validates or invalidates an assumption, use the assumptions CLI:

```
python strategy/assumptions/cli.py list                          # see all 33 assumptions
python strategy/assumptions/cli.py show <id>                     # full detail for one
python strategy/assumptions/cli.py update <id> --status testing  # change status
python strategy/assumptions/cli.py update <id> --notes "..."     # add notes
python strategy/assumptions/cli.py aggregate                     # see alignment gaps
python strategy/assumptions/cli.py export                        # markdown dump
```

The CLI reads and writes `strategy/Fishbone assumptions.xlsx` directly. Default updates go to Avishay's sheet; use `--person ohav` for Ohav's.

### Record a decision
For significant decisions, create a new ADR in `strategy/decisions/` following the existing format. Number sequentially.

### Prep for a call
Ask Claude Code to pull together context from prospects, previous learnings, and strategy docs into a brief for the call.

## Review cadence

- Weekly: scan learnings, update assumptions if needed
- Monthly: review thesis and strategy docs, check if anything needs to change
