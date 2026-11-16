---
name: project-bootstrap
description: Bootstrap the project file set for starting a project with Claude Code, or for taking over an existing repo - CLAUDE.md, PROJECT.md, BUG_AND_FIXES.md, DECISIONS.md, DEV_OPS.md and BACKLOG.csv - by reading the user's context, asking only the questions that are still missing, and generating all six files with bundled scripts. Use this skill whenever the user wants to start, kick off, scaffold, bootstrap or set up a new project (or add project docs to an existing repo) for Claude Code, mentions CLAUDE.md, PROJECT.md, a project backlog, a decisions log or a project spec, or describes an app/tool/product idea and wants to get it ready for building with Claude Code, even if they never name the files.
---

# Project Bootstrap

Produce the six files that let Claude Code start a project well and keep it coherent across sessions. The user decides *what* to build; this skill turns a rough description into a complete, consistent file set, asking questions only where the answer would change the files.

| File | Role |
|---|---|
| `CLAUDE.md` | Instructions for Claude Code: commands, conventions, working rules, pointers to the other files. |
| `PROJECT.md` | The spec: vision, users, scope, requirements, architecture, stack, constraints, open questions. |
| `BUG_AND_FIXES.md` | Running bug log so the same bug is not investigated twice. |
| `DECISIONS.md` | Technical decision log so past choices are not silently reversed. |
| `DEV_OPS.md` | Delivery cycle: branching, commits, versioning, CI/CD, environments, release, rollback. |
| `BACKLOG.csv` | Ordered work items toward the product goal; row order is priority order. |

The work is split on purpose. **You supply the judgment** (what the project is, requirements, decisions and their reasons, backlog stories, assumptions). **Scripts supply the boilerplate and the bookkeeping** (skeletons, how-to text, DEV_OPS defaults, the Foundation epic, ID numbering, CSV quoting, dependency order, validation). Reading and re-typing boilerplate costs tokens and invites inconsistencies, so do not do by hand what a script here already does.

## Workflow

### 1. Detect the situation

- **Target directory**: the project root the user names, otherwise the current working directory. In claude.ai without a project folder, write to the working directory and deliver the files at the end.
- **Greenfield or existing repo?** If the directory has source code, a manifest, a README or git history, it is an existing repo; otherwise greenfield.
- **Existing repo**: run the scanner once instead of exploring file by file:
  ```bash
  python3 <skill-path>/scripts/scan_repo.py <repo-dir>
  ```
  It prints one compact JSON object: languages, frameworks, dependencies, real commands (from manifests, Makefile, CI), CI summary, git state, TODO/FIXME with file and line, a shallow tree, and `hints` (suggested stack profile and Foundation items to skip). Treat what it reports as facts to record, not questions to ask. Open an individual file only when the scan leaves a real gap.

### 2. Ask about the gaps (adaptive rounds)

Check what you know against the checklist in `references/interview-guide.md` (read it only when you actually need to ask or propose defaults). Ask in at most two rounds of 3-4 questions, only about gaps that would change the files, using `AskUserQuestion` when available with a recommended default first; otherwise put the same 3-4 questions in one plain-text message, recommended option marked, and wait for the answer. Ask in the user's language. If the first message already covers purpose, MVP, platform, stack and team, skip asking and list your assumptions at the end. If it is a one-line idea, ask before writing anything. Whatever stays unknown becomes an explicit assumption, never a third round.

### 3. Write the brief

Read `references/brief-schema.md`, then write one `brief.json` in a scratch location (not the project folder) containing only project-specific content. Rules that matter:

- **Never invent facts about the user's business or constraints.** A confident but wrong spec misleads Claude Code in every later session. Unknowns go in `assumptions` as `ASSUMED` or `TBD`.
- **Label proposals.** What the user stated or confirmed is `Accepted`; what you suggested is `Proposed`. Seed `decisions` with the choices already made so the log is useful from day one.
- **Use keys and `{fr:key}` / `{bl:key}` references**, never hand-typed IDs; the script numbers and cross-links everything.
- **Backlog**: after the Foundation epic (generated for you from the stack profile), add roughly 10-25 well-formed MVP items ordered by value, each with acceptance criteria, plus `Spike` items for open questions that block a feature. For an existing repo, turn the scan's TODOs into items citing file and line.
- Write in English regardless of the interview language.

### 4. Render and validate

```bash
python3 <skill-path>/scripts/render_project_files.py brief.json <target-dir>
```

The script writes all six files and runs the validator (all files present, no leftover placeholders, valid backlog columns and values, unique IDs, dependencies that exist and come earlier, every `FR-`/`NFR-`/`DEC-`/`BL-` reference defined). If it reports errors, nothing is written: fix the brief and rerun. Existing files are never overwritten; the new versions are written as `<name>.proposed` (tell the user, and offer to merge). Use `--force` only when the user asks to replace them.

Do not re-read the generated files to check them; the validator already did, and the boilerplate is the same every time. Spend that effort on the quality of the brief instead. Open a file only to fix something the script reported.

### 5. Deliver

- Say where the files are. In claude.ai, send each file to the user.
- Close with a short summary built from the script's digest line: the project in one sentence, the assumptions made, the open questions, any risk worth deciding early, and the first `Ready` backlog item. No recap of the steps.
- Natural next step: start Claude Code in the folder and take the first `Ready` item.

## Fallback

If `python3` is unavailable or the user needs a layout the script cannot produce, write the files by hand following `references/file-specs.md` (structure and quality bar for each file), keep the same ID and cross-reference discipline, and run `scripts/validate_project_files.py <dir> --digest` if Python exists.

## Edge cases

- **Only some files wanted**: render all, then deliver only those; cross-references stay valid.
- **Monorepo or several apps**: one root set of files; add per-app sections through `extra_sections`.
- **Non-software projects**: pick `stack_profile: "generic"` or `"none"` and give your own equivalent commands and Foundation items in the backlog.
- **User changes their mind later**: regenerate only if the files are still untouched; otherwise edit the affected file directly and supersede (never delete) old decisions.
