#!/usr/bin/env python3
"""Fix CDN hosts in a tree, then report. Deploy is separate."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

CDN = "https://www.themotorcoachstore.com"
BAD = re.compile(r"https?://(?:www\.)?themotorcoach\.store/(hubfs|hs-fs)/", re.I)
REL_ATTR = re.compile(
    r"""(?P<attr>(?:href|src|data-src|poster|content)=["'])/(?P<path>hubfs|hs-fs)/""",
    re.I,
)
REL_URL = re.compile(r"""url\((?P<q>['"]?)/(?P<path>hubfs|hs-fs)/""", re.I)


def fix_text(text: str) -> tuple[str, int]:
    n = 0

    def bad_sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return f"{CDN}/{m.group(1)}/"

    def rel_attr_sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return f"{m.group('attr')}{CDN}/{m.group('path')}/"

    def rel_url_sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return f"url({m.group('q')}{CDN}/{m.group('path')}/"

    text = BAD.sub(bad_sub, text)
    text = REL_ATTR.sub(rel_attr_sub, text)
    text = REL_URL.sub(rel_url_sub, text)
    return text, n


def count_bad(text: str) -> int:
    return len(BAD.findall(text)) + len(REL_ATTR.findall(text)) + len(REL_URL.findall(text))


def scan(root: Path) -> None:
    files = 0
    refs = 0
    samples = []
    for p in sorted(root.rglob("*.html")):
        if "node_modules" in p.parts:
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        c = count_bad(t)
        if c:
            files += 1
            refs += c
            if len(samples) < 20:
                samples.append(f"{c:5d} {p.relative_to(root)}")
    print(f"scan {root}: bad_files={files} bad_refs={refs}")
    for s in samples:
        print(s)


def fix(root: Path) -> None:
    changed = 0
    refs = 0
    for p in sorted(root.rglob("*.html")):
        if "node_modules" in p.parts:
            continue
        original = p.read_text(encoding="utf-8", errors="ignore")
        fixed, n = fix_text(original)
        if n:
            p.write_text(fixed, encoding="utf-8")
            changed += 1
            refs += n
            print(f"fixed {n:5d} {p.relative_to(root)}")
    print(f"DONE changed_files={changed} refs={refs}")


def main() -> None:
    cmd = sys.argv[1]
    root = Path(sys.argv[2]).resolve()
    if cmd == "scan":
        scan(root)
    elif cmd == "fix":
        fix(root)
        scan(root)
    else:
        raise SystemExit("usage: run_fix_deploy.py scan|fix ROOT")


if __name__ == "__main__":
    main()
