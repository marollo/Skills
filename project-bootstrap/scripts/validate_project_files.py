#!/usr/bin/env python3
"""Validate the six project-bootstrap files in a directory.

Usage: python3 validate_project_files.py <target-dir> [--suffix .proposed]

Exit code 0 = no errors (warnings allowed), 1 = at least one error.
Standard library only.
"""
import csv
import re
import sys
from pathlib import Path

FILES = ["CLAUDE.md", "PROJECT.md", "BUG_AND_FIXES.md", "DECISIONS.md", "DEV_OPS.md", "BACKLOG.csv"]
BACKLOG_HEADER = ["ID", "Epic", "Title", "Description", "Type", "Priority", "Status",
                  "Estimate", "Acceptance Criteria", "Depends On"]
TYPES = {"Story", "Task", "Bug", "Spike", "Chore"}
PRIORITIES = {"Must", "Should", "Could", "Won't"}
STATUSES = {"Backlog", "Ready", "In Progress", "In Review", "Done", "Blocked"}
ESTIMATES = {"", "1", "2", "3", "5", "8"}
ID_RE = re.compile(r"^BL-\d{3,}$")
PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}|<[A-Za-z][^<>\n]*\s[^<>\n]*>|\bTODO_FILL\b|\bLorem ipsum\b")
SINGLE_WORD_ANGLE_RE = re.compile(r"<[a-z][a-z-]{1,20}>")
CLAUDE_MD_MAX_LINES = 150

errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def strip_code(text):
    """Remove fenced code blocks and inline code so '<cmd>'-style text in examples is ignored."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def check_placeholders(name, text):
    hits = PLACEHOLDER_RE.findall(strip_code(text))
    # HTML comments are allowed (used for 'no bugs logged yet' notes)
    hits = [h for h in hits if not h.startswith("<!--")]
    if hits:
        err(f"{name}: leftover template placeholders, e.g. {hits[0]!r} ({len(hits)} total)")
    singles = SINGLE_WORD_ANGLE_RE.findall(text)
    if singles:
        warn(f"{name}: possible unfilled placeholder(s) like {singles[0]} ({len(singles)} total); fine only if intentional")


def check_claude_md(text, existing):
    lines = text.count("\n") + 1
    if lines > CLAUDE_MD_MAX_LINES:
        warn(f"CLAUDE.md: {lines} lines; it is loaded every session, keep it under ~{CLAUDE_MD_MAX_LINES}")
    for other in FILES:
        if other == "CLAUDE.md" or other not in existing:
            continue
        if other not in text:
            warn(f"CLAUDE.md: does not mention {other}")
    if not re.search(r"^#{2,3}\s*Commands", text, flags=re.M | re.I):
        warn("CLAUDE.md: no 'Commands' section")


def check_project_md(text):
    if not re.search(r"\bFR-\d+", text):
        warn("PROJECT.md: no functional requirement IDs (FR-1, FR-2, ...)")
    if not re.search(r"open questions|assumptions", text, flags=re.I):
        warn("PROJECT.md: no 'Open questions and assumptions' section")
    tbd = len(re.findall(r"\bTBD\b", text))
    if tbd:
        pass  # reported by --digest


def check_decisions(text):
    ids = re.findall(r"^##\s+(DEC-\d+)", text, flags=re.M)
    if not ids:
        warn("DECISIONS.md: no DEC-### entries (seed it with the decisions made during the interview)")
    if len(ids) != len(set(ids)):
        err("DECISIONS.md: duplicate DEC IDs")
    sections = re.split(r"^##\s+DEC-\d+", text, flags=re.M)[1:]
    for dec_id, body in zip(ids, sections):
        if not re.search(r"\*\*Status\*\*\s*:", body):
            err(f"DECISIONS.md: {dec_id} has no Status line")


def check_backlog(path):
    try:
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
    except Exception as e:  # noqa: BLE001
        err(f"BACKLOG.csv: cannot parse ({e})")
        return
    if not rows:
        err("BACKLOG.csv: empty")
        return
    if rows[0] != BACKLOG_HEADER:
        err(f"BACKLOG.csv: header must be exactly {','.join(BACKLOG_HEADER)}")
        return
    data = rows[1:]
    if not data:
        err("BACKLOG.csv: no items")
        return
    seen = {}
    for i, row in enumerate(data, start=2):
        if len(row) != len(BACKLOG_HEADER):
            err(f"BACKLOG.csv line {i}: {len(row)} columns, expected {len(BACKLOG_HEADER)} (unquoted comma?)")
            continue
        rec = dict(zip(BACKLOG_HEADER, (c.strip() for c in row)))
        rid = rec["ID"]
        if not ID_RE.match(rid):
            err(f"BACKLOG.csv line {i}: ID {rid!r} does not match BL-001 format")
        elif rid in seen:
            err(f"BACKLOG.csv line {i}: duplicate ID {rid}")
        else:
            seen[rid] = i
        for col in ("Epic", "Title", "Description"):
            if not rec[col]:
                err(f"BACKLOG.csv line {i} ({rid}): empty {col}")
        if rec["Type"] not in TYPES:
            err(f"BACKLOG.csv line {i} ({rid}): Type {rec['Type']!r} not in {sorted(TYPES)}")
        if rec["Priority"] not in PRIORITIES:
            err(f"BACKLOG.csv line {i} ({rid}): Priority {rec['Priority']!r} not in {sorted(PRIORITIES)}")
        if rec["Status"] not in STATUSES:
            err(f"BACKLOG.csv line {i} ({rid}): Status {rec['Status']!r} not in {sorted(STATUSES)}")
        if rec["Estimate"] not in ESTIMATES:
            warn(f"BACKLOG.csv line {i} ({rid}): Estimate {rec['Estimate']!r} outside 1,2,3,5,8 (split large items)")
        if rec["Status"] in ("Ready", "In Progress") and not rec["Acceptance Criteria"]:
            err(f"BACKLOG.csv line {i} ({rid}): {rec['Status']} item has no Acceptance Criteria")
        if i - 2 < 10 and rec["Type"] in ("Story", "Task") and not rec["Acceptance Criteria"]:
            warn(f"BACKLOG.csv line {i} ({rid}): top-10 item without Acceptance Criteria")
    # dependencies: must exist and come earlier
    order = {rid: ln for rid, ln in seen.items()}
    for i, row in enumerate(data, start=2):
        if len(row) != len(BACKLOG_HEADER):
            continue
        rid = row[0].strip()
        deps = [d.strip() for d in row[9].split(";") if d.strip()]
        for d in deps:
            if d == rid:
                err(f"BACKLOG.csv line {i} ({rid}): depends on itself")
            elif d not in order:
                err(f"BACKLOG.csv line {i} ({rid}): depends on unknown ID {d}")
            elif order[d] > i:
                warn(f"BACKLOG.csv line {i} ({rid}): depends on {d}, which is ordered after it")
    if not any(r[6].strip() == "Ready" for r in data if len(r) == len(BACKLOG_HEADER)):
        warn("BACKLOG.csv: no item is Ready; Claude Code has nothing to start on")
    pass


def cross_refs(root, suffix):
    """Every FR-/NFR-/DEC-/BL- ID mentioned anywhere must be defined in its home file."""
    def txt(n):
        p = root / (n + suffix)
        return p.read_text(encoding="utf-8") if p.exists() else ""
    proj, dec = txt("PROJECT.md"), txt("DECISIONS.md")
    defined = {
        "FR": set(re.findall(r"\b(FR-\d+)", proj)), "NFR": set(re.findall(r"\b(NFR-\d+)", proj)),
        "DEC": set(re.findall(r"^##\s+(DEC-\d+)", dec, flags=re.M)),
        "BL": set(),
    }
    bp = root / ("BACKLOG.csv" + suffix)
    if bp.exists():
        try:
            with open(bp, newline="", encoding="utf-8") as f:
                defined["BL"] = {r[0] for r in list(csv.reader(f))[1:] if r}
        except Exception:  # noqa: BLE001
            pass
    for name in FILES:
        text = txt(name)
        if name == "BUG_AND_FIXES.md":
            continue
        for kind, rx in (("NFR", r"\b(NFR-\d+)"), ("FR", r"\b(FR-\d+)"), ("DEC", r"\b(DEC-\d+)"), ("BL", r"\b(BL-\d+)")):
            for ref in sorted(set(re.findall(rx, text))):
                if ref not in defined[kind] and defined[kind]:
                    err(f"{name}: references {ref}, which is not defined in its home file")
    return defined


def digest(root, suffix, defined):
    parts = []
    bp = root / ("BACKLOG.csv" + suffix)
    if bp.exists():
        with open(bp, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))[1:]
        ready = [r[0] for r in rows if len(r) > 6 and r[6].strip() == "Ready"]
        parts.append(f"backlog {len(rows)} items, Ready: {', '.join(ready) or 'none'}")
        if rows:
            parts.append(f"first: {rows[0][0]} {rows[0][2]}")
    parts.append(f"FR {len(defined['FR'])}, NFR {len(defined['NFR'])}, DEC {len(defined['DEC'])}")
    pm = root / ("PROJECT.md" + suffix)
    if pm.exists():
        t = pm.read_text(encoding="utf-8")
        parts.append(f"ASSUMED {len(re.findall(r'^- ASSUMED', t, flags=re.M))}, TBD {len(re.findall(r'^- TBD', t, flags=re.M))}")
    cm = root / ("CLAUDE.md" + suffix)
    if cm.exists():
        parts.append(f"CLAUDE.md {cm.read_text(encoding='utf-8').count(chr(10)) + 1} lines")
    return " | ".join(parts)


def main():
    args = sys.argv[1:]
    want_digest = "--digest" in args
    args = [a for a in args if a != "--digest"]
    suffix = ""
    if "--suffix" in args:
        k = args.index("--suffix")
        suffix = args[k + 1]
        del args[k:k + 2]
    if len(args) != 1:
        print(__doc__)
        return 2
    root = Path(args[0])
    if not root.is_dir():
        print(f"error: {root} is not a directory")
        return 2

    existing = {n for n in FILES if (root / (n + suffix)).exists()}
    present = []
    for name in FILES:
        p = root / (name + suffix)
        if not p.exists():
            err(f"{name}{suffix}: missing")
            continue
        if p.stat().st_size < 40:
            err(f"{name}{suffix}: file is empty or nearly empty")
            continue
        present.append(name)
        if name.endswith(".md"):
            text = p.read_text(encoding="utf-8")
            check_placeholders(name, text)
            if name == "CLAUDE.md":
                check_claude_md(text, existing)
            elif name == "PROJECT.md":
                check_project_md(text)
            elif name == "DECISIONS.md":
                check_decisions(text)
        else:
            check_backlog(p)

    defined = cross_refs(root, suffix)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    status = "OK" if not errors else "FAILED"
    print(f"{status}: {len(errors)} error(s), {len(warnings)} warning(s)")
    if want_digest and not errors:
        print("digest:", digest(root, suffix, defined))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
