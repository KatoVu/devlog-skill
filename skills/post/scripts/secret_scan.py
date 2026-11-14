#!/usr/bin/env python3
"""Look for things that must not be published: credentials, private keys, internal addresses.

    python3 secret_scan.py FILE [FILE ...]

Exit code 0 when clean, 1 when something was found (each hit is printed with its line).
Standard library only. A hit is a reason to look, not proof — but nothing ships with one
unexplained.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{20,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("BlogRAG token", re.compile(r"\bpf[lrcu]_[A-Za-z0-9_-]{20,}\b")),
    ("connection string with password",
     re.compile(r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis|amqp)://[^\s:/@]+:[^\s@]{3,}@", re.I)),
    ("password in config", re.compile(r"(?i)\b(?:password|passwd|pwd)\s*[=:]\s*['\"]?(?!\$|\{|<|\*{3}|x{3}|changeme)[^\s'\"]{6,}")),
    ("secret assignment",
     re.compile(r"(?i)\b(?:api[_-]?key|secret|token|access[_-]?key|client[_-]?secret)\s*[=:]\s*['\"][A-Za-z0-9/+_=-]{16,}['\"]")),
    ("private IP address", re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
]

# Values that look like secrets but are documentation of the shape of one.
PLACEHOLDER = re.compile(r"(?i)(example|placeholder|your[_-]|xxxx|<[^>]+>|\.\.\.|…|dummy|redacted|test[_-]?key)")


def scan(path: Path) -> list[str]:
    hits: list[str] = []
    try:
        lines = path.read_text(errors="ignore").splitlines()
    except OSError as error:
        return [f"{path}: could not read ({error})"]

    for number, line in enumerate(lines, 1):
        for label, pattern in PATTERNS:
            match = pattern.search(line)
            if match and not PLACEHOLDER.search(match.group(0)):
                shown = match.group(0)
                if len(shown) > 12:
                    shown = shown[:6] + "…" + shown[-3:]
                hits.append(f"{path}:{number}: {label}: {shown}")
    return hits


def main(argv: list[str]) -> int:
    if not argv:
        print((__doc__ or "").strip(), file=sys.stderr)
        return 2

    hits = [hit for name in argv for hit in scan(Path(name))]
    for hit in hits:
        print(hit)

    if hits:
        print(f"\n{len(hits)} possible secret(s). Remove or replace each before publishing.", file=sys.stderr)
        return 1

    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
