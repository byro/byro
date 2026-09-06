# Legacy-Setup: docker-compose-Dateien in `production/` (veraltet)

!!! warning
    Dieses Setup ist **veraltet**. Es funktioniert weiter mit dem aktuellen
    byro-Image, bekommt aber keine neuen Funktionen und wird in einem späteren
    Release entfernt. Neue Installationen sollten [byroctl](byroctl.md)
    (empfohlen) oder [Docker Compose](docker-compose.md) verwenden.
    `production/DEPRECATED.md` im Repository erklärt, wie eine bestehende
    Installation umzieht, und listet die bekannten Probleme dieses Setups.

Im Ordner `production/` des byro-Repositorys findest du Setup-Skripte und eine
`docker-compose.yml`, die dir helfen, byro produktiv mit Docker zu betreiben.

!!! note
    Es gibt auch eine `docker-compose`-Datei im Ordner `src/`. Diese Datei ist
    nur für die Entwicklung gedacht!

## Schritt 0: Voraussetzungen

Diese Anleitung setzt voraus, dass folgende Systemdienste installiert und
eingerichtet sind:

* Docker
* docker-compose
* Ein SMTP-Server zum Mailversand
* Ein HTTP Reverse Proxy, z. B. nginx oder Apache, für HTTPS-Verbindungen

## Schritt 1: Konfiguration

Repository auschecken und das Setup-Skript ausführen:

```console
# git clone https://github.com/byro/byro
# byro/production/setup.sh
```

Das legt neben dem byro-Ordner einen Ordner `byro-data/` an, der alle deine
Daten enthält. Außerdem kopiert es eine erste `byro.cfg` in den Datenordner.

Öffne diese Datei in einem Editor und konfiguriere folgende Punkte:

`[mail]`
:   Verbindungsdaten zu deinem SMTP-Server. Die vorausgefüllte IP ist die
    Adresse, über die der Docker-Container deinen Host erreicht. Ändere sie,
    wenn dein SMTP-Server nicht auf demselben Server läuft.

`[site]`
:   Ändere die URL auf eine, unter der dein Server erreichbar ist. Ist dein
    Server noch nicht öffentlich erreichbar, musst du `debug` aktivieren, um
    Djangos URL-Prüfung zu umgehen.

`[pgp]`
:   Die Beispielkonfiguration speichert GnuPG-Daten in
    `/var/byro/data/gnupg`, Teil des byro-Datenvolumes. Das offizielle
    byro-Image enthält die nötigen GnuPG-Pakete. Aktiviere Signieren und
    Verschlüsseln in den Office-Einstellungen, sobald die Installation läuft.

!!! note
    Setze deinen Server niemals mit `debug = True` öffentlich aus. Besucher
    könnten sonst potenziell sensible Informationen einsehen.

## Schritt 2: Deployment

Nach der Konfiguration führe das Setup-Skript erneut aus:

```console
# byro/production/setup.sh
```

Jetzt wird die Datenbank angelegt, und du wirst aufgefordert, einen Superuser
zu erstellen. Danach ist die Installation vollständig. Mit `setup.sh` kannst du
weitere Aufgaben erledigen, etwa die Installation stoppen, Logs verfolgen oder
byro-Plugins installieren.

Mehr Informationen:

```console
# byro/production/setup.sh help
```

## Schritt 3: FinTS-Plugin installieren (optional)

Der folgende Aufruf installiert das
[byro-fints-Plugin](https://github.com/henryk/byro-fints):

```console
# byro/production/setup.sh fints
```
