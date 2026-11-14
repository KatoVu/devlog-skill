#!/usr/bin/env python3
"""Check a devlog post folder before it is called done (and before anything is uploaded).

    python3 validate_post.py .devlog/<slug>

Checks the front matter, the body, every local image or video the body embeds, the
thumbnail (16:9 still) and trailer, the claims ledger, and runs the secret scan. Prints one
line per problem; exit code 1 if any are errors. Standard library only.
"""

from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from secret_scan import scan  # noqa: E402

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO = {".mp4", ".webm"}
MAX_IMAGE = 10 * 1024 * 1024
MAX_VIDEO = 100 * 1024 * 1024
EMBED = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line and not line.startswith((" ", "#")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("\"'")
    return fields, text[end + 4 :].lstrip("\n")


def dimensions(path: Path) -> tuple[int, int] | None:
    """Width and height of a PNG, JPEG, GIF or WebP, read from its header."""
    data = path.read_bytes()[:256 * 1024]
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return struct.unpack("<HH", data[6:10])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return 1 + int.from_bytes(data[24:27], "little"), 1 + int.from_bytes(data[27:30], "little")
        if chunk == b"VP8 ":
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2

    folder = Path(argv[0])
    post = folder / "post.md"
    errors: list[str] = []
    warnings: list[str] = []

    if not post.exists():
        print(f"error: {post} does not exist")
        return 1

    text = post.read_text()
    meta, body = front_matter(text)

    title = meta.get("title", "")
    if not 3 <= len(title) <= 200:
        errors.append("front matter: title must be 3–200 characters")
    if len(meta.get("summary", "")) > 500:
        errors.append("front matter: summary must be at most 500 characters")
    if not meta.get("summary"):
        warnings.append("front matter: no summary (the project card shows one)")
    if meta.get("slug") and not SLUG.match(meta["slug"]):
        errors.append("front matter: slug must be lowercase words joined by single hyphens")
    if not body.strip():
        errors.append("body is empty")
    if len(body) > 100_000:
        errors.append(f"body is {len(body):,} characters; BlogRAG accepts at most 100,000")

    words = len(re.findall(r"\b\w+\b", re.sub(r"```.*?```", "", body, flags=re.S)))
    if words < 400:
        warnings.append(f"body is only {words} words of prose")

    fence_open = False
    for number, line in enumerate(body.splitlines(), 1):
        if line.startswith("```"):
            if not fence_open and line.strip() == "```":
                warnings.append(f"post.md body line {number}: code block without a language")
            fence_open = not fence_open
    if fence_open:
        errors.append("an unclosed ``` code block")

    for alt, target in EMBED.findall(body):
        if re.match(r"^(https?:)?//|^/api/media/", target):
            continue
        path = (folder / target).resolve()
        if not path.exists():
            errors.append(f"embedded file missing: {target}")
            continue
        suffix = path.suffix.lower()
        if suffix not in IMAGE | VIDEO:
            errors.append(f"{target}: BlogRAG accepts PNG, JPEG, GIF, WebP, MP4 and WebM only")
        limit = MAX_VIDEO if suffix in VIDEO else MAX_IMAGE
        if path.stat().st_size > limit:
            errors.append(f"{target}: {path.stat().st_size / 1_048_576:.1f} MB is over the limit")
        if not alt.strip():
            warnings.append(f"{target}: no alt text — the caption becomes the image's alt text")

    assets = folder / "assets"
    thumbnail = next(iter(sorted(assets.glob("thumbnail.*"))), None) if assets.exists() else None
    trailer = next(iter(sorted(assets.glob("trailer.*"))), None) if assets.exists() else None

    if thumbnail is None:
        errors.append("no assets/thumbnail.* (a 16:9 picture is required to publish)")
    elif thumbnail.suffix.lower() not in IMAGE:
        errors.append("the thumbnail must be a picture, not a video")
    else:
        size = dimensions(thumbnail)
        if size and abs(size[0] / size[1] - 16 / 9) > 0.02:
            warnings.append(f"thumbnail is {size[0]}×{size[1]}; cards are drawn 16:9 and will crop it")

    if trailer is None:
        errors.append("no assets/trailer.* (a picture or a video is required to publish)")
    elif trailer.suffix.lower() not in IMAGE | VIDEO:
        errors.append("the trailer must be a picture or an MP4/WebM video")

    claims = folder / "claims.md"
    if not claims.exists():
        errors.append("no claims.md — every technical claim needs its evidence recorded")
    else:
        rows = [line for line in claims.read_text().splitlines() if line.startswith("|") and "---" not in line]
        unsupported = [row for row in rows[1:] if re.search(r"\|\s*(TODO|\?|unverified)\s*\|", row, re.I)]
        if len(rows) <= 1:
            warnings.append("claims.md lists no claims")
        for row in unsupported:
            errors.append(f"claims.md: unverified claim: {row.strip()[:100]}")

    for name in ("post.md", "claims.md"):
        if (folder / name).exists():
            errors += [f"possible secret — {hit}" for hit in scan(folder / name)]

    for line in errors:
        print(f"error: {line}")
    for line in warnings:
        print(f"warning: {line}")
    if not errors:
        print(f"ok: {title!r}, {words} words, thumbnail {thumbnail.name if thumbnail else '-'}, "
              f"trailer {trailer.name if trailer else '-'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
