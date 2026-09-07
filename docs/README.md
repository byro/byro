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
`docs/check_parity.py docs` verifies that `docs/de` and `docs/en` contain the
same set of Markdown pages (not their content or translation quality) — the
simple, maintainable substitute for a translation-status tool.

The workflow `.github/workflows/docs.yml` runs on every pull request that
touches the documentation: the page-parity check, the Read the Docs
simulation for both languages, the site check, an external link check with
lychee over the Markdown sources, and `codespell` over the English tree
(words that codespell must accept go into `docs/codespell-ignore.txt`). The
German tree is not spellchecked by a tool: codespell's dictionary is English
and flags ordinary German words.

## Editorial standard

This section is the writing standard for anyone adding or changing a page,
including future contributors who did not work on the Zensical migration.

**Source of truth.** The running code (`src/`, `deploy/`) is authoritative,
not old documentation, issues or previous releases. If you find a page that
contradicts the code, fix the page or, if you are unsure which is right, leave
a short HTML comment `<!-- migration note (...): ... -->` next to the
paragraph and mention it in your pull request rather than guessing. Several
such notes already exist from the Sphinx migration (see
`grep -rn "migration note" docs/de docs/en`); remove one once the page it
annotates is rewritten with real content, do not carry it forward.

**Audience and structure.** The navigation has seven top-level tabs
(Zensical's `navigation.tabs`), aimed at a role each, in this order:
*Getting started* (the start page, a single page); *Installation* (the three
installation methods only — byroctl, Docker Compose, bare metal); *Administration*
(day-2 server operation regardless of install method: updating, backup/restore,
management commands, monitoring/troubleshooting, security baseline);
*Configuration* (what you set up *inside* byro through the Office — users/login,
MFA, PGP, settings — plus the `byro.cfg`/`BYRO_*` configuration reference);
*User guide* (day-to-day work in a running byro, split into *Member
management*, *Finance*, *Member area* and *My account*); *Plugins* (which
plugins exist, and how to build one); and *Development & API* (developing
byro itself). Pick the page for the role doing the task, not the page that
already exists and is closest. Describe one topic in one place; link to it
from other pages instead of repeating it (an install method's own update
procedure is not a repeat, since the steps differ per method — a concept like
"what a plugin is" would be).

Every tab's own tree renders in the sidebar as a nested group
(`navigation.sections`) named after the tab itself, so even a single-topic
tab like *Installation* or *Administration* gets a bold sidebar heading
instead of a bare page list. Where a group's first entry is a bare page path
(not a `{Label = path}` table) whose own `#`-heading matches the group name,
`navigation.indexes` also makes that heading clickable to the page (for
example *Plugins* → *Plugin-Entwicklung*, or *Benutzerhandbuch* →
*Finanzen*/*Mein Konto*); a group with no matching landing page (*Mitgliederverwaltung*,
*Mitgliederbereich*) stays a plain, non-clickable bold label, which is normal
Material/mkdocs behaviour for a section without an index page.

Installation, Administration and Configuration look similar (all three are
"for administrators"), but split on three different axes: Installation is
about first getting a byro instance running — a page whose steps depend on
byroctl vs. Docker Compose vs. bare metal belongs there. Administration is
about keeping an already-running instance alive — update, backup, monitoring
— regardless of which of the three installation methods was used. Configuration
is about what happens *inside* byro through the Office UI (or the `byro.cfg`
file/`BYRO_*` variables that back it), regardless of how or where byro is
hosted. A page that would answer the same way no matter who's hosting the
instance belongs in Configuration, not Installation or Administration. Plugins
and Development & API split similarly: Plugins is about using and choosing
plugins, and about building one yourself; Development & API is about working
on byro's own core (setup, contributing, releasing, signals, the REST API).

**Diátaxis, applied quietly.** Within a page, keep tutorial ("do this to
learn"), how-to ("do this to get a result"), reference ("look this up
precisely") and explanation ("understand why") separate paragraphs or
sections rather than mixing them, but do not create top-level `tutorials/`,
`how-to/` etc. folders or force every page into exactly one category — most
pages combine a short explanation with a how-to or a reference table, which is
fine as long as each part stays internally consistent.

**Language and tone.** German is the leading language; every page exists in
both `docs/de/` and `docs/en/` at the identical relative path (checked by
`docs/check_parity.py`, see below). German uses the informal second-person
address, not the formal register, matching the tone already used throughout
`docs/de/` (imperative "Scanne den QR-Code…"). English uses plain, direct
address ("you"). Both languages: short sentences, active voice, no marketing
language.

**Terminology.** Use these terms consistently and do not introduce synonyms
for them: *Mitglied*/member (a `Member` in byro, not "user" unless you mean a
backend login), *Office*/Office (the backend UI at `/office/`, sometimes
"Backend" in German text — pick one per page), *Plugin* (never
"extension"/"Erweiterung"), *Instanz*/instance (a running deployment of
byro), *byroctl* (lowercase, the CLI tool, not "byro-ctl" or "ByroCtl").
Product name is always lowercase "byro", including at the start of a
sentence.

**Translation workflow.** New content is written in German first (the leading
language) and translated into English in the same pull request; both files
change together, at the same relative path. Do not introduce a
gettext/PO-based translation pipeline — file-based, human-reviewed
translation is the deliberate choice for this project (see the masterplan).
If you cannot write both languages, say so explicitly in your pull request
and ask for help with the other one; do not merge a page that exists in only
one language, `docs/check_parity.py` (wired into
`.github/workflows/docs.yml`) fails the build in that case.

**Front matter and titles.** Pages have no YAML front matter. The page title
is the first-level heading (`# Title`); Zensical uses it for the page's
`<title>` and for auto-generated cross references. The visible navigation
label is set separately in the `nav` table of `zensical.de.toml` and
`zensical.en.toml` (localized per language) and does not have to match the
heading word for word.

**Headings.** Exactly one `#` per page. Use `##` for the page's main
sections and `###`/`####` sparingly below that; do not skip a level. Headings
are also anchor targets other pages may link to — avoid renaming a heading
that is linked from elsewhere without checking `docs/check_site.py` output
and other pages' links.

**Links.** Link to other pages with a relative Markdown link to the `.md`
file (`[Configuration](../configuration/index.md)`), not an absolute URL;
Zensical resolves and validates these in strict mode
(`invalid_links`/`invalid_link_anchors`) and rewrites them to the built HTML
paths. Link to a heading with `#anchor-slug`. Only link to
`https://byro.readthedocs.io/...` for a target outside the docs build (for
example from `README.rst`).

**Admonitions.** Use `!!! note`, `!!! warning` and `!!! info` (in that
order of frequency; see any existing page for the syntax) and nothing else,
unless a page has a genuine need for a collapsible aside (`pymdownx.details`,
`??? note`) or tabbed content for per-platform instructions
(`pymdownx.tabbed`) — both extensions are enabled but rarely needed. `warning`
is for data loss, security or irreversible actions; `note` for a caveat;
`info` for a cross-reference or "good to know". Do not use admonitions for
ordinary paragraphs.

**Code examples.** Fence every code block with a language
(` ```console `, ` ```ini `, ` ```python `, …) so highlighting and copy
buttons work. Prefer a real, runnable example over a placeholder; if a value
must be replaced by the reader, use a name that makes that obvious
(`your-domain.example`, not `xyz`). Include real files from the repository
with a snippet instead of pasting a copy that will drift:
` --8<-- "deploy/byro.conf.example" `; the path resolves relative to the
repository root, so always build from there (`pymdownx.snippets.base_path =
["."]`).

**Screenshots.** Sparse by design (masterplan decision): only where a reader
genuinely cannot orient themselves from text, never one screenshot per click.
Screenshots are language-specific (the UI shown is in that language) and live
inside the language tree, `docs/<lang>/img/screenshots/`; there is no shared
screenshot pool. Every image needs descriptive alt text
(`![byro's member list, filtered by...](...)`), not the file name or "image
of...". The exception is `docs/en/img/screenshots/office_dashboard.png`,
embedded by `README.rst` at the repository root via a raw GitHub URL; it is
not part of either language tree's page content and has no German
counterpart.

**Version and deprecation notices.** There is no automated "added in
version X" tagging. Note a version-specific behavior in prose
(`Since v2026.1.0, ...`) only where the code or changelog confirms the
version; when unsure, describe current behavior without a version claim.
Mark a deprecated feature's page both in its navigation label
(`"Legacy: production/ (deprecated)"` in the `nav` tables) and with a
`!!! warning` at the top of the page stating what to use instead and, if
known, when the feature will be removed (see
`installation/legacy-production.md` for the pattern).

**License.** New documentation text is CC BY-SA 4.0, alongside the
AGPL-3.0-only code; see the [LICENSE](https://github.com/byro/byro/blob/main/LICENSE)
file for the full history, including Apache-2.0-licensed older contributions.
State the documentation's license once, on the start page and in
`development/contributing.md` — do not repeat a license notice on every page.
Do not carry over pre-CC-BY-SA-4.0 wording verbatim unless you have checked
`feature/features/documentation-rework/migration/LICENSE_REVIEW.md` (or its
successor once that review is folded into the repository) that the rights for
it are secured; otherwise rewrite the passage from the code and known facts.

**Review checklist.** Before opening a pull request that touches `docs/`:

- [ ] The page (or its change) exists at the same relative path in both
      `docs/de/` and `docs/en/`.
- [ ] `zensical build -f zensical.de.toml --strict` and
      `... zensical.en.toml --strict` both exit 0.
- [ ] `python docs/check_site.py docs/_build/zensical/de docs/_build/zensical/en`
      reports 0 broken references, and any new image renders (strict mode
      does not check images).
- [ ] `python docs/check_parity.py docs` exits 0.
- [ ] `codespell --ignore-words docs/codespell-ignore.txt docs/en docs/README.md`
      is clean for English changes (German is not spell-checked by tooling).
- [ ] New or changed content follows this standard: terminology, tone,
      heading levels, admonition choice, alt text on images, no repeated
      license notice, no leftover migration-note comment for content you just
      rewrote.
- [ ] A page you moved or removed has an entry in
      `feature/features/documentation-rework/migration/url-map.csv` (until
      that migration bookkeeping is retired after cutover).

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
- The `nav` tree in `zensical.de.toml`/`zensical.en.toml` is independent of
  the file layout under `docs/de/`/`docs/en/`: a page's directory does not
  have to match which top-level tab it appears under, and moving a page
  between tabs is a `nav` edit, not a file move (no broken links, no new
  URL). This is used deliberately: every page physically under
  `administration/` is split across three different tabs by topic, not by
  directory — `updating.md`, `backup-restore.md`, `management-commands.md`,
  `troubleshooting.md`, `security-baseline.md` (plus a new landing page,
  `operations.md`) live under the *Administration* tab; `users-and-login.md`,
  `mfa.md`, `pgp.md`, `settings.md` (plus the existing `index.md` and
  `configuration/index.md`, physically outside `administration/`) live under
  *Configuration*; `plugins.md` lives under *Plugins* together with
  `development/plugins/index.md` and its subpages, even though those are
  physically under `development/`, not `administration/`. Only rename a
  directory or file when the page's own topic changes, not to make it match
  its current tab.
- Every top-level tab wraps its own page tree in one nested `nav` group named
  after the tab (for example `{ "Plugins" = [ { "Plugins" = [...] }, {
  "Plugin-Entwicklung" = [...] } ] }`), so the sidebar always shows a bold
  section heading, even for a tab with only one topic. A group's first entry
  can be a bare page path instead of a `{Label = path}` table; if that page's
  `#`-heading matches the group name exactly, `navigation.indexes` turns the
  otherwise plain heading into a link to that page (`development/plugins/index.md`'s
  `# Plugin-Entwicklung` heading against the `"Plugin-Entwicklung"` group, or
  `usage/finances.md`'s `# Finanzen` against the `"Finanzen"` group). Don't use
  a bare first entry unless the heading text matches the group label exactly —
  otherwise the sidebar shows the wrong label for that heading.
