# An der Dokumentation arbeiten

Du hast etwas in unserer Dokumentation gefunden, das besser werden kann?
Großartig! Wir gehen davon aus, dass du byro bereits geforkt und geklont hast,
wie in den [Hinweisen zum Mitwirken](contributing.md) beschrieben. Für die
folgenden Schritte brauchst du Python 3 auf deinem System.

Die Dokumentation wird mit [Zensical](https://zensical.org/) aus
Markdown-Dateien gebaut. Es gibt einen Quellbaum je Sprache mit identischen
Dateinamen: `docs/de/` (Deutsch, die führende Sprache) und `docs/en/`
(Englisch). Jede Seite existiert in beiden Bäumen.

## Dokumentation bauen

Beginne in einer Shell im Wurzelverzeichnis des Repositorys. Lege eine
virtuelle Umgebung an und installiere die gepinnten Doku-Abhängigkeiten:

```console
$ python3 -m venv .venv-docs
$ source .venv-docs/bin/activate
$ pip install -r docs/requirements-zensical.txt
```

Baue eine Sprache (das Ergebnis landet in `docs/_build/zensical/<lang>/`):

```console
$ zensical build -f zensical.de.toml --strict
$ zensical build -f zensical.en.toml --strict
```

`--strict` macht aus kaputten Links, fehlenden Ankern und fehlenden
Snippet-Dateien Build-Fehler. CI baut strict, also baue auch lokal strict.

Für eine Live-Vorschau, die bei jeder Änderung neu baut, starte eines von

```console
$ zensical serve -f zensical.de.toml
$ zensical serve -f zensical.en.toml
```

und öffne <http://localhost:8000/>.

## Dokumentation schreiben

Finde die Seite, die du anpassen willst, in `docs/de/` und `docs/en/` (oder
lege sie in beiden Bäumen an), ändere sie und prüfe das Ergebnis in der
Vorschau. Neue Seiten trägst du in die `nav`-Liste sowohl in
`zensical.de.toml` als auch in `zensical.en.toml` ein.

Konventionen:

- Bilder liegen im Sprachbaum (`docs/<lang>/img/`).
- Dateien aus dem Repository, etwa Compose-Dateien oder die
  Beispielkonfiguration, werden per Snippet eingebunden statt kopiert:
  ` --8<-- "deploy/byro.conf.example" ` in einem Codeblock.
- Der deutsche und der englische Baum müssen dieselben Dateien enthalten. Kannst
  du die andere Sprache nicht schreiben, sag das in deinem Pull Request.

`docs/README.md` im Repository beschreibt das Tooling ausführlicher.

## Dokumentation prüfen

Jeder Pull Request, der die Dokumentation berührt, durchläuft die Prüfungen in
`.github/workflows/docs.yml`: einen strict Build beider Sprachen so, wie Read
the Docs ihn ausführt, eine Prüfung aller lokalen Links und Bilder in der
gebauten Site (`python docs/check_site.py`), eine Prüfung externer Links und
eine Rechtschreibprüfung des englischen Baums mit `codespell`. Wörter, die
codespell akzeptieren muss, etwa Produktnamen, gehören in
`docs/codespell-ignore.txt`.
