# Memory Search

Search persistent memory from past sessions across this project.

## When to Use

When you need to recall something from a previous conversation or session:
- "What did we decide about X?"
- "Did we already fix this?"
- "What happened last time with Y?"

## How to Search

```bash
curl -s "http://host.docker.internal:37777/api/search?query=YOUR_QUERY&limit=20"
```

Returns a formatted table of matching observations with IDs, timestamps, and titles.

## How to Fetch Full Details

```bash
curl -s "http://host.docker.internal:37777/api/observations/ID"
```

Replace `ID` with the numeric ID from the search results.

## Tips

- Keep queries short and specific: `"auth bug"` not `"the authentication bug we fixed"`
- Filter by type with `&obs_type=bugfix,feature,decision`
- Filter by date with `&dateStart=2026-04-01`
- The top-50 recent observations are already in your context — search is for going deeper
