# Working on the documentation

You have found something to improve in our documentation? Great! We'll assume
that you have already forked and cloned byro as detailed in the
[contributing documentation](contributing.md). For the following steps, you'll
need to have Python 3 installed on your system.

The documentation is built with [Zensical](https://zensical.org/) from Markdown
files. There is one source tree per language with identical file names:
`docs/de/` (German, the leading language) and `docs/en/` (English). Every page
exists in both trees.

## Building the documentation

Start out in a shell in the repository root. Create a virtual environment and
install the pinned documentation dependencies:

```console
$ python3 -m venv .venv-docs
$ source .venv-docs/bin/activate
$ pip install -r docs/requirements-zensical.txt
```

Build one language (the result lands in `docs/_build/zensical/<lang>/`):

```console
$ zensical build -f zensical.de.toml --strict
$ zensical build -f zensical.en.toml --strict
```

`--strict` turns broken links, missing anchors and missing snippet files into
build failures. CI builds strict, so build strict locally too.

For a live preview that rebuilds on every change, run one of

```console
$ zensical serve -f zensical.de.toml
$ zensical serve -f zensical.en.toml
```

and open <http://localhost:8000/>.

## Writing documentation

Find the page you want to adjust in `docs/de/` and `docs/en/` (or create it in
both trees), make your changes and check the result in the preview. Add new
pages to the `nav` list in both `zensical.de.toml` and `zensical.en.toml`.

Conventions:

- Images live inside the language tree (`docs/<lang>/img/`).
- Files from the repository, for example Compose files or the example
  configuration, are included with a snippet instead of being copied:
  ` --8<-- "deploy/byro.conf.example" ` inside a code block.
- The German and English trees must contain the same files. If you cannot
  write the other language, say so in your pull request.

How a page should be written — target audiences, terminology, tone,
Diátaxis, front matter, headings, links, admonitions, code examples,
screenshots, version and deprecation notices, license and a review checklist
— is in the "Editorial standard" section of `docs/README.md` in the
repository; the tooling is also described there in more detail.

## Checking documentation

Every pull request that touches the documentation runs the checks in
`.github/workflows/docs.yml`: a check that `docs/de` and `docs/en` cover the
same pages (`python docs/check_parity.py`), a strict build of both languages
as Read the Docs would run it, a check of all local links and images in the
built site (`python docs/check_site.py`), an external link check and a spell
check of the English tree with `codespell`. Words that codespell must accept,
for example product names, go into `docs/codespell-ignore.txt`.
