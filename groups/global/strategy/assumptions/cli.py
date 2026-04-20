#!/usr/bin/env python3
"""CLI for reading and updating the Fishbone assumptions spreadsheet."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
with open(CONFIG_PATH) as f:
    SPREADSHEET_ID = json.load(f)["spreadsheet_id"]

VALID_PERSONS = {"avishay", "ohav"}
EXPECTED_COLS = 11

# Column layout (0-indexed) -- same for Avishay and Ohav sheets
COL_ID = 0
COL_LAYER = 1
COL_NAME = 2
COL_DESC = 3
COL_CONFIDENCE = 4
COL_FATALITY = 5
COL_BLOCKED_BY = 6
COL_STATUS = 7
COL_TEST_METHOD = 8
COL_NOTES = 9
COL_UPDATED = 10


def err(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def gws_get(range_):
    """Read values from a Google Sheets range via gws."""
    params = json.dumps({"spreadsheetId": SPREADSHEET_ID, "range": range_})
    result = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "get", "--params", params],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err(f"gws get failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return data.get("values", [])


def gws_update(range_, values):
    """Write values to a Google Sheets range via gws."""
    params = json.dumps({
        "spreadsheetId": SPREADSHEET_ID,
        "range": range_,
        "valueInputOption": "USER_ENTERED",
    })
    body = json.dumps({"values": values})
    result = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "update",
         "--params", params, "--json", body],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err(f"gws update failed: {result.stderr.strip()}")


def gws_append(range_, values):
    """Append rows to a Google Sheets range via gws."""
    params = json.dumps({
        "spreadsheetId": SPREADSHEET_ID,
        "range": range_,
        "valueInputOption": "USER_ENTERED",
    })
    body = json.dumps({"values": values})
    result = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "append",
         "--params", params, "--json", body],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err(f"gws append failed: {result.stderr.strip()}")


def gws_clear(range_):
    """Clear values from a Google Sheets range via gws."""
    params = json.dumps({"spreadsheetId": SPREADSHEET_ID, "range": range_})
    result = subprocess.run(
        ["gws", "sheets", "spreadsheets", "values", "clear",
         "--params", params],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        err(f"gws clear failed: {result.stderr.strip()}")


def parse_number(val):
    """Convert a string value from gws to int or float, or None if empty."""
    if val is None or val == "":
        return None
    try:
        f = float(val)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return None


def pad_row(row):
    """Pad a row list to the expected number of columns."""
    if len(row) < EXPECTED_COLS:
        return row + [""] * (EXPECTED_COLS - len(row))
    return row


def find_row_number(person, assumption_id):
    """Find the 1-based row number for an assumption on a person's sheet."""
    rows = gws_get(f"{person}!A:A")
    for i, row in enumerate(rows):
        if i == 0:
            continue  # skip header
        if row and safe_int(row[0], f" in {person}'s sheet") == assumption_id:
            return i + 1  # 1-based for Sheets API
    return None


def validate_person(person):
    p = person.lower()
    if p not in VALID_PERSONS:
        err(f"Unknown person '{person}'. Valid options: {', '.join(VALID_PERSONS)}")
    return p.capitalize()


def validate_score(value, name):
    if value < 1 or value > 5:
        err(f"{name} must be between 1 and 5 (got {value})")


def safe_int(value, context=""):
    try:
        return int(value)
    except (ValueError, TypeError):
        err(f"Expected numeric ID but got '{value}'{context}")




def read_person_sheet(person):
    """Read all assumptions from a person's sheet. Returns list of dicts."""
    raw_rows = gws_get(f"{person}!A1:K999")
    rows = []
    for raw_row in raw_rows[1:]:  # skip header
        row = pad_row(raw_row)
        if not row[COL_ID]:
            continue
        rows.append({
            "id": safe_int(row[COL_ID], f" in {person}'s sheet"),
            "layer": row[COL_LAYER] or "",
            "name": row[COL_NAME] or "",
            "description": row[COL_DESC] or "",
            "confidence": parse_number(row[COL_CONFIDENCE]),
            "fatality": parse_number(row[COL_FATALITY]),
            "status": row[COL_STATUS] or "Untested",
            "test_method": row[COL_TEST_METHOD] or "",
            "notes": row[COL_NOTES] or "",
            "updated": row[COL_UPDATED] or "",
            "blocked_by": parse_number(row[COL_BLOCKED_BY]),
        })
    return rows


def compute_aggregated():
    """Compute aggregated view from both sheets."""
    avishay = {r["id"]: r for r in read_person_sheet("Avishay")}
    ohav = {r["id"]: r for r in read_person_sheet("Ohav")}

    all_ids = sorted(set(avishay.keys()) | set(ohav.keys()))
    results = []
    for aid in all_ids:
        a = avishay.get(aid, {})
        o = ohav.get(aid, {})
        base = a if a else o

        ac = a.get("confidence")
        af = a.get("fatality")
        oc = o.get("confidence")
        of_ = o.get("fatality")

        avg_conf = nullable_avg(ac, oc)
        avg_fat = nullable_avg(af, of_)

        priority = None
        if avg_conf is not None and avg_fat is not None:
            priority = (6 - avg_conf) * avg_fat

        # Alignment gap
        gap = None
        if ac is not None and oc is not None and af is not None and of_ is not None:
            gap = abs(float(ac) - float(oc)) + abs(float(af) - float(of_))

        results.append({
            "id": aid,
            "layer": base.get("layer", ""),
            "name": base.get("name", ""),
            "description": base.get("description", ""),
            "blocked_by": base.get("blocked_by"),
            "avishay_confidence": ac,
            "avishay_fatality": af,
            "avishay_status": a.get("status", ""),
            "avishay_notes": a.get("notes", ""),
            "avishay_test_method": a.get("test_method", ""),
            "ohav_confidence": oc,
            "ohav_fatality": of_,
            "ohav_status": o.get("status", ""),
            "ohav_notes": o.get("notes", ""),
            "ohav_test_method": o.get("test_method", ""),
            "avg_confidence": avg_conf,
            "avg_fatality": avg_fat,
            "priority": priority,
            "gap": gap,
        })

    # Compute effective priority: capped at blocker's effective priority.
    # Resolve iteratively to handle chains (A blocks B blocks C).
    by_id = {r["id"]: r for r in results}
    for r in results:
        r["effective_priority"] = r["priority"]
    changed = True
    while changed:
        changed = False
        for r in results:
            if r["blocked_by"] is not None and r["blocked_by"] in by_id:
                blocker_ep = by_id[r["blocked_by"]]["effective_priority"]
                if blocker_ep is not None and r["effective_priority"] is not None:
                    capped = min(r["effective_priority"], blocker_ep)
                    if capped != r["effective_priority"]:
                        r["effective_priority"] = capped
                        changed = True

    # Compute depth (0 = root, 1 = depends on root, etc.)
    for r in results:
        depth = 0
        cur = r
        while cur.get("blocked_by") is not None and cur["blocked_by"] in by_id:
            depth += 1
            cur = by_id[cur["blocked_by"]]
        r["depth"] = depth

    return results


def fmt(val, width, align="<"):
    s = str(val) if val is not None else "-"
    if len(s) > width:
        s = s[: width - 1] + "\u2026"
    return f"{s:{align}{width}}"


def dash(val, spec=""):
    """Format a value for display, returning '-' when None."""
    if val is None:
        return "-"
    if spec:
        return f"{val:{spec}}"
    return str(val)


def nullable_avg(a, b):
    """Average two values, tolerating None on either side."""
    if a is not None and b is not None:
        return (float(a) + float(b)) / 2
    if a is not None:
        return float(a)
    if b is not None:
        return float(b)
    return None


def cmd_list(args):
    rows = compute_aggregated()

    # Filter by layer
    if args.layer:
        q = args.layer.lower()
        rows = [r for r in rows if q in r["layer"].lower()]

    # Filter by status
    if args.status:
        q = args.status.lower()
        rows = [r for r in rows if q in r["avishay_status"].lower() or q in r["ohav_status"].lower()]

    # Sort
    if args.sort == "priority":
        # Effective priority DESC, depth ASC (roots before dependents), raw priority DESC
        rows.sort(key=lambda r: (
            -(r["effective_priority"] if r["effective_priority"] is not None else 0),
            r["depth"],
            -(r["priority"] if r["priority"] is not None else 0),
        ))
    elif args.sort == "gap":
        rows.sort(key=lambda r: r["gap"] if r["gap"] is not None else 0, reverse=True)
    else:
        rows.sort(key=lambda r: r["id"])

    # Print table
    if args.sort == "priority":
        header = f"{'#':>2}  {'ID':>3}  {fmt('Layer', 28)}  {fmt('Assumption', 36)}  {'Conf':>4}  {'Fat':>4}  {'Pri':>5}  {'EPri':>5}  {'Blk':>3}  {fmt('Status', 10)}"
        print(header)
        print("-" * len(header))
        for i, r in enumerate(rows, 1):
            conf_s = dash(r["avg_confidence"], ".1f")
            fat_s = dash(r["avg_fatality"], ".1f")
            pri_s = dash(r["priority"], ".1f")
            epri_s = dash(r["effective_priority"], ".1f")
            blk_s = str(int(r["blocked_by"])) if r["blocked_by"] is not None else ""
            print(f"{i:>2}  {r['id']:>3}  {fmt(r['layer'], 28)}  {fmt(r['name'], 36)}  {conf_s:>4}  {fat_s:>4}  {pri_s:>5}  {epri_s:>5}  {blk_s:>3}  {fmt(r['avishay_status'], 10)}")
    else:
        header = f"{'ID':>3}  {fmt('Layer', 28)}  {fmt('Assumption', 40)}  {'Conf':>4}  {'Fat':>4}  {'Pri':>5}  {fmt('Status', 10)}"
        print(header)
        print("-" * len(header))
        for r in rows:
            conf_s = dash(r["avg_confidence"], ".1f")
            fat_s = dash(r["avg_fatality"], ".1f")
            pri_s = dash(r["priority"], ".1f")
            print(f"{r['id']:>3}  {fmt(r['layer'], 28)}  {fmt(r['name'], 40)}  {conf_s:>4}  {fat_s:>4}  {pri_s:>5}  {fmt(r['avishay_status'], 10)}")

    print(f"\n{len(rows)} assumptions")


def cmd_show(args):
    agg = compute_aggregated()
    match = [r for r in agg if r["id"] == args.id]
    if not match:
        err(f"Assumption #{args.id} not found.")
    r = match[0]

    print(f"# Assumption #{r['id']}: {r['name']}")
    print(f"Layer: {r['layer']}")
    print()
    print("## Description")
    print(r["description"])
    print()
    print("## Scores")
    print(f"{'':15} {'Confidence':>10}  {'Fatality':>10}  {'Status':>10}")
    ac = dash(r["avishay_confidence"])
    af = dash(r["avishay_fatality"])
    oc = dash(r["ohav_confidence"])
    of_ = dash(r["ohav_fatality"])
    print(f"{'Avishay':15} {ac:>10}  {af:>10}  {r['avishay_status']:>10}")
    print(f"{'Ohav':15} {oc:>10}  {of_:>10}  {r['ohav_status']:>10}")
    print()
    conf_s = dash(r["avg_confidence"], ".1f")
    fat_s = dash(r["avg_fatality"], ".1f")
    pri_s = dash(r["priority"], ".1f")
    gap_s = dash(r["gap"], ".1f")
    epri_s = dash(r["effective_priority"], ".1f")
    blk_s = f"#{int(r['blocked_by'])}" if r["blocked_by"] is not None else "-"
    print(f"Avg Confidence: {conf_s}   Avg Fatality: {fat_s}   Priority: {pri_s}   Eff. Priority: {epri_s}   Alignment Gap: {gap_s}")
    print(f"Blocked by: {blk_s}")
    print()
    if r["avishay_test_method"] or r["ohav_test_method"]:
        print("## Test Method")
        if r["avishay_test_method"]:
            print(f"Avishay: {r['avishay_test_method']}")
        if r["ohav_test_method"]:
            print(f"Ohav: {r['ohav_test_method']}")
        print()
    if r["avishay_notes"] or r["ohav_notes"]:
        print("## Notes")
        if r["avishay_notes"]:
            print(f"Avishay: {r['avishay_notes']}")
        if r["ohav_notes"]:
            print(f"Ohav: {r['ohav_notes']}")


def cmd_update(args):
    person = validate_person(args.person)

    if args.confidence is not None:
        validate_score(args.confidence, "confidence")
    if args.fatality is not None:
        validate_score(args.fatality, "fatality")

    row_num = find_row_number(person, args.id)
    if row_num is None:
        err(f"Assumption #{args.id} not found on {person}'s sheet.")

    # Read current row to preserve unchanged values
    current = gws_get(f"{person}!A{row_num}:K{row_num}")
    if not current:
        err(f"Could not read row {row_num} from {person}'s sheet.")
    row = pad_row(current[0])

    updatable_fields = [
        ("status", COL_STATUS),
        ("confidence", COL_CONFIDENCE),
        ("fatality", COL_FATALITY),
        ("notes", COL_NOTES),
        ("test_method", COL_TEST_METHOD),
    ]
    changes = []
    for field, col in updatable_fields:
        val = getattr(args, field)
        if val is not None:
            row[col] = str(val)
            changes.append(f"{field} -> {val}")

    if not changes:
        err("No changes specified. Use --status, --confidence, --fatality, --notes, or --test-method.")

    gws_update(f"{person}!A{row_num}:K{row_num}", [row])
    print(f"Updated assumption #{args.id} on {person}'s sheet:")
    for c in changes:
        print(f"  {c}")


def cmd_add(args):
    # Determine next ID from both sheets
    max_id = 0
    for person in ["Avishay", "Ohav"]:
        for r in read_person_sheet(person):
            max_id = max(max_id, r["id"])
    new_id = max_id + 1

    blocked_by = str(args.blocked_by) if args.blocked_by else ""
    new_row = [str(new_id), args.layer, args.name, args.description or "",
               "", "", blocked_by, "Untested", "", "", ""]

    # Append to both sheets
    for person in ["Avishay", "Ohav"]:
        gws_append(f"{person}!A:K", [new_row])

    print(f"Added assumption #{new_id} to both sheets:")
    print(f"  Layer: {args.layer}")
    print(f"  Name: {args.name}")
    if args.description:
        print(f"  Description: {args.description}")
    if args.blocked_by:
        print(f"  Blocked by: #{args.blocked_by}")


def cmd_edit(args):
    if args.name is None and args.description is None and args.layer is None and args.blocked_by is None:
        err("No changes specified. Use --name, --description, --layer, or --blocked-by.")

    # Verify existence and update both sheets
    changes = []
    for person in ["Avishay", "Ohav"]:
        row_num = find_row_number(person, args.id)
        if row_num is None:
            err(f"Assumption #{args.id} not found on {person}'s sheet.")

        current = gws_get(f"{person}!A{row_num}:K{row_num}")
        if not current:
            err(f"Could not read row {row_num} from {person}'s sheet.")
        row = pad_row(current[0])

        if args.name is not None:
            row[COL_NAME] = args.name
        if args.description is not None:
            row[COL_DESC] = args.description
        if args.layer is not None:
            row[COL_LAYER] = args.layer
        if args.blocked_by is not None:
            row[COL_BLOCKED_BY] = "" if args.blocked_by == 0 else str(args.blocked_by)

        gws_update(f"{person}!A{row_num}:K{row_num}", [row])

    if args.name is not None:
        changes.append(f"name -> {args.name}")
    if args.description is not None:
        changes.append(f"description -> {args.description}")
    if args.layer is not None:
        changes.append(f"layer -> {args.layer}")
    if args.blocked_by is not None:
        if args.blocked_by == 0:
            changes.append("blocked_by -> (cleared)")
        else:
            changes.append(f"blocked_by -> #{args.blocked_by}")

    print(f"Updated assumption #{args.id} on both sheets:")
    for c in changes:
        print(f"  {c}")


def cmd_delete(args):
    for person in ["Avishay", "Ohav"]:
        row_num = find_row_number(person, args.id)
        if row_num is None:
            err(f"Assumption #{args.id} not found on {person}'s sheet.")
        gws_clear(f"{person}!A{row_num}:K{row_num}")

    print(f"Deleted assumption #{args.id} from both sheets.")


def cmd_aggregate(args):
    agg = compute_aggregated()

    # Only show rows where both have scored
    scored = [r for r in agg if r["gap"] is not None]
    unscored = [r for r in agg if r["gap"] is None]

    if scored:
        scored.sort(key=lambda r: r["gap"], reverse=True)
        print("## Alignment gaps (biggest disagreements first)")
        print()
        header = f"{'ID':>3}  {fmt('Assumption', 40)}  {'A.Conf':>6}  {'O.Conf':>6}  {'A.Fat':>5}  {'O.Fat':>5}  {'Gap':>4}  {'Pri':>5}"
        print(header)
        print("-" * len(header))
        for r in scored:
            ac = dash(r["avishay_confidence"])
            oc = dash(r["ohav_confidence"])
            af = dash(r["avishay_fatality"])
            of_ = dash(r["ohav_fatality"])
            gap_s = dash(r["gap"], ".1f")
            pri_s = dash(r["priority"], ".1f")
            print(f"{r['id']:>3}  {fmt(r['name'], 40)}  {ac:>6}  {oc:>6}  {af:>5}  {of_:>5}  {gap_s:>4}  {pri_s:>5}")

    if unscored:
        print()
        print(f"## {len(unscored)} assumptions not yet scored by both people")
        for r in unscored:
            who = []
            if r["avishay_confidence"] is None:
                who.append("Avishay")
            if r["ohav_confidence"] is None:
                who.append("Ohav")
            print(f"  #{r['id']:>2} {r['name'][:50]}  (missing: {', '.join(who)})")


def cmd_export(args):
    agg = compute_aggregated()

    print("# Fishbone Assumptions")
    print()

    current_layer = None
    for r in agg:
        if r["layer"] != current_layer:
            current_layer = r["layer"]
            print(f"## {current_layer}")
            print()

        conf_s = dash(r["avg_confidence"], ".1f")
        fat_s = dash(r["avg_fatality"], ".1f")
        pri_s = dash(r["priority"], ".1f")

        print(f"### #{r['id']}: {r['name']}")
        epri_s = dash(r["effective_priority"], ".1f")
        blk_s = f"#{int(r['blocked_by'])}" if r["blocked_by"] is not None else "-"
        print(f"**Confidence:** {conf_s} | **Fatality:** {fat_s} | **Priority:** {pri_s} | **Eff. Priority:** {epri_s} | **Blocked by:** {blk_s} | **Status:** {r['avishay_status']}")
        print()
        if r["description"]:
            print(r["description"])
            print()

        # Individual scores
        if r["avishay_confidence"] is not None or r["ohav_confidence"] is not None:
            print("| | Confidence | Fatality | Status |")
            print("|---|---|---|---|")
            ac = dash(r["avishay_confidence"])
            af = dash(r["avishay_fatality"])
            oc = dash(r["ohav_confidence"])
            of_ = dash(r["ohav_fatality"])
            print(f"| Avishay | {ac} | {af} | {r['avishay_status']} |")
            print(f"| Ohav | {oc} | {of_} | {r['ohav_status']} |")
            print()

        if r["avishay_notes"]:
            print(f"**Avishay notes:** {r['avishay_notes']}")
        if r["ohav_notes"]:
            print(f"**Ohav notes:** {r['ohav_notes']}")
        if r["avishay_test_method"]:
            print(f"**Test method (Avishay):** {r['avishay_test_method']}")
        if r["ohav_test_method"]:
            print(f"**Test method (Ohav):** {r['ohav_test_method']}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Fishbone assumptions CLI")
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list", help="List all assumptions")
    p_list.add_argument("--layer", help="Filter by layer (fuzzy match)")
    p_list.add_argument("--status", help="Filter by status (fuzzy match)")
    p_list.add_argument("--sort", choices=["id", "priority", "gap"], default="id", help="Sort order")

    # show
    p_show = sub.add_parser("show", help="Show full detail for one assumption")
    p_show.add_argument("id", type=int, help="Assumption ID")

    # update
    p_update = sub.add_parser("update", help="Update an assumption")
    p_update.add_argument("id", type=int, help="Assumption ID")
    p_update.add_argument("--person", default="avishay", help="Whose sheet to update (default: avishay)")
    p_update.add_argument("--status", help="New status")
    p_update.add_argument("--confidence", type=float, help="New confidence score (1-5)")
    p_update.add_argument("--fatality", type=float, help="New fatality score (1-5)")
    p_update.add_argument("--notes", help="New notes")
    p_update.add_argument("--test-method", dest="test_method", help="New test method")

    # add
    p_add = sub.add_parser("add", help="Add a new assumption")
    p_add.add_argument("name", help="Short name for the assumption")
    p_add.add_argument("--layer", required=True, help="Layer (e.g. 'L1 - Market')")
    p_add.add_argument("--description", help="Full description")
    p_add.add_argument("--blocked-by", dest="blocked_by", type=int, help="ID of assumption that must be validated first")

    # edit
    p_edit = sub.add_parser("edit", help="Edit shared fields (updates both sheets)")
    p_edit.add_argument("id", type=int, help="Assumption ID")
    p_edit.add_argument("--name", help="New short name")
    p_edit.add_argument("--description", help="New description")
    p_edit.add_argument("--layer", help="New layer")
    p_edit.add_argument("--blocked-by", dest="blocked_by", type=int, help="ID of blocker (0 to clear)")

    # delete
    p_delete = sub.add_parser("delete", help="Delete an assumption from both sheets")
    p_delete.add_argument("id", type=int, help="Assumption ID")

    # aggregate
    sub.add_parser("aggregate", help="Show alignment view between scorers")

    # export
    sub.add_parser("export", help="Export all assumptions as markdown")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    commands = {
        "list": cmd_list,
        "show": cmd_show,
        "update": cmd_update,
        "add": cmd_add,
        "edit": cmd_edit,
        "delete": cmd_delete,
        "aggregate": cmd_aggregate,
        "export": cmd_export,
    }
    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
