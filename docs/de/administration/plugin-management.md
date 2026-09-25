# Plugin-Verwaltung

Diese Seite beschreibt die Verwaltung von Plugins in einer byroctl-Installation.
Die Installationsseiten erklären die Besonderheiten von [byroctl](../installation/byroctl.md),
[Docker Compose](../installation/docker-compose.md) und
[Bare Metal](../installation/bare-metal.md).

## Plugins installieren

byro findet Plugins unter den Python-Paketen, die neben ihm installiert sind.
In einem Container baut byroctl dafür ein **abgeleitetes Image** aus dem
Release-Image und den in `plugins/plugins.txt` gelisteten Plugins.
`plugins/Dockerfile` wird von byroctl verwaltet; das Add-on
`compose/plugins.yml` schaltet die Dienste auf das neue Image um, sobald die
Liste mindestens ein Plugin nennt.

Jede Änderung am Plugin-Satz läuft in zwei Phasen:

1. **Bauen und prüfen** (umkehrbar): Das Image wird gebaut und byros
   Konfigurationsprüfung läuft darin. Schlägt das fehl, setzt byroctl
   `plugins/plugins.txt`, `COMPOSE_FILE` und das Image auf den vorherigen
   Stand zurück; die laufenden Container wurden nie angefasst.
2. **Migrieren und starten** (nicht umkehrbar): Eine
   **Pre-Plugin-Sicherheitskopie** wird nach `backups/` geschrieben
   (Datenbank-Dump, vorherige `byro.conf`, vorherige `plugins.txt`, Secret
   Key), die Datenbankmigrationen laufen, und die Dienste werden mit dem neuen
   Image neu erstellt. Benutzer sehen eine kurze Unterbrechung.

Schlägt die Migration oder der folgende Start fehl, wechselt byroctl **nicht**
eigenständig zu den vorherigen Plugins zurück: Die Datenbank trägt vielleicht
schon das Schema des neuen Plugin-Satzes. Stelle für den Weg zurück die
Sicherheitskopie wieder her (Datenbank, `byro.conf` und `plugins/plugins.txt`)
und führe anschließend `byroctl plugin rebuild` und `byroctl start` aus.
Alternativ behebe die Ursache und starte den Build erneut.

Plugins können beim Installieren mit `--plugin NAME|SPEC` oder später mit den
folgenden Befehlen verwaltet werden:

```console
$ byroctl plugin list
$ byroctl plugin add finance-import-bank-files
$ byroctl plugin add 'byro-x==1.2.0'
$ byroctl plugin remove finance-import-bank-files
$ byroctl plugin update [finance-import-bank-files]
$ byroctl plugin rebuild [--no-cache]
```

Plugins lassen sich auch bei der Installation wählen: Der Installer fragt nach
Katalog-Kurznamen, und `byroctl install --plugin NAME|SPEC` (wiederholbar, auch
über `install.sh`) nimmt Namen und Requirements.

`add`, `remove`, `update` und `rebuild` führen die beiden oben beschriebenen
Phasen aus. Sie enden mit 1 bei Build- oder Prüfungsfehlern (nichts wurde
geändert), mit 2 bei einem Migrationsfehler, mit 3 wenn byro nicht gesund
zurückkam und mit 64 bei einem Bedienfehler. `--skip-safeguard` überspringt den
Datenbank-Dump vor der Migration.

## Zwei Arten, ein Plugin zu benennen

**Katalog-Kurznamen.** Jedes byro-Release liefert einen kleinen Plugin-Katalog
(`plugin-catalog.conf`; `byroctl plugin list` zeigt ihn). Fügt man ein
Katalog-Plugin hinzu, ermittelt byroctl dessen **aktuelles Release** und pinnt
es: bei GitHub auf den Commit des aktuellen regulären Release-Tags
(Pre-Releases werden ignoriert), bei PyPI als `paket==<aktuelle version>`.

byroctl sucht nicht nach einem älteren Release, das besser zur installierten
byro-Version passt. Benötigt das aktuelle Release ein neueres byro, installiere
eine ältere Version als explizites Requirement oder aktualisiere erst byro.

**Explizite pip-Requirements.** Alles, was pip versteht, kann verwendet
werden, zum Beispiel `byro-mailman==1.0.1`,
`byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0`
oder `./my-plugin` für einen Checkout in `plugins/`. Pinne immer eine Version
oder einen Tag; ungepinnte Requirements können bei jedem Rebuild ein anderes
Release installieren. `byroctl plugin update` lässt explizite Requirements
unverändert.

Das GitHub-Thema [byro-plugin](https://github.com/topics/byro-plugin) listet
weitere Community-Plugins. Es ist ein Ort zum Nachsehen, mehr nicht: byroctl
installiert daraus nie etwas automatisch.

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
Checkout hinzuzufügen: Lege den Quellcode nach `plugins/my-plugin` und liste
ihn als `./my-plugin`. Dann `byroctl plugin rebuild` ausführen. byroctl prüft
die Datei (`byroctl config check` ebenfalls) und lehnt Zeilen ab, die wie
pip-Optionen oder Kommentare aussehen; die Datei wird wie `byro.conf` als
vertrauenswürdig behandelt, behalte sie also unter Kontrolle.

Das Verzeichnis `plugins/` ist der Docker-Build-Kontext. `plugins/Dockerfile`
wird von byroctl bei jedem byro-Update ersetzt; bearbeite es nicht. Sichere
`plugins/` zusammen mit `byro.conf`.

## Was ein byro-Update mit Plugins macht

`byroctl update` behält die gesetzten Pins und baut das Plugin-Image auf dem
neuen byro-Release neu, bevor es irgendetwas stoppt. Die Pre-Update-
Sicherheitskopie enthält die vorherige `plugins.txt`. Schlägt der Build fehl,
bleibt der laufende Stack unberührt. Mit `--update-plugins` hebt es
Katalog-Plugins im selben Lauf auf ihr aktuelles Release; ohne die Option
führe danach `byroctl plugin update` aus.

Release-Tags von Plugins gelten als **unveränderlich**. Zeigt ein installierter
Release-Tag plötzlich auf einen anderen Commit, bricht `byroctl plugin update`
(und `byroctl update --update-plugins`) mit einem Integritätsfehler ab, behält
deinen Pin und aktualisiert nichts weiter.

Das Entfernen eines Plugins entfernt seinen Code aus dem Image, nicht aber
seine Datenbanktabellen oder erzeugten Dokumente. Tabellen müssen vor dem
Entfernen mit `byroctl manage migrate <app> zero` entfernt werden.

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

`byroctl version` zeigt die geladenen Plugins des laufenden Web-Dienstes;
`byroctl plugin list` zeigt die konfigurierte Liste. Weichen sie ab, führe
`byroctl plugin rebuild` aus. Das Image `<projekt>-plugins:<version>` des
vorherigen byro-Release bleibt, bis du es mit `docker image rm` entfernst.
