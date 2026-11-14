# devlog

A [Claude Code](https://claude.com/claude-code) plugin that turns a codebase into a technical blog
post. It reads the code, interviews you about what the code can't say, and checks every technical
claim against the source. It also makes the thumbnail, trailer and screenshots by running your app.

It works entirely offline into a local folder. It can also publish to [BlogRAG](https://blograg.pbh-dev.tech),
but only when you ask it to.

## Install

```
/plugin marketplace add KatoVu/devlog
/plugin install devlog@devlog
```

Then, in any repository:

```
/devlog:post
/devlog:post the new OAuth flow
/devlog:post ../other-project --out ~/posts
```

You can also just ask: *"write a blog post about how this repo handles auth"*.

### Requirements

- `git` and `python3`, for the survey, the validator and the secret scan (standard library only)
- [`uv`](https://docs.astral.sh/uv/), for the visuals. The script pulls in Playwright on its own
- A browser for Playwright, once: `uv run --with playwright playwright install chromium`
- `ffmpeg` (optional), for `.mp4` trailers. Without it you get `.webm`

## What it does

```
survey ─► angles ─► interview ─► deep read + claims ledger ─► outline ─► write ─► visuals ─► verify
                       ▲ you                                     ▲ you
```

1. **Survey.** `scan_repo.py` maps the languages, how the project runs, where the commits went,
   recent work, and which files must never be read or quoted (`.env`, keys, …).
2. **Angles.** It proposes three: a hard problem solved, a design trade-off, or a feature traced end to end.
3. **Interview.** It asks 3–5 questions only you can answer: why you built it, what was hard, what
   you measured. Anything you skip stays out of the post.
4. **Claims ledger.** Every technical statement gets a row in `claims.md` pointing at
   `path:line @ commit`, or at your interview answer. Anything unsupported is cut.
5. **Outline.** You approve the outline before anything is written.
6. **Visuals.** If the app has a UI, it runs it with demo data, screenshots the best screen for the
   thumbnail, and records a 10–20 second trailer. If not, you get a title card built around one telling
   code excerpt, plus the architecture diagram.
7. **Verify.** It re-checks the ledger against the code, then runs `validate_post.py` (front matter,
   embeds, 16:9 thumbnail, size limits, unverified claims) and `secret_scan.py`.

It asks before installing dependencies, starting containers or using credentials.

## Output

```
<repo>/.devlog/<slug>/
├── post.md          front matter + Markdown body (Mermaid diagrams inline)
├── claims.md        every claim → its evidence
├── notes.md         survey notes and your interview answers
└── assets/
    ├── thumbnail.png    16:9 still
    ├── trailer.mp4      or .webm / .png
    └── *.png            screenshots the body embeds
```

`post.md` is plain Markdown that works on any blog. Add `.devlog/` to your `.gitignore` if you don't
want drafts committed.

## Your voice

Put a `style.md` in `<repo>/.devlog/` or `~/.config/devlog/` and it's followed over the defaults:

```markdown
- First person, "I". Dry, no exclamation marks.
- Readers are backend engineers; skip the basics of HTTP.
- British spelling.
```

## Publishing to BlogRAG (optional)

devlog never contacts BlogRAG unless you ask. To enable it, add the BlogRAG MCP server once:

```
claude mcp add --transport http blograg https://mcp.blograg.pbh-dev.tech/mcp
```

Then say *"upload it to BlogRAG"*. It creates a **draft**, uploads the thumbnail, the trailer and
every embedded picture, rewrites the embeds to the uploaded files, and reports what's left before
it can go live. It publishes only if you say *publish*.

The connection is limited on the server side. It can't delete anything, edit or unpublish a live
post, or replace existing artwork, whatever the model tries. You can disconnect it from the
BlogRAG studio's Access tab.

## The scripts

They're usable on their own too:

```bash
python3 skills/post/scripts/scan_repo.py ~/code/project
python3 skills/post/scripts/secret_scan.py post.md
python3 skills/post/scripts/validate_post.py .devlog/my-post
uv run skills/post/scripts/visuals.py card --title "…" --code src/main.rs:10-24 --out thumb.png
uv run skills/post/scripts/visuals.py screenshot --url http://localhost:3000 --title "…" --out thumb.png
uv run skills/post/scripts/visuals.py record --url http://localhost:3000 --steps steps.json --out trailer.mp4
uv run skills/post/scripts/visuals.py diagram --mermaid arch.mmd --out arch.png
```

## Development

```
python3 -m unittest discover tests
claude plugin validate .
```

## License

MIT
