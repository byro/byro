# Mein Konto

Dein Benutzermenü (dein Benutzername oben rechts im Office) bündelt drei
Aktionen für dein **eigenes** Konto – anders als „Einstellungen → Benutzer“
in der [Administration](../administration/overview.md), wo Superuser alle
Konten verwalten (siehe
[Berechtigungsmodell](../administration/users-and-login.md#berechtigungsmodell)).

## Eigenes Profil bearbeiten

*Benutzermenü → Mein Profil* öffnet das Bearbeitungsformular für dein eigenes
Konto (Benutzername, Name, E-Mail-Adresse). Jedes Konto mit Zugriff auf das
Office kann es nutzen. Die Felder für Staff- und Superuser-Status sehen nur
Superuser; ein Staff-Konto kann seine eigenen Rechte hier also nicht ändern.
Ein Superuser kann seinen eigenen Staff-Status ändern, sich den
Superuser-Status aber nicht selbst entziehen. Es gilt dieselbe Einschränkung
wie in der Benutzerverwaltung: **jedes Speichern verlangt ein neues
Passwort**, auch wenn du nur deinen Namen oder deine E-Mail-Adresse ändern
willst. Details und Hintergrund:
[Benutzerkonten verwalten](../administration/users-and-login.md#benutzerkonten-verwalten).

## Mehr-Faktor-Authentifizierung

*Benutzermenü → Mehr-Faktor-Authentifizierung* richtet TOTP für dein Konto
ein oder verwaltet es. Eigene Seite: [MFA](mfa.md).

## API-Token

*Benutzermenü → API-Token* zeigt deinen persönlichen Token für die
[REST-API](../development/api.md); *Erneuern* löscht den alten und erzeugt
einen neuen. Der Token funktioniert nur, solange dein Konto Staff oder
Superuser ist (siehe
[Berechtigungsmodell](../administration/users-and-login.md#berechtigungsmodell));
ohne eines der beiden Flags lehnt die API ihn ab.
