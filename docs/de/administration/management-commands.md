# Management-Befehle

byro wird über Management-Befehle administriert, dem Django-üblichen Weg für
Aufgaben, die keine Weboberfläche brauchen. Rufe sie so auf:

```console
$ byroctl manage <befehl> [argumente]           # byroctl
$ docker compose run --rm manage <befehl> [argumente]   # Docker Compose von Hand
$ python -m byro <befehl> [argumente]           # Bare Metal
```

Die folgenden Beispiele zeigen die byroctl-Form; ersetze sie nach Bedarf.

## Einrichtung und Wartung

* `migrate` – Datenbankmigrationen ausführen. Läuft bei byroctl und Docker
  Compose automatisch beim Start des Web-Dienstes (`BYRO_AUTO_MIGRATE`,
  Standard an); bei Bare Metal manuell nach jedem Update.
* `rebuild` – kompiliert Übersetzungen (auch die installierter Plugins),
  sammelt statische Dateien (`collectstatic`) und komprimiert sie
  (`compress`). Nach jedem Bare-Metal-Update und nach jeder Plugin-Änderung
  nötig; die Container-Images bringen das Ergebnis bereits gebaut mit.
* `runperiodic` – führt byros periodische Aufgaben einmal aus (PGP-Refresh,
  Ablauferinnerungen, Aufräumen unvollendeter MFA-Einrichtungen). Bei
  byroctl/Docker Compose übernimmt das der `periodic`-Dienst automatisch alle
  `BYRO_DEPLOY_PERIODIC_INTERVAL` Sekunden; bei Bare Metal ein systemd-Timer
  (siehe [Bare-Metal-Installation](../installation/bare-metal.md#schritt-6-byro-als-dienst-starten)).
* `check --deploy` – Djangos Produktions-Checkliste; läuft auch beim
  Container-Start (`python -m byro check`) und in CI.
* `make_testdata` – füllt eine leere Installation mit Testdaten. Nur für
  Ausprobieren und Entwicklung, nicht für eine Installation mit echten Daten.

## Kontoverwaltung

* `createsuperuser` – legt ein neues Administratorkonto an (Django-Standard).
* `changepassword <benutzername>` – setzt das Passwort eines bestehenden
  Kontos zurück (Django-Standard). byro hat keinen Self-Service-Passwort-Reset;
  das ist der Weg, ein ausgesperrtes Administratorkonto wiederherzustellen
  (siehe [Konto-Wiederherstellung](troubleshooting.md#konto-wiederherstellung)).
* `mfa_status <benutzername oder e-mail>` und
  `mfa_reset <benutzername oder e-mail>` – MFA-Status abfragen bzw. alle
  MFA-Geräte eines Kontos entfernen (siehe
  [MFA-Status eines Benutzers prüfen](mfa.md#mfa-status-eines-benutzers-prufen)
  und
  [MFA eines Benutzers zurücksetzen](mfa.md#mfa-eines-benutzers-zurucksetzen-notfallwiederherstellung)).

## Prüfung und Export

* `export_logchain` – exportiert die vollständige Hash-Kette als JSON (jeder
  Eintrag mit Hash und authentifizierten Metadaten); relevant für Vereine mit
  Prüfpflichten. Alle Einträge erscheinen immer; `-a`/`--data-include-actions`
  und `-A`/`--data-exclude-actions` (je ein Regex auf `action_type`, Standard
  für `-a` ist „alles“) steuern nur, ob das Feld `data` je Eintrag mit
  exportiert wird oder nicht – nützlich, um sensible Nutzdaten aus einem
  weitergegebenen Export herauszuhalten, ohne die Kette selbst zu verändern.
  Siehe [Audit-Log](settings.md#audit-log) für den Hintergrund.

## Referenz

`<befehl> --help` zeigt alle Argumente eines Befehls; `help` ohne Argument
listet alle verfügbaren Befehle, einschließlich der von Plugins und von
Django/Django-Apps selbst (zum Beispiel `dbshell`, `shell`), die hier nicht
einzeln aufgeführt sind.
