#!/usr/bin/env python3
"""Check a built documentation site for broken local references.

Zensical's strict mode validates Markdown links and anchors, but not images,
stylesheets or other assets. This script walks the generated HTML and verifies
that every relative ``href``/``src`` points to an existing file (a directory
counts when it contains ``index.html``). External URLs are left to the link
checker in CI.

    python docs/check_site.py docs/_build/zensical/de docs/_build/zensical/en
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ATTRIBUTES = {"href", "src", "poster", "data"}
SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "data:", "javascript:")


class ReferenceCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ATTRIBUTES and value:
                self.references.append(value)


CANONICAL = re.compile(r'<link rel="canonical" href="([^"]+)"')


def url_prefix(site: Path) -> str:
    """Path under which the site is served, taken from the canonical link of index.html.

    Zensical writes absolute URLs (for example in 404.html) below the path of
    ``site_url``; that prefix has to be stripped before resolving them locally.
    """
    index = site / "index.html"
    if index.is_file():
        match = CANONICAL.search(index.read_text(encoding="utf-8", errors="replace"))
        if match:
            return urlsplit(match.group(1)).path.rstrip("/") + "/"
    return "/"


def check_page(page: Path, site: Path, prefix: str) -> list[str]:
    parser = ReferenceCollector()
    parser.feed(page.read_text(encoding="utf-8", errors="replace"))
    problems = []
    for reference in parser.references:
        if reference.startswith(SKIP_SCHEMES) or reference.startswith("//"):
            continue
        path = unquote(urlsplit(reference).path)
        if not path or path.startswith("#"):
            continue
        if path.startswith("/"):
            if not path.startswith(prefix):
                problems.append(f"{page.relative_to(site)}: outside site prefix {reference}")
                continue
            target = site / path[len(prefix):]
        else:
            target = page.parent / path
        try:
            target = target.resolve()
        except OSError:
            problems.append(f"{page.relative_to(site)}: unresolvable {reference}")
            continue
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            problems.append(f"{page.relative_to(site)}: missing {reference}")
    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    failures = 0
    for site_arg in argv:
        site = Path(site_arg).resolve()
        pages = sorted(site.rglob("*.html"))
        if not pages:
            print(f"{site}: no HTML pages found")
            failures += 1
            continue
        prefix = url_prefix(site)
        problems = [p for page in pages for p in check_page(page, site, prefix)]
        for problem in problems:
            print(problem)
        print(f"{site}: {len(pages)} pages under {prefix}, {len(problems)} broken local references")
        failures += bool(problems)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
