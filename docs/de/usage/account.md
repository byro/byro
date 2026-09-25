# Mein Konto

Dein Benutzermenü (dein Benutzername oben rechts im Office) bündelt drei
Aktionen für dein **eigenes** Konto – anders als „Einstellungen → Benutzer“
in der [Administration](../administration/overview.md), wo Konten verwaltet
werden (auch fremde, sofern du angemeldet bist, siehe die Sicherheitshinweise
dort).

## Eigenes Profil bearbeiten

*Benutzermenü → Mein Profil* öffnet dasselbe Bearbeitungsformular, das auch
zur Verwaltung anderer Konten dient (Benutzername, Name, E-Mail-Adresse,
`is_staff`/`is_superuser`). Es gilt dieselbe Einschränkung wie dort: **jedes
Speichern verlangt ein neues Passwort**, auch wenn du nur deinen Namen oder
deine E-Mail-Adresse ändern willst. Details und Hintergrund:
[Benutzerkonten verwalten](../administration/users-and-login.md#benutzerkonten-verwalten).

## Mehr-Faktor-Authentifizierung

*Benutzermenü → Mehr-Faktor-Authentifizierung* richtet TOTP für dein Konto
ein oder verwaltet es. Eigene Seite: [MFA](mfa.md).

## API-Token

*Benutzermenü → API-Token* zeigt deinen persönlichen Token für die
[REST-API](../development/api.md); *Erneuern* löscht den alten und erzeugt
einen neuen. Der Token funktioniert nur, solange dein Konto `is_staff` ist
(siehe [Benutzerkonten verwalten](../administration/users-and-login.md#benutzerkonten-verwalten));
ohne `is_staff` lässt er sich zwar anzeigen, die API lehnt ihn aber ab.
