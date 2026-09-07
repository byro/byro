# Entwicklungs-Setup

Um an byro mitzuarbeiten, ist es nützlich, byro lokal auf deinem Rechner zu
betreiben und Änderungen dort zu testen. Zuerst musst du einige Pakete auf
deinem Betriebssystem installieren.

Wenn du byro auf einem Server für den echten Einsatz installieren willst, geh
stattdessen zur [Installationsdokumentation](../installation/index.md).

Stelle sicher, dass folgende Abhängigkeiten installiert sind:

| Werkzeug                          | Debian-Paket     |
|-----------------------------------|------------------|
| Python 3.12 oder neuer            |                  |
| pip für Python 3                  | `python3-pip`    |
| `python-dev` für Python 3         | `python3-dev`    |
| `python-venv`, falls nicht enthalten | `python3-venv` |
| libffi                            | `libffi-dev`     |
| gettext                           | `gettext`        |
| git                               | `git`            |
| libmagic                          |                  |
| libjpeg                           |                  |

libjpeg lässt sich durch jede andere von
[pillow](https://pillow.readthedocs.io/en/latest/installation/basic-installation.html#basic-installation)
unterstützte Bibliothek ersetzen (für [qrcode](https://pypi.org/project/qrcode/)).

Manche Python-Abhängigkeiten brauchen bei der Installation einen Compiler; das
Debian-Paket `build-essential` oder etwas Vergleichbares sollte genügen.

## Quellcode beschaffen

Klone unser git-Repository:

```console
$ git clone https://github.com/byro/byro.git
$ cd byro/
```

## Deine lokale Python-Umgebung

Prüfe mit `python -V` oder `python3 -V`, dass Python 3.x installiert ist, und
mit `pip3 -V`, dass pip für Python 3 vorhanden ist. Lege dann mit Pythons
Bordmitteln (Ubuntu-Paket `python3-venv`) eine virtuelle Umgebung an und
aktiviere sie für die aktuelle Sitzung:

```console
$ python3 -m venv env  # oder virtualenv -p /usr/bin/python3 env, oder ...
$ source env/bin/activate
```

Dein Shell-Prompt sollte jetzt ein `(env)` vorangestellt haben. Das musst du in
jeder Shell tun, in der du mit byro arbeitest (oder deine Shell entsprechend
konfigurieren). Unter Ubuntu oder Debian empfehlen wir dringend, `pip` und
`setuptools` in der virtuellen Umgebung zu aktualisieren, sonst können manche
Abhängigkeiten fehlschlagen:

```console
(env)$ pip3 install -U pip setuptools wheel
```

## Mit dem Code arbeiten

Zuerst brauchst du alle Abhängigkeiten der Hauptanwendung:

```console
(env)$ cd src/
(env)$ pip3 install -e .
```

Um Code-Checks und Unit-Tests ausführen zu können, installiere auch die
Entwicklungsabhängigkeiten:

```console
(env)$ pip3 install -e ".[dev]"
```

!!! note
    Unter Windows: Bei der Fehlermeldung
    `failed to find libmagic.  Check your installation` installiere mit
    `pip install python-magic-bin` in der virtuellen Umgebung die nötige
    magic-Bibliothek für Windows.

!!! note
    Unter macOS: Bei der Fehlermeldung
    `failed to find libmagic.  Check your installation` installiere die
    Bibliothek mit `brew install libmagic`.

Lege eine Datei `byro.cfg` mit diesem Inhalt an:

```ini
[database]
engine = sqlite3
```

Brauchst du eigene Datenbank- oder andere Einstellungen, gib sie stattdessen so
an:

```ini
[database]
name = byro
user = byro
password = byro
host = localhost
port = 5432
```

Die Standard- und empfohlene Produktivinstallation verwendet PostgreSQL; für
die lokale Entwicklung reicht SQLite.

Lege dann die lokale Datenbank an:

```console
(env)$ python manage.py migrate
```

Um dich anmelden zu können, lege außerdem einen Admin-Benutzer an:

```console
(env)$ python manage.py createsuperuser
```

Willst du byro in einer anderen Sprache als Englisch sehen, kompiliere die
Sprachdateien:

```console
(env)$ python manage.py compilemessages
```

### Entwicklungsserver starten

Den lokalen Entwicklungsserver startest du mit:

```console
(env)$ python manage.py runserver
```

Öffne <http://localhost:8000/> im Browser – du solltest dich anmelden und
herumprobieren können! Beispieldaten erzeugst du mit:

```console
(env)$ python manage.py make_testdata
```

### Code-Checks und Unit-Tests

Bevor du Code in git eincheckst, führe immer die statischen Prüfungen und
Unit-Tests aus:

```console
(env)$ isort .
(env)$ black .
(env)$ flake8 .
(env)$ djhtml byro/
(env)$ python manage.py check --deploy
(env)$ python -m pytest tests
```

CI führt dieselben Prüfungen aus, aber ohne automatisch zu formatieren:
`isort -c .` und `black --check .` (nur prüfen, nicht schreiben), außerdem
parallelisiert und mit automatischen Wiederholungen bei geflakten Tests:
`python -m pytest --reruns=3 -nauto -p no:sugar --maxfail=100 tests`. Lies
`.github/workflows/ci-cd.yml`, wenn du die exakten CI-Kommandos brauchst.

!!! note
    Hast du mehr als einen CPU-Kern und willst die Testsuite beschleunigen,
    verwende `python -m pytest -n auto tests` (`pytest-xdist` ist bereits Teil
    der Entwicklungsabhängigkeiten).

Es empfiehlt sich, die Stilprüfungen in den git-Hook `.git/hooks/pre-commit`
zu legen, zum Beispiel:

```sh
#!/bin/sh
set -e
cd $GIT_DIR/../src
source ../env/bin/activate
isort .
black .
flake8 .
djhtml byro/
```

### Mit Übersetzungen arbeiten

Willst du neue Strings übersetzen, die das Übersetzungssystem noch nicht kennt,
durchsuche den Quellcode nach zu übersetzenden Strings und aktualisiere die
`*.po`-Dateien:

```console
(env)$ python manage.py makemessages
```

Um byro in deiner Sprache zu sehen, kompiliere die `*.po`-Dateien in ihre
optimierten binären `*.mo`-Gegenstücke:

```console
(env)$ python manage.py compilemessages
```

### Nächste Schritte

Um an byro mitzuwirken, lies die [Hinweise zum Mitwirken](contributing.md).

Willst du die Dokumentation verbessern, geh zu
[An der Dokumentation arbeiten](documentation.md).

Willst du an Plugins arbeiten, geh zu den
[Plugin-Anleitungen](plugins/index.md).
