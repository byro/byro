# Monitoring, Logging und Fehlersuche

## Health-Check

byro beantwortet unauthentifiziert `GET /healthz` mit `200 {"status": "ok"}`,
wenn die Datenbankverbindung funktioniert, sonst mit `503`. Der Endpunkt prüft
absichtlich nur das und nichts weiter (keine Version, keine Konfiguration).
Für ein eigenes Monitoring reicht ein HTTP-Check auf diesen Pfad mit dem
richtigen `Host`-Header (deine `BYRO_SITE_URL` bzw. `[site] url`), da byros
`ALLOWED_HOSTS`-Prüfung auch hier gilt.

* **byroctl/Docker Compose:** Der Container-Healthcheck ruft `/healthz`
  bereits intern ab; `docker compose ps` zeigt den Status
  (`healthy`/`unhealthy`/`starting`), und `byroctl start`, `update` und
  `config set --apply` warten darauf (Timeout über
  `BYROCTL_WEB_HEALTH_TIMEOUT`, siehe
  [byroctl](../installation/byroctl.md#umgebungsvariablen)). Ein externes
  Monitoring kann denselben Pfad über den konfigurierten Reverse Proxy
  abfragen.
* **Bare Metal:** Kein eingebauter Healthcheck-Prozess; richte einen externen
  HTTP-Check auf `https://deine-domain/healthz` ein oder frage lokal über
  gunicorn ab.

## Logging

* **byroctl/Docker Compose:** `byroctl logs [-f] [SERVICE...]` bzw.
  `docker compose logs [-f] [SERVICE...]` zeigt die Container-Logs (byro
  schreibt nach stdout/stderr, nicht in Dateien im Container). Zusätzlich
  legt byro Logdateien in `BYRO_FILESYSTEM_LOGS` innerhalb des
  Datenverzeichnisses an (siehe [Konfiguration](../configuration/reference.md#abschnitt-filesystem)).
* **Bare Metal:** `journalctl -u byro-web` bzw. `journalctl -u
  byro-periodic` zeigen die systemd-Logs; das Logverzeichnis aus
  `[filesystem] logs` enthält zusätzlich byros eigene Logdateien. Die
  Startausgabe von byro nennt dieses Verzeichnis.
* **Fehler per Mail:** Der Abschnitt `[logging]` (`BYRO_LOGGING_EMAIL`,
  `BYRO_LOGGING_EMAIL_LEVEL`) schickt Log-Meldungen ab einem einstellbaren
  Schweregrad per Mail, unabhängig vom Installationsweg (siehe
  [Konfiguration](../configuration/reference.md#abschnitt-logging)). Das ist
  sinnvoll, um von Serverfehlern zu erfahren, ohne die Logs aktiv zu
  beobachten.

## Ressourcen und Skalierung

byro skaliert innerhalb eines Servers über die Anzahl gunicorn-Worker
(`BYRO_DEPLOY_WEB_WORKERS` bei Docker/byroctl, `--workers` in der
systemd-Unit bei Bare Metal). Es gibt **keine eingebaute horizontale
Skalierung über mehrere Hosts**: Der Secret Key liegt lokal in
`data/.secret`, es gibt keine verteilte Job-Queue für periodische Aufgaben
(genau ein `periodic`-Prozess sollte laufen, sonst laufen Aufgaben doppelt),
und Uploads landen im lokalen Datenverzeichnis. Mehrere `web`-Prozesse auf
verschiedenen Hosts vor derselben Datenbank sind möglich, wenn sie sich
`data/` (insbesondere `.secret` und Media) und genau einen `periodic`-Prozess
teilen; byroctl unterstützt das nicht eingebaut.

## Konto-Wiederherstellung

byro hat **keinen Self-Service-Passwort-Reset** für Office-Konten. Ist ein
Administrator ausgesperrt, setze ein neues Passwort über einen
Management-Befehl (siehe
[Management-Befehle](management-commands.md#kontoverwaltung)):

```console
$ byroctl manage changepassword <benutzername>
$ docker compose run --rm manage changepassword <benutzername>
$ python -m byro changepassword <benutzername>
```

Existiert noch kein Administratorkonto mehr, lege mit `createsuperuser` (auf
demselben Weg) ein neues an. Für einen MFA-bedingten Aussperr-Fall (Gerät
verloren) siehe
[MFA eines Benutzers zurücksetzen](mfa.md#mfa-eines-benutzers-zurucksetzen-notfallwiederherstellung).

## Häufige Probleme

* **`byroctl config check` meldet einen Fehler in `byro.conf`.** Meist ein
  nicht in einfache Anführungszeichen gesetzter Wert mit `$`, `#`, Leerzeichen
  oder Backslash (siehe [byroctl](../installation/byroctl.md#konfiguration)).
* **Ein Port ist bei der Installation bereits belegt.** Ein anderer Dienst
  lauscht dort; wähle einen eigenen Reverse-Proxy-Modus oder einen anderen
  `BYRO_DEPLOY_PORT`.
* **byro wird nicht gesund (`wait_healthy`/Container `unhealthy`).** Prüfe die
  Logs des Web-Dienstes: Meist eine fehlgeschlagene Datenbankverbindung, eine
  fehlende Pflichtvariable (`BYRO_DB_PASS` leer lässt den Stack gar nicht
  erst starten) oder eine fehlgeschlagene Migration.
* **Absolute URLs sind `http://` statt `https://`, oder OIDC-Redirects
  schlagen fehl.** `[site] trust_proxy` (`BYRO_TRUST_PROXY`) ist nicht gesetzt,
  obwohl ein Reverse Proxy TLS terminiert (siehe
  [Sicherheits-Baseline](security-baseline.md#tls-und-reverse-proxy)).
* **Plugin-Build schlägt fehl.** Siehe die
  [Fehlersuche bei Plugins](plugin-management.md#fehlersuche).
