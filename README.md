# devlog skill

A [Claude Code](https://claude.com/claude-code) plugin that turns a codebase into a technical blog
post. It reads the code, asks you what the code can't say, checks every claim against the source,
and makes the thumbnail, trailer and screenshots by running your app. Everything stays in a local folder.

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

Or just ask: *"write a blog post about how this repo handles auth"*.

### Requirements

- `git` and `python3`
- [`uv`](https://docs.astral.sh/uv/) for the visuals, plus a browser once: `uv run --with playwright playwright install chromium`
- `ffmpeg` (optional) for `.mp4` trailers, otherwise you get `.webm`

## What it does

| # | Step | What happens |
|---|------|--------------|
| 1 | Survey | Maps the languages, how the project runs, recent work, and files it must never read (`.env`, keys) |
| 2 | Angles | Proposes three angles: a hard problem, a design trade-off, or a feature end to end |
| 3 | Interview | Asks you 3–5 questions only you can answer. Anything you skip stays out |
| 4 | Claims | Every technical claim is linked to `path:line` or your answer. Unsupported claims are cut |
| 5 | Outline | You approve it before anything is written |
| 6 | Visuals | Screenshots and a short trailer of your app, or a title card and diagram if there's no UI |
| 7 | Verify | Re-checks the claims, validates the post and scans it for secrets |

It asks before installing dependencies, starting containers or using credentials.

## Output

```
<repo>/.devlog/<slug>/
├── post.md      the post (plain Markdown, works on any blog)
├── claims.md    every claim → its evidence
├── notes.md     survey notes and your answers
└── assets/      thumbnail, trailer, screenshots
```

Add `.devlog/` to your `.gitignore` if you don't want drafts committed.

## Your voice

Put a `style.md` in `<repo>/.devlog/` or `~/.config/devlog/` and it's followed over the defaults:

```markdown
- First person, "I". Dry, no exclamation marks.
- Readers are backend engineers; skip the basics of HTTP.
- British spelling.
```

## License

MIT
