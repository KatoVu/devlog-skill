# Visuals

Every post needs a **thumbnail** (a 16:9 still for the card) and a **trailer** (a still or short
video for the post's banner). Add body images only where they show something the text is about.

All commands run from the post folder. `V` is `${CLAUDE_SKILL_DIR}/scripts/visuals.py`:

```bash
V="${CLAUDE_SKILL_DIR}/scripts/visuals.py"
```

The default size is 1600×900. If Playwright says the browser is missing, run this once:
`uv run --with playwright playwright install chromium`

## Deciding what to make

```
Does the project have a UI that can run locally with demo/seed data?
├─ yes → thumbnail: screenshot of its best screen + title strip
│        trailer:   10–20 s recording of the main flow (.mp4)
│        body:      screenshots of the screens the text discusses
└─ no  → thumbnail: title card with one telling code excerpt
         trailer:   the architecture diagram rendered to PNG (or a second card)
         body:      Mermaid blocks; terminal output as text blocks
```

A CLI counts as "no UI". Show its output as a text block in the body. Don't screenshot a terminal.

## Running the app

1. Take the command from the survey ("How it seems to run") or the README.
2. If it needs `npm install`, `pip install`, Docker, a database, migrations, seed data or any
   secret, **ask the author first**. Say exactly what you'll run and what it'll create.
3. Start it in the background, wait for the port (`curl -sf http://localhost:PORT >/dev/null`),
   and use demo or seed data only. Never sign in with real credentials. If a screen needs a
   signed-in user, ask the author for a demo account or skip that screen.
4. Stop everything you started when you're done.

## Thumbnail

```bash
# from the running app, with the post's title across the bottom
uv run "$V" screenshot --url http://localhost:3000/ --out assets/thumbnail.png \
  --title "Letting an AI write drafts without ever letting it delete" --eyebrow "PortfolioRAG"

# no UI: a title card with the one excerpt that carries the idea (≤ 14 lines are shown)
uv run "$V" card --title "…" --eyebrow "project-name" --stack "Rust · Tokio · Postgres" \
  --code src/scheduler.rs:118-131 --out assets/thumbnail.png
```

- The title on the thumbnail is the post title, or a shorter version of it (≤ 60 characters reads best).
- `--theme light|dark`. Pick the one that contrasts with the screenshot or matches the project.
- Pick the screen that shows what's distinctive, not the login page or an empty state.

## Trailer

```bash
# steps.json: what to do on camera
[
  {"wait_for": "main"},
  {"click": "text=New project"},
  {"type": ["input[name=title]", "Hello world"]},
  {"press": "Enter"},
  {"wait": 1200},
  {"scroll": 600}
]
uv run "$V" record --url http://localhost:3000/ --steps steps.json --out assets/trailer.mp4 --max-seconds 20
```

Step types: `goto`, `click`, `type` (`[selector, text]`), `press`, `hover`, `scroll` (pixels),
`wait` (ms), `wait_for` (selector). Each step pauses 600 ms after it (`"pause"` overrides).
`.mp4` needs `ffmpeg`. Without it, write `.webm`, which is accepted too.

Keep it to 10–20 seconds and one flow. Check the result:
`ffprobe -v error -show_entries format=duration -of csv=p=0 assets/trailer.mp4`

Without a UI:

```bash
uv run "$V" diagram --mermaid architecture.mmd --out assets/trailer.png
```

`diagram` loads Mermaid from a CDN, so it needs the network. Offline, make a second `card` instead.

## Body screenshots

```bash
uv run "$V" screenshot --url http://localhost:3000/settings --out assets/settings.png
uv run "$V" screenshot --url http://localhost:3000/ --selector "#pricing" --out assets/pricing.png
uv run "$V" screenshot --url http://localhost:3000/ --steps open-dialog.json --out assets/dialog.png
```

- Name files for what they show (`consent-page.png`, not `screenshot-3.png`).
- The alt text says what's in the picture: "The consent page listing what the app can and can
  never do". It becomes the caption and the alt text on BlogRAG.
- Before keeping a screenshot, look at it (Read the PNG). Check it isn't showing a spinner, an
  error, a cookie banner, or anything personal.

## Limits

| Kind | Formats | Max size |
| --- | --- | --- |
| Pictures | PNG, JPEG, GIF, WebP | 10 MB |
| Video (trailer only, or attachments) | MP4, WebM | 100 MB |

The thumbnail must be a picture. `validate_post.py` checks all of this.
