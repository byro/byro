# Update

Diese Seite bündelt, was für ein byro-Update unabhängig vom Installationsweg
gilt. Die genauen Befehle unterscheiden sich je Weg und stehen auf der
jeweiligen Installationsseite:

- [Update mit byroctl](../installation/byroctl.md#updates)
- [Update mit Docker Compose](../installation/docker-compose.md#updates)
- [Update bei Bare-Metal-Installationen](../installation/bare-metal.md#nachste-schritte-updates)

## Vor jedem Update

1. Lies die [Release Notes](https://github.com/byro/byro/releases) der
   Zielversion. byro markiert Releases mit breaking changes oder Änderungen an
   Dateien in `data/` ausdrücklich; byroctl fragt in diesen Fällen nach, bevor
   es weitermacht.
2. Erstelle ein vollständiges Backup (siehe
   [Backup und Restore](backup-restore.md)), nicht nur die automatische
   Pre-Update-Sicherheitskopie, die byroctl anlegt. Bei einer Docker-Compose-
   oder Bare-Metal-Installation gibt es diese automatische Kopie nicht;
   sichere dort selbst, bevor du aktualisierst.
3. Aktualisiere Plugins nach der gleichen Logik wie byro selbst und prüfe ihre
   eigenen Release Notes (siehe [Plugin-Verwaltung](plugin-management.md#was-ein-byro-update-mit-plugins-macht)).

## Was während eines Updates passiert

Bei allen drei Wegen läuft ein Update in derselben Reihenfolge ab: neue
Artefakte (Compose-Dateien, Image oder Paket) laden, Konfiguration auf neue
Optionen prüfen, byro stoppen, Datenbankmigrationen ausführen, byro mit der
neuen Version starten. byroctl automatisiert das vollständig inklusive
Sicherheitskopie; bei Docker Compose von Hand und bei Bare Metal führst du die
Schritte selbst aus.

## Downgrade-Grenzen

**Downgrades werden nicht unterstützt.** Datenbankmigrationen laufen bei byro
nur vorwärts; es gibt keine geprüften, umkehrbaren Migrationen für ein
Downgrade. Willst du eine fehlgeschlagene Aktualisierung rückgängig machen,
spiele stattdessen dein Backup von vor dem Update zurück (Datenbank, `data/`,
Konfiguration) – siehe [Restore](backup-restore.md#restore). Das ist auch der
Grund, warum ein vollständiges, aktuelles Backup vor jedem Update Pflicht ist
und nicht optional.

## Wenn ein Update fehlschlägt

Schlägt eine Migration fehl, bleiben die byro-Dienste gestoppt. Behebe die
Ursache und starte erneut, oder spiele die Sicherheitskopie zurück (siehe
[Restore](backup-restore.md#restore)). Kombiniere niemals eine bereits
migrierte Datenbank mit dem Code der vorherigen Version: Ein Downgrade des
Codes allein macht ein fehlgeschlagenes Update nicht rückgängig, wenn die
Migration schon (teilweise) angewendet wurde.
