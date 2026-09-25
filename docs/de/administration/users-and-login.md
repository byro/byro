# Benutzer und Login

Diese Seite beschreibt, wer sich am byro-Office anmelden kann, wie das
Login funktioniert und wie du Benutzerkonten verwaltest. Für
Mehr-Faktor-Authentifizierung siehe die eigene Seite
[MFA](mfa.md); für den technischen Serverbetrieb (TLS, Secret Key,
Container-Rechte) siehe
[Sicherheits-Baseline](security-baseline.md).

!!! warning
    byro kennt **keine abgestuften Rollen im Office**: Jedes Konto, das sich
    erfolgreich anmeldet, sieht und bedient das gesamte Office – Mitglieder,
    Finanzen, Einstellungen, andere Benutzerkonten eingeschlossen. Es gibt
    keinen Nur-Lese-Zugang und keine Beschränkung auf einzelne Bereiche. Wäge
    das ab, bevor du OIDC-Autoprovisionierung aktivierst oder Konten anlegst.

## Erstlogin

Solange **Name**, **Absenderadresse** und **Benachrichtigungsadresse**
(Einstellungen → Allgemein, siehe [Einstellungen](settings.md)) nicht gesetzt
sind, leitet byro jedes angemeldete Konto (außer während des MFA-Ablaufs) auf
die Ersteinrichtung um. Das betrifft auch ein frisch per OIDC angelegtes
Konto, nicht nur den ersten Administrator.

## Passwort-Login

Der Standardweg: Benutzername und Passwort, geprüft gegen das lokale Konto.
Ein Konto ohne nutzbares Passwort (siehe „Passwort deaktivieren“ unten) kann
sich nicht per Passwort anmelden – NUR mit einer der anderen aktivierten
Methoden.

## OIDC/SSO-Login

Ist `[oidc] issuer_url` gesetzt (siehe
[Konfiguration](../configuration/reference.md#abschnitt-oidc)), zeigt die
Login-Seite zusätzlich einen SSO-Button. Der Ablauf:

1. byro leitet zum OIDC-Anbieter weiter (Authorization-Code-Flow mit `state`
   und `nonce`).
2. Nach erfolgreicher Anmeldung beim Anbieter validiert byro den ID-Token
   (Signatur über die JWKS des Anbieters, Aussteller, Zielgruppe, Ablauf,
   `nonce`).
3. Ist `admin_group` gesetzt, muss der Claim `groups` diesen Wert enthalten,
   sonst schlägt der Login fehl – **das ist die einzige Zugriffsprüfung, die
   OIDC bietet.** Sie entscheidet nur, wer sich anmelden darf, nicht, was das
   Konto danach im Office darf (siehe Warnung oben).
4. byro sucht ein bestehendes Konto mit dem Benutzernamen aus `username_field`
   (Standard `preferred_username`). Findet es keins und ist
   `auto_create_account` aktiviert, legt es ein neues, **passwortloses** Konto
   an (`is_staff`/`is_superuser` bleiben dabei `False`, siehe unten). Ist
   `auto_create_account` deaktiviert, schlägt der Login für unbekannte
   Benutzernamen fehl.
5. Ist das gefundene oder angelegte Konto `is_active=False`, wird die
   Anmeldung mit einer Fehlermeldung abgelehnt.

**Fehlerfälle** (abgelaufener Code, ungültiger `state`, Ablehnung durch den
Anbieter, Netzwerkfehler beim Anbieter) landen alle als Fehlermeldung auf der
Login-Seite; es gibt keine gesonderte Fehlerseite und keinen Rückfall auf
Passwort-Login im selben Versuch.

!!! warning
    „Passwort deaktivieren“ (siehe unten) sperrt nur die
    Passwort-Anmeldung dieses Kontos. Ist OIDC konfiguriert und der
    Benutzername identisch, kann sich das Konto weiterhin per OIDC anmelden.
    Um ein Konto vollständig zu sperren, muss es beim OIDC-Anbieter selbst
    entfernt oder deaktiviert werden (`admin_group` verlassen lassen genügt,
    falls konfiguriert), oder `is_active` muss falsch sein.

## Benutzerkonten verwalten

Unter „Einstellungen → Benutzer“ (`settings/users/`) siehst du alle Konten,
legst neue an und bearbeitest bestehende. Jedes Konto hat:

- **Benutzername**, **Name**, **E-Mail-Adresse**,
- **`is_staff`**: Voraussetzung für Zugriff auf die REST-API (siehe
  [API](../development/api.md)). Hat **keine** weitere
  Wirkung auf das Office selbst.
- **`is_superuser`**: byro wertet dieses Feld **an keiner Stelle** selbst aus
  (kein Django-Admin-Interface eingebunden). Es erscheint im Audit-Log, hat
  aber im laufenden Betrieb keinen praktischen Effekt.

!!! note
    Da es keine Rollen gibt (siehe Warnung oben), unterscheiden `is_staff`
    und `is_superuser` **nicht**, wer wie viel im Office darf – nur `is_staff`
    hat mit dem API-Zugriff überhaupt eine Auswirkung.

**Passwort beim Bearbeiten:** Das Bearbeitungsformular verlangt bei **jedem**
Speichern ein neues Passwort für das Konto – auch wenn du nur den Namen oder
`is_staff` änderst. Es gibt keine Möglichkeit, andere Felder zu ändern, ohne
gleichzeitig ein neues Passwort zu vergeben. Informiere die betroffene Person
danach über das neue Passwort, oder nutze stattdessen
`changepassword` (siehe [Management-Befehle](management-commands.md#kontoverwaltung)),
wenn du nur ein bekanntes Passwort setzen willst, ohne das Bearbeitungsformular
zu öffnen.

**Passwort deaktivieren** (`settings/users/<pk>/disable-password`) setzt ein
unbrauchbares Passwort; das Konto kann sich danach nicht mehr per Passwort
anmelden (siehe die OIDC-Warnung oben zur Wechselwirkung). Es lässt sich nicht
selbst auf das eigene Konto anwenden. Um das Passwort wieder zu aktivieren,
speichere das Bearbeitungsformular mit einem neuen Passwort.

**Es gibt keine Möglichkeit, ein Konto zu löschen oder zu deaktivieren**
(`is_active=False` zu setzen) über die Office-Oberfläche. „Passwort
deaktivieren“ ist die einzige eingebaute Möglichkeit, ein Konto
einzuschränken, und blockiert wie oben beschrieben nur die
Passwort-Anmeldung.

Es gibt **keinen Self-Service-Passwort-Reset** und keinen Einladungs-Workflow
für neue Konten; ein Administrator legt jedes Konto selbst mit einem
Erstpasswort an. Ist niemand mehr angemeldet, der ein neues Konto anlegen
kann, hilft nur der Server-Zugang, siehe
[Konto-Wiederherstellung](troubleshooting.md#konto-wiederherstellung).

## MFA-Pflicht

Ob Mehr-Faktor-Authentifizierung optional oder für alle Konten vorgeschrieben
ist, wird global eingestellt, nicht je Konto: siehe
[MFA-Richtlinie wählen](mfa.md#mfa-richtlinie-wahlen).

## Anmeldeverhalten

- Sitzungscookie heißt `byro_session`, CSRF-Cookie `byro_csrftoken`; beide
  sind Django-Standardsitzungen ohne festes Ablaufdatum außer dem
  Browser-Session-Ende (kein `SESSION_COOKIE_AGE` gesetzt).
- **Kein Login-Lockout:** byro sperrt ein Konto nach falschen Passwortversuchen
  nicht (weder zeitlich noch dauerhaft; das gilt nur für MFA-Codes, siehe
  [MFA](mfa.md#sicherheitshinweise)). Ein externer Schutz (Reverse Proxy,
  Fail2ban) ist deine Sache.
- **Fehlgeschlagene Passwort-Logins landen nicht im Audit-Log** – nur
  erfolgreiche Logins, Logins auf deaktivierte Konten und Logouts werden
  protokolliert (siehe [Audit-Log](settings.md#audit-log)).
