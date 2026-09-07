# Plugins

byro lässt sich mit Plugins erweitern: Python-Pakete, die sich bei byro
registrieren und Importer, Mitgliedsdaten, Dokumente oder ganze Funktionen
hinzufügen (wie sie geschrieben werden, steht in der
[Entwicklerdokumentation](../development/plugins/creating-a-plugin.md)). Ein
Plugin läuft mit denselben Rechten wie byro selbst und hat vollen Zugriff auf
deine Datenbank, installiere also nur Plugins, denen du vertraust.

Diese Seite beschreibt Plugins in einer byroctl-Installation. Die Abschnitte
am Ende behandeln das manuelle Docker-Compose-Setup und die
Bare-Metal-Installation. Andere Integrationen (SMTP-Mailversand, OIDC/SSO)
sind kein Plugin-Mechanismus und stehen bei
[Konfiguration](../configuration/index.md) beziehungsweise
[Benutzer und Login](users-and-login.md).

## Offizielle Plugins

**Mitgeliefert** (jede byro-Installation, nicht einzeln installierbar oder
entfernbar): `byro.plugins.profile` (zusätzliche persönliche Mitgliedsdaten
wie Spitzname, Geburtsdatum, Telefonnummer) und `byro.plugins.sepa`
(SEPA-Lastschrift-Daten je Mitglied).

**Katalog** (einzeln installierbar über `byroctl plugin add`, siehe unten):

| Plugin | Beschreibung | Repository |
|---|---|---|
| `finance-import-bank-files` | Datei-basierter Bankimport (aktuell CAMT.053) | [byro/byro-finance-import-bank-files](https://github.com/byro/byro-finance-import-bank-files) |

Das ist der vollständige Katalog zum Zeitpunkt dieser Seite – kein
ausgedachtes Beispiel, sondern `deploy/plugin-catalog.conf` dieses Release.
Zwei weitere von der byro-Organisation gepflegte Plugins existieren, sind
aber mit der aktuellen byro-Version **nicht kompatibel** und deshalb nicht
im Katalog: [byro-mailman](https://github.com/byro/byro-mailman)
(Mailinglisten-Integration) und
[byro-gemeinnuetzigkeit](https://github.com/byro/byro-gemeinnuetzigkeit)
(Zuwendungsbestätigungen für deutsche gemeinnützige Vereine).

Weitere, nicht offiziell geprüfte Plugins listet das GitHub-Thema
[byro-plugin](https://github.com/topics/byro-plugin) – ein Ort zum
Nachsehen, keine Empfehlung; byroctl installiert daraus nichts automatisch.
Wie ein Plugin in den Katalog aufgenommen wird, beschreibt
[Plugin-Katalog](../development/releasing.md#plugin-katalog) in der
Entwicklerdokumentation.

## Wie byroctl Plugins installiert

byro findet Plugins unter den Python-Paketen, die neben ihm installiert sind.
In einem Container heißt das: Das Plugin muss Teil des Images sein, also baut
byroctl ein **abgeleitetes Image**: das gepinnte Release-Image plus die von
dir gelisteten Plugins. Die Liste liegt in `plugins/plugins.txt`, einer
pip-Requirements-Datei in deinem Installationsverzeichnis; `plugins/Dockerfile`
(von byroctl verwaltet) baut das Image, und das Add-on `compose/plugins.yml`
schaltet die byro-Dienste darauf um, solange die Liste mindestens ein Plugin
nennt.

Jede Änderung am Plugin-Satz läuft in zwei Phasen:

1. **Bauen und prüfen** (umkehrbar): Das Image wird gebaut und byros
   Konfigurationsprüfung läuft darin. Schlägt das fehl, setzt byroctl
   `plugins/plugins.txt`, `COMPOSE_FILE` und das Image auf den vorherigen
   Stand zurück; die laufenden Container wurden nie angefasst.
2. **Migrieren und starten** (nicht umkehrbar): Eine
   **Pre-Plugin-Sicherheitskopie** wird nach `backups/` geschrieben
   (Datenbank-Dump, vorherige `byro.conf`, vorherige `plugins.txt`, Secret
   Key), die Datenbankmigrationen des neuen Plugin-Satzes laufen, und die
   byro-Dienste werden mit dem neuen Image neu erstellt. Benutzer sehen eine
   kurze Unterbrechung.

Schlägt die Migration oder der folgende Start fehl, wechselt byroctl **nicht**
eigenständig zu den vorherigen Plugins zurück: Die Datenbank trägt vielleicht
schon das Schema des neuen Plugin-Satzes, und alter Code auf neuem Schema würde
es schlimmer machen. Die Dateien behalten den versuchten Stand, und byroctl
gibt den Weg nach vorn (Ursache beheben, `byroctl plugin rebuild`) und den Weg
zurück aus (Sicherheitskopie einspielen: Datenbank, `byro.conf` und
`plugins/plugins.txt`, dann `byroctl plugin rebuild` und `byroctl start`).

## Zwei Arten, ein Plugin zu benennen

**Katalog-Kurznamen.** Jedes byro-Release liefert einen kleinen Plugin-Katalog
(`plugin-catalog.conf` in deinem Installationsverzeichnis; `byroctl plugin
list` zeigt ihn). Der Katalog enthält nur Metadaten: Name, Beschreibung, das
Python-Paket und dessen Herkunft. Fügst du ein Katalog-Plugin hinzu, ermittelt
byroctl in diesem Moment dessen **aktuelles Release** und pinnt es:

* ein Plugin auf GitHub wird vom Commit installiert, auf den sein aktueller
  regulärer Release-Tag zeigt (Pre-Releases werden ignoriert); der Release-Tag
  bleibt als lesbare Version erhalten,
* ein Plugin auf PyPI wird als `paket==<aktuelle version>` installiert.

byroctl sucht nicht nach einem älteren Release, das besser zu deiner
byro-Version passen könnte. Braucht das aktuelle Release ein neueres byro,
schlägt der Build mit pips Meldung fehl; installiere dann eine ältere Version
als explizites Requirement oder aktualisiere zuerst byro.

**Explizite pip-Requirements.** Alles, was pip versteht, zum Beispiel
`byro-mailman==1.0.1`,
`byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0`
oder `./my-plugin` für einen Checkout in `plugins/`. Pinne eine Version oder
einen Tag; ein ungepinntes Requirement wird mit Warnung akzeptiert, aber jeder
Rebuild kann dann ein anderes Release ziehen. Explizite Requirements sind deine
Sache: `byroctl plugin update` lässt sie unangetastet.

Das GitHub-Topic [byro-plugin](https://github.com/topics/byro-plugin) listet
weitere Community-Plugins. Es ist ein Ort zum Nachsehen, mehr nicht: byroctl
installiert daraus nie etwas automatisch.

## Befehle

```console
$ byroctl plugin list                                Katalog, Installiertes, zusätzliche Einträge
$ byroctl plugin add finance-import-bank-files       Katalog-Plugin hinzufügen (aktuelles Release)
$ byroctl plugin add 'byro-x==1.2.0'                 explizites Requirement hinzufügen
$ byroctl plugin remove finance-import-bank-files    Eintrag entfernen (nach Name, Requirement oder Paket)
$ byroctl plugin update --check                      welche Katalog-Plugins ein neueres Release haben
$ byroctl plugin update [finance-import-bank-files]  Katalog-Plugins auf ihr aktuelles Release heben
$ byroctl plugin rebuild [--no-cache]                Image aus plugins/plugins.txt neu bauen
```

Plugins lassen sich auch bei der Installation wählen: Der Installer fragt nach
Katalog-Kurznamen, und `byroctl install --plugin NAME|SPEC` (wiederholbar, auch
über `install.sh`) nimmt Namen und Requirements.

`add`, `remove`, `update` und `rebuild` enden alle mit den beiden oben
beschriebenen Phasen und beenden sich mit 1, wenn Build oder Prüfung
fehlschlugen (nichts wurde geändert), mit 2, wenn die Migration fehlschlug,
und mit 3, wenn byro nicht gesund zurückkam (siehe den Hinweis zur
Wiederherstellung in beiden Fällen); 64 ist ein Bedienfehler.
`--skip-safeguard` überspringt den Datenbank-Dump vor der Migration.

Das Entfernen eines Plugins entfernt seinen Code aus dem Image, nicht seine
Datenbanktabellen oder die von ihm erzeugten Dokumente. Sollen die Tabellen
weg, führe *vor* dem Entfernen `byroctl manage migrate <app> zero` aus.

## Die Plugin-Liste und das plugins-Verzeichnis

`plugins/plugins.txt` ist eine gewöhnliche pip-Requirements-Datei: ein
Requirement pro Zeile, `#` beginnt einen Kommentar. Katalogeinträge tragen
eine Markierung, die byroctl schreibt und liest:

```text
byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@3f2a9c1e7b6d4a5f8c0e1d2b3a4f5e6d7c8b9a01  # byroctl:catalog=finance-import-bank-files version=v1.2.0
byro-mailman==1.0.1
./my-plugin
```

Du darfst die Datei von Hand bearbeiten, zum Beispiel um einen lokalen
Checkout hinzuzufügen: Lege den Quellcode des Plugins nach `plugins/my-plugin`
und liste es als `./my-plugin`. Dann `byroctl plugin rebuild` ausführen.
byroctl prüft die Datei (`byroctl config check` ebenfalls) und lehnt Zeilen ab,
die wie pip-Optionen oder Kommentare aussehen; die Datei wird wie `byro.conf`
als vertrauenswürdig behandelt, behalte sie also unter Kontrolle.

Das Verzeichnis `plugins/` ist der Docker-Build-Kontext. `plugins/Dockerfile`
wird von byroctl bei jedem byro-Update ersetzt; bearbeite es nicht. Sichere
`plugins/` zusammen mit `byro.conf`.

## Was ein byro-Update mit Plugins macht

`byroctl update` behält deine Pins und baut das Plugin-Image auf dem neuen
byro-Release neu, bevor es irgendetwas stoppt. Die Pre-Update-Sicherheitskopie
enthält die vorherige `plugins.txt`. Schlägt der Build fehl, bleibt der
laufende Stack unberührt und byroctl gibt den Weg zurück aus. Mit
`--update-plugins` hebt es Katalog-Plugins im selben Lauf auf ihr aktuelles
Release; ohne die Option führe danach `byroctl plugin update` aus.

Release-Tags von Plugins gelten als **unveränderlich**. Zeigt ein installierter
Release-Tag plötzlich auf einen anderen Commit, bricht `byroctl plugin update`
(und `byroctl update --update-plugins`) mit einem Integritätsfehler ab, behält
deinen Pin und aktualisiert nichts weiter. Bitte den Plugin-Maintainer, für
geänderten Code ein neues Release zu veröffentlichen.

## Fehlersuche

* Lies die Ausgabe des fehlgeschlagenen `docker compose build`; typische
  Ursachen sind ein nicht existierender git-Ref, ein Plugin, das eine andere
  Django- oder byro-Version verlangt (byroctl baut mit den Paketen des
  Basis-Images als Constraints, sodass pip einen Konflikt meldet statt Django
  zu ersetzen), oder eine Abhängigkeit ohne Wheel für deine Plattform (das
  Image hat keinen Compiler).
* `byroctl plugin rebuild --no-cache` baut von Grund auf neu.
* GitHubs API erlaubt 60 anonyme Anfragen pro Stunde und Adresse; byroctl
  braucht zwei pro GitHub-Plugin. Setze `GITHUB_TOKEN` in der Umgebung, wenn
  du das Limit erreichst.
* `byroctl version` zeigt, welche Plugins der laufende Web-Dienst geladen hat;
  `byroctl plugin list`, was konfiguriert ist. Weichen sie ab, führe
  `byroctl plugin rebuild` aus.
* Das Image `<projekt>-plugins:<version>` des vorherigen byro-Release bleibt,
  bis du es mit `docker image rm` entfernst.

## Docker Compose von Hand

Derselbe Mechanismus funktioniert ohne byroctl. In deinem
Installationsverzeichnis:

1. Lege `plugins/` an, lade `plugins/Dockerfile` des Release, das du betreibst
   (`deploy/plugins/Dockerfile` im Repository), und schreibe
   `plugins/plugins.txt` mit gepinnten Requirements.
2. Nimm `compose/plugins.yml` (`deploy/compose/plugins.yml` des Release) in
   `COMPOSE_FILE` in `byro.conf` auf.
3. Bauen, migrieren, neu starten:

    ```console
    $ docker compose build web
    $ docker compose run --rm manage migrate
    $ docker compose up -d
    ```

Wiederhole den Build nach jeder Änderung an `plugins.txt` und nach jedem
byro-Update (das Basis-Image hat sich geändert).

## Bare-Metal-Installation

Installiere das Plugin in dieselbe Python-Umgebung wie byro, migriere, baue die
Assets neu (`rebuild` kompiliert auch die Übersetzungen des Plugins) und starte
neu:

```console
$ pip install --user 'byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0'
$ python -m byro migrate
$ python -m byro rebuild
# systemctl restart byro-web
```
