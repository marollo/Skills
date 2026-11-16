# Brief schema

The brief is one JSON file holding only what is specific to this project. `scripts/render_project_files.py` adds everything else (skeletons, how-to text, DEV_OPS defaults, Foundation backlog items, IDs, CSV quoting, dependency order). Write plain, concrete sentences; never repeat boilerplate. For a complete working example, read `assets/example-brief.json` only if a field below is unclear.

Required: `project`, `summary`, `product_goal`, `requirements.functional` (at least one), `backlog` (at least one item). Everything else is optional; omit what you do not know instead of inventing it (put unknowns in `assumptions`).

```
project:        {name, one_liner, mode: "new" | "existing"}
stack_profile:  "python" | "node-ts" | "generic" | "none"      # picks the Foundation epic and default commands
walking_skeleton: "the thinnest end-to-end slice, as a phrase"    # new projects
foundation_skip:  ["f-ci", ...]                                   # Foundation items to leave out (existing repos: use scan hints)
foundation_override: {"f-repo": {title, description, ac:[...]}}   # adapt a Foundation item
summary, product_goal: strings
goals:          [{goal, metric}]
users:          [{who, needs}]
scope:          {mvp:[], later:[], out:[]}
requirements:   {functional:[{key, text, phase?:"later"}], non_functional:[{key, category, text}]}
architecture, data_and_integrations: short paragraphs
stack:          [{layer, choice, notes}]
constraints:    [strings];  risks: [{risk, mitigation}]
assumptions:    [{kind:"ASSUMED"|"TBD", text, confirm_with?}]
glossary:       [{term, definition}]
decisions:      [{key?, title, status:"Accepted"|"Proposed", context, options?:[], decision, consequences}]
claude:         {layout:[], commands:{install,run,test,lint,typecheck,build}, conventions:[], ask_before:[], working_rules:[], do_not:[]}
devops:         {team:"solo"|"team", git_host, repo, environments:[{name,purpose,where,deploy,status}], ci_live?, ci_on_pr?:[],
                 release_cadence?, secrets?, rollback?, monitoring?, definition_of_done?:[], defaults_confirmed?, use_defaults?}
backlog:        [{key, epic, title, description, type?, priority?, status?, estimate?, ac:[], depends_on:[keys]}]
extra_sections: {"PROJECT.md"|"CLAUDE.md": [{heading, body}]}
```

## Foundation items you do not need to write

The script generates these at the top of the backlog, so do not add similar items yourself (check the list before writing yours):

| Key | Item | In profiles |
|---|---|---|
| `f-repo` | Initialise repository and project layout | all |
| `f-tooling` | Set up test, lint and type-check tooling | python, node-ts |
| `f-ci` | Add CI pipeline | all |
| `f-config` | Configuration and secrets handling (env vars, `.env.example`) | all |
| `f-skeleton` | Walking skeleton (uses your `walking_skeleton` phrase; dropped for existing repos) | all |

Skip an item the repo already satisfies with `foundation_skip` (scan hints cover tooling, CI, repo and config, but verify them); adapt one with `foundation_override`.

## Rules that save you work

- **Keys, not numbers.** Give requirements and backlog items a short `key`. Refer to them in any text field with `{fr:key}`, `{nfr:key}`, `{dec:key}`, `{bl:key}`; the script replaces them with `FR-3`, `BL-007` and so on. Never type an ID by hand.
- **Dependencies by key.** `depends_on` lists backlog keys, including Foundation keys (`f-repo`, `f-tooling`, `f-ci`, `f-config`, `f-skeleton`). Order the backlog by value; the script moves an item after its dependencies if you got it wrong.
- **Backlog defaults.** `type` Story, `priority` Must, `status` Backlog. Use `Ready` only for items with acceptance criteria that can start now (Foundation items already are). `estimate` is one of 1 2 3 5 8.
- **Decisions.** Use `Accepted` only for what the user stated or confirmed; everything you suggested is `Proposed`. The script adds a `Proposed` entry for the delivery defaults (branching, commits, SemVer, CI) unless `devops.use_defaults` is false; set `devops.defaults_confirmed` when the user chose them.
- **Existing repos.** Set `mode: "existing"`; the walking-skeleton item is dropped automatically. Take `stack_profile` and `foundation_skip` from the scan hints, put real commands in `claude.commands`, and turn code TODOs from the scan into backlog items that cite the file and line.
- **Commands.** For new projects the profile's default commands are annotated "(after BL-00x)" automatically. For anything the profile does not know, give the command yourself.
- **Statuses.** Mark an environment or CI as `Live` only if it exists today.

## Run

```bash
python3 <skill-path>/scripts/render_project_files.py brief.json <target-dir> [--map]
```

Exit 0 means all six files were written and validated. On errors it prints them and writes nothing; fix the brief and rerun. `--map` prints the key-to-ID table. Existing files are kept and the new ones are written as `<name>.proposed`; `--force` overwrites.
