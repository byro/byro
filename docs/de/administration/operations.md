# Administration

Was installationswegübergreifend für den laufenden Betrieb einer
byro-Installation gilt – unabhängig davon, ob sie mit byroctl, Docker Compose
oder Bare Metal aufgesetzt wurde (siehe [Installation](../installation/overview.md)).
Was du danach *in* byro einrichtest (Benutzerkonten, Login, MFA, Einstellungen)
steht unter [Konfiguration](overview.md).

- [Update](updating.md): was für ein Update gilt, und die Grenzen von
  Downgrades.
- [Backup und Restore](backup-restore.md): was gesichert werden muss,
  Wiederherstellung und Umzug auf einen neuen Host.
- [Management-Befehle](management-commands.md): Referenz der
  Kommandozeilenbefehle für Einrichtung, Wartung und Kontoverwaltung.
- [Monitoring, Logging und Fehlersuche](troubleshooting.md): Health-Checks,
  Log-Speicherorte, Ressourcen/Skalierung und häufige Probleme.
- [Sicherheits-Baseline](security-baseline.md): TLS, Geheimnisse,
  Container-Rechte und Konto-Wiederherstellung im Überblick.

Die genauen Update- und Backup-Befehle je Installationsweg stehen weiterhin
auf den Installationsseiten
([byroctl](../installation/byroctl.md#updates),
[Docker Compose](../installation/docker-compose.md#updates),
[Bare Metal](../installation/bare-metal.md#nachste-schritte-updates)).
