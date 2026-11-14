---
name: post
description: Write a technical blog post about a codebase. It's researched from the code, every claim is checked against it, and the thumbnail, trailer and screenshots are made locally. Use when the user asks for a blog post, devlog, write-up, case study, article or "post about" a project, repo, feature, PR or commit range, or wants to turn their code into something to publish. Works fully offline into a local folder. Publishes to BlogRAG through the blograg MCP server, but only when the user explicitly asks for that.
argument-hint: "[path | topic] [--out DIR]"
---

# devlog: technical posts from a codebase

You're writing a technical blog post on behalf of the author of a codebase, in their voice, about
their work. The post has to be **true**. Every technical claim must be checkable against the code,
and anything the code can't tell you has to come from the author, not from you.

Everything is written to a local folder. Nothing leaves the machine unless the author asks for it.

## Ground rules

- **Never invent.** That covers numbers, benchmarks, user counts, performance claims, timelines,
  motivations and "lessons learned". If the code doesn't show it and the author didn't say it, it
  isn't in the post. A measured number needs to come from a command you ran or from the author.
- **Every technical claim goes in the ledger.** `claims.md` maps each claim to its evidence
  (`path:line` at a commit, or "author said"). Anything you can't support gets cut or reworded.
- **Secrets never appear.** Don't open the files `scan_repo.py` lists under "Do not read or quote".
  Run `secret_scan.py` over the draft before calling it done. Screenshots use demo or seed data,
  never real users' data or anything that shows a token.
- **Don't touch BlogRAG unless asked.** This skill doesn't call any `blograg` MCP tool unless the
  author explicitly asks you to post, upload or publish to BlogRAG. That includes reading their posts.
  When they do ask, follow [references/blograg.md](references/blograg.md).
- **Ask before anything heavy or outward-facing.** That means installing dependencies, starting
  containers, running migrations, or anything that needs credentials. Reading code and running the
  scripts below doesn't need permission.

## Setup

1. **Target.** If the argument is a path, use it; otherwise use the current repository. If it's a
   topic ("the new auth flow"), the target is the current repository and the topic fixes the angle.
2. **Output.** Default is `<repo>/.devlog/<slug>/`, or `--out DIR`. Create it, plus `assets/`
   inside. If `.devlog/` isn't gitignored, tell the author once; don't edit `.gitignore` yourself.
3. **Voice.** If `<repo>/.devlog/style.md` or `~/.config/devlog/style.md` exists, read it and follow
   it over the defaults in the writing guide.
4. **Tools.** `python3` and `git` are required. `uv` is needed for the visuals. If the first visuals
   command says no browser is installed, run
   `uv run --with playwright playwright install chromium` once.

The scripts live in this skill's folder:

| Script | What it's for |
| --- | --- |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/scan_repo.py <repo>` | Survey: languages, how it runs, churn, recent work, files to avoid |
| `uv run ${CLAUDE_SKILL_DIR}/scripts/visuals.py …` | Screenshots, screen recordings, title cards, Mermaid → PNG |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/secret_scan.py <files>` | Credentials, keys, private addresses |
| `python3 ${CLAUDE_SKILL_DIR}/scripts/validate_post.py <folder>` | Checks the post folder before it's called done |

## Workflow

Work through these in order. Steps 3 and 5 are the only places to stop and wait for the author.
Keep each check-in short.

### 1. Survey

Run `scan_repo.py`. Then read the README, the manifests, the entry points, and the most-changed
files it lists. Write what you learn to `notes.md`: what the project does, its architecture in a few
lines, how to run it, and whether it has a UI you could screenshot.

### 2. Pick the angle

A post is about **one** thing. If the author named a topic, that's the angle. Otherwise propose
three, each with:

- a working title,
- a one-sentence thesis (the claim the post will defend),
- who it's for,
- the files it'll draw on.

Good angles come from where the work went (churn), from what's unusual in the design, and from a
hard problem visibly solved in the code. "An overview of the project" is the weakest angle. Only
offer it when the project is small. See [references/writing-guide.md](references/writing-guide.md#angles).

### 3. Interview (stop and ask)

Present the angles, if you have them, along with 3–5 questions about what the code can't tell you.
Use the AskUserQuestion tool if it's available. Pick from:

- Why did you build it, and what existed before that wasn't good enough?
- What was the hardest part, and what did you try first that didn't work?
- What would you do differently now?
- Did you measure anything? (latency, cost, size, users). Only numbers you actually have.
- Who's the reader: recruiters, peers in the same stack, or beginners?

The author can skip any question. Record the answers verbatim in `notes.md`. They're the only
source for motivation, history and results.

### 4. Read deeply and build the ledger

Now read the code the angle depends on, all of it, not just the files' first screens. Follow the
calls. For each thing you'd want to say, add a row to `claims.md`:

```markdown
| # | Claim | Evidence | Status |
| - | ----- | -------- | ------ |
| 1 | Refresh tokens rotate, and replaying one revokes the grant | backend/Services/OAuthService.cs:402-418 @ d13175a | verified |
| 2 | Built because existing matchers hallucinated experience | author, interview | author said |
```

Status is `verified` (you read the code and it does exactly that), `author said`, or `measured`
(you ran the command; put the command in the evidence). Anything else gets cut.

### 5. Outline (stop and ask)

Show the outline: title, a one-line summary, sections with one sentence each, the code excerpts
you plan to show (file and lines), and the planned visuals. Wait for approval or changes.

### 6. Write

Write `post.md` following [references/writing-guide.md](references/writing-guide.md). Front matter:

```yaml
---
title: "…"            # 3–200 characters
slug: "…"             # lowercase-words-with-hyphens
summary: "…"          # ≤ 500 characters; shown on the project card
repo_url: "…"         # only if the remote is public; ask if unsure
demo_url: ""          # only if the author gave one
source_commit: "…"    # HEAD when written, so claims stay checkable
---
```

Embed local pictures as `![alt text that describes the picture](assets/name.png)`. Put diagrams
in ` ```mermaid ` blocks. BlogRAG renders them, and so do GitHub and most static sites.

### 7. Make the visuals

Follow [references/visuals.md](references/visuals.md). In short:

- **Thumbnail** (`assets/thumbnail.png`, 16:9, required): a screenshot of the running app with a
  title strip. If there's nothing visual to show, use a title card with one telling code excerpt.
- **Trailer** (`assets/trailer.mp4` or `.webm`, or a `.png`, required): a 10–20 second recording of
  the main flow if the app runs. Otherwise a still, such as the architecture diagram rendered to PNG.
- **In the body**: screenshots of the specific screens the text discusses. Diagrams stay as Mermaid.

To run the project, use the commands from the survey. If it needs dependencies installed,
containers, a database, seed data or secrets, ask first and say exactly what you'll run. Use seed or
demo data only. Stop everything you started when you're done.

### 8. Verify

1. Re-read every row in `claims.md` against the code as it is now. Fix the post wherever they disagree.
2. Run `validate_post.py <folder>` and fix every error. Address the warnings or say why not.
3. Read the post once as the intended reader. Cut anything that doesn't serve the thesis.

### 9. Hand off

Tell the author where the folder is, give the word count, list the visuals made, and name anything
cut for lack of evidence. If the blograg MCP tools are available in this session, mention that you
can upload it as a BlogRAG draft. Then **stop**: don't upload until they ask.

## Publishing to BlogRAG

Only when the author explicitly asks ("post it to BlogRAG", "upload this as a draft", "publish it").
Follow [references/blograg.md](references/blograg.md) exactly. In short: drafts only, upload every
asset through `request_upload`, and call `publish_post` only if they said *publish*.
