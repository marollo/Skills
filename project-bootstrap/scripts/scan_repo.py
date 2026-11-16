#!/usr/bin/env python3
"""Scan an existing repository and print a compact JSON summary.

Usage: python3 scan_repo.py <repo-dir> [--pretty]

Replaces many Read/Glob/Bash calls: one call returns stack, commands, CI, git info,
TODOs, a shallow tree and hints about which Foundation backlog items can be skipped.
Standard library only. Read-only: never modifies the repo.
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    tomllib = None

SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", "dist", "build", ".next", "target", ".idea",
             ".vscode", "site-packages", ".tox", "coverage", ".turbo"}
SRC_EXT = {".py": "python", ".js": "javascript", ".jsx": "javascript", ".ts": "typescript",
           ".tsx": "typescript", ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
           ".rb": "ruby", ".php": "php", ".cs": "csharp", ".c": "c", ".cpp": "cpp",
           ".swift": "swift", ".sh": "shell", ".ino": "arduino"}
PROJECT_FILES = ["CLAUDE.md", "PROJECT.md", "BUG_AND_FIXES.md", "DECISIONS.md", "DEV_OPS.md", "BACKLOG.csv"]
FRAMEWORKS = {"flask", "django", "fastapi", "starlette", "tornado", "streamlit", "react", "next",
              "vue", "nuxt", "svelte", "angular", "express", "fastify", "nestjs", "koa",
              "python-telegram-bot", "aiogram", "sqlalchemy", "pydantic", "celery", "pandas",
              "numpy", "torch", "tensorflow", "langchain", "ollama", "electron", "vite", "tailwindcss"}
TEST_TOOLS = {"pytest", "unittest", "jest", "vitest", "mocha", "playwright", "cypress", "nose"}
LINT_TOOLS = {"ruff", "flake8", "pylint", "black", "mypy", "pyright", "eslint", "prettier",
              "biome", "isort", "tslint"}
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b[:\s]*(.*)")


def walk(root, max_files=4000):
    n = 0
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            n += 1
            if n > max_files:
                return
            yield p


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def read(p, limit=200_000):
    try:
        return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:  # noqa: BLE001
        return ""


def parse_requirements(text):
    out = []
    for line in text.splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        out.append(re.split(r"[=<>~!\[ ;]", line, maxsplit=1)[0].lower() + (
            "==" + line.split("==")[1].strip() if "==" in line else ""))
    return out


def scan(root):
    root = root.resolve()
    files = list(walk(root))
    rel = [f.relative_to(root) for f in files]
    names = {str(r) for r in rel}
    out = {"name": root.name, "path": str(root), "file_count": len(files)}

    # languages
    lang = Counter(SRC_EXT[f.suffix] for f in files if f.suffix in SRC_EXT)
    out["languages"] = dict(lang.most_common(5))

    # git
    if (root / ".git").exists():
        g = {"is_git": True, "branch": run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root),
             "remote": run(["git", "remote", "get-url", "origin"], root),
             "commit_count": run(["git", "rev-list", "--count", "HEAD"], root),
             "tags": run(["git", "tag", "--sort=-creatordate"], root).splitlines()[:5],
             "last_commits": run(["git", "log", "-5", "--pretty=%s"], root).splitlines()}
        out["git"] = g
    else:
        out["git"] = {"is_git": False}

    # manifests, deps, commands
    deps, commands, manifests = set(), [], []
    pj = root / "package.json"
    if pj.exists():
        manifests.append("package.json")
        try:
            d = json.loads(read(pj))
            out["package"] = {k: d.get(k) for k in ("name", "version", "engines", "type") if d.get(k)}
            deps |= set((d.get("dependencies") or {}).keys()) | set((d.get("devDependencies") or {}).keys())
            for k, v in (d.get("scripts") or {}).items():
                commands.append({"name": k, "command": f"npm run {k}" if k not in ("test", "start") else f"npm {k}",
                                 "source": "package.json", "runs": v[:80]})
        except Exception:  # noqa: BLE001
            pass
    pp = root / "pyproject.toml"
    if pp.exists():
        manifests.append("pyproject.toml")
        if tomllib:
            try:
                d = tomllib.loads(read(pp))
                proj = d.get("project", {})
                out["python"] = {k: proj.get(k) for k in ("name", "version", "requires-python") if proj.get(k)}
                for dep in proj.get("dependencies", []):
                    deps.add(re.split(r"[=<>~!\[ ;]", dep, maxsplit=1)[0].lower())
                for grp in (proj.get("optional-dependencies") or {}).values():
                    for dep in grp:
                        deps.add(re.split(r"[=<>~!\[ ;]", dep, maxsplit=1)[0].lower())
                out["python"]["tool_sections"] = sorted((d.get("tool") or {}).keys())
                for k in (proj.get("scripts") or {}):
                    commands.append({"name": k, "command": k, "source": "pyproject.toml"})
            except Exception:  # noqa: BLE001
                pass
    for rq in sorted(root.glob("requirements*.txt")):
        manifests.append(rq.name)
        reqs = parse_requirements(read(rq))
        out.setdefault("requirements", {})[rq.name] = reqs[:25]
        deps |= {r.split("==")[0] for r in reqs}
    for m in ("Cargo.toml", "go.mod", "Gemfile", "composer.json", "pom.xml", "build.gradle", "platformio.ini"):
        if (root / m).exists():
            manifests.append(m)
    if (root / "go.mod").exists():
        gm = read(root / "go.mod")
        mm = re.search(r"^module\s+(\S+)", gm, re.M)
        gv = re.search(r"^go\s+(\S+)", gm, re.M)
        out["go"] = {"module": mm.group(1) if mm else None, "version": gv.group(1) if gv else None}
    mk = root / "Makefile"
    if mk.exists():
        manifests.append("Makefile")
        for t in re.findall(r"^([A-Za-z][\w-]*):(?!=)", read(mk), re.M)[:15]:
            commands.append({"name": t, "command": f"make {t}", "source": "Makefile"})
    out["manifests"] = manifests

    dl = {d.lower() for d in deps}
    out["frameworks"] = sorted(dl & FRAMEWORKS)
    out["test_tools"] = sorted(dl & TEST_TOOLS)
    out["lint_tools"] = sorted(dl & LINT_TOOLS)
    if "pytest" not in out["test_tools"] and any(n.startswith("tests/") and n.endswith(".py") for n in names):
        out["test_tools"].append("pytest-or-unittest (tests/ dir, not in deps)")
    out["dependency_count"] = len(dl)

    # CI
    ci = []
    wf = root / ".github" / "workflows"
    if wf.is_dir():
        for y in sorted(wf.glob("*.y*ml")):
            t = read(y)
            runs = [r.strip() for r in re.findall(r"^\s*-?\s*run:\s*(.+)$", t, re.M)][:8]
            trig = re.search(r"^on:\s*(.*)$", t, re.M)
            ci.append({"system": "github-actions", "file": str(y.relative_to(root)),
                       "triggers": trig.group(1).strip()[:60] if trig else "", "runs": runs,
                       "python": re.findall(r"python-version:\s*[\"']?([\d.]+)", t)[:1],
                       "deploys": bool(re.search(r"deploy|publish|release", t, re.I))})
            for r in runs:
                commands.append({"name": "ci-step", "command": r[:80], "source": "ci"})
    for other in (".gitlab-ci.yml", "Jenkinsfile", ".circleci/config.yml", "azure-pipelines.yml", "bitbucket-pipelines.yml"):
        if (root / other).exists():
            ci.append({"system": other})
    out["ci"] = ci

    # misc flags
    out["has"] = {"gitignore": ".gitignore" in names, "readme": any(n.lower().startswith("readme") for n in names),
                  "env_example": any(n in names for n in (".env.example", ".env.sample", "env.example")),
                  "dockerfile": any(n.endswith("Dockerfile") or n == "Dockerfile" for n in names),
                  "compose": any(n.startswith("docker-compose") or n.startswith("compose.") for n in names),
                  "license": any(n.upper().startswith("LICENSE") for n in names),
                  "changelog": any(n.upper().startswith("CHANGELOG") for n in names),
                  "tests": any(re.search(r"(^|/)(tests?|__tests__)/|test_.*\.py$|\.(test|spec)\.[jt]sx?$", n) for n in names)}
    out["existing_project_files"] = [n for n in PROJECT_FILES if n in names]
    for r in rel:
        if r.name.lower().startswith("readme"):
            txt = read(root / r, 3000)
            out["readme_excerpt"] = re.sub(r"\s+", " ", txt)[:400]
            break

    # TODOs (source files only)
    todos = []
    for f in files:
        if f.suffix in SRC_EXT or f.suffix in (".md", ".yml", ".yaml"):
            if f.stat().st_size > 300_000:
                continue
            for i, line in enumerate(read(f).splitlines(), 1):
                m = TODO_RE.search(line)
                if m and ("#" in line or "//" in line or "/*" in line or "<!--" in line or f.suffix in (".md",)):
                    todos.append(f"{f.relative_to(root)}:{i}: {m.group(0)[:90]}")
                    if len(todos) >= 25:
                        break
        if len(todos) >= 25:
            break
    out["todos"] = todos

    # shallow tree
    tree = []
    for p in sorted(root.iterdir()):
        if p.name in SKIP_DIRS or p.name == ".git":
            continue
        if p.is_dir():
            kids = [c.name for c in sorted(p.iterdir()) if c.name not in SKIP_DIRS][:8]
            tree.append(p.name + "/" + (" [" + ", ".join(kids) + "]" if kids else ""))
        else:
            tree.append(p.name)
        if len(tree) >= 40:
            break
    out["tree"] = tree

    # hints
    skip = []
    if out["git"].get("is_git") and out["has"]["gitignore"]:
        skip.append("f-repo")
    if out["has"]["tests"] and out["lint_tools"]:
        skip.append("f-tooling")
    if ci:
        skip.append("f-ci")
    if out["has"]["env_example"]:
        skip.append("f-config")
    primary = next(iter(out["languages"]), None)
    profile = {"python": "python", "typescript": "node-ts", "javascript": "node-ts"}.get(primary, "generic")
    out["hints"] = {"suggested_stack_profile": profile, "suggested_foundation_skip": skip,
                    "is_empty": len(files) == 0}
    out["commands"] = commands[:25]
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or not Path(args[0]).is_dir():
        print(__doc__)
        return 2
    res = scan(Path(args[0]))
    print(json.dumps(res, indent=2 if "--pretty" in sys.argv else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
