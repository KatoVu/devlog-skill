"""Tests for the standard-library scripts. Run: python3 -m unittest discover tests"""

from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "post" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import secret_scan  # noqa: E402
import validate_post  # noqa: E402


def png(width: int, height: int) -> bytes:
    raw = b"".join(b"\x00" + b"\x10\x20\x30" * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


GOOD_POST = """---
title: "Letting an assistant write drafts"
slug: "letting-an-assistant-write-drafts"
summary: "How the connector writes drafts and never deletes."
---

# Why

{prose}

![The consent page](assets/consent.png)

```python
print("hello")
```
"""

LEDGER = """| # | Claim | Evidence | Status |
| - | ----- | -------- | ------ |
| 1 | Tokens rotate | src/auth.py:10-20 @ abc123 | verified |
"""


class SecretScanTests(unittest.TestCase):
    def scan_text(self, text: str) -> list[str]:
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(text)
        return secret_scan.scan(Path(handle.name))

    def test_finds_real_looking_credentials(self):
        samples = [
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "key = AKIAIOSFODNN7ABCDEFG",
            "token ghp_" + "a" * 36,
            "postgres://app:hunter2hunter2@db.internal:5432/app",
            "Authorization: Bearer pfl_" + "Z" * 30,
            "sk-ant-" + "b" * 30,
            "connect to 10.0.3.7 first",
        ]
        for sample in samples:
            with self.subTest(sample=sample[:20]):
                self.assertTrue(self.scan_text(sample), sample)

    def test_leaves_placeholders_and_ordinary_prose_alone(self):
        samples = [
            "Set API_KEY=<your-key> in .env",
            "postgres://user:<password>@localhost/db",
            "The token is opaque and rotates hourly.",
            "Version 10.0.11 of the package",
            "password = ${DB_PASSWORD}",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.assertEqual(self.scan_text(sample), [])


class ValidatePostTests(unittest.TestCase):
    def make_folder(self, *, post: str, thumbnail=(1600, 900), trailer=True, ledger: str | None = LEDGER) -> Path:
        folder = Path(tempfile.mkdtemp())
        (folder / "assets").mkdir()
        (folder / "post.md").write_text(post)
        (folder / "assets" / "consent.png").write_bytes(png(40, 30))
        if thumbnail:
            (folder / "assets" / "thumbnail.png").write_bytes(png(*thumbnail))
        if trailer:
            (folder / "assets" / "trailer.png").write_bytes(png(160, 90))
        if ledger is not None:
            (folder / "claims.md").write_text(ledger)
        return folder

    def run_validator(self, folder: Path) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "validate_post.py"), str(folder)],
            capture_output=True, text=True, check=False,
        )
        return result.returncode, result.stdout

    def test_a_complete_post_passes(self):
        folder = self.make_folder(post=GOOD_POST.format(prose="word " * 450))
        code, out = self.run_validator(folder)
        self.assertEqual(code, 0, out)
        self.assertIn("ok:", out)

    def test_missing_artwork_and_ledger_are_errors(self):
        folder = self.make_folder(post=GOOD_POST.format(prose="word " * 450), thumbnail=None, trailer=False, ledger=None)
        code, out = self.run_validator(folder)
        self.assertEqual(code, 1)
        self.assertIn("thumbnail", out)
        self.assertIn("trailer", out)
        self.assertIn("claims.md", out)

    def test_an_unverified_claim_is_an_error(self):
        ledger = LEDGER + "| 2 | It is 3x faster | | unverified |\n"
        folder = self.make_folder(post=GOOD_POST.format(prose="word " * 450), ledger=ledger)
        code, out = self.run_validator(folder)
        self.assertEqual(code, 1)
        self.assertIn("unverified claim", out)

    def test_a_missing_embed_and_a_secret_are_errors(self):
        post = GOOD_POST.format(prose="word " * 450) + "\n![gone](assets/nope.png)\nghp_" + "aB3dE5" * 6 + "\n"
        folder = self.make_folder(post=post)
        code, out = self.run_validator(folder)
        self.assertEqual(code, 1)
        self.assertIn("embedded file missing: assets/nope.png", out)
        self.assertIn("possible secret", out)

    def test_a_thumbnail_that_is_not_16_by_9_is_flagged(self):
        folder = self.make_folder(post=GOOD_POST.format(prose="word " * 450), thumbnail=(800, 800))
        _, out = self.run_validator(folder)
        self.assertIn("16:9", out)

    def test_reads_png_dimensions(self):
        path = Path(tempfile.mkdtemp()) / "x.png"
        path.write_bytes(png(1600, 900))
        self.assertEqual(validate_post.dimensions(path), (1600, 900))


class ScanRepoTests(unittest.TestCase):
    def test_surveys_a_small_repository(self):
        repo = Path(tempfile.mkdtemp())
        (repo / "app.py").write_text("print('hi')\n")
        (repo / ".env").write_text("SECRET=1\n")
        (repo / "package.json").write_text('{"scripts": {"dev": "vite"}, "dependencies": {"react": "1"}}')
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
            check=True,
        )

        out = subprocess.run(
            [sys.executable, str(SCRIPTS / "scan_repo.py"), str(repo)],
            capture_output=True, text=True, check=True,
        ).stdout

        self.assertIn("Python", out)
        self.assertIn("npm run dev", out)
        self.assertIn("React", out)
        self.assertIn("`.env`", out.split("## Do not read or quote")[1])


if __name__ == "__main__":
    unittest.main()
