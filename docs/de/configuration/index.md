# Konfiguration

byro lässt sich auf zwei Arten konfigurieren: über Konfigurationsdateien oder
über Umgebungsvariablen. Beides lässt sich kombinieren, die Reihenfolge der
Priorität ist:

1. Umgebungsvariablen
2. Konfigurationsdateien
    - Nur die in der Umgebungsvariablen `BYRO_CONFIG_FILE` genannte Datei, wenn
      diese Variable gesetzt ist (byro startet nicht, wenn die Datei fehlt),
      **oder**:
    - die folgenden drei Dateien, wobei eine spätere Datei eine frühere
      überschreibt:
        - `/etc/byro/byro.cfg`
        - `~/.byro.cfg` im Home-Verzeichnis des ausführenden Benutzers
        - `byro.cfg` im Arbeitsverzeichnis des byro-Prozesses (in einem
          Entwicklungs-Checkout das Verzeichnis `src`, neben
          `byro.example.cfg`)
3. Sinnvolle Standardwerte

Die Container-Installationen ([byroctl](../installation/byroctl.md),
[Docker Compose](../installation/docker-compose.md)) verwenden ausschließlich
Umgebungsvariablen, geschrieben als `KEY=VALUE`-Zeilen in `byro.conf`. Die
Bare-Metal-Installation verwendet die Konfigurationsdatei. Beide Formen
beschreiben dieselben Optionen.

Diese Seite erklärt die Optionen nach Abschnitten der Konfigurationsdatei und
nennt jeweils die zugehörige Umgebungsvariable. Eine Konfigurationsdatei sieht
so aus:

```ini
--8<-- "src/byro.example.cfg"
```

<!-- migration note (AP01 GAPS A3/A4): Abschnitt [oidc] und Option https sind noch nicht dokumentiert; kommt in AP07/AP08. -->

## Abschnitt filesystem

### `data`

- Basisverzeichnis für das Media-Verzeichnis und die Logdateien. Wenn es keinen
  zwingenden Grund gibt, diese Dateien zu trennen, ist `data` die einfachste
  Option.
- **Umgebungsvariable:** `BYRO_DATA_DIR`
- **Standard:** ein Verzeichnis `data` neben byros `manage.py`.

### `media`

- Verzeichnis für nutzergenerierte Dateien. Muss für den byro-Prozess
  beschreibbar sein.
- **Umgebungsvariable:** `BYRO_FILESYSTEM_MEDIA`
- **Standard:** ein Verzeichnis `media` im `data`-Verzeichnis (siehe oben).

### `logs`

- Verzeichnis für Logdateien. Muss für den byro-Prozess beschreibbar sein.
- **Umgebungsvariable:** `BYRO_FILESYSTEM_LOGS`
- **Standard:** ein Verzeichnis `logs` im `data`-Verzeichnis (siehe oben).

### `static`

- Verzeichnis für statische Dateien. Muss für den byro-Prozess beschreibbar
  sein; byro legt dort beim Befehl `collectstatic` Dateien ab.
- **Umgebungsvariable:** `BYRO_FILESYSTEM_STATIC`
- **Standard:** ein Verzeichnis `static.dist` neben byros `manage.py`.

## Abschnitt site

### `debug`

- Legt fest, ob byro im Debug-Modus läuft. Nur für Entwicklung und
  Fehlersuche, nicht für den Betrieb.
- **Umgebungsvariable:** `BYRO_DEBUG`
- **Standard:** `True` beim Ausführen von `runserver`, sonst `False`.
  **Betreibe niemals einen Produktivserver im Debug-Modus.**

### `url`

- Erscheint überall, wo byro vollständige URLs erzeugt (zum Beispiel in
  E-Mails), und setzt die erlaubten Hosts.
- **Umgebungsvariable:** `BYRO_SITE_URL`
- **Standard:** `http://localhost`

### `trust_proxy`

- **Nur** auf `True` setzen, wenn byro hinter einem Reverse Proxy (nginx,
  Apache, Caddy, …) läuft, der TLS terminiert und den Header
  `X-Forwarded-Proto` setzt. byro behandelt Anfragen mit
  `X-Forwarded-Proto: https` dann als sicher, was für korrekte absolute URLs
  nötig ist, etwa die OpenID-Connect-Redirect-URI. Bei direkt erreichbarem
  byro auf `False` lassen, weil Clients den Header sonst fälschen könnten.
  Unabhängig von `https`, das nur die Cookie-Sicherheit steuert.
- **Umgebungsvariable:** `BYRO_TRUST_PROXY`
- **Standard:** `False`

### `secret`

- Jede Django-Anwendung hat ein Geheimnis für kryptografische Signaturen. Du
  musst es nicht setzen: byro erzeugt einen Secret Key und speichert ihn in
  einer lokalen Datei, wenn du ihn nicht manuell setzt.
- **Standard:** keiner

## Abschnitt database

### `name`

- Name der Datenbank.
- **Umgebungsvariable:** `BYRO_DB_NAME`
- **Standard:** `''`

### `user`

- Datenbankbenutzer.
- **Umgebungsvariable:** `BYRO_DB_USER`
- **Standard:** `''`

### `password`

- Datenbankpasswort.
- **Umgebungsvariable:** `BYRO_DB_PASS`
- **Standard:** `''`

### `host`

- Datenbank-Host oder Socket-Pfad, je nach Bedarf.
- **Umgebungsvariable:** `BYRO_DB_HOST`
- **Standard:** `''`

### `port`

- Datenbank-Port.
- **Umgebungsvariable:** `BYRO_DB_PORT`
- **Standard:** `''`

### `engine`

- Datenbank-Backend.
- **Umgebungsvariable:** `BYRO_DB_ENGINE`
- **Standard:** `'postgresql'`
- **Mögliche Werte:** `postgresql`, `mysql`, `sqlite3`, `oracle`

## Abschnitt mail

### `from`

- Absenderadresse als Rückfall, zum Beispiel für ereignisunabhängige Mails.
- **Umgebungsvariable:** `BYRO_MAIL_FROM`
- **Standard:** `admin@localhost`

### `host`

- Adresse des Mailservers.
- **Umgebungsvariable:** `BYRO_MAIL_HOST`
- **Standard:** `localhost`

### `port`

- Port des Mailservers.
- **Umgebungsvariable:** `BYRO_MAIL_PORT`
- **Standard:** `25`

### `user`

- Benutzerkonto für die Anmeldung am Mailserver, falls nötig.
- **Umgebungsvariable:** `BYRO_MAIL_USER`
- **Standard:** `''`

### `password`

- Passwort für die Anmeldung am Mailserver, falls nötig.
- **Umgebungsvariable:** `BYRO_MAIL_PASSWORD`
- **Standard:** `''`

### `tls`

- Soll byro beim Mailversand TLS verwenden? Entweder TLS oder SSL wählen.
- **Umgebungsvariable:** `BYRO_MAIL_TLS`
- **Standard:** `False`

### `ssl`

- Soll byro beim Mailversand SSL verwenden? Entweder TLS oder SSL wählen.
- **Umgebungsvariable:** `BYRO_MAIL_SSL`
- **Standard:** `False`

## Abschnitt pgp

### `backend`

- Python-Importpfad des PGP-Backends für Signieren, Verschlüsseln und
  Schlüsselimport.
- **Umgebungsvariable:** `BYRO_PGP_BACKEND`
- **Standard:** `byro.mails.gnupg_backend.GnuPGBackend`

### `home`

- GnuPG-Home-Verzeichnis für byro. Dort liegen die von byro importierten
  öffentlichen Schlüssel, und dort sucht GnuPG den privaten Signaturschlüssel
  der Organisation. Sollte nur für den byro-Benutzer lesbar und beschreibbar
  sein.
- **Umgebungsvariable:** `BYRO_PGP_HOME`
- **Standard:** `''`, GnuPG verwendet seinen normalen Standard für den
  ausführenden Benutzer.

## Abschnitt logging

### `email`

- E-Mail-Adresse (oder mehrere, durch Komma getrennt), an die Systemlogs
  gesendet werden.
- **Umgebungsvariable:** `BYRO_LOGGING_EMAIL`
- **Standard:** `''`

### `email_level`

- Log-Level, ab dem Mails verschickt werden. Einer von
  `[DEBUG, INFO, WARNING, ERROR, CRITICAL]`.
- **Umgebungsvariable:** `BYRO_LOGGING_EMAIL_LEVEL`
- **Standard:** `'ERROR'`

## Abschnitt locale

### `language_code`

- Standardsprache des Systems.
- **Umgebungsvariable:** `BYRO_LANGUAGE_CODE`
- **Standard:** `'de'`

<!-- migration note (AP01 GAPS A2): der Standard im Code ist 'en'; wird in AP07 korrigiert. -->

### `time_zone`

- Standardzeitzone des Systems als `pytz`-Name.
- **Umgebungsvariable:** `BYRO_TIME_ZONE`
- **Standard:** `'UTC'`
