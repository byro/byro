# Ein Plugin erstellen

Du kannst byro über die offizielle Plugin-API mit eigenem Python-Code
erweitern, und vermutlich musst du das auch. Stell dir jedes Plugin als
eigenständige Django-„App“ in einem eigenen Python-Paket vor, das wie jedes
andere Python-Modul installiert wird.

Die Kommunikation zwischen byro und den Plugins läuft vor allem über Djangos
[Signal-Dispatcher](https://docs.djangoproject.com/en/dev/topics/signals/).
Die Kernmodule von byro stellen Signale für verschiedene Zwecke bereit. Ihre
Dokumentation findest du in der [Signalliste](../signals.md). Außerdem gibt es
Anleitungen für häufige Anwendungsfälle wie eigene Mitgliedsdaten oder den
Import und die Zuordnung von Zahlungen.

Um ein neues Plugin zu erstellen, lege ein neues Python-Paket an, das eine
gültige [Django-App](https://docs.djangoproject.com/en/dev/ref/applications/)
sein und die unten beschriebenen Plugin-Metadaten enthalten muss. Für jedes
Plugin braucht es etwas Boilerplate. Um dir Zeit zu sparen, haben wir eine
[cookiecutter](https://cookiecutter.readthedocs.io/en/latest/)-Vorlage, die
du so verwendest:

```console
(env)$ pip install cookiecutter
(env)$ cookiecutter https://github.com/byro/byro-plugin-cookiecutter
```

Das stellt dir ein paar Fragen und legt dann einen Projektordner für dein
Plugin an.

Die folgenden Seiten gehen auf die verschiedenen Plugin-Typen ein, die byro
unterstützt. Diese Anleitungen setzen nicht viel Wissen über byro voraus, aber
Vorkenntnisse in Django (View-Schicht, ORM usw.).

## Plugin-Metadaten

Die Plugin-Metadaten leben in einer Klasse `ByroPluginMeta` innerhalb der
Konfigurationsklasse deiner App. byro selbst liest daraus drei Attribute und
zeigt sie unverändert auf der Seite „Über byro“ (siehe
[Einstellungen](../../administration/settings.md#uber-byro)):

| Attribut    | Typ    | Beschreibung                                        |
|-------------|--------|-----------------------------------------------------|
| name        | string | Der lesbare Name deines Plugins                     |
| version     | string | Eine lesbare Versionsangabe deines Plugins          |
| description | string | Eine ausführlichere Beschreibung des Plugins        |

Zusätzlich liest byro `document_categories` (ein Dict von Kategorie-ID auf
lesbaren Namen), falls dein Plugin eigene Dokumentkategorien anbieten will
(siehe [Dokumente](../../usage/documents.md#kategorien)).

**`author` und `visible` sind reine Konvention** aus der Cookiecutter-Vorlage
unten – byro selbst liest oder wertet sie an keiner Stelle aus. Trag sie ein,
wenn es dir hilft, dein Plugin zu dokumentieren, aber erwarte keine Wirkung
in byro.

Ein funktionierendes Beispiel in `byro_irc/apps.py`:

```python
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class IRCApp(AppConfig):
    name = 'byro_irc'
    verbose_name = _("IRC")

    class ByroPluginMeta:
        name = _("IRC")
        version = '1.0.0'
        description = _("This plugin sends notifications via IRC.")
        # Konvention, nicht von byro ausgewertet:
        author = _("irclover")
        visible = True
```

Django findet die einzige `AppConfig`-Unterklasse in deinem Submodul `apps`
automatisch. Definiert das Modul mehr als eine `AppConfig`-Unterklasse,
markiere die, die byro verwenden soll, mit `default = True`. Die alte Variable
`default_app_config` hat seit Django 4.1 keine Wirkung mehr und sollte nicht
verwendet werden.

!!! warning
    byro registriert dein Plugin in `INSTALLED_APPS` über seinen bloßen
    Modulnamen. Liegt deine `AppConfig` nicht in `apps.py`, fällt Django auf
    eine einfache `AppConfig` ohne `ByroPluginMeta` zurück. byro startet ohne
    Fehler, ignoriert das Plugin aber stillschweigend: Seine URLs werden nicht
    eingebunden, es erscheint nicht auf der Plugin-Seite, seine
    Dokumentkategorien fehlen, und `ready()` läuft nie, sodass keiner seiner
    Signal-Receiver verbunden wird.

## Plugin-Registrierung

Irgendwie muss byro erfahren, dass dein Plugin existiert. Dafür nutzen wir den
[Entry-Point](https://packaging.python.org/en/latest/specifications/entry-points/)-Mechanismus.
Um ein Plugin in einem eigenen Python-Paket zu registrieren, sollte deine
`pyproject.toml` etwa Folgendes enthalten:

```toml
[project.entry-points."byro.plugin"]
byro_irc = "byro_irc:ByroPluginMeta"
```

byro wertet nur den Modulteil vor dem Doppelpunkt aus und fügt dieses Modul zu
`INSTALLED_APPS` hinzu; der Teil nach dem Doppelpunkt ist Konvention. Verwendet
dein Projekt noch eine `setup.py`, gehört derselbe Eintrag in deren Argument
`entry_points` unter der Gruppe `[byro.plugin]`.

Damit erkennt byro das Plugin automatisch, sobald du es installiert hast, z. B.
per `pip`. Während der Entwicklung installiere dein Plugin im Editable-Modus
mit `pip install -e .` im Quellverzeichnis des Plugins, damit es gefunden wird.

## In den Plugin-Katalog aufgenommen werden

Administratoren installieren Plugins mit `byroctl plugin add <kurzname>` aus
einem kleinen Katalog, den jedes byro-Release mitliefert (siehe
[Plugins](../../administration/plugins.md)). Damit dein Plugin gelistet wird:

* veröffentliche reguläre GitHub-Releases (oder Releases auf PyPI): byroctl
  installiert das aktuelle Release und pinnt den Commit, auf den sein Tag
  zeigt; ein bloßer Tag reicht also nicht, und ein verschobener Tag gilt als
  Integritätsfehler;
* erkläre die unterstützten byro-Versionen als Abhängigkeit, zum Beispiel
  `dependencies = ["byro>=2026.3"]`, damit eine inkompatible Kombination beim
  Bauen statt zur Laufzeit scheitert;
* lass die `AppConfig` in `apps.py` (siehe Warnung oben) und liefere deine
  Übersetzungen als `.po`-Dateien; der Image-Build kompiliert sie;
* eröffne einen Pull Request gegen `deploy/plugin-catalog.conf` im
  byro-Repository mit Kurzname, Anzeigename, Beschreibung, Paketname, Quelle
  und Repository deines Plugins (Maintainer: [byro veröffentlichen](../releasing.md)).

## Signale

byro definiert verschiedene Signale, auf die dein Plugin hören kann. Die
Details stehen in der [Signalliste](../signals.md). Wir empfehlen, deine
Signal-Receiver in ein Submodul `signals` deines Plugins zu legen. Erweitere
deine `AppConfig` in `apps.py` (siehe oben) um folgende Methode, damit die
Receiver verfügbar sind:

```python
class IRCApp(AppConfig):
    …

    def ready(self):
        from . import signals  # noqa
```

## Views

Dein Plugin darf eigene Views definieren. Legst du ein Submodul `urls` in dein
Plugin-Modul, importiert byro es automatisch und bindet es mit dem Namespace
`plugins:<label>:` in die Root-URL-Konfiguration ein, wobei `<label>` dein
Django-App-Label ist.

!!! warning
    Definierst du eigene URLs und Views, bist du bei der Berechtigungsprüfung
    auf dich gestellt. byro stellt sicher, dass du es mit einem
    authentifizierten Benutzer zu tun hast, aber nicht mehr.
