# Backup und Restore

byro selbst legt keine eigenen Backups an (die Pre-Update- und
Pre-Plugin-Sicherheitskopien von byroctl sind eine Ausnahme, siehe unten, aber
kein Ersatz für ein reguläres Backup). Sichern und Wiederherstellen ist Aufgabe
der Administration, unabhängig vom Installationsweg.

## Was gesichert werden muss

Bei allen drei Installationswegen sind es dieselben drei Dinge:

1. **Die Datenbank.** Enthält alle Mitglieder-, Finanz- und Konfigurationsdaten.
2. **Das Datenverzeichnis** (`data/` bei byroctl und Docker Compose,
   `/var/byro/data` bei Bare Metal). Enthält hochgeladene Dokumente, GnuPG-
   Schlüssel und die Datei `.secret` mit Djangos `SECRET_KEY`.
3. **Die Konfiguration** (`byro.conf` bzw. `/etc/byro/byro.cfg`). Enthält
   Datenbankpasswort, Mail-Zugangsdaten und weitere Geheimnisse – behandle die
   Kopie entsprechend vertraulich.

**Der Verlust von `.secret` allein macht bereits alle Sitzungen und alle
MFA-Geräte ungültig**, auch wenn Datenbank und Konfiguration erhalten sind
(siehe [Mehr-Faktor-Authentifizierung](mfa.md#sicherheitshinweise)). Sichere
`data/` deshalb genauso zuverlässig wie die Datenbank, nicht nur gelegentlich.

Ein konsistentes Datenbank-Backup entsteht entweder bei gestopptem byro oder
über einen transaktionalen Dump (`pg_dump`); ein Dateisystem-Snapshot eines
laufenden Datenbank-Datenverzeichnisses ohne Dateisystem- oder
Datenbank-Unterstützung dafür ist nicht konsistent.

Die genauen Befehle je Installationsweg stehen auf der jeweiligen
Installationsseite: [byroctl](../installation/byroctl.md#backups),
[Docker Compose](../installation/docker-compose.md#backups),
[Bare Metal](../installation/bare-metal.md#nachste-schritte-updates).

!!! note
    Die **Pre-Update-Sicherheitskopie** von `byroctl update` und die
    **Pre-Plugin-Sicherheitskopie** von `byroctl plugin add/remove/update`
    (beide in `backups/`) enthalten die Datenbank, `byro.conf`,
    `plugins/plugins.txt` und `.secret` – **aber nicht** die Dokumente und
    anderen Dateien in `data/`. Sie schützen vor einem fehlgeschlagenen
    Update, nicht vor Datenverlust im Allgemeinen.

## Restore

!!! warning
    Ein Restore überschreibt den aktuellen Datenbestand. Es gibt kein
    `byroctl restore` – die folgenden Schritte sind manuell auszuführen. Prüfe
    vorher, dass das Backup, das du einspielst, wirklich das gewünschte ist
    (Zeitpunkt, Vollständigkeit).

### byroctl und Docker Compose

Im Installationsverzeichnis, mit gestoppten byro-Diensten, aber laufender
Datenbank:

```console
$ byroctl stop            # oder: docker compose stop web periodic
$ docker compose exec -T db pg_restore -U byro -d byro --clean --if-exists < byro.dump
$ rm -rf data && cp -a /pfad/zum/backup/data ./data
$ byroctl start           # oder: docker compose up -d
```

`--clean --if-exists` löscht vorhandene Objekte vor dem Wiedereinspielen und
verträgt sich mit einer bereits vorhandenen Datenbank; `byro.dump` ist ein
Dump im `pg_dump -Fc`-Format (siehe die Backup-Abschnitte oben). Ersetze auch
`byro.conf`, wenn sich seitdem etwas daran geändert hat, das du nicht behalten
willst.

### Bare Metal

Als Benutzer `byro`, mit gestopptem `byro-web` und `byro-periodic.timer`:

```console
# systemctl stop byro-web byro-periodic.timer
$ pg_restore -U byro -d byro --clean --if-exists -h localhost byro.dump
$ rm -rf /var/byro/data && cp -a /pfad/zum/backup/data /var/byro/data
# cp /pfad/zum/backup/byro.cfg /etc/byro/byro.cfg
# systemctl start byro-web byro-periodic.timer
```

Bei MySQL/MariaDB ersetze den `pg_restore`-Aufruf durch das Einspielen deines
`mysqldump`- oder `mariadb-dump`-Exports mit dem jeweiligen Client.

Nach jedem Restore lohnt sich ein Blick in die Logs (siehe
[Monitoring, Logging und Fehlersuche](troubleshooting.md)), um sicherzustellen,
dass byro mit dem wiederhergestellten Stand sauber startet.

## Disaster Recovery: Umzug auf einen neuen Host

Der Ablauf ist ein Restore auf einer frischen Installation, nicht die
Installationsroutine selbst – `byroctl install` bzw. der Bare-Metal-Ablauf
`python -m byro migrate` würden sonst eine **neue, leere** Datenbank und einen
**neuen** Secret Key anlegen.

Für byroctl/Docker Compose:

1. Docker und Docker Compose auf dem neuen Host einrichten (siehe
   [Voraussetzungen](../installation/byroctl.md#voraussetzungen)), byroctl und
   die Compose-Dateien desselben byro-Release wie zuvor installiert
   herunterladen (nicht `byroctl install` ausführen).
2. Die gesicherte `byro.conf` in das Installationsverzeichnis legen und als
   `.env` verlinken.
3. Nur die Datenbank starten (`docker compose up -d db`), warten, bis sie
   gesund ist, dann den Dump einspielen wie oben unter Restore beschrieben.
4. Die gesicherte `data/` an die gleiche Stelle kopieren.
5. Den restlichen Stack starten (`byroctl start` bzw. `docker compose up -d`)
   und `byroctl version` bzw. `docker compose ps` prüfen.

Für Bare Metal entsprechend: Systempakete, Python-Umgebung und byro auf dem
neuen Host wie in der [Bare-Metal-Installation](../installation/bare-metal.md)
einrichten, dabei aber Schritt 5 (`python -m byro migrate`) durch das
Einspielen des Datenbank-Dumps ersetzen, `data/` und `byro.cfg` aus dem Backup
zurückkopieren, dann mit Schritt 6 (Dienste starten) fortfahren.

Aktualisiere danach den DNS-Eintrag deiner Domain auf den neuen Host und
prüfe, dass `BYRO_SITE_URL` bzw. `[site] url` weiterhin zu der Adresse passt,
unter der byro erreichbar ist.
