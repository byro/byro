# Administration

Dieser Bereich behandelt die Verwaltung einer laufenden byro-Installation: die
Funktionen, die Administratoren in byro selbst einrichten, und die
Wartungsaufgaben rundherum.

- [Mehr-Faktor-Authentifizierung (MFA)](mfa.md): TOTP für Backend-Nutzer, die
  Richtlinie für Administratoren, Wiederherstellung und die Management
  Commands.
- [PGP-Mailverschlüsselung](pgp.md): ausgehende Mails signieren und Mails an
  Mitglieder mit OpenPGP verschlüsseln.
- [Plugins](plugins.md): wie Plugins in einer byroctl-, Docker-Compose- oder
  Bare-Metal-Installation installiert und gepflegt werden.
- [Update](updating.md): was für ein byro-Update installationswegübergreifend
  gilt, und die Grenzen von Downgrades.
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
