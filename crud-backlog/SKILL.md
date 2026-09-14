---
name: crud-backlog
description: Manage a project's task backlog stored in a project-management/backlog.csv file — add tasks, list or filter them, update their status/priority/notes, and delete them. Use this whenever the user talks about their backlog, task list, or project tracker in natural language, e.g. "add a task to the backlog", "what's still open", "mark task 4 as done", "show me everything that's blocked", "delete that task", "what's high priority right now", or "update the notes on task 7". Trigger this even if the user doesn't say the word "backlog" explicitly but is clearly describing adding, listing, changing, or removing a tracked task or to-do item for the project. If project-management/backlog.csv doesn't exist yet in the current project, this skill creates it.
---

# CRUD Backlog

Keeps a lightweight task backlog for a project as a CSV file, and handles
every read/write to it through a bundled script rather than by hand-editing
the file. Hand-editing CSV text is where small mistakes creep in — a comma
inside a note breaks the columns, two tasks end up with the same ID, a typo
like "In Progres" creates a silent new status that never shows up again in
filters. The script (`scripts/backlog.py`) prevents all of that: it validates
status and priority against the fixed lists below, assigns IDs itself, and
always re-reads the file from disk before writing so it's never working from
a stale copy.

## Where the file lives

The backlog is `project-management/backlog.csv` at the root of the current
project (the directory the user is working in — usually the git repo root).
If it doesn't exist yet, the script creates it automatically the first time
you add a task. If you're unsure where the project root is, look for the
nearest `.git` folder or `CLAUDE.md` going up from the current directory.

## Schema

```
id,title,status,priority,notes
```

- **id** — plain integer, assigned automatically. Never set this yourself.
- **title** — short free text describing the task.
- **status** — one of: `Backlog`, `To Do`, `In Progress`, `Blocked`, `Done`
- **priority** — one of: `High`, `Medium`, `Low`
- **notes** — free text, optional.

The script matches status/priority case-insensitively (so `done` or `DONE`
both resolve to `Done`), so you don't need to worry about exact capitalization
when passing values through — just don't invent values outside these lists.
If a user asks for a status or priority that isn't one of these (e.g.
"urgent" or "In Review"), don't silently substitute the closest match —
ask them which of the real options they mean, since picking wrong could
misfile their task in a way they don't notice for a while.

## Running the script

Always call it with `python3`, the path to the project's backlog file, and
one subcommand. All commands print JSON to stdout describing what happened —
read that output and turn it into a plain-English confirmation or table for
the user rather than showing them raw JSON.

**Add a task:**
```
python3 <skill-dir>/scripts/backlog.py <path>/backlog.csv add --title "Build camera pan control" --priority High --notes "blocked on API keys"
```
`--status` and `--priority` default to `Backlog` and `Medium` if the user
doesn't specify them — mention what you defaulted to in your confirmation so
it's not a surprise.

**List / filter tasks:**
```
python3 <skill-dir>/scripts/backlog.py <path>/backlog.csv list [--status "In Progress"] [--priority High] [--keyword camera]
```
With no filters this lists everything. `--keyword` searches title and notes
(case-insensitive, substring match). Combine filters freely — they all apply
together (AND, not OR).

**Update a task:**
```
python3 <skill-dir>/scripts/backlog.py <path>/backlog.csv update 4 --status Done
```
Only pass the fields that are changing — anything you don't pass is left
alone. You can update several fields in one call (`--status`, `--priority`,
`--title`, `--notes` can all be combined).

**Delete a task:**
```
python3 <skill-dir>/scripts/backlog.py <path>/backlog.csv delete 4
```

If a command exits with an error (invalid id, invalid status/priority),
that error message is written for a person — relay it plainly rather than
retrying with a guessed value.

## Handling requests that touch several tasks at once

The user may ask for something like "mark all the bug fixes as done" or
"delete everything that's done". The script only acts on one task per call,
by design — that keeps every write small and auditable — but you can chain
calls yourself: first run `list` with a filter to find the matching tasks,
show the user which ones matched, then call `update`/`delete` once per
matching id. For anything that would change or remove more than a couple of
tasks, confirm the list with the user before making the changes, since a
bulk action is harder to notice and undo than a single one.

## Showing results to the user

After any change, confirm in plain English what happened (e.g. "Added task
5: 'Build camera pan control' — Backlog, High priority."). When showing a
list of tasks, render them as a markdown table, most relevant column order:

| ID | Title | Status | Priority | Notes |
|----|-------|--------|----------|-------|
| 4  | Build camera pan control | In Progress | High | blocked on API keys |

If a filtered list comes back empty, say so plainly ("Nothing is currently
Blocked") rather than showing an empty table.

## Adding a new project's first backlog

If a project has no `project-management/backlog.csv` yet and the user asks
to add a task, just run `add` — the script creates the file and the folder
for you. Let the user know you created it and where, since it's a new file
in their project they didn't ask for by name directly.
