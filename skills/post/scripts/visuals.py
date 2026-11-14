# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.50"]
# ///
"""Make a post's pictures: screenshots and recordings of the running app, title cards, diagrams.

    uv run visuals.py screenshot --url http://localhost:3000 --out assets/thumbnail.png --title "…"
    uv run visuals.py record     --url http://localhost:3000 --steps steps.json --out assets/trailer.webm
    uv run visuals.py card       --title "…" --code src/app.py:40-58 --out assets/thumbnail.png
    uv run visuals.py diagram    --mermaid architecture.mmd --out assets/architecture.png

Everything is 1600×900 (16:9, what BlogRAG's cards and banners are drawn at) unless told
otherwise. First run needs a browser: `uv run --with playwright playwright install chromium`.

Style rules the card follows on purpose: flat colour, square corners, no gradients, no
glows. A thumbnail is read at 300px wide, so it carries a title and one strong detail.
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

WIDTH, HEIGHT = 1600, 900

THEMES = {
    "dark": {"bg": "#141414", "fg": "#f2efe8", "muted": "#9a968c", "panel": "#1d1d1d",
             "line": "#2e2e2e", "accent": "#e4572e"},
    "light": {"bg": "#f4f1ea", "fg": "#161616", "muted": "#6b675e", "panel": "#ffffff",
              "line": "#d9d4c7", "accent": "#d1462a"},
}

SANS = "Inter, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
MONO = "'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', Menlo, monospace"


# ---------------------------------------------------------------------------------------
# Browser actions shared by screenshot and record
# ---------------------------------------------------------------------------------------


def run_steps(page: Page, steps: list[dict], default_pause: int = 600) -> None:
    """Steps: {"goto": url} {"click": sel} {"type": [sel, text]} {"press": key}
    {"hover": sel} {"scroll": px} {"wait": ms} {"wait_for": sel}."""
    for step in steps:
        if "goto" in step:
            page.goto(step["goto"], wait_until="networkidle")
        elif "click" in step:
            page.click(step["click"])
        elif "type" in step:
            selector, text = step["type"]
            page.click(selector)
            page.keyboard.type(text, delay=step.get("delay", 45))
        elif "press" in step:
            page.keyboard.press(step["press"])
        elif "hover" in step:
            page.hover(step["hover"])
        elif "scroll" in step:
            page.mouse.wheel(0, int(step["scroll"]))
        elif "wait_for" in step:
            page.wait_for_selector(step["wait_for"], timeout=step.get("timeout", 15000))
        elif "wait" in step:
            page.wait_for_timeout(int(step["wait"]))
            continue
        page.wait_for_timeout(step.get("pause", default_pause))


def load_steps(path: str | None) -> list[dict]:
    if not path:
        return []
    steps = json.loads(Path(path).read_text())
    if not isinstance(steps, list):
        raise SystemExit("--steps must be a JSON list of step objects")
    return steps


def goto(page: Page, url: str) -> None:
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
    except Exception:  # an app that polls never goes idle; the page is still there
        page.wait_for_load_state("load")


# ---------------------------------------------------------------------------------------
# Cards
# ---------------------------------------------------------------------------------------


def read_excerpt(spec: str, max_lines: int = 14) -> tuple[str, str]:
    """`path:START-END` → (label, code). Trims common indentation; caps the length."""
    path, _, span = spec.partition(":")
    lines = Path(path).read_text(errors="ignore").splitlines()
    start, end = 1, min(len(lines), max_lines)
    if span:
        a, _, b = span.partition("-")
        start, end = int(a), int(b or a)
    chosen = lines[start - 1 : end][:max_lines]
    indent = min((len(line) - len(line.lstrip()) for line in chosen if line.strip()), default=0)
    # NOTE: the panel holds about 44 columns at this size; longer lines are cut, visibly.
    trimmed = [line[indent:].rstrip() for line in chosen]
    code = "\n".join(line if len(line) <= 44 else line[:43] + "…" for line in trimmed)
    return f"{Path(path).name}:{start}", code


def card_html(args: argparse.Namespace, background: str | None) -> str:
    t = THEMES[args.theme]
    title = html.escape(args.title)
    eyebrow = html.escape(args.eyebrow or "")
    subtitle = html.escape(args.subtitle or "")
    stack = html.escape(args.stack or "")

    if background:
        # Screenshot with a solid title strip: the app is the picture, the strip names it.
        return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; box-sizing:border-box; }}
  body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; background:{t['bg']}; font-family:{SANS}; }}
  .shot {{ position:absolute; inset:0; background:url('{background}') top center / cover no-repeat; }}
  .strip {{ position:absolute; left:0; right:0; bottom:0; padding:34px 56px 38px;
            background:{t['bg']}; border-top:6px solid {t['accent']}; color:{t['fg']}; }}
  .eyebrow {{ font:600 22px/1 {MONO}; letter-spacing:.08em; text-transform:uppercase; color:{t['muted']}; margin-bottom:14px; }}
  h1 {{ font-size:64px; line-height:1.05; font-weight:750; letter-spacing:-.02em; }}
</style></head><body><div class="shot"></div><div class="strip">
  {f'<div class="eyebrow">{eyebrow}</div>' if eyebrow else ''}<h1>{title}</h1></div></body></html>"""

    code_block = ""
    if args.code:
        label, code = read_excerpt(args.code)
        code_block = f"""<figure class="code"><figcaption>{html.escape(label)}</figcaption>
<pre>{html.escape(code)}</pre></figure>"""

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; box-sizing:border-box; }}
  body {{ width:{WIDTH}px; height:{HEIGHT}px; overflow:hidden; background:{t['bg']}; color:{t['fg']};
          font-family:{SANS}; padding:80px 88px; display:flex; flex-direction:column; gap:40px; }}
  .top {{ display:flex; align-items:center; gap:16px; font:600 24px/1 {MONO}; letter-spacing:.08em;
          text-transform:uppercase; color:{t['muted']}; }}
  .mark {{ width:20px; height:20px; background:{t['accent']}; }}
  .main {{ flex:1; display:flex; gap:64px; align-items:center; min-height:0; }}
  .words {{ flex:1.15; min-width:0; }}
  h1 {{ font-size:{88 if not args.code else 76}px; line-height:1.02; font-weight:780; letter-spacing:-.025em;
        display:-webkit-box; -webkit-line-clamp:4; -webkit-box-orient:vertical; overflow:hidden; }}
  .subtitle {{ margin-top:28px; font-size:32px; line-height:1.3; color:{t['muted']}; max-width:24em; }}
  .code {{ flex:1; min-width:0; background:{t['panel']}; border:2px solid {t['line']}; }}
  .code figcaption {{ font:500 20px/1 {MONO}; color:{t['muted']}; padding:18px 24px; border-bottom:2px solid {t['line']}; }}
  .code pre {{ font:500 20px/1.5 {MONO}; font-variant-ligatures:none; padding:22px 24px; white-space:pre; overflow:hidden; color:{t['fg']}; }}
  .stack {{ font:500 24px/1 {MONO}; color:{t['muted']}; border-top:2px solid {t['line']}; padding-top:28px; }}
</style></head><body>
  <div class="top"><span class="mark"></span>{eyebrow}</div>
  <div class="main"><div class="words"><h1>{title}</h1>
    {f'<p class="subtitle">{subtitle}</p>' if subtitle else ''}</div>{code_block}</div>
  {f'<div class="stack">{stack}</div>' if stack else ''}
</body></html>"""


def render_html(markup: str, out: Path) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write(markup)
        page.goto(Path(handle.name).as_uri())
        page.wait_for_timeout(300)
        page.screenshot(path=str(out))
        browser.close()


def cmd_card(args: argparse.Namespace) -> None:
    background = Path(args.background).resolve().as_uri() if args.background else None
    render_html(card_html(args, background), Path(args.out))


# ---------------------------------------------------------------------------------------
# Screenshots and recordings of the real thing
# ---------------------------------------------------------------------------------------


def cmd_screenshot(args: argparse.Namespace) -> None:
    out = Path(args.out)
    raw = out if not args.title else Path(tempfile.mkstemp(suffix=".png")[1])

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": args.width, "height": args.height},
            color_scheme=args.color_scheme,
            device_scale_factor=1,
        )
        goto(page, args.url)
        run_steps(page, load_steps(args.steps))
        if args.wait_for:
            page.wait_for_selector(args.wait_for, timeout=20000)
        page.wait_for_timeout(args.delay)
        if args.selector:
            page.locator(args.selector).first.screenshot(path=str(raw))
        else:
            page.screenshot(path=str(raw), full_page=args.full_page)
        browser.close()

    if args.title:
        args.background = str(raw)
        args.code = None
        render_html(card_html(args, raw.resolve().as_uri()), out)
        raw.unlink(missing_ok=True)


def cmd_record(args: argparse.Namespace) -> None:
    out = Path(args.out)
    steps = load_steps(args.steps)
    started = time.monotonic()

    with tempfile.TemporaryDirectory() as folder, sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": WIDTH, "height": HEIGHT},
            record_video_dir=folder,
            record_video_size={"width": WIDTH, "height": HEIGHT},
            color_scheme=args.color_scheme,
        )
        page = context.new_page()
        goto(page, args.url)
        page.wait_for_timeout(800)
        run_steps(page, steps)

        # Hold the last frame for a beat, and never run past the cap.
        remaining = args.max_seconds - (time.monotonic() - started)
        page.wait_for_timeout(max(0, min(1500, remaining * 1000)))
        video = page.video
        context.close()
        browser.close()
        recorded = Path(video.path()) if video else None
        if not recorded or not recorded.exists():
            raise SystemExit("No video was recorded.")

        if out.suffix.lower() == ".mp4":
            if not shutil.which("ffmpeg"):
                raise SystemExit("ffmpeg is needed for .mp4; write .webm instead (BlogRAG accepts both).")
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", str(recorded), "-t", str(args.max_seconds),
                 "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(out)],
                check=True,
            )
        else:
            shutil.copy(recorded, out)


# ---------------------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------------------


def cmd_diagram(args: argparse.Namespace) -> None:
    """Mermaid → PNG, framed at 16:9. Loads mermaid from a CDN, so it needs the network."""
    t = THEMES[args.theme]
    source = html.escape(Path(args.mermaid).read_text())
    markup = f"""<!doctype html><html><head><meta charset="utf-8"><style>
  * {{ margin:0; box-sizing:border-box; }}
  body {{ width:{WIDTH}px; height:{HEIGHT}px; background:{t['bg']}; display:flex; align-items:center;
          justify-content:center; padding:72px; font-family:{SANS}; }}
  .mermaid {{ display:flex; align-items:center; justify-content:center; }}
</style></head><body><pre class="mermaid">{source}</pre>
<script type="module">
  import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
  mermaid.initialize({{ startOnLoad: false, theme: "{'dark' if args.theme == 'dark' else 'neutral'}",
                       fontFamily: "{SANS.replace('"', '')}" }});
  await mermaid.run();
  // Mermaid draws at its natural size, which for a small graph is a postage stamp in the
  // middle of the frame. Scale it to fill the frame instead, keeping its proportions.
  const svg = document.querySelector(".mermaid svg");
  const box = svg.viewBox.baseVal;
  const scale = Math.min({WIDTH - 144} / box.width, {HEIGHT - 144} / box.height);
  svg.style.maxWidth = "none";
  svg.setAttribute("width", box.width * scale);
  svg.setAttribute("height", box.height * scale);
  document.body.dataset.ready = "1";
</script></body></html>"""

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as handle:
            handle.write(markup)
        page.goto(Path(handle.name).as_uri())
        page.wait_for_selector("body[data-ready='1']", timeout=30000)
        page.screenshot(path=args.out)
        browser.close()


# ---------------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def card_options(p: argparse.ArgumentParser, title_required: bool) -> None:
        p.add_argument("--title", required=title_required)
        p.add_argument("--eyebrow", help="small label above the title: the project name")
        p.add_argument("--subtitle")
        p.add_argument("--stack", help='e.g. "Rust · WebAssembly · Postgres"')
        p.add_argument("--theme", choices=THEMES, default="dark")

    card = sub.add_parser("card", help="a title card, optionally with a code excerpt")
    card_options(card, True)
    card.add_argument("--code", help="path:START-END excerpt to show beside the title")
    card.add_argument("--background", help="an image to put behind a title strip")
    card.add_argument("--out", required=True)
    card.set_defaults(run=cmd_card)

    shot = sub.add_parser("screenshot", help="a screenshot of a running app")
    card_options(shot, False)
    shot.add_argument("--url", required=True)
    shot.add_argument("--out", required=True)
    shot.add_argument("--steps", help="JSON list of steps to run first")
    shot.add_argument("--wait-for", help="selector to wait for before shooting")
    shot.add_argument("--selector", help="shoot only this element")
    shot.add_argument("--delay", type=int, default=800, help="ms to settle before shooting")
    shot.add_argument("--width", type=int, default=WIDTH)
    shot.add_argument("--height", type=int, default=HEIGHT)
    shot.add_argument("--full-page", action="store_true")
    shot.add_argument("--color-scheme", choices=["light", "dark", "no-preference"], default="no-preference")
    shot.set_defaults(run=cmd_screenshot)

    record = sub.add_parser("record", help="a short screen recording (the trailer)")
    record.add_argument("--url", required=True)
    record.add_argument("--steps", help="JSON list of steps to perform on camera")
    record.add_argument("--out", required=True, help=".webm, or .mp4 if ffmpeg is installed")
    record.add_argument("--max-seconds", type=float, default=20)
    record.add_argument("--color-scheme", choices=["light", "dark", "no-preference"], default="no-preference")
    record.set_defaults(run=cmd_record)

    diagram = sub.add_parser("diagram", help="render a Mermaid diagram to a 16:9 PNG")
    diagram.add_argument("--mermaid", required=True, help="a .mmd file")
    diagram.add_argument("--out", required=True)
    diagram.add_argument("--theme", choices=THEMES, default="dark")
    diagram.set_defaults(run=cmd_diagram)

    args = parser.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    args.run(args)
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
