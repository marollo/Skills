# File specs (manual fallback)

The scripts render these files from a brief (see `brief-schema.md`); read this file only when writing them by hand.

Contents: 1 CLAUDE.md · 2 PROJECT.md · 3 BUG_AND_FIXES.md · 4 DECISIONS.md · 5 DEV_OPS.md · 6 BACKLOG.csv

Each section gives the purpose, the quality bar, and a skeleton. Replace every `<...>` with real content; if the content is unknown, write `TBD` and add it to the open questions in PROJECT.md. Delete skeleton sections that genuinely do not apply rather than leaving them empty.

---

## 1. CLAUDE.md

**Purpose**: the operating manual Claude Code loads at the start of every session.
**Quality bar**: under ~120 lines. Concrete and verifiable ("run `npm test` before committing", not "write good tests"). No long specs: point to PROJECT.md. Every command must be a real command for this stack; for a greenfield project whose tooling does not exist yet, write the command that *will* exist after the first foundation backlog item and mark it `(after BL-001)`.

```markdown
# <Project name>

<One sentence: what this is and who it is for.>

## Project files (read these, keep them current)
- `PROJECT.md` - the spec. Read before starting any feature; update when scope or requirements change.
- `BACKLOG.csv` - ordered work items. Work the top `Ready` item unless told otherwise; update its Status as you go.
- `DECISIONS.md` - technical decisions. Check before making an architectural choice; append a new entry for any non-trivial one. Never rewrite history: supersede.
- `BUG_AND_FIXES.md` - bug log. Search it before debugging; add an entry when a non-trivial bug is fixed.
- `DEV_OPS.md` - branching, commits, versioning, release. Follow it for every commit and release.

## Stack and layout
- <language/framework/runtime and versions>
- <key directories and what lives in each>

## Commands
- Install: `<cmd>`
- Run: `<cmd>`
- Test: `<cmd>`
- Lint/format: `<cmd>`
- Build: `<cmd>`

## Conventions
- <naming, structure, error handling, typing, logging - only rules that are specific to this project>
- <testing expectations>

## Working rules
- Make small, reviewable changes; one backlog item per branch/PR.
- Ask before adding a dependency, changing the architecture, or touching <sensitive area>.
- Never commit secrets; configuration comes from <env vars / secret manager>.
- Definition of done: <tests pass, lint clean, docs/decisions updated, backlog status updated>.

## Do not
- <project-specific prohibitions, e.g. "do not edit generated files in /gen">
```

---

## 2. PROJECT.md

**Purpose**: the single source of truth for what is being built and why.
**Quality bar**: requirements are individually testable and have stable IDs (`FR-1`, `NFR-1`) so backlog items can cite them. Scope states what is *out* as clearly as what is in. Facts the user gave are stated plainly; unknowns live only in section 11.

```markdown
# <Project name> - Project specification

## 1. Summary
<2-4 sentences: problem, solution, who benefits.>

## 2. Goals and success metrics
- <Goal> - measured by <metric / target>
- Product goal the backlog serves: <one sentence>

## 3. Users and use cases
- <Persona/role>: <what they need and the main scenarios>

## 4. Scope
- **In scope (MVP)**: <list>
- **Later**: <list>
- **Out of scope**: <list>

## 5. Functional requirements
- FR-1: <testable statement>
- FR-2: ...

## 6. Non-functional requirements
- NFR-1 (performance/security/privacy/accessibility/availability/compliance): <testable statement>

## 7. Architecture overview
<Components and how they interact in a short paragraph or list; optionally a simple text diagram. Reference DECISIONS.md IDs for the reasons behind choices.>

## 8. Tech stack
| Layer | Choice | Notes |
|---|---|---|

## 9. Data model and integrations
<Key entities and relationships; external APIs, services, and data sources.>

## 10. Constraints and risks
- Constraints: <budget, deadline, team, regulation, platform limits>
- Risks: <risk> - <mitigation>

## 11. Open questions and assumptions
- ASSUMED: <assumption made to proceed> (confirm with <who>)
- TBD: <question that still needs an answer>

## 12. Glossary
- <Term>: <definition>
```

---

## 3. BUG_AND_FIXES.md

**Purpose**: institutional memory of bugs so Claude Code does not re-derive the same fixes.
**Quality bar**: starts with the usage rules and one entry template; no fake example bugs. Newest entries on top.

```markdown
# Bugs and fixes

How to use: before debugging, search this file for the symptom or error message. After fixing a non-trivial bug, add an entry at the top using the template. Trivial typos do not need an entry. Statuses: Open, Fixed, Won't fix.

## Template

### BUG-000 - <short title>
- **Date**: YYYY-MM-DD
- **Status**: Open | Fixed | Won't fix
- **Severity**: Critical | High | Medium | Low
- **Symptom**: <what was observed, with the exact error message if any>
- **Root cause**: <why it happened>
- **Fix**: <what changed; commit/PR reference>
- **Regression test**: <test name or "none - reason">
- **Prevention**: <how to avoid this class of bug>

## Log

<!-- Newest first. No bugs logged yet. -->
```

---

## 4. DECISIONS.md

**Purpose**: a lightweight decision record so past choices (and their reasons) survive between sessions.
**Quality bar**: seeded with the real decisions from the interview (stack, hosting, workflow, repo layout). Each has context, options considered, the decision, and consequences. Statuses: `Proposed` (suggested by Claude, not confirmed), `Accepted` (stated or confirmed by the user), `Superseded by DEC-N`, `Rejected`. Never delete an entry; supersede it.

```markdown
# Technical decisions

How to use: before making an architectural or tooling choice, scan this file. Add an entry for any decision that is hard to reverse or that a future reader would ask "why?" about. Number entries sequentially.

## DEC-001 - <decision title>
- **Date**: YYYY-MM-DD
- **Status**: Accepted | Proposed | Superseded by DEC-N | Rejected
- **Context**: <the problem and the constraints>
- **Options considered**: <A - pros/cons; B - pros/cons>
- **Decision**: <what was chosen>
- **Consequences**: <what this makes easier or harder; follow-ups>
```

---

## 5. DEV_OPS.md

**Purpose**: everything about the delivery cycle and versioning, so releases are boring.
**Quality bar**: sized to the project. A solo prototype gets a short file with sensible defaults; a team product gets more. Defaults when the user has no preference: trunk-based development with short-lived branches, Conventional Commits, SemVer, CHANGELOG generated from commits, CI running lint + tests on every PR. Record each default you assume as a `Proposed` decision in DECISIONS.md. Never describe pipelines or environments that do not exist as if they did: mark them `Planned`.

```markdown
# DevOps: delivery cycle and versioning

## 1. Environments
| Environment | Purpose | Where | Deploy trigger | Status (Live/Planned) |
|---|---|---|---|---|

## 2. Source control
- Host/repo: <e.g. GitHub org/repo>
- Branching: <trunk-based with short-lived `feat/…`, `fix/…`, `chore/…` branches off `main`>
- `main` is always releasable; protected: <rules>
- Pull requests: <required? reviewers? size guidance; link the backlog ID in the title>

## 3. Commit conventions
- Format: Conventional Commits - `type(scope): summary` (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `perf`)
- Reference the backlog ID in the body or footer, e.g. `Refs: BL-001`.

## 4. Versioning
- Scheme: Semantic Versioning `MAJOR.MINOR.PATCH` (<what counts as breaking for this project>)
- Version lives in: <file/tag>; tags are `vX.Y.Z` on `main`.
- Pre-1.0 policy: <e.g. minor bumps may break>

## 5. Release process
1. <Steps from "main is green" to "tagged and deployed", including changelog update>
2. Changelog: <CHANGELOG.md, generated or hand-written>
- Release cadence: <on demand / weekly / per milestone>

## 6. CI/CD
- On every PR: <lint, type-check, tests, build>
- On merge to main: <deploy to ...>
- Required checks before merge: <list>

## 7. Configuration and secrets
- Config via <env vars / .env (gitignored) / secret manager>; never commit secrets. Document variables in <.env.example>.

## 8. Rollback and recovery
- <How to roll back a bad release; data backup/restore if relevant>

## 9. Monitoring and operations
- <Logging, error tracking, alerts, who is on point> (or `Planned`)

## 10. Definition of done
- <Checklist that applies to every backlog item>
```

---

## 6. BACKLOG.csv

**Purpose**: the ordered list of work that gets the product to its goal.
**Row order = priority order** (highest value / earliest first, respecting dependencies). Use exactly this header, in this order:

```
ID,Epic,Title,Description,Type,Priority,Status,Estimate,Acceptance Criteria,Depends On
```

| Column | Rules |
|---|---|
| ID | `BL-001`, `BL-002`, ... unique, never reused or renumbered. |
| Epic | Short epic name, e.g. `E0 Foundation`, `E1 Onboarding`. Reuse identical names so items group. |
| Title | Short, imperative or story title. |
| Description | User stories as "As a <role>, I want <goal>, so that <benefit>." Tasks/chores as a plain sentence. Cite requirement IDs (`FR-3`) where relevant. |
| Type | `Story`, `Task`, `Bug`, `Spike`, `Chore`. |
| Priority | MoSCoW: `Must`, `Should`, `Could`, `Won't`. |
| Status | `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`, `Blocked`. Start with the first foundation items as `Ready`, everything else `Backlog`. |
| Estimate | Story points from `1 2 3 5 8`, or empty if not estimated. Anything that feels like 13+ should be split. |
| Acceptance Criteria | Testable conditions separated by ` | `. Required for every item expected to start soon. |
| Depends On | Backlog IDs separated by `;`. Each must exist and appear earlier in the file. Empty if none. |

Seeding approach:
1. `E0 Foundation` first: repo and tooling set-up, CI, the walking skeleton (thinnest end-to-end slice), config/secrets handling. These make the later items executable.
2. Then MVP epics derived from PROJECT.md scope and FR IDs, ordered by value and dependencies, 3-8 items per epic.
3. A short tail of `Could`/later items so the next planning round has something to pull from.
4. Include `Spike` items for open questions in PROJECT.md that block a feature.

Quote any field containing a comma or a double quote (standard CSV). Keep each row on one line (no embedded newlines).
