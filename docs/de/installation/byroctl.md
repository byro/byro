# Installation mit byroctl (empfohlen)

`byroctl` installiert byro als Satz von Docker-Containern, hält alles Nötige in
einem Verzeichnis und spielt Updates mit einem einzigen Befehl ein. Es richtet
sich an Administratoren kleiner und mittelgroßer Organisationen, die ein
funktionierendes byro auf einem Linux-Server wollen, ohne die Einzelteile von
Hand zusammenzusetzen.

Was du bekommst:

* das offizielle byro-Container-Image, auf ein exaktes Release gepinnt,
* eine PostgreSQL-Datenbank (oder eine Verbindung zu deiner eigenen),
* optional Caddy als Reverse Proxy, der TLS-Zertifikate beschafft und erneuert,
* eine Konfigurationsdatei, `byro.conf`,
* Plugins aus einem Katalog oder als pip-Requirements, für dich ins Image
  gebaut ([Plugin-Verwaltung](../administration/plugin-management.md)),
* `byroctl update` mit einer Sicherheitskopie der Datenbank vor jedem Update.

Alles, was byroctl startet, ist gewöhnliches Docker Compose. Du kannst dir die
Dateien im Installationsverzeichnis jederzeit ansehen und `docker compose`
direkt verwenden.

## Voraussetzungen

* Ein Linux-Server (Debian und Ubuntu sind die getesteten Plattformen) mit
  einem DNS-Namen, der auf ihn zeigt.
* Docker Engine 24 oder neuer mit dem Compose-Plugin 2.20 oder neuer. Dein
  Benutzer muss Docker verwenden dürfen (Mitglied der Gruppe `docker`).
  Beachte, dass diese Gruppenmitgliedschaft Root-Rechten auf der Maschine
  entspricht.
* `bash` 4 oder neuer und `curl`. Beides ist auf jeder aktuellen
  Linux-Distribution vorhanden. macOS liefert weiterhin bash 3.2 aus; um den
  Installer auf einem Mac auszuprobieren, installiere zuerst eine aktuelle bash
  (`brew install bash`) und führe die Befehle unten mit dieser bash
  (`/opt/homebrew/bin/bash`) oder in einer Linux-VM aus.
* Freie Ports 80 und 443, wenn Caddy TLS für dich terminieren soll, sonst ein
  eigener Reverse Proxy, der an byro weiterleitet.
* Ein SMTP-Server zum Mailversand. Er kann später konfiguriert werden.
* Etwa 2 GB freier Plattenplatz für die Images, plus Platz für deine Daten.

Der Installer braucht kein Root. Soll er in das Standardverzeichnis
`/opt/byro` installieren, lege das Verzeichnis einmal an und übergib es
deinem Benutzer:

```console
$ sudo mkdir -p /opt/byro && sudo chown "$(id -u):$(id -g)" /opt/byro
```

Alternativ wähle mit `--root ~/byro` ein Verzeichnis, das dir gehört.

## Installation

Führe das Bootstrap-Skript aus. Es lädt `byroctl` für das aktuelle stabile
Release, prüft es und startet die Installation:

```console
$ bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)"
```

Hänge `-- --root /pfad` an, um woanders zu installieren, `-- --dry-run`, um zu
sehen, was das Skript tun würde, ohne etwas zu ändern, `-- --version vYYYY.M.P`,
um statt des aktuellen stabilen Release eine bestimmte Version zu installieren,
oder `-- --no-symlink`, wenn `byroctl` nicht nach `/usr/local/bin` oder
`~/.local/bin` verlinkt werden soll.

Der Installer stellt ein paar Fragen, jede mit einem sinnvollen Standard:

* die öffentliche URL deines byro, zum Beispiel `https://byro.example.org`,
* ob byro selbst TLS-Zertifikate beschaffen soll (Caddy, Ports 80 und 443
  müssen frei sein), ob du einen eigenen Reverse Proxy betreibst oder ob byro
  direkt ohne HTTPS erreichbar ist (nur für Tests),
* Sprache und Zeitzone,
* ob die eingebaute PostgreSQL oder eine externe Datenbank verwendet wird,
* wie Mails versendet werden: ein Mailserver auf derselben Maschine, ein
  externer SMTP-Server oder später,
* welche Plugins aus dem Katalog installiert werden (Kurznamen wie
  `finance-import-bank-files`; standardmäßig keine, siehe
  [Plugin-Verwaltung](../administration/plugin-management.md)),
* Benutzername, E-Mail-Adresse und Passwort des ersten Administrators.

Danach schreibt er die Konfiguration, lädt die Images, baut bei Bedarf das
Plugin-Image, legt das Datenbankschema und das Administratorkonto an und
startet byro. Am Ende gibt er die URL und die Pfade aus, die du kennen musst.

### Unbeaufsichtigte Installation

Jede Antwort lässt sich mit `--set KEY=VALUE` vorab geben, Passwörter nur über
Umgebungsvariablen, damit sie nie in einer Prozessliste oder Shell-Historie
auftauchen:

```console
$ export BYROCTL_ADMIN_PASSWORD='…'
$ bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)" -- \
    --non-interactive \
    --set BYRO_SITE_URL=https://byro.example.org \
    --set BYROCTL_PROXY=caddy \
    --set BYRO_LANGUAGE_CODE=de --set BYRO_TIME_ZONE=Europe/Berlin \
    --set BYROCTL_MAIL=smtp --set BYRO_MAIL_HOST=mail.example.org --set BYRO_MAIL_FROM=byro@example.org \
    --admin-user admin --admin-email admin@example.org
```

`BYROCTL_PROXY` akzeptiert `caddy`, `own` oder `none`; `BYROCTL_DB` akzeptiert
`internal` oder `external`; `BYROCTL_MAIL` akzeptiert `host`, `smtp` oder
`skip`; `BYROCTL_PLUGINS` nimmt durch Leerzeichen getrennte Katalog-Kurznamen
(`--set BYROCTL_PLUGINS="finance-import-bank-files"`). Plugins als
pip-Requirement verwenden stattdessen `--plugin`, einmal je Plugin:
`--plugin 'byro-x==1.2.0'`. Passwörter für eine externe Datenbank oder ein
SMTP-Konto kommen aus `BYROCTL_DB_PASSWORD` und `BYROCTL_MAIL_PASSWORD`.
`--skip-superuser` legt kein Administratorkonto an (lege es später mit
`byroctl manage createsuperuser` an); `--no-pull` verwendet ein bereits lokal
vorhandenes Image, statt es zu laden (nur für Entwicklung sinnvoll).
`byroctl install --help` listet alle Optionen.

Bleibt die Installation auf halbem Weg stehen, etwa weil die E-Mail-Adresse
des Administrators abgelehnt wurde, korrigiere die Eingabe und führe
`byroctl install` erneut aus. Es macht dort weiter, wo es stehen geblieben ist,
und stellt die allgemeinen Fragen nicht noch einmal.

## Das Installationsverzeichnis

Standardmäßig liegt alles in `/opt/byro`:

```text
/opt/byro/
├── byroctl                     das Werkzeug selbst (nach /usr/local/bin verlinkt)
├── byro.conf                   deine Konfiguration - die einzige Datei, die du bearbeitest
├── .env -> byro.conf           lässt gewöhnliches "docker compose" dieselbe Datei lesen
├── docker-compose.yml          byro-Dienste (nicht bearbeiten, byroctl ersetzt sie beim Update)
├── compose/postgres.yml        Add-on: eingebaute PostgreSQL
├── compose/caddy.yml           Add-on: Caddy Reverse Proxy
├── compose/plugins.yml         Add-on: byro mit Plugins (aktiv, solange Plugins gelistet sind)
├── Caddyfile
├── plugin-catalog.conf         der Plugin-Katalog des installierten Release
├── plugins/plugins.txt         deine Plugin-Liste (pip-Requirements)
├── plugins/Dockerfile          baut das Image mit Plugins (nicht bearbeiten)
├── data/                       Dokumente, Uploads, Schlüssel, der Secret Key, Logs
├── db/                         PostgreSQL-Daten
├── caddy/                      Zertifikate (nur mit Caddy)
├── backups/                    Sicherheitskopien vor Updates und Plugin-Änderungen
└── .byroctl/                   interner Zustand
```

Lokale Ergänzungen, zum Beispiel zusätzliche Labels für einen Reverse Proxy,
gehören in eine `docker-compose.override.yml` neben diesen Dateien; byroctl
fasst sie nie an.

## Konfiguration

`byro.conf` enthält die Einstellungen von byro selbst (`BYRO_*`, alle Optionen
unter [Konfiguration](../configuration/reference.md)), die
Deployment-Einstellungen (`BYRO_DEPLOY_*`) und die Liste der Compose-Dateien
(`COMPOSE_FILE`). Lies und ändere sie mit byroctl:

```console
$ byroctl config get BYRO_SITE_URL
$ byroctl config set BYRO_MAIL_HOST mail.example.org --apply
$ byroctl config edit
$ byroctl config check
```

`--apply` prüft die Datei und erstellt nur die Container neu, deren
Einstellungen sich geändert haben. Passwörter werden aus der Umgebung statt
von der Kommandozeile gesetzt:

```console
$ BYROCTL_VALUE='…' byroctl config set BYRO_MAIL_PASSWORD --apply
```

Wenn du die Datei von Hand bearbeitest: Setze Werte mit `$`, `#`, Leerzeichen,
Anführungszeichen oder Backslashes in einfache Anführungszeichen. Compose
interpoliert `$` in doppelten Anführungszeichen und in Werten ohne
Anführungszeichen, und ein `#` nach einem Leerzeichen beginnt einen Kommentar.
`byroctl config check` meldet solche Fehler.

## Alltägliche Befehle

```console
$ byroctl start                  Stack starten und warten, bis byro gesund ist
$ byroctl stop                   Container stoppen, alle Daten behalten
$ byroctl restart                byro-Dienste neu erstellen (nicht die Datenbank)
$ byroctl logs [-f] [web db …]   Logs eines oder mehrerer Dienste anzeigen (oder verfolgen)
$ byroctl manage <befehl>        einen byro-Management-Befehl ausführen, siehe unten
$ byroctl plugin list|add|remove|update|rebuild   Plugins verwalten (siehe unten)
$ byroctl version                installiertes Release, Image-Digest, laufende Version, Plugins
$ byroctl self-update            byroctl für das installierte Release neu laden (Reparatur)
```

Plugins haben eigene Seiten: [Plugins](../administration/plugins.md) und
[Plugin-Verwaltung](../administration/plugin-management.md);
alle Management-Befehle stehen unter
[Management-Befehle](../administration/management-commands.md).

### Umgebungsvariablen

Diese Variablen wirken auf byroctl und `install.sh` selbst, nicht auf byro
(das über `byro.conf` konfiguriert wird), und sind für den Normalbetrieb nicht
nötig:

* `BYRO_ROOT` – Installationsverzeichnis, alternativ zu `byroctl --root DIR`.
* `BYROCTL_WEB_HEALTH_TIMEOUT` – Sekunden, die `start`/`update`/`config set
  --apply` maximal auf einen gesunden Web-Dienst warten (Standard 180).
* `BYROCTL_OIDC_CLIENT_SECRET` – OIDC-Client-Secret für `byroctl install`,
  falls du OIDC-Login direkt bei der Installation setzt (siehe
  [Konfiguration](../configuration/reference.md)).
* `BYROCTL_RAW_BASE`, `BYROCTL_SOURCE_DIR` – abweichende Quelle für
  Deployment-Dateien und byroctl selbst (Registry-Mirror bzw. lokaler
  `deploy/`-Checkout); nur für Entwicklung und Tests, nicht für den
  Produktivbetrieb gedacht.
* `BYROCTL_STABLE_URL`, `BYROCTL_STABLE_FILE` – wirken nur auf `install.sh`
  und ersetzen die URL bzw. die lokale Datei, aus der es das aktuelle stabile
  Release ermittelt (Standard: `$BYROCTL_RAW_BASE/stable/stable.env`); auch
  das nur für Entwicklung und Tests.

## Updates

```console
$ byroctl update --check
$ byroctl update
```

`update --check` vergleicht das installierte Release mit dem aktuellen stabilen
und zeigt den Link zu den Release Notes. `update` macht dann Folgendes:

1. wechselt zu dem byroctl, das zum neuen Release gehört,
2. schreibt eine **Pre-Update-Sicherheitskopie** nach `backups/`: einen Dump
   der Datenbank, deine `byro.conf`, deine `plugins/plugins.txt` und die
   Secret-Key-Datei,
3. ergänzt neue Konfigurationsoptionen mit ihren Standardwerten in `byro.conf`
   (nichts wird entfernt oder umsortiert),
4. ersetzt die Compose-Dateien, lädt das neue Image und pinnt dessen Digest,
5. baut das Plugin-Image auf dem neuen Release neu, falls du Plugins verwendest
   (mit unveränderten Pins; `--update-plugins` hebt Katalog-Plugins im selben
   Lauf auf ihr aktuelles Release, siehe
   [Plugin-Verwaltung](../administration/plugin-management.md)),
6. stoppt byro, führt die Datenbankmigrationen aus und startet das neue
   Release.

Ist ein Release als breaking markiert, bittet byroctl dich, die Release Notes
zu lesen und zu bestätigen (`--yes`). Ändert ein Release Dateien in `data/`,
verweigert byroctl den Fortgang, bis du mit `--data-safeguard-done`
bestätigst, dass du ein vollständiges Backup dieses Verzeichnisses hast.
[Downgrades werden nicht unterstützt](../administration/updating.md#downgrade-grenzen).

Schlägt eine Migration fehl, bleiben die byro-Dienste gestoppt und byroctl gibt
den Weg zurück zum vorherigen Release aus, inklusive des Speicherorts der
Sicherheitskopie.

Weitere Optionen von `byroctl update`:

* `--check` meldet nur, ob ein Update verfügbar ist, ändert nichts. Endet mit
  Exit-Code 0, wenn ein Update ansteht, mit 3, wenn bereits die aktuelle
  Version läuft – nützlich für Skripte und Monitoring.
* `--to TAG` aktualisiert auf ein bestimmtes Release statt auf das aktuelle
  stabile.
* `--prefetch` lädt nur das Ziel-Image herunter, ändert sonst nichts.
* `--skip-safeguard` überspringt die Pre-Update-Sicherheitskopie (nicht
  empfohlen).
* `--non-interactive` fragt nie nach; zusammen mit `--yes` (und
  `--data-safeguard-done`, falls nötig) für unbeaufsichtigte Updates.
* `--no-pull` verwendet das lokal vorhandene Ziel-Image (nur für Entwicklung).

!!! note
    Die Pre-Update-Sicherheitskopie ist **kein Backup**. Sie enthält die
    Datenbank, `byro.conf` und den Secret Key, aber keine der Dokumente und
    anderen Dateien in `data/`.

## Backups

Sichere diese drei Dinge regelmäßig, idealerweise bei gestopptem byro oder mit
einem konsistenten Datenbank-Dump:

* `data/` – Dokumente, Uploads, GnuPG-Schlüssel und `.secret`. Der Verlust von
  `.secret` macht alle Sitzungen und alle MFA-Geräte ungültig.
* die Datenbank – `db/` bei gestopptem Stack, oder ein Dump:

    ```console
    $ cd /opt/byro && docker compose exec -T db pg_dump -Fc -U byro byro > byro.dump
    ```

* `byro.conf` – sie enthält deine Passwörter, halte die Kopie geheim.

Eine Wiederherstellung aus diesem Backup sowie der Umzug auf einen neuen Host
sind unter [Backup und Restore](../administration/backup-restore.md)
beschrieben.

## Reverse Proxy

Mit `BYROCTL_PROXY=caddy` bringt byro seinen eigenen Reverse Proxy mit. Caddy
lauscht auf den Ports 80 und 443, holt ein Zertifikat von Let's Encrypt für
den Host in `BYRO_SITE_URL` und leitet Anfragen an byro weiter.

Mit eigenem Reverse Proxy (`BYROCTL_PROXY=own`) lauscht byro auf
`127.0.0.1:8345` (`BYRO_DEPLOY_BIND` und `BYRO_DEPLOY_PORT`). Leite
HTTPS-Verkehr dorthin, reiche den `Host`-Header durch und setze
`X-Forwarded-Proto`. byroctl setzt in diesem Modus `BYRO_TRUST_PROXY=true`,
damit byro weitergeleitete Anfragen als sicher behandelt. Setze es niemals,
wenn byro direkt erreichbar ist, weil Clients den Header fälschen könnten.

## Fehlersuche

* `byroctl config check` prüft `byro.conf` und die Compose-Dateien.
* `byroctl logs web` zeigt, was der Web-Dienst tut; `byroctl logs db` die
  Datenbank.
* `docker compose ps` im Installationsverzeichnis zeigt die Container und ihren
  Zustand.
* Ein belegter Port bei der Installation bedeutet, dass dort ein anderer
  Dienst lauscht: wähle den Proxy-Modus `own` oder einen anderen
  `BYRO_DEPLOY_PORT`.
* `byroctl self-update` lädt byroctl für das installierte Release neu, falls
  das Skript beschädigt wurde.

Health-Checks, Log-Speicherorte und weitere Fehlerbilder stehen unter
[Monitoring, Logging und Fehlersuche](../administration/troubleshooting.md).
