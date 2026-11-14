#!/usr/bin/env python3
"""Survey a repository so a post can be planned from facts instead of guesses.

Prints a Markdown report: what the project is made of, how it is run, where the work went
(by commit churn), what changed recently, and which files must not be read or quoted.

Standard library only, and read-only: it runs `git` and reads files, nothing else.

    python3 scan_repo.py [PATH] [--commits 40] [--top 15]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

LANGUAGES = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript", ".js": "JavaScript",
    ".jsx": "JavaScript", ".mjs": "JavaScript", ".cs": "C#", ".go": "Go", ".rs": "Rust",
    ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".rb": "Ruby", ".php": "PHP",
    ".c": "C", ".h": "C", ".cpp": "C++", ".hpp": "C++", ".cc": "C++", ".scala": "Scala",
    ".ex": "Elixir", ".exs": "Elixir", ".hs": "Haskell", ".lua": "Lua", ".dart": "Dart",
    ".vue": "Vue", ".svelte": "Svelte", ".sql": "SQL", ".sh": "Shell", ".zig": "Zig",
    ".css": "CSS", ".scss": "CSS", ".html": "HTML", ".tf": "Terraform", ".nix": "Nix",
}

MANIFESTS = [
    "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod", "pom.xml",
    "build.gradle", "build.gradle.kts", "Gemfile", "composer.json", "mix.exs", "pubspec.yaml",
    "Makefile", "justfile", "Taskfile.yml", "Dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "compose.yml", "compose.yaml", "deno.json", "flake.nix",
]

UI_HINTS = {
    "next": "Next.js", "react": "React", "vue": "Vue", "svelte": "Svelte", "@angular/core": "Angular",
    "vite": "Vite", "astro": "Astro", "solid-js": "Solid", "nuxt": "Nuxt", "remix": "Remix",
    "electron": "Electron", "@tauri-apps/api": "Tauri", "streamlit": "Streamlit", "gradio": "Gradio",
    "flask": "Flask", "django": "Django", "fastapi": "FastAPI", "express": "Express",
}

# Files whose contents must never end up in a post. Listed so the writer knows to skip them.
SENSITIVE = re.compile(
    r"(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*|id_ed25519.*|.*secret.*|.*credential.*"
    r"|.*\.p12|.*\.pfx|\.npmrc|\.pypirc|.*\.tfvars|.*\.kdbx|appsettings\.Production\.json)$",
    re.IGNORECASE,
)

SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", "target", "bin", "obj", ".venv",
             "venv", "__pycache__", "vendor", ".turbo", "coverage", ".cache"}


def git(repo: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def tracked_files(repo: Path) -> list[str]:
    listed = git(repo, "ls-files")
    if listed:
        return listed.splitlines()

    # Not a git repository: walk it, skipping the usual build output.
    files = []
    for path in repo.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(repo).parts):
            continue
        if path.is_file():
            files.append(str(path.relative_to(repo)))
    return files


def public_remote(repo: Path) -> str | None:
    """The origin URL with any embedded credentials removed, as https if it was ssh."""
    url = git(repo, "remote", "get-url", "origin")
    if not url:
        return None

    ssh = re.match(r"^git@([^:]+):(.+?)(\.git)?$", url)
    if ssh:
        return f"https://{ssh.group(1)}/{ssh.group(2)}"

    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host += f":{parts.port}"
    return urlunsplit((parts.scheme, host, re.sub(r"\.git$", "", parts.path), "", ""))


def count_lines(path: Path) -> int:
    try:
        with path.open("rb") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def languages(repo: Path, files: list[str]) -> list[tuple[str, int, int]]:
    lines: Counter[str] = Counter()
    count: Counter[str] = Counter()
    for name in files:
        language = LANGUAGES.get(Path(name).suffix.lower())
        if not language or "generated" in name.lower() or name.endswith(".min.js"):
            continue
        count[language] += 1
        lines[language] += count_lines(repo / name)
    return [(lang, count[lang], lines[lang]) for lang, _ in lines.most_common(10)]


def tree(files: list[str], depth: int = 2, limit: int = 60) -> list[str]:
    seen: Counter[str] = Counter()
    for name in files:
        parts = Path(name).parts
        for level in range(1, min(depth, len(parts) - 1) + 1):
            seen["/".join(parts[:level]) + "/"] += 1
    top_files = [f for f in files if "/" not in f]
    rows = [f"{d}  ({n} files)" for d, n in sorted(seen.items())][:limit]
    return rows + top_files[:20]


def run_commands(repo: Path, files: list[str]) -> list[str]:
    commands: list[str] = []

    for manifest in [f for f in files if f.endswith("package.json") and "node_modules" not in f][:6]:
        try:
            scripts = json.loads((repo / manifest).read_text()).get("scripts", {})
        except (OSError, ValueError):
            continue
        prefix = str(Path(manifest).parent)
        for name in ("dev", "start", "serve", "preview", "build", "test", "storybook"):
            if name in scripts:
                where = f"(cd {prefix} && " if prefix != "." else "("
                commands.append(f"{where}npm run {name})   # {scripts[name]}")

    makefile = repo / "Makefile"
    if makefile.exists():
        targets = re.findall(r"^([a-zA-Z][\w-]*):", makefile.read_text(errors="ignore"), re.M)
        if targets:
            commands.append("make " + " | make ".join(targets[:10]))

    for compose in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"):
        if (repo / compose).exists():
            text = (repo / compose).read_text(errors="ignore")
            # Only the services block: top-level volumes and networks look the same.
            block = re.search(r"^services:\n((?:[ \t].*\n|\n)+)", text, re.M)
            services = re.findall(r"^  ([a-zA-Z][\w-]*):\s*$", block.group(1) if block else "", re.M)
            commands.append(f"docker compose -f {compose} up   # services: {', '.join(services[:12])}")

    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        scripts = re.search(r"\[project\.scripts\]\n((?:[^\[\n].*\n?)+)", pyproject.read_text(errors="ignore"))
        if scripts:
            names = re.findall(r"^([\w-]+)\s*=", scripts.group(1), re.M)
            commands.append("console scripts: " + ", ".join(names[:10]))

    return commands


def ui_frameworks(repo: Path, files: list[str]) -> list[str]:
    found: set[str] = set()
    for manifest in [f for f in files if f.endswith(("package.json", "pyproject.toml", "requirements.txt"))][:10]:
        try:
            text = (repo / manifest).read_text(errors="ignore").lower()
        except OSError:
            continue
        for key, label in UI_HINTS.items():
            if f'"{key}"' in text or re.search(rf"^\s*{re.escape(key)}\b", text, re.M):
                found.add(label)
    return sorted(found)


def churn(repo: Path, top: int) -> list[tuple[str, int]]:
    log = git(repo, "log", "--no-merges", "--name-only", "--pretty=format:", "-n", "1500")
    counts = Counter(
        line for line in log.splitlines()
        if line and not line.endswith((".lock", "lock.json", ".snap", ".svg"))
        and "generated" not in line and "Migrations/" not in line
    )
    return counts.most_common(top)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--commits", type=int, default=40, help="recent commit subjects to list")
    parser.add_argument("--top", type=int, default=15, help="most-changed files to list")
    args = parser.parse_args()

    repo = Path(args.path).resolve()
    if not repo.is_dir():
        print(f"Not a directory: {repo}", file=sys.stderr)
        return 2

    files = tracked_files(repo)
    out: list[str] = [f"# Repository survey: {repo.name}", ""]

    remote = public_remote(repo)
    head = git(repo, "rev-parse", "HEAD")
    out += [
        "## Facts",
        f"- Path: `{repo}`",
        f"- Remote: {remote or '(none — a local or private project; ask before linking anything)'}",
        f"- HEAD: `{head[:12]}`" if head else "- Not a git repository",
        f"- Branch: `{git(repo, 'rev-parse', '--abbrev-ref', 'HEAD')}`" if head else "",
        f"- Commits: {git(repo, 'rev-list', '--count', 'HEAD') or '?'}"
        f" (first {(git(repo, 'log', '--max-parents=0', '--format=%as').splitlines() or ['?'])[-1]},"
        f" latest {git(repo, 'log', '-1', '--format=%as') or '?'})" if head else "",
        f"- Tracked files: {len(files)}",
        "",
        "## Languages (files, lines)",
    ]
    out += [f"- {lang}: {n} files, {loc:,} lines" for lang, n, loc in languages(repo, files)] or ["- (none recognised)"]

    manifests = [f for f in files if Path(f).name in MANIFESTS and f.count("/") <= 2]
    out += ["", "## Manifests and entry points", *([f"- `{m}`" for m in manifests[:30]] or ["- (none)"])]

    ui = ui_frameworks(repo, files)
    out += ["", "## Frameworks spotted", f"- {', '.join(ui)}" if ui else "- (none recognised)"]
    out += ["- Has a UI that could be screenshotted: " + ("likely" if set(ui) - {"FastAPI", "Express", "Flask", "Django"} else "unclear — check")]

    commands = run_commands(repo, files)
    out += ["", "## How it seems to run", *([f"- `{c}`" for c in commands] or ["- (nothing obvious — read the README)"])]

    out += ["", "## Layout", "```", *tree(files), "```"]

    hot = churn(repo, args.top)
    if hot:
        out += ["", "## Where the work went (most-changed files)", *[f"- `{f}` — {n} commits" for f, n in hot]]

    recent = git(repo, "log", "--no-merges", f"-n{args.commits}", "--format=%as  %s")
    if recent:
        out += ["", f"## Recent commits (last {args.commits})", "```", recent, "```"]

    readme = next((f for f in files if f.lower() in ("readme.md", "readme.rst", "readme.txt", "readme")), None)
    out += ["", "## README", f"- `{readme}` ({count_lines(repo / readme)} lines) — read it first" if readme else "- (no README)"]

    sensitive = [f for f in files if SENSITIVE.search(f)]
    out += ["", "## Do not read or quote"]
    out += [f"- `{f}`" for f in sensitive[:40]] or ["- (no obviously sensitive files tracked)"]
    out += ["- and anything untracked: `.env*`, keys, local config"]

    print("\n".join(line for line in out if line is not None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
