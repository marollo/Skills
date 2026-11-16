# Interview guide

The goal is a complete picture with the fewest questions. Every question must pass this test: *would a different answer change what I write in one of the six files?* If not, do not ask it.

Contents: Information checklist · Rounds · Phrasing · Defaults to propose · Handling "I don't know"

## Information checklist

Mark each item as **known** (from the user's message, attachments or the repo scan), **inferable** (a sensible default exists), or **gap**. Only gaps in the *Essential* tier justify asking; the others should usually be defaulted and recorded as assumptions.

**Essential** (ask if a gap)
1. What is being built, for whom, and what problem it solves (feeds PROJECT.md §1-3).
2. What "done for the first version" means: MVP boundary and the one product goal the backlog serves (§2, §4, backlog ordering).
3. Platform / kind of product: web app, mobile, CLI, bot, API, library, data pipeline, hardware, content (drives stack, commands, DEV_OPS).
4. Tech stack: chosen already, or should it be proposed? Hard constraints (language, cloud, existing systems).
5. Who works on it: solo, small team, with reviewers (drives branching, PR rules, DEV_OPS depth).

**Important** (ask in round 2 if still unknown and it matters; otherwise default)
6. Hosting and environments: where it runs, staging or not.
7. Git host and CI preference.
8. Release style: continuous, scheduled, manual; any versioning expectations.
9. Non-functional needs: privacy/GDPR, security, performance, accessibility, offline, languages/locales.
10. External services and data sources to integrate.
11. Deadline or budget limits.

**Nice to have** (default silently, record only if it shaped a choice)
12. Testing depth and tools, code style tools, naming conventions.
13. Monitoring and alerting.
14. Names of directories, branch names, ID formats.

For an existing repo, items 3, 4, 6, 7, 8, 12 are usually *known* after the scan. Ask the user to confirm only the things that look inconsistent (e.g. two test frameworks, no CI but a deploy script).

## Rounds

- **Round 1** (3-4 questions): the gaps from the Essential tier. Bundle them in one `AskUserQuestion` call when possible.
- **Round 2** (3-4 questions, only if needed): the gaps from the Important tier that would change DEV_OPS.md or the NFRs, plus any contradiction found in round 1 answers.
- Never a third round. Remaining unknowns become `ASSUMED:` / `TBD:` lines in PROJECT.md §11.

If the user's message already covers the Essential tier, skip asking and go write; list the assumptions in the closing summary.

## Phrasing

- Offer 2-4 concrete options with your recommended default first, labeled "(Recommended)", and a one-line consequence for each. The user can always type something else.
- Name things plainly. The user may be a product owner rather than an engineer: explain jargon in half a sentence ("trunk-based = everyone merges small changes to one main branch").
- Open-ended questions (what/why/who) are better asked as plain text than as forced multiple choice. Use plain text when the answer is a description, and the choice tool when the answer is a pick.
- Ask in the language the user writes in; the files themselves are English.

Examples:
- Weak: "What stack do you want?" Strong: "Which stack should I plan for? (a) Python + FastAPI + Postgres (Recommended: fits your bot/API focus), (b) TypeScript + Next.js, (c) I already have one - I'll tell you."
- Weak: "Do you want CI?" Strong: "How should code be checked before it ships? (a) GitHub Actions running lint + tests on every PR (Recommended), (b) manual checks for now, (c) other."

## Defaults to propose

Use these when the user has no preference, and record each as a `Proposed` entry in DECISIONS.md.

| Area | Default |
|---|---|
| Branching | Trunk-based: short-lived `feat/…`, `fix/…`, `chore/…` branches into `main`; solo projects may commit small changes straight to `main`. |
| Commits | Conventional Commits, with the backlog ID in the footer. |
| Versioning | SemVer, tags `vX.Y.Z`, start at `0.1.0`; pre-1.0 minor bumps may break. |
| Changelog | `CHANGELOG.md`, Keep a Changelog format, updated at release. |
| CI | Lint + type-check + tests on every PR; deploy on merge to `main` only once an environment exists. |
| Environments | `local` + `production` for a solo MVP; add `staging` when there are real users. |
| Secrets | Env vars, `.env` gitignored, `.env.example` committed. |
| Estimates | Story points `1 2 3 5 8`. |
| Stack | If asked to propose: pick the simplest mainstream stack that fits the platform and the user's stated skills; give the reason in one line. Prefer technologies the user already mentioned. |

## Handling "I don't know"

- Choose the default, mark it `ASSUMED`, and move on. Do not stall the whole bootstrap on one unknown.
- If the unknown blocks a feature (not the foundation), add a `Spike` item to the backlog instead of guessing.
- If the unknown changes the architecture (e.g. data is personal and may be GDPR-relevant, offline vs online), say so in the closing summary as a risk worth deciding early.
