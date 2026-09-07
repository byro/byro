# Konfiguration

Dieser Bereich behandelt, was du *innerhalb* einer laufenden byro-Installation
einrichtest, über das Office – unabhängig davon, wie und wo byro betrieben
wird.

- [Benutzer und Login](users-and-login.md): Konten anlegen und bearbeiten,
  Passwort- und OIDC/SSO-Login, was `is_staff`/`is_superuser` wirklich
  bedeuten.
- [Mehr-Faktor-Authentifizierung (MFA)](mfa.md): Richtlinie für alle Konten
  vorschreiben, Status prüfen, Wiederherstellung und die Management Commands
  (die persönliche Einrichtung steht im
  [Benutzerhandbuch](../usage/mfa.md)).
- [PGP-Mailverschlüsselung](pgp.md): ausgehende Mails signieren und Mails an
  Mitglieder mit OpenPGP verschlüsseln.
- [Einstellungen](settings.md): Vereinskonfiguration, Registrierungsformular,
  Über byro und das Audit-Log.
- [Konfigurationsreferenz](../configuration/index.md): alle Optionen aus
  `byro.cfg`/den `BYRO_*`-Umgebungsvariablen.

Dein eigenes Profil, deine persönliche MFA-Einrichtung und dein API-Token
sind über dein Benutzermenü erreichbar, nicht über diese Seite – siehe
[Mein Konto](../usage/account.md) im Benutzerhandbuch. Serverbetrieb, Update,
Backup und Restore, Monitoring und die Sicherheits-Baseline gehören zum
technischen Selbst-Hosting und stehen unter [Administration](operations.md);
welche Plugins es gibt und wie sie installiert werden, steht unter
[Plugins & Integrationen](plugins.md).
