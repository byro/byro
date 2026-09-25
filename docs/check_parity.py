#!/usr/bin/env python3
"""Check that docs/de and docs/en contain the same set of Markdown pages.

German and English are two file trees with identical relative paths (see
docs/README.md). This script is the simple, dependency-free check for that
invariant: it does not compare content or translation quality, only that
every page exists on both sides. Run from the repository root:

    python docs/check_parity.py
"""

from __future__ import annotations

import sys
from pathlib import Path

LANGUAGES = ("de", "en")


def markdown_pages(root: Path) -> set[str]:
    return {str(path.relative_to(root)) for path in root.rglob("*.md")}


def main(argv: list[str]) -> int:
    docs_root = Path(argv[0]) if argv else Path(__file__).resolve().parent
    pages = {language: markdown_pages(docs_root / language) for language in LANGUAGES}
    missing_in_en = sorted(pages["de"] - pages["en"])
    missing_in_de = sorted(pages["en"] - pages["de"])
    for page in missing_in_en:
        print(f"docs/en/{page}: missing (present in docs/de)")
    for page in missing_in_de:
        print(f"docs/de/{page}: missing (present in docs/en)")
    total = len(pages["de"] | pages["en"])
    mismatches = len(missing_in_en) + len(missing_in_de)
    print(f"{total} distinct pages, {mismatches} missing on one side")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
