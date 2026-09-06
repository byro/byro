# Installation mit Docker Compose

Diese Seite beschreibt dieselbe Installation, die [byroctl](byroctl.md)
einrichtet, aber von Hand mit `docker compose` verwaltet. Verwende sie, wenn du
eine eigene Docker-Umgebung betreibst und die Dateien lieber selbst
kontrollierst. Compose-Dateien, Image und Konfigurationsformat sind identisch,
du kannst also später zu byroctl wechseln.

## Voraussetzungen

* Docker Engine 24 oder neuer mit dem Compose-Plugin 2.20 oder neuer.
* Ein Reverse Proxy, der TLS terminiert, oder freie Ports 80 und 443 für das
  Caddy-Add-on.
* Ein SMTP-Server zum Mailversand.

## Dateien

Die Installation besteht aus einer Basisdatei mit den byro-Diensten und
optionalen, rein additiven Add-on-Dateien. Sie liegen im Verzeichnis `deploy/`
des byro-Repositorys und werden mit jedem Release versioniert; nimm immer die
Dateien des Release, das du installierst.

Die Basisdatei startet den Web-Dienst, den Runner für periodische Aufgaben und
definiert den Dienst `manage` für einmalige Befehle:

```yaml
--8<-- "deploy/docker-compose.yml"
```

Die eingebaute PostgreSQL ist ein Add-on. Lass es weg, um eine externe
Datenbank zu verwenden:

```yaml
--8<-- "deploy/compose/postgres.yml"
```

Caddy als Reverse Proxy mit automatischem HTTPS ist das zweite Add-on:

```yaml
--8<-- "deploy/compose/caddy.yml"
```

Das dritte Add-on schaltet die byro-Dienste auf ein lokal gebautes Image mit
Plugins um (siehe [Plugins](../administration/plugins.md)):

```yaml
--8<-- "deploy/compose/plugins.yml"
```

Dieses Image wird aus `plugins/Dockerfile` und der Plugin-Liste
`plugins/plugins.txt` im Installationsverzeichnis gebaut:

```docker
--8<-- "deploy/plugins/Dockerfile"
```

Alle Werte kommen aus einer Datei, `byro.conf`, die Docker Compose als `.env`
zur Interpolation liest und den Containern als `env_file` übergibt:

```bash
--8<-- "deploy/byro.conf.example"
```

## Einrichtung

Lege ein Verzeichnis an, lade die Dateien des gewünschten Release (Tag
ersetzen) und verlinke die Konfiguration als `.env`:

```console
$ sudo mkdir -p /opt/byro && sudo chown "$(id -u):$(id -g)" /opt/byro && cd /opt/byro
$ T=v2026.3.0
$ R="https://raw.githubusercontent.com/byro/byro/$T/deploy"
$ curl -fsSLO "$R/docker-compose.yml"
$ mkdir -p compose && curl -fsSL -o compose/postgres.yml "$R/compose/postgres.yml"
$ curl -fsSL -o compose/caddy.yml "$R/compose/caddy.yml" && curl -fsSLO "$R/Caddyfile"
$ curl -fsSL -o byro.conf "$R/byro.conf.example" && chmod 600 byro.conf && ln -s byro.conf .env
```

Bearbeite `byro.conf`:

* `BYRO_DEPLOY_VERSION`: der geladene Tag, z. B. `v2026.3.0`. Das Image
  `ghcr.io/byro/byro:<tag>` wird aus GitHubs Container-Registry geladen.
* `COMPOSE_FILE`: `docker-compose.yml:compose/postgres.yml` für die eingebaute
  Datenbank, für Caddy `:compose/caddy.yml` anhängen. Für eine externe
  Datenbank `compose/postgres.yml` weglassen und `BYRO_DB_HOST` sowie die
  übrigen `BYRO_DB_*`-Werte ausfüllen.
* `BYRO_DB_PASS`: ein langes zufälliges Passwort für die eingebaute Datenbank.
  Der Stack startet nicht, solange es leer ist.
* `BYRO_SITE_URL`, `BYRO_HTTPS`, Sprache, Zeitzone, Mail-Einstellungen.
* `BYRO_TRUST_PROXY=true`, wenn dein eigener Reverse Proxy TLS terminiert. Das
  Caddy-Add-on setzt es für dich.

Setze Werte mit `$`, `#`, Leerzeichen, Anführungszeichen oder Backslashes in
einfache Anführungszeichen; Compose interpoliert `$` in doppelten
Anführungszeichen und in Werten ohne Anführungszeichen.

Dann starte den Stack und lege den ersten Administrator an:

```console
$ docker compose pull
$ docker compose up -d
$ docker compose run --rm manage createsuperuser
```

Der Web-Dienst führt die Datenbankmigrationen beim Start aus; der Dienst
`periodic` wartet, bis der Web-Dienst gesund ist, und führt dann alle zehn
Minuten byros periodische Aufgaben aus. byro lauscht auf `127.0.0.1:8345`,
solange du `BYRO_DEPLOY_BIND` und `BYRO_DEPLOY_PORT` nicht änderst.

### Plugins

Um byro mit Plugins zu betreiben, lade `plugins/Dockerfile` und
`compose/plugins.yml` desselben Release, liste die Plugins als gepinnte
pip-Requirements und baue das abgeleitete Image:

```console
$ mkdir -p plugins && curl -fsSL -o plugins/Dockerfile "$R/plugins/Dockerfile"
$ curl -fsSL -o compose/plugins.yml "$R/compose/plugins.yml"
$ printf '%s\n' 'byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0' > plugins/plugins.txt
$ docker compose build web
$ docker compose run --rm manage migrate
$ docker compose up -d
```

und hänge vor dem Build `:compose/plugins.yml` an `COMPOSE_FILE` an. Das Image
heißt `<COMPOSE_PROJECT_NAME>-plugins:<BYRO_DEPLOY_VERSION>`; baue es nach
jeder Änderung an `plugins.txt` und nach jedem byro-Update neu. Details und
der Plugin-Katalog: [Plugins](../administration/plugins.md).

## Alltäglicher Betrieb

```console
$ docker compose ps
$ docker compose logs -f web
$ docker compose run --rm manage <byro-befehl>
$ docker compose up -d                 Konfigurationsänderungen anwenden
$ docker compose stop
```

## Updates

Lies zuerst die Release Notes der neuen Version. Dann im
Installationsverzeichnis:

1. Datenbank dumpen und Secret Key kopieren:

    ```console
    $ docker compose exec -T db pg_dump -Fc -U byro byro > pre-update.dump
    $ cp data/.secret byro.conf /irgendwo/sicher/
    ```

2. Die Compose-Dateien des neuen Release wie oben laden (sie können sich
   geändert haben) und `BYRO_DEPLOY_VERSION` auf den neuen Tag setzen.
   `BYRO_DEPLOY_IMAGE_DIGEST` leeren, falls du einen Digest gepinnt hattest.
3. `byro.conf.example` des neuen Release mit deiner `byro.conf` vergleichen und
   benötigte neue Optionen ergänzen.
4. Laden und neu starten; der Web-Dienst führt die Migrationen aus:

    ```console
    $ docker compose pull
    $ docker compose up -d
    ```

    Mit Plugins das Basis-Image explizit laden und das abgeleitete Image vor
    `up` neu bauen:

    ```console
    $ docker pull ghcr.io/byro/byro:<neuer tag>
    $ docker compose pull --ignore-buildable
    $ docker compose build web
    $ docker compose up -d
    ```

Downgrades werden nicht unterstützt: Spiele stattdessen den Dump und die
vorherigen Dateien zurück.

## Backups

Sichere `data/` (Dokumente, Uploads, Schlüssel und `.secret`), die Datenbank
(`db/` bei gestopptem Stack, oder ein `pg_dump`) und `byro.conf`. Der Verlust
von `data/.secret` macht alle Sitzungen und MFA-Geräte ungültig.

## Eigene Compose-Einstellungen

Halte lokale Änderungen in einer `docker-compose.override.yml` im selben
Verzeichnis und nimm sie in `COMPOSE_FILE` auf. Bearbeite die geladenen
Dateien nicht, damit du sie beim nächsten Update ersetzen kannst.
