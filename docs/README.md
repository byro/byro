# Working on the byro documentation

The documentation is built with [Zensical](https://zensical.org/) from
Markdown sources: `docs/de/` and `docs/en/` are one source tree per language
with identical relative paths (German is the leading language, English is
complete as well), configured by `zensical.de.toml` and `zensical.en.toml`,
with dependencies pinned in `requirements-zensical.txt`. The contributor-facing
version of this page is `docs/<lang>/development/documentation.md`.

## Building the Zensical documentation

From the repository root:

```bash
python3 -m venv .venv-docs
source .venv-docs/bin/activate
pip install -r docs/requirements-zensical.txt

zensical build -f zensical.de.toml --strict   # -> docs/_build/zensical/de/
zensical build -f zensical.en.toml --strict   # -> docs/_build/zensical/en/
```

`--strict` turns warnings (broken links, missing anchors, missing snippet
files) into build failures; CI builds strict, so build strict locally too.

Live preview with automatic rebuilds:

```bash
zensical serve -f zensical.de.toml            # http://localhost:8000/
zensical serve -f zensical.en.toml
```

## Read the Docs and CI

Read the Docs runs `docs/rtd_build.py` (see `.readthedocs.yml`). The script
selects the language tree from `READTHEDOCS_LANGUAGE`, sets the canonical URL
from `READTHEDOCS_CANONICAL_URL` and copies the site to `$READTHEDOCS_OUTPUT/html/`.
Simulate it locally:

```bash
READTHEDOCS_LANGUAGE=de READTHEDOCS_OUTPUT=/tmp/rtd python docs/rtd_build.py
python docs/check_site.py /tmp/rtd/html
```

`docs/check_site.py` verifies that every local link, image and asset in a
built site exists; Zensical's strict mode does not check images.

The workflow `.github/workflows/docs.yml` runs on every pull request that
touches the documentation: the Read the Docs simulation for both languages,
the site check, an external link check with lychee over the Markdown sources,
and `codespell` over the English tree (words that codespell must accept go
into `docs/codespell-ignore.txt`). The German tree is not spellchecked by a
tool: codespell's dictionary is English and flags ordinary German words.

## Conventions established so far

- Images live inside the language tree (`docs/de/img/`, `docs/en/img/`),
  because Zensical only copies files below `docs_dir` and does not follow
  symlinked directories. Screenshots are language specific anyway (the UI is
  shown in that language); the logo is the only shared file and is kept as a
  copy in both trees.
- Zensical's strict mode catches broken links, missing anchors and missing
  snippet files, but not missing images. Check images with the link checker
  on the built HTML (set up in CI).
- Files from the repository (Compose files, example configuration) are
  included with snippets relative to the repository root, e.g.
  `--8<-- "deploy/byro.conf.example"`, instead of being copied into the docs.
  Snippet paths resolve relative to the directory the build runs in, so
  always build from the repository root.
- Zensical is pinned exactly in `requirements-zensical.txt`. Upgrading it is a
  deliberate change: bump the pin, rebuild both languages, review the output.
- The Python API reference (signals, the bank import errors) is generated
  with [mkdocstrings](https://mkdocstrings.github.io/) using static analysis
  (Griffe), not a Django import: no `DJANGO_SETTINGS_MODULE` is needed to
  build the docs. mkdocstrings depends on the `mkdocs` package itself even
  though Zensical does not use it; that transitive weight is accepted.
  `byro.common` has no `__init__.py`, unlike every other byro app, which
  blocks static analysis of `byro.common.signals`; that page documents those
  three signals by hand instead (see the note on the page and the product
  finding in the migration report).
  Dataclass field comments (`#:` above a field) are not extracted by Griffe
  either, so `ImportedBankTransaction`'s fields stay hand-written prose next
  to a generated, member-less class block.
