# Sicherheits-Baseline

Diese Seite bündelt die betrieblichen Sicherheitsentscheidungen, die für
jede byro-Installation gelten, unabhängig vom Installationsweg. Anmeldung
(OIDC, Passwort-Login) und Benutzerrollen stehen unter
[Benutzer und Login](users-and-login.md), das Audit-Log unter
[Einstellungen](settings.md#audit-log),
[Mehr-Faktor-Authentifizierung](mfa.md) auf ihrer eigenen Seite.

## TLS und Reverse Proxy

**Betreibe byro nie ohne HTTPS**, außer zu Testzwecken. byro verarbeitet
personenbezogene und finanzielle Daten der Mitglieder.

* Mit `BYROCTL_PROXY=caddy` (byroctl-Standard) beschafft und erneuert Caddy
  automatisch ein Let's-Encrypt-Zertifikat.
* Mit einem eigenen Reverse Proxy muss dieser TLS terminieren, den Header
  `X-Forwarded-Proto` setzen, und byro muss `[site] trust_proxy`
  (`BYRO_TRUST_PROXY=true`) gesetzt haben, damit es weitergeleitete Anfragen
  korrekt als sicher behandelt (absolute URLs, Cookie-Sicherheit,
  OIDC-Redirects). **Setze `trust_proxy` niemals, wenn byro ohne einen
  solchen Proxy direkt erreichbar ist** – Clients könnten den Header sonst
  fälschen und byro zu Unrecht vertrauen lassen.
* Liefere `/media/` nie direkt über den Webserver aus: byro gibt Dokumente
  erst nach eigener Zugriffsprüfung heraus. Ein Alias auf das Media-Verzeichnis
  im Reverse Proxy legt jedes hochgeladene Dokument gegenüber jedem offen, der
  die URL kennt.

## Geheimnisse und ihre Sicherung

* **`data/.secret`** enthält Djangos `SECRET_KEY`, aus dem unter anderem die
  Verschlüsselung der TOTP-Geheimnisse abgeleitet wird. Sein Verlust macht
  alle Sitzungen und alle MFA-Geräte ungültig; es gibt keine Möglichkeit,
  einen vorherigen Schlüssel als Fallback anzugeben (siehe
  [MFA](mfa.md#sicherheitshinweise)). Sichere ihn wie in
  [Backup und Restore](backup-restore.md) beschrieben.
* **`byro.conf`/`byro.cfg`** enthält Datenbank- und Mail-Passwörter sowie ggf.
  das OIDC-Client-Secret. Halte die Datei bei `0600` (byroctl und die
  Installationsanleitungen setzen das) und behandle Kopien entsprechend
  vertraulich.
* **Passwörter nie auf der Kommandozeile.** `byroctl install`/`config set`
  nehmen Geheimnisse nur aus Umgebungsvariablen entgegen
  (`BYROCTL_ADMIN_PASSWORD`, `BYROCTL_DB_PASSWORD`, `BYROCTL_MAIL_PASSWORD`,
  `BYROCTL_OIDC_CLIENT_SECRET`), nie als `--set`-Wert, damit sie nicht in
  einer Prozessliste oder Shell-Historie landen.

## Container-Rechte

Die Container-Images laufen standardmäßig unprivilegiert als Benutzer `byro`.
Der Entrypoint startet zwar als root, aber nur um optional `BYRO_UID`/
`BYRO_GID` anzuwenden (fail-closed: nur numerische, nicht bereits vergebene,
nicht-root-IDs werden akzeptiert) und die Eigentümerschaft des
Datenverzeichnisses anzupassen, danach legt er die Rechte dauerhaft ab.
Ändere `BYRO_UID`/`BYRO_GID` nur, wenn du `data/` mit einem bestimmten
Host-Benutzer teilen musst.

## Konto-Wiederherstellung

byro hat keinen Self-Service-Passwort-Reset für Office-Konten. Das ist eine
bewusste Lücke, kein Versehen: Der Wiederherstellungsweg für ein
ausgesperrtes Administratorkonto führt über die Kommandozeile
(`changepassword`/`createsuperuser`), siehe
[Konto-Wiederherstellung](troubleshooting.md#konto-wiederherstellung). Wer
Zugriff auf die Server-Kommandozeile hat, kann also jedes Konto
übernehmen – schütze den Server-Zugang entsprechend.

## Web-Sicherheitsheader

byro setzt einige Header fest, ohne Konfigurationsoption:
`X-Frame-Options: DENY` (kein Einbetten in fremde `<iframe>`s),
`X-Content-Type-Options: nosniff` sowie einen eigenen Cookie-Namen für
Session (`byro_session`) und CSRF (`byro_csrftoken`).
`CSRF_TRUSTED_ORIGINS` wird automatisch aus `[site] url` abgeleitet, du musst
es nicht selbst pflegen. Es gibt **keine HSTS-Einstellung im Code** – dafür
ist dein Reverse Proxy zuständig (das Caddy-Add-on setzt es nicht automatisch;
ergänze es in einem eigenen Caddyfile-Snippet oder deiner Proxy-Konfiguration,
falls gewünscht).

## Was hier absichtlich fehlt

OpenID-Connect-Login, Benutzerrollen/`is_staff` und das Audit-Log sind
sicherheitsrelevant, aber Sache der Administration *in* byro, nicht des
Selbst-Hostings; sie stehen unter
[Benutzer und Login](users-and-login.md) und
[Einstellungen](settings.md#audit-log). Kurz zur Einordnung: Die
API-Dokumentation (`/api/v1/docs/`) und das API-Schema (`/api/v1/schema/`)
sind ohne Login erreichbar, die API selbst verlangt einen Token und setzt
`is_staff` voraus (siehe [API](../development/api.md)).
