# Assumptions

Strategic assumptions across 6 layers, independently scored by Avishay and Ohav. The CLI reads and writes a shared Google Sheet via `gws` (Google Workspace CLI), so both co-founders can edit from the browser or the terminal.

## Files

- `config.json` -- spreadsheet ID for the Google Sheet
- `cli.py` -- CLI wrapper for reading and updating assumptions

## Usage

```
python strategy/assumptions/cli.py list                          # all assumptions
python strategy/assumptions/cli.py list --layer market           # filter by layer
python strategy/assumptions/cli.py list --sort priority          # sort by priority
python strategy/assumptions/cli.py list --sort gap               # sort by alignment gap
python strategy/assumptions/cli.py show 1                        # full detail
python strategy/assumptions/cli.py update 1 --status testing     # update status
python strategy/assumptions/cli.py update 1 --person ohav --confidence 4  # update Ohav's score
python strategy/assumptions/cli.py add "Name here" --layer "L1 - Market"  # add new assumption
python strategy/assumptions/cli.py edit 1 --name "New name" --layer "L4 - GTM"  # edit shared fields
python strategy/assumptions/cli.py delete 1                      # delete from both sheets
python strategy/assumptions/cli.py aggregate                     # alignment gaps
python strategy/assumptions/cli.py export                        # markdown dump
```

## Scoring

- **Confidence (1-5):** How confident we are this assumption is true
- **Fatality (1-5):** How fatal it would be if this assumption is wrong
- **Priority:** `(6 - avg_confidence) * avg_fatality` -- higher = more urgent to test
- **Alignment Gap:** `abs(confidence_diff) + abs(fatality_diff)` -- higher = more disagreement
