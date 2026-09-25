# byro veröffentlichen

Diese Seite ist für byro-Maintainer. Sie beschreibt, wie ein Release entsteht,
was die Release-Pipeline tut, und die zwei Pflichten, die mit dem
Deployment-Tooling einhergehen: den `stable`-Zeiger und die Release-Flags in
`deploy/release.env`.

## Wie ein Release entsteht

1. [Release Drafter](https://github.com/release-drafter/release-drafter) hält
   auf GitHub einen Release-Entwurf aktuell. Jeder gemergte Pull Request fügt
   eine Zeile unter der Kategorie seines Labels hinzu (`breaking-change`,
   `enhancement`, `bug`/`fix`, `maintenance`, `dependencies`,
   `documentation`). Der Drafter schlägt auch den nächsten Tag vor, aber nach
   Semantic-Versioning-Regeln: `breaking-change` erhöht das erste Feld,
   `enhancement` das zweite, alles andere das dritte. byros Schema ist
   `vYYYY.MINOR.PATCH`, prüfe den vorgeschlagenen Tag also und passe ihn bei
   Bedarf von Hand an: Das erste Feld ist immer das aktuelle Jahr, das erste
   Release eines Jahres ist `vYYYY.1.0`, und ein `breaking-change`-Label darf
   das Jahr nicht erhöhen.
2. Vor dem Veröffentlichen bearbeite den Entwurf: Schreibe die Einleitung (der
   Platzhalter oben) und geh die Checkliste am Ende dieser Seite durch.
3. Veröffentliche das Release. GitHub erzeugt den Tag, und der Tag startet die
   Release-Pipeline (`.github/workflows/ci-cd.yml`, Ereignis
   `release: published`):

    * Stilprüfungen und Testmatrix,
    * das Python-Paket, hochgeladen zu PyPI (Environment `pypi`),
    * das Container-Image `ghcr.io/byro/byro:vYYYY.M.P` für `linux/amd64` und
      `linux/arm64`, zusätzlich mit dem Tag `latest`,
    * und, erst nachdem beide Uploads erfolgreich waren, der `stable`-Zeiger
      (siehe unten).

    Der Lauf dauert etwa eine halbe Stunde; der Multi-Plattform-Image-Build ist
    der langsame Teil. Beobachte ihn unter *Actions*.

byro hat bisher keine Pre-Releases veröffentlicht. Markierst du ein Release als
*Pre-Release*, läuft die Pipeline trotzdem: Paket und Image werden
veröffentlicht, und das Image erhält auch den Tag `latest`, den das veraltete
`production/`-Setup ungepinnt zieht. Nur der `stable`-Zeiger wird nicht
bewegt. Wandelst du das Pre-Release später in ein Release um, läuft die
Pipeline nicht erneut (GitHub sendet `released`, nicht `published`); bewege
`stable` in diesem Fall von Hand mit dem Workflow *Stable pointer*.

## Der stable-Zeiger

Das byroctl-Bootstrap ([Installation mit byroctl](../installation/byroctl.md))
beginnt mit:

```console
$ bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)"
```

und `byroctl update --check` fragt an derselben Stelle, welches Release aktuell
ist. `stable` ist ein Branch dieses Repositorys mit genau drei Dateien, den nur
CI schreibt:

* `stable.env` mit einer Zeile `BYRO_RELEASE_VERSION=vYYYY.M.P`,
* `install.sh`, eine byteidentische Kopie von `deploy/install.sh` aus diesem
  Release-Tag,
* eine `README.md`, die den Branch erklärt.

Alles andere (byroctl, die Compose-Dateien, das Image) wird vom
unveränderlichen Release-Tag geholt; der Branch sagt also nur, *welches*
Release aktuell ist. Der Job *Point stable at the release* läuft als letzter
Schritt der Pipeline und ruft `.github/scripts/update-stable-branch.sh` über
den Workflow `.github/workflows/stable.yml` auf. Das Skript

* lehnt alles ab, was kein `vYYYY.M.P`-Tag ist,
* prüft, dass der Tag `deploy/install.sh` passend zu seiner `SHA256SUMS`
  enthält und dass das Image in der Registry existiert,
* vergleicht Versionen numerisch und bewegt den Zeiger nie eigenständig auf
  ein älteres Release (der Job endet dann grün mit einem Hinweis),
* hängt einen Commit an die Branch-Historie an und pusht ihn als Fast-Forward;
  der Branch wird nie force-gepusht.

`raw.githubusercontent.com` cacht Dateien ein paar Minuten, sodass Installer
bis zu etwa fünf Minuten nach dem Bewegen des Zeigers noch das vorherige
Release sehen können.

### Den Zeiger von Hand bewegen

Bearbeite oder pushe den Branch `stable` nicht direkt. Stellt sich ein Release
als defekt heraus, setze `stable` auf das vorherige Release zurück: *Actions* →
*Stable pointer* → *Run workflow*, Tag eingeben und *force* ankreuzen (ein
Wechsel auf ein älteres Release wird sonst verweigert). Behebe dann das Problem
und veröffentliche ein neues Release; die Pipeline bewegt den Zeiger wieder
vorwärts. Erwäge, die defekte Version auch auf PyPI zu yanken. Das Image-Tag
bleibt verfügbar, weil byroctl-Installationen das installierte Release pinnen.
byroctl macht kein Downgrade: Solange `stable` ein älteres Release nennt als das
installierte, brechen `byroctl update` und `byroctl update --check` auf dem
defekten Release mit einem Fehler ab, der beide Versionen nennt. Diese
Installationen warten auf das korrigierte Release und aktualisieren darauf
(`byroctl update --to vX.Y.Z`, bis `stable` dorthin gewandert ist).

Der Workflow pusht mit dem `GITHUB_TOKEN` des Repositorys. Ist `stable` durch
eine Branch-Protection-Regel oder ein Ruleset geschützt, braucht dieser
Automations-Akteur Push- oder Bypass-Rechte für den Branch. Menschen brauchen
sie nicht: Änderungen am Zeiger laufen über den Workflow, nie über einen
direkten Push.

## Release-Flags

`deploy/release.env` trägt zwei Flags, die `byroctl update` aus dem
*Ziel*-Release liest, bevor es irgendetwas ändert:

`BYRO_RELEASE_BREAKING=1`
:   Administratoren müssen die Release Notes lesen und das Update ausdrücklich
    bestätigen (`byroctl update` fragt, `--yes` bestätigt). Verwende es nur,
    wenn ein Administrator vor dem Update handeln oder entscheiden muss: eine
    Konfiguration, die sich ändern muss, ein Dienst, der wegfällt, ein
    manueller Schritt. Es ist kein Synonym für das Label `breaking-change`,
    das auch Code- und Plugin-API-Änderungen abdeckt, die von Administratoren
    nichts verlangen.

`BYRO_RELEASE_DATA_MIGRATION=1`
:   Das Release ändert Dateien außerhalb der Datenbank (Dokumente, Uploads,
    GnuPG-Home). Die reguläre Pre-Update-Sicherheitskopie deckt sie nicht ab,
    daher verweigert `byroctl update` den Fortgang, bis der Administrator mit
    `--data-safeguard-done` ein vollständiges Backup von `data/` bestätigt.

Beide Flags sind auf `main` `0`. Für ein Release, das eines braucht:

1. Setze im Pull Request, der das Release vorbereitet, das Flag auf `1`, führe
   `.github/scripts/deploy-checksums.sh --write` aus (`release.env` steht auf
   der Prüfsummenliste, die CI erzwingt) und schreibe den Abschnitt der
   Release Notes, der erklärt, was Administratoren tun müssen.
2. Veröffentliche das Release. Das Flag ist Teil des Tags, und byroctl liest es
   dort.
3. Eröffne direkt danach einen Pull Request, der das Flag auf `0` zurücksetzt,
   wieder mit neu erzeugter `SHA256SUMS`.

Die CI-Prüfung *[Deploy] release flags* (Workflow `release-flags.yml`, jeder
Push auf `main` und jeder Pull Request) erzwingt das Format der Datei (jedes
Flag genau einmal, nur `0` oder `1`, nichts sonst) und erinnert an Schritt 3:
Auf `main` schlägt sie fehl, solange ein Flag `1` ist, der jüngste Release-Tag
es mit `1` ausgeliefert hat und kein Commit seit diesem Release die Zeile des
Flags geändert hat; in Pull Requests warnt sie nur. Diese rote Phase zwischen
Veröffentlichung und Reset-Pull-Request ist beabsichtigt.

byroctl liest die Flags des Release, auf das es aktualisiert, sonst nichts. Eine
Installation, die ein geflaggtes Release überspringt (von `v2026.2.0` direkt
auf `v2026.4.0`, wenn `v2026.3.0` `BYRO_RELEASE_DATA_MIGRATION=1` trug), wird
von diesem Flag nicht gestoppt, obwohl die Migration trotzdem läuft. Setzt du
ein Flag, sag Administratoren in den Release Notes der folgenden Releases, was
diejenigen tun müssen, die das geflaggte Release übersprungen haben. Tagge
keinen Hotfix von `main`, solange ein Flag noch `1` ist, es sei denn, der
Hotfix braucht es ebenfalls.

## Plugin-Katalog

`deploy/plugin-catalog.conf` ist die Liste der Plugins, die
`byroctl plugin add <kurzname>` kennt. Sie ist ein Release-Artefakt wie die
Compose-Dateien: mit dem Release versioniert, in `deploy/SHA256SUMS` gelistet,
von byroctl geladen und geprüft. Sie enthält **nur Metadaten**, keine
Versionen:

```ini
[finance-import-bank-files]
name=Bank file importers
description=Imports file-based bank statements
package=byro-finance-import-bank-files
source=github
repo=https://github.com/byro/byro-finance-import-bank-files
```

byroctl ermittelt die Version, wenn ein Administrator das Plugin hinzufügt oder
aktualisiert: bei `source=github` das aktuelle reguläre GitHub-Release von
`repo`, installiert vom Commit, auf den sein Tag zeigt; bei `source=pypi` das
aktuelle Release auf PyPI. Ein neues Plugin-Release braucht also keine Änderung
in diesem Repository. Ob ein Plugin-Release mit einem byro-Release
funktioniert, erklärt das Plugin selbst (`dependencies = ["byro>=2026.3"]` in
seiner `pyproject.toml`); der Image-Build prüft das gegen das installierte
byro.

Um ein Plugin aufzunehmen:

1. Das Plugin muss einen `byro.plugin`-Entry-Point, eine `apps.py` mit
   `ByroPluginMeta` und mindestens ein reguläres GitHub-Release (oder ein
   Release auf PyPI) haben. Ohne Release scheitert `byroctl plugin add` mit
   einer klaren Meldung.
2. Füge einen Abschnitt mit den fünf Schlüsseln oben hinzu. Abschnittsnamen
   bestehen aus Kleinbuchstaben, Ziffern und Bindestrichen; `repo` ist
   `https://github.com/<owner>/<repo>` für GitHub-Plugins.
3. Führe `.github/scripts/check-plugin-catalog.sh` und
   `.github/scripts/deploy-checksums.sh --write` aus; beides erzwingt CI (Job
   *[Deploy] shellcheck, checksums, bats*).

In den Katalog gehören nur Plugins, die mit dem aktuellen byro-Release
funktionieren. Kandidaten, die noch Arbeit brauchen, werden als Issues
verfolgt, nicht als auskommentierte Einträge.

## Hinweise für Administratoren

Die Pipeline veröffentlicht das Release, aber nur du kannst Administratoren
sagen, was zu tun ist. Prüfe vor dem Veröffentlichen:

* Ändert das Release Konfigurationsoptionen, die Compose-Dateien oder das
  Verhalten des Images? Beschreibe die Schritte für byroctl-Nutzer
  (`byroctl update` kümmert sich um neue Optionen und Compose-Dateien), für
  `docker compose`-Nutzer und für Bare-Metal-Installationen
  (`pip install -U byro`, `migrate`, `rebuild`, Neustart).
* Nutzer des veralteten `production/`-Setups ziehen `ghcr.io/byro/byro:latest`
  und bekommen das neue Image ohne Pinning. Erwähne alles, was sie betrifft,
  und verweise auf `production/DEPRECATED.md`.

Das erste Release, das `deploy/` ausliefert, verdient einen eigenen Abschnitt
für `production/`-Nutzer, weil das veröffentlichte Image zum ersten Mal sein
Standardverhalten ändert. Es braucht kein `BYRO_RELEASE_BREAKING=1`: Es gibt
noch keine byroctl-Installation, die das Flag lesen könnte.

## Checkliste

Vor dem Veröffentlichen:

* der Entwurf ist geprüft, die Einleitung geschrieben, die Kategorien sind
  vollständig,
* `deploy/release.env` hat die Flags, die dieses Release braucht, und die
  Release Notes erklären sie,
* die Release Notes sagen Administratoren, was zu tun ist,
* `deploy/plugin-catalog.conf` listet nur Plugins, die mit diesem Release
  funktionieren, und der Katalog-Lint ist grün,
* `main` ist grün; ist *[Deploy] release flags* rot, wurde das vorherige Flag
  noch nicht zurückgesetzt, erledige das zuerst.

Nach dem Veröffentlichen:

* der Pipeline-Lauf ist grün, einschließlich *Point stable at the release*,
* `stable` nennt das neue Release (`stable.env` auf dem Branch),
* ein gesetztes Flag ist in einem Folge-Pull-Request auf `0` zurückgesetzt.
