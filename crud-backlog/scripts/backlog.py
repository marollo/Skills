#!/usr/bin/env python3
"""
Small helper for reading and writing a project's backlog.csv file.

Why this script exists: hand-editing CSV text is an easy place to make a
small mistake (a stray comma in a note field breaks the columns, an ID
gets reused, a typo in "In Progres" silently creates a new status that
never shows up when filtering). This script does the file handling so
those mistakes can't happen, and always prints back what it did as JSON
so the caller can show the person a clear confirmation.

Every command re-reads the file from disk before changing anything and
writes the whole file back when done, so it's always working from the
current contents on disk rather than a stale copy.
"""

import argparse
import csv
import json
import os
import sys

FIELDNAMES = ["id", "title", "status", "priority", "notes"]
ALLOWED_STATUS = ["Backlog", "To Do", "In Progress", "Blocked", "Done"]
ALLOWED_PRIORITY = ["High", "Medium", "Low"]


def normalize(value, allowed, field_name):
    """
    Matches a value against the allowed list without caring about
    capitalization (so "done" and "Done" both work), and returns the
    correctly-capitalized version. Exits with a clear error if the
    value isn't one of the allowed options at all.
    """
    for option in allowed:
        if value.strip().lower() == option.lower():
            return option
    sys.exit(
        f'Invalid {field_name} "{value}". Allowed values: {", ".join(allowed)}'
    )


def read_rows(path):
    """Loads all backlog rows from disk. Returns an empty list if the file doesn't exist yet."""
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def write_rows(path, rows):
    """Writes the full set of rows back to disk, creating the folder if needed."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def next_id(rows):
    """Picks the next free ID: one higher than the largest ID currently in use, starting at 1."""
    if not rows:
        return 1
    return max(int(row["id"]) for row in rows) + 1


def cmd_list(args):
    """Prints backlog rows as JSON, optionally narrowed by status, priority, or a keyword search."""
    rows = read_rows(args.path)
    if args.status:
        status = normalize(args.status, ALLOWED_STATUS, "status")
        rows = [r for r in rows if r["status"] == status]
    if args.priority:
        priority = normalize(args.priority, ALLOWED_PRIORITY, "priority")
        rows = [r for r in rows if r["priority"] == priority]
    if args.keyword:
        needle = args.keyword.lower()
        rows = [
            r for r in rows
            if needle in r["title"].lower() or needle in r["notes"].lower()
        ]
    print(json.dumps(rows, indent=2))


def cmd_add(args):
    """Adds one new task with an auto-assigned ID and prints the row that was created."""
    rows = read_rows(args.path)
    status = normalize(args.status, ALLOWED_STATUS, "status")
    priority = normalize(args.priority, ALLOWED_PRIORITY, "priority")
    new_row = {
        "id": str(next_id(rows)),
        "title": args.title,
        "status": status,
        "priority": priority,
        "notes": args.notes or "",
    }
    rows.append(new_row)
    write_rows(args.path, rows)
    print(json.dumps(new_row, indent=2))


def cmd_update(args):
    """Changes one or more fields on an existing task, found by its ID, and prints the updated row."""
    rows = read_rows(args.path)
    for row in rows:
        if row["id"] == str(args.id):
            if args.title is not None:
                row["title"] = args.title
            if args.status is not None:
                row["status"] = normalize(args.status, ALLOWED_STATUS, "status")
            if args.priority is not None:
                row["priority"] = normalize(args.priority, ALLOWED_PRIORITY, "priority")
            if args.notes is not None:
                row["notes"] = args.notes
            write_rows(args.path, rows)
            print(json.dumps(row, indent=2))
            return
    sys.exit(f"No task with id {args.id} found.")


def cmd_delete(args):
    """Removes one task by its ID and prints the row that was removed."""
    rows = read_rows(args.path)
    for i, row in enumerate(rows):
        if row["id"] == str(args.id):
            removed = rows.pop(i)
            write_rows(args.path, rows)
            print(json.dumps(removed, indent=2))
            return
    sys.exit(f"No task with id {args.id} found.")


def main():
    parser = argparse.ArgumentParser(description="CRUD operations on a backlog.csv file.")
    parser.add_argument("path", help="Path to backlog.csv")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List tasks, optionally filtered")
    p_list.add_argument("--status")
    p_list.add_argument("--priority")
    p_list.add_argument("--keyword")
    p_list.set_defaults(func=cmd_list)

    p_add = sub.add_parser("add", help="Add a new task")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--status", default="Backlog")
    p_add.add_argument("--priority", default="Medium")
    p_add.add_argument("--notes", default="")
    p_add.set_defaults(func=cmd_add)

    p_update = sub.add_parser("update", help="Update fields on an existing task")
    p_update.add_argument("id")
    p_update.add_argument("--title")
    p_update.add_argument("--status")
    p_update.add_argument("--priority")
    p_update.add_argument("--notes")
    p_update.set_defaults(func=cmd_update)

    p_delete = sub.add_parser("delete", help="Delete a task by id")
    p_delete.add_argument("id")
    p_delete.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
