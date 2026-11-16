#!/usr/bin/env python3
"""Render the six project files from a JSON brief.

Usage:
  python3 render_project_files.py <brief.json> <target-dir> [--force] [--map]

Claude writes only the project-specific content in the brief (see references/brief-schema.md);
this script supplies every boilerplate part (skeletons, how-to text, DEV_OPS defaults,
Foundation backlog items, CSV quoting, ID numbering, dependency ordering) and then runs the
validator. Existing files are never overwritten unless --force: they get a .proposed suffix.
Standard library only.
"""
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets" / "foundation"
FILES = ["CLAUDE.md", "PROJECT.md", "BUG_AND_FIXES.md", "DECISIONS.md", "DEV_OPS.md", "BACKLOG.csv"]
HEADER = ["ID", "Epic", "Title", "Description", "Type", "Priority", "Status", "Estimate",
          "Acceptance Criteria", "Depends On"]
TOKEN_RE = re.compile(r"\{(fr|nfr|dec|bl):([A-Za-z0-9_-]+)\}")
errors = []


def fail(msg):
    errors.append(msg)


def lst(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def bullets(items, fmt=lambda x: str(x)):
    return "\n".join(f"- {fmt(i)}" for i in items)


def get(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict) or p not in d or d[p] in (None, "", []):
            return default
        d = d[p]
    return d


# ---------------------------------------------------------------- ids and tokens
class Ids:
    def __init__(self):
        self.maps = {"fr": {}, "nfr": {}, "dec": {}, "bl": {}}

    def add(self, kind, key, ident):
        if key:
            if key in self.maps[kind]:
                fail(f"duplicate {kind} key {key!r}")
            self.maps[kind][key] = ident

    def resolve(self, text):
        if not isinstance(text, str):
            return text

        def sub(m):
            kind, key = m.group(1), m.group(2)
            if key not in self.maps[kind]:
                fail(f"unknown reference {{{kind}:{key}}}")
                return m.group(0)
            return self.maps[kind][key]
        return TOKEN_RE.sub(sub, text)


# ---------------------------------------------------------------- backlog
def build_backlog(brief, profile, ids):
    skeleton = get(brief, "walking_skeleton", default="the smallest end-to-end version of the main use case")
    skip = set(lst(get(brief, "foundation_skip", default=[])))
    if brief["project"].get("mode") == "existing":
        skip.add("f-skeleton")  # an existing project already has a running slice
    items = []
    if get(brief, "stack_profile", default="generic") != "none":
        for it in profile["items"]:
            if it["key"] in skip:
                continue
            it = json.loads(json.dumps(it))
            it.update((get(brief, "foundation_override", it["key"], default={}) or {}))
            it["epic"] = "E0 Foundation"
            it["priority"] = "Must"
            it["description"] = it["description"].replace("{skeleton}", skeleton)
            it["depends_on"] = [d for d in it["depends_on"] if d not in skip]
            if "{skeleton}" in it["title"]:
                it["title"] = it["title"].replace("{skeleton}", skeleton)
            items.append(it)
    for it in lst(get(brief, "backlog", default=[])):
        it = dict(it)
        it.setdefault("type", "Story")
        it.setdefault("priority", "Must")
        it.setdefault("status", "Backlog")
        it["depends_on"] = [d for d in lst(it.get("depends_on")) if d not in skip]
        items.append(it)
    if not items:
        fail("backlog is empty: add items to brief.backlog")
        return []
    keys = [i.get("key") for i in items]
    for i, k in enumerate(keys):
        if not k:
            fail(f"backlog item {i + 1} ({items[i].get('title')!r}) has no key")
    if len(set(keys)) != len(keys):
        fail("duplicate backlog keys")
    # stable topological sort: keep given order, but never place an item before its dependencies
    by_key = {i["key"]: i for i in items if i.get("key")}
    for it in items:
        for d in it["depends_on"]:
            if d not in by_key:
                fail(f"backlog item {it.get('key')!r} depends on unknown key {d!r}")
    ordered, placed, pending = [], set(), list(items)
    moved = []
    while pending:
        progressed = False
        for it in list(pending):
            if all(d in placed or d not in by_key for d in it["depends_on"]):
                ordered.append(it)
                placed.add(it["key"])
                pending.remove(it)
                progressed = True
                break
        if not progressed:
            fail("dependency cycle among: " + ", ".join(i["key"] for i in pending))
            return []
    if [i["key"] for i in ordered] != [i["key"] for i in items]:
        moved = [i["key"] for i in ordered if items.index(i) != ordered.index(i)]
    for n, it in enumerate(ordered, 1):
        it["id"] = f"BL-{n:03d}"
        ids.add("bl", it["key"], it["id"])
    return ordered, moved


def render_backlog(items, ids):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADER)
    for it in items:
        ac = " | ".join(ids.resolve(a) for a in lst(it.get("ac")))
        deps = ";".join(ids.maps["bl"].get(d, d) for d in it["depends_on"])
        w.writerow([it["id"], it.get("epic", "E1 MVP"), ids.resolve(it.get("title", "")),
                    ids.resolve(it.get("description", "")), it["type"], it["priority"], it["status"],
                    it.get("estimate", ""), ac, deps])
    return buf.getvalue()


# ---------------------------------------------------------------- documents
def render_bugs(name):
    return f"""# Bugs and fixes - {name}

How to use: before debugging, search this file for the symptom or error message. After fixing a non-trivial bug, add an entry at the top of the Log using the template. Trivial typos do not need an entry. Statuses: Open, Fixed, Won't fix.

## Template

### BUG-000 - Short title
- **Date**: YYYY-MM-DD
- **Status**: Open | Fixed | Won't fix
- **Severity**: Critical | High | Medium | Low
- **Symptom**: what was observed, with the exact error message if any
- **Root cause**: why it happened
- **Fix**: what changed; commit or PR reference
- **Regression test**: test name, or "none" with the reason
- **Prevention**: how to avoid this class of bug

## Log

<!-- Newest first. No bugs logged yet. -->
"""


def render_decisions(brief, ids, devops_ctx):
    today = date.today().isoformat()
    out = ["# Technical decisions", "",
           "How to use: before making an architectural or tooling choice, scan this file. Add an entry for any decision that is hard to reverse or that a future reader would ask \"why?\" about. Number entries sequentially. Statuses: Proposed (suggested by Claude, not yet confirmed by the owner), Accepted (stated or confirmed by the owner), Superseded by DEC-N, Rejected. Never delete an entry; supersede it.", ""]
    for d in devops_ctx["decisions"]:
        out += [f"## {d['id']} - {ids.resolve(d['title'])}",
                f"- **Date**: {d.get('date', today)}",
                f"- **Status**: {d.get('status', 'Proposed')}",
                f"- **Context**: {ids.resolve(d.get('context', 'TBD'))}"]
        if d.get("options"):
            out.append("- **Options considered**: " + "; ".join(ids.resolve(o) for o in lst(d["options"])))
        out += [f"- **Decision**: {ids.resolve(d.get('decision', 'TBD'))}",
                f"- **Consequences**: {ids.resolve(d.get('consequences', 'TBD'))}", ""]
    return "\n".join(out)


def devops_defaults(brief, profile):
    dv = brief.get("devops", {}) or {}
    team = dv.get("team", "solo")
    ctx = {}
    ctx["host"] = dv.get("git_host", "GitHub")
    ctx["repo"] = dv.get("repo", "TBD")
    ctx["branching"] = dv.get("branching") or (
        "Trunk-based: `main` is always releasable. Small changes may be committed straight to `main`; larger work goes on short-lived branches (`feat/...`, `fix/...`, `chore/...`) merged back quickly."
        if team == "solo" else
        "Trunk-based with short-lived branches (`feat/...`, `fix/...`, `chore/...`) merged into `main` through pull requests; no direct commits to `main`.")
    ctx["pr"] = dv.get("pull_requests") or (
        "Optional while solo; use them for anything risky. Put the backlog ID in the title." if team == "solo"
        else "Required for every change; at least one review; put the backlog ID in the title.")
    ctx["envs"] = dv.get("environments") or [
        {"name": "local", "purpose": "Development", "where": "Developer machine", "deploy": "n/a", "status": "Live"},
        {"name": "production", "purpose": "Real use", "where": "TBD", "deploy": "Manual until CI/CD exists", "status": "Planned"}]
    ctx["ci_on_pr"] = lst(dv.get("ci_on_pr")) or profile["ci_checks"]
    ctx["ci_on_main"] = lst(dv.get("ci_on_main")) or ["Re-run the same checks; no automatic deploy until an environment exists"]
    ctx["ci_status"] = "Live" if dv.get("ci_live") else "Planned"
    ctx["cadence"] = dv.get("release_cadence", "On demand, when a meaningful set of backlog items is done")
    ctx["start_version"] = dv.get("version", "0.1.0")
    ctx["version_file"] = dv.get("version_file", profile["version_file"])
    ctx["secrets"] = dv.get("secrets", "Configuration comes from environment variables. A local `.env` file is gitignored; `.env.example` documents every variable. Secrets are never committed or logged.")
    ctx["rollback"] = dv.get("rollback", "Redeploy the previous tagged release. If data is changed by a release, take a backup first. TBD: project-specific data restore steps.")
    ctx["monitoring"] = dv.get("monitoring", "Planned: structured logs and an alert on failure of the main job or endpoint.")
    ctx["team"] = team
    return ctx


def render_devops(brief, profile, ctx, cmds):
    dv = brief.get("devops", {}) or {}
    envs = "\n".join(f"| {e['name']} | {e.get('purpose', '')} | {e.get('where', '')} | {e.get('deploy', '')} | {e.get('status', 'Planned')} |" for e in ctx["envs"])
    dod = lst(dv.get("definition_of_done")) or (
        [f"`{c}` passes" for c in (cmds.get("test"), cmds.get("lint"), cmds.get("typecheck")) if c] +
        ["Acceptance criteria of the backlog item are met", "Relevant docs updated (PROJECT.md, DECISIONS.md, BUG_AND_FIXES.md)",
         "BACKLOG.csv status updated"])
    release = lst(dv.get("release_steps")) or [
        "Make sure `main` is green and BACKLOG.csv reflects what is released.",
        "Update CHANGELOG.md (Keep a Changelog format) and bump the version in " + ctx["version_file"] + ".",
        "Tag the commit `vX.Y.Z` on `main` and push the tag.",
        "Deploy to production following the environment table; verify with a smoke check.",
    ]
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(release, 1))
    return f"""# DevOps: delivery cycle and versioning - {brief['project']['name']}

## Environments
| Environment | Purpose | Where | Deploy trigger | Status |
|---|---|---|---|---|
{envs}

## Source control
- Host: {ctx['host']}; repository: {ctx['repo']}
- Branching: {ctx['branching']}
- Pull requests: {ctx['pr']}

## Commit conventions
- Conventional Commits: `type(scope): summary` with types `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`.
- Reference the backlog ID in the footer, e.g. `Refs: BL-001`.

## Versioning
- Semantic Versioning `MAJOR.MINOR.PATCH`; start at `{ctx['start_version']}`. Before 1.0 a minor bump may break behaviour.
- The version lives in {ctx['version_file']}; releases are tagged `vX.Y.Z` on `main`.

## Release process
{steps}
- Cadence: {ctx['cadence']}.

## CI/CD ({ctx['ci_status']})
- On every pull request: {', '.join(ctx['ci_on_pr'])}.
- On merge to main: {'; '.join(ctx['ci_on_main'])}.

## Configuration and secrets
- {ctx['secrets']}

## Rollback and recovery
- {ctx['rollback']}

## Monitoring and operations
- {ctx['monitoring']}

## Definition of done
{bullets(dod)}
"""


def render_claude(brief, profile, ids, cmds, mode):
    p = brief["project"]
    c = brief.get("claude", {}) or {}
    stack = [f"{r['layer']}: {r['choice']}" for r in lst(brief.get("stack"))]
    layout = lst(c.get("layout"))
    cmd_lines = []
    after_map = profile.get("commands_after", {})
    defaults = profile.get("default_commands", {})
    for label, key in (("Install", "install"), ("Run", "run"), ("Test", "test"), ("Lint", "lint"), ("Type-check", "typecheck"), ("Build", "build")):
        v = cmds.get(key)
        if v:
            suffix = ""
            after = after_map.get(key, after_map.get("default"))
            if mode == "new" and v == defaults.get(key) and after and after in ids.maps["bl"]:
                suffix = f" (after {ids.maps['bl'][after]})"
            cmd_lines.append(f"- {label}: `{v}`{suffix}")
    rules = ["Make small, reviewable changes; one backlog item at a time.",
             "Ask before adding a dependency, changing the architecture" + (", or touching " + ", ".join(lst(c.get("ask_before"))) if c.get("ask_before") else "") + ".",
             "Never commit secrets; configuration comes from environment variables (see DEV_OPS.md).",
             "Definition of done is in DEV_OPS.md; follow its commit and release rules."] + lst(c.get("working_rules"))
    out = [f"# {p['name']}", "", p["one_liner"], "",
           "## Project files (read these, keep them current)",
           "- `PROJECT.md` - the spec. Read before starting a feature; update it when scope or requirements change.",
           "- `BACKLOG.csv` - ordered work items. Take the top `Ready` item unless told otherwise and update its Status as you go.",
           "- `DECISIONS.md` - technical decisions. Check before an architectural choice; append an entry for any non-trivial one; supersede, never rewrite.",
           "- `BUG_AND_FIXES.md` - bug log. Search it before debugging; add an entry after fixing a non-trivial bug.",
           "- `DEV_OPS.md` - branching, commits, versioning, release. Follow it for every commit and release.", ""]
    if stack or layout:
        out += ["## Stack and layout", bullets(stack + layout), ""]
    if cmd_lines:
        out += ["## Commands", "\n".join(cmd_lines), ""]
    elif mode == "new":
        out += ["## Commands", "- TBD: add install/run/test/lint commands once the tooling exists.", ""]
    if c.get("conventions"):
        out += ["## Conventions", bullets(lst(c["conventions"])), ""]
    out += ["## Working rules", bullets(rules), ""]
    if c.get("do_not"):
        out += ["## Do not", bullets(lst(c["do_not"])), ""]
    for s in lst(get(brief, "extra_sections", "CLAUDE.md", default=[])):
        out += [f"## {s['heading']}", s["body"], ""]
    return ids.resolve("\n".join(out))


def render_project(brief, ids):
    p = brief["project"]
    out = [f"# {p['name']} - Project specification", "", "## Summary", brief["summary"], ""]
    if brief.get("goals"):
        out += ["## Goals and success metrics",
                bullets(lst(brief["goals"]), lambda g: f"{g['goal']} - measured by {g['metric']}" if isinstance(g, dict) else g),
                f"- Product goal the backlog serves: {brief['product_goal']}", ""]
    else:
        out += ["## Goals and success metrics", f"- Product goal the backlog serves: {brief['product_goal']}", ""]
    if brief.get("users"):
        out += ["## Users and use cases", bullets(lst(brief["users"]), lambda u: f"{u['who']}: {u['needs']}" if isinstance(u, dict) else u), ""]
    sc = brief.get("scope", {})
    out += ["## Scope",
            "- **In scope (MVP)**: " + "; ".join(lst(sc.get("mvp"))) if sc.get("mvp") else "- **In scope (MVP)**: TBD",
            "- **Later**: " + "; ".join(lst(sc.get("later"))) if sc.get("later") else "- **Later**: none yet",
            "- **Out of scope**: " + "; ".join(lst(sc.get("out"))) if sc.get("out") else "- **Out of scope**: TBD", ""]
    req = brief.get("requirements", {})
    fr = lst(req.get("functional"))
    if not fr:
        fail("requirements.functional is empty")
    out += ["## Functional requirements"]
    for n, r in enumerate(fr, 1):
        r = {"text": r} if isinstance(r, str) else r
        later = " (Later)" if r.get("phase") == "later" else ""
        out.append(f"- FR-{n}{later}: {r['text']}")
    out.append("")
    nfr = lst(req.get("non_functional"))
    if nfr:
        out += ["## Non-functional requirements"]
        for n, r in enumerate(nfr, 1):
            r = {"text": r} if isinstance(r, str) else r
            cat = f" ({r['category']})" if r.get("category") else ""
            out.append(f"- NFR-{n}{cat}: {r['text']}")
        out.append("")
    if brief.get("architecture"):
        out += ["## Architecture overview", brief["architecture"], ""]
    if brief.get("stack"):
        out += ["## Tech stack", "| Layer | Choice | Notes |", "|---|---|---|"]
        out += [f"| {r['layer']} | {r['choice']} | {r.get('notes', '')} |" for r in brief["stack"]]
        out.append("")
    if brief.get("data_and_integrations"):
        out += ["## Data model and integrations", brief["data_and_integrations"], ""]
    cons, risks = lst(brief.get("constraints")), lst(brief.get("risks"))
    if cons or risks:
        out += ["## Constraints and risks"]
        if cons:
            out.append("- Constraints: " + "; ".join(cons))
        out += [f"- Risk: {r['risk']} - mitigation: {r.get('mitigation', 'TBD')}" if isinstance(r, dict) else f"- Risk: {r}" for r in risks]
        out.append("")
    out += ["## Open questions and assumptions"]
    for a in lst(brief.get("assumptions")):
        a = {"kind": "ASSUMED", "text": a} if isinstance(a, str) else a
        conf = f" (confirm with {a['confirm_with']})" if a.get("confirm_with") else ""
        out.append(f"- {a.get('kind', 'ASSUMED')}: {a['text']}{conf}")
    if not lst(brief.get("assumptions")):
        out.append("- None recorded.")
    out.append("")
    if brief.get("glossary"):
        out += ["## Glossary", bullets(lst(brief["glossary"]), lambda g: f"{g['term']}: {g['definition']}")]
        out.append("")
    for s in lst(get(brief, "extra_sections", "PROJECT.md", default=[])):
        out += [f"## {s['heading']}", s["body"], ""]
    return ids.resolve("\n".join(out))


# ---------------------------------------------------------------- main
def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        return 2
    brief_path, target = Path(args[0]), Path(args[1])
    try:
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: cannot read brief: {e}")
        return 2
    for need in ("project", "summary", "product_goal"):
        if need not in brief:
            fail(f"brief is missing {need!r}")
    if "project" in brief:
        for need in ("name", "one_liner"):
            if need not in brief["project"]:
                fail(f"brief.project is missing {need!r}")
    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1

    mode = brief["project"].get("mode", "new")
    prof_name = brief.get("stack_profile", "generic")
    prof_path = ASSETS / (("generic" if prof_name == "none" else prof_name) + ".json")
    if not prof_path.exists():
        print(f"ERROR: unknown stack_profile {prof_name!r}; use python, node-ts, generic or none")
        return 1
    profile = json.loads(prof_path.read_text(encoding="utf-8"))
    ids = Ids()

    # functional / non-functional keys
    req = brief.get("requirements", {})
    for n, r in enumerate(lst(req.get("functional")), 1):
        if isinstance(r, dict):
            ids.add("fr", r.get("key"), f"FR-{n}")
    for n, r in enumerate(lst(req.get("non_functional")), 1):
        if isinstance(r, dict):
            ids.add("nfr", r.get("key"), f"NFR-{n}")

    # decisions (+ automatic delivery-defaults decision)
    ctx = devops_defaults(brief, profile)
    decisions = [dict(d) for d in lst(brief.get("decisions"))]
    dv = brief.get("devops", {}) or {}
    if dv.get("use_defaults", True):
        decisions.append({
            "key": "delivery-defaults", "title": "Delivery workflow defaults (branching, commits, versioning, CI)",
            "status": "Accepted" if dv.get("defaults_confirmed") else "Proposed",
            "context": "No preference was stated for the delivery cycle, so simple, widely used defaults were chosen.",
            "options": ["Trunk-based vs long-lived branches", "Conventional Commits vs free-form messages", "SemVer vs date-based versions"],
            "decision": "Trunk-based development, Conventional Commits, Semantic Versioning with `vX.Y.Z` tags, CI on every pull request. Details in DEV_OPS.md.",
            "consequences": "Keeps releases simple for " + ("a solo developer" if ctx["team"] == "solo" else "a small team") + ". Revisit when the team grows or a staging environment is added."})
    for n, d in enumerate(decisions, 1):
        d["id"] = f"DEC-{n:03d}"
        ids.add("dec", d.get("key"), d["id"])
        if not d.get("title"):
            fail(f"decision {n} has no title")

    res = build_backlog(brief, profile, ids)
    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1
    items, moved = res

    cmds = dict(profile.get("default_commands", {}))
    cmds.update({k: v for k, v in (get(brief, "claude", "commands", default={}) or {}).items() if v})

    tmp = Path(tempfile.mkdtemp(prefix="pb-render-"))
    try:
        (tmp / "BACKLOG.csv").write_text(render_backlog(items, ids), encoding="utf-8")
        (tmp / "PROJECT.md").write_text(render_project(brief, ids), encoding="utf-8")
        (tmp / "CLAUDE.md").write_text(render_claude(brief, profile, ids, cmds, mode), encoding="utf-8")
        (tmp / "DECISIONS.md").write_text(render_decisions(brief, ids, {"decisions": decisions}), encoding="utf-8")
        (tmp / "DEV_OPS.md").write_text(ids.resolve(render_devops(brief, profile, ctx, cmds)), encoding="utf-8")
        (tmp / "BUG_AND_FIXES.md").write_text(render_bugs(brief["project"]["name"]), encoding="utf-8")
        if errors:
            print("\n".join("ERROR: " + e for e in errors))
            return 1

        v = subprocess.run([sys.executable, str(HERE / "validate_project_files.py"), str(tmp), "--digest"],
                           capture_output=True, text=True)
        verdict = v.stdout.strip()
        if v.returncode != 0:
            print(verdict)
            print("nothing written: fix the brief and rerun")
            return 1

        force = "--force" in sys.argv
        target.mkdir(parents=True, exist_ok=True)
        written, proposed = [], []
        for name in FILES:
            dest = target / name
            if dest.exists() and not force:
                dest = target / (name + ".proposed")
                proposed.append(name)
            shutil.copyfile(tmp / name, dest)
            written.append(dest.name)
        print(verdict)
        if moved:
            print("note: reordered to respect dependencies: " + ", ".join(moved))
        if proposed:
            print("note: existing files kept; wrote .proposed next to: " + ", ".join(proposed))
        if "--map" in sys.argv:
            print("ids: " + ", ".join(f"{k}={v}" for k, v in ids.maps["bl"].items()))
        return v.returncode
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
