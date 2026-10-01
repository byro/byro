# Benutzer und Login

Diese Seite beschreibt, wer sich am byro-Office anmelden kann, wie das
Login funktioniert und wie du Benutzerkonten verwaltest. Für
Mehr-Faktor-Authentifizierung siehe die eigene Seite
[MFA](mfa.md); für den technischen Serverbetrieb (TLS, Secret Key,
Container-Rechte) siehe
[Sicherheits-Baseline](security-baseline.md).

## Berechtigungsmodell

byro unterscheidet über die beiden Flags `is_staff` und `is_superuser` drei
Arten von Konten:

| `is_staff` | `is_superuser` | Office und API | Einstellungen, Registrierungsformular, Benutzer, Log |
|---|---|---|---|
| nein | nein | nein | nein |
| ja | nein | ja | nein |
| nein | ja | ja | ja |
| ja | ja | ja | ja |

- **Kein Flag:** Das Konto kann sich weder am Office anmelden noch die
  authentifizierte API nutzen.
- **Staff (`is_staff`):** normaler Zugriff auf das Office – Mitglieder,
  Finanzen, Dokumente, Mails, das eigene Profil – und auf die API.
- **Superuser (`is_superuser`):** alles, was Staff darf, dazu die
  administrativen Funktionen, die in dieser Dokumentation mit
  **nur Superuser** gekennzeichnet sind: die
  [Ersteinrichtung](settings.md#ersteinrichtung), die
  [allgemeinen Einstellungen](settings.md#allgemein), das
  [Registrierungsformular](settings.md#registrierungsformular), das
  [Audit-Log](settings.md#audit-log) und die
  [Benutzerverwaltung](#benutzerkonten-verwalten). Ein Superuser kann sich
  immer anmelden, auch ohne `is_staff`; eine widersprüchliche Kombination der
  Flags sperrt also keinen Superuser aus. In der deutschen Oberfläche heißt
  der Superuser „Administrator“.

Diese Regeln setzt der Server durch, nicht nur das Ausblenden von
Menüeinträgen. Ein Staff-Konto, das eine Superuser-Seite direkt aufruft,
erhält eine Fehlerseite (HTTP 403). Ein Konto, das beide Flags verliert,
während es angemeldet ist, wird mit dem nächsten Aufruf abgemeldet.

!!! warning
    Das Modell ist bewusst klein. Es gibt **keine feineren Rollen**: keinen
    Nur-Lese-Zugang und keine Beschränkung auf einzelne Bereiche wie Finanzen
    oder Mitgliederverwaltung. Jedes Staff-Konto sieht und bearbeitet alle
    Mitglieder, Finanzen und Mails. Wäge das ab, bevor du
    OIDC-Autoprovisionierung aktivierst oder Konten anlegst.

!!! note "Plugins"
    Plugins, die Seiten in das Menü „Einstellungen“ einhängen, müssen diese
    selbst auf Superuser beschränken. byro blendet die Menüeinträge für Staff
    aus, kann die Seiten eines noch nicht angepassten Plugins aber nicht
    schützen: Eine solche Seite bleibt für Staff über ihre direkte Adresse
    erreichbar. Siehe
    [Einträge unter Einstellungen sind nur für Superuser](../development/signals.md#eintrage-unter-einstellungen-sind-nur-fur-superuser).

### Bestehende Installationen

Vor Einführung dieses Berechtigungsmodells hatte jedes Konto uneingeschränkten
Zugriff auf das gesamte Office, einschließlich Einstellungen und
Benutzerverwaltung. Damit genau dieser Zugriff erhalten bleibt, setzt das
Update für **jedes vorhandene Konto** `is_staff` und `is_superuser`, auch für
per OIDC angelegte Konten. Durch das Update verliert niemand Zugriff.

Prüfe nach dem Update „Einstellungen → Benutzer“ und entziehe den Konten, die
nur normalen Zugriff haben sollen, den Superuser-Status. Die Migration selbst
schreibt keinen Eintrag ins Audit-Log, und eine Rückwärtsmigration stellt die
früheren Flag-Werte nicht wieder her.

### Lokalen Notfall-Superuser behalten

Im Office kann ein Superuser sich den Superuser-Status nicht selbst entziehen,
und nur Superuser verwalten Konten; mindestens ein Superuser bleibt also
immer bestehen. Diese Garantie endet am Office: Ein Konto lässt sich weiterhin
auf dem Server ändern (Shell, Datenbank), und was bei einem externen
Identity-Provider passiert, sieht byro nicht. Per OIDC angelegte Konten sind
von sich aus nie Superuser.

Behalte mindestens ein lokales Superuser-Konto mit Passwort, das nicht von
OIDC abhängt, zum Beispiel das bei der Installation mit `createsuperuser`
angelegte Konto. Ist kein Superuser mehr vorhanden, siehe
[Konto-Wiederherstellung](troubleshooting.md#konto-wiederherstellung).

## Erstlogin

**Nur Superuser.** Solange **Name**, **Absenderadresse** und
**Benachrichtigungsadresse** (Einstellungen → Allgemein, siehe
[Einstellungen](settings.md)) nicht gesetzt sind, leitet byro jedes
angemeldete Konto (außer während des MFA-Ablaufs) auf die Ersteinrichtung um.
Abschließen kann sie nur ein Superuser; ein Staff-Konto, zum Beispiel ein
frisch per OIDC angelegtes, sieht eine Fehlerseite mit dem Hinweis, dass
zuerst ein Superuser die Einrichtung abschließen muss.

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
   OIDC bietet.** Sie entscheidet nur, wer sich per OIDC anmelden darf, nicht,
   was das Konto danach im Office darf; das bestimmen die Flags des lokalen
   Kontos (siehe [Berechtigungsmodell](#berechtigungsmodell)).
4. byro sucht ein bestehendes Konto mit dem Benutzernamen aus `username_field`
   (Standard `preferred_username`). Findet es keins und ist
   `auto_create_account` aktiviert, legt es ein neues, **passwortloses** Konto
   mit `is_staff=True` und `is_superuser=False` an; die Person kann also
   sofort im Office arbeiten, hat aber keinen administrativen Zugriff. Ist
   `auto_create_account` deaktiviert, schlägt der Login für unbekannte
   Benutzernamen fehl.
5. Ist das gefundene oder angelegte Konto `is_active=False`, wird die
   Anmeldung mit einer Fehlermeldung abgelehnt.
6. Ist das Konto weder Staff noch Superuser, wird die Anmeldung mit einer
   Fehlermeldung abgelehnt und im Audit-Log festgehalten.

Die Flags werden **einmalig beim Anlegen des Kontos** gesetzt. byro
synchronisiert `is_staff` und `is_superuser` nicht anhand von OIDC-Gruppen:
Ein OIDC-Login ändert die Flags eines bestehenden Kontos nie, vergeben und
entzogen werden sie von einem Superuser unter „Einstellungen → Benutzer“.

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

**Nur Superuser.** Unter „Einstellungen → Benutzer“ (`settings/users/`) siehst
du alle Konten, legst neue an und bearbeitest bestehende. Staff-Konten können
diesen Bereich nicht öffnen; sie bearbeiten nur ihr eigenes Profil über das
Benutzermenü (siehe [Mein Konto](../usage/account.md)), und dieses Formular
enthält die beiden Berechtigungsfelder nicht. Jedes Konto hat:

- **Benutzername**, **Name**, **E-Mail-Adresse**,
- **Backend-Zugriff (Staff)** (`is_staff`): erlaubt dem Konto die Anmeldung
  am Office und die Nutzung der REST-API (siehe
  [API](../development/api.md)). Beim Anlegen eines Kontos vorausgewählt;
  schalte es ab, wenn das Konto (noch) keinen Zugriff haben soll.
- **Administrator** (`is_superuser`): gewährt zusätzlich Zugriff auf die
  Funktionen, die nur Superusern offenstehen (siehe
  [Berechtigungsmodell](#berechtigungsmodell)). Nicht vorausgewählt.

**Keine Selbst-Herabstufung:** Im eigenen Profil ist das Superuser-Feld
gesperrt. Du kannst dir den Superuser-Status nicht selbst entziehen; das muss
ein anderer Superuser tun. Dein eigenes `is_staff` kannst du abschalten, was
nichts ändert, solange du Superuser bist.

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
für neue Konten; ein Superuser legt jedes Konto selbst mit einem
Erstpasswort an. Ist kein Superuser mehr vorhanden, der ein neues Konto
anlegen kann, hilft nur der Server-Zugang, siehe
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
  erfolgreiche Logins, Logins auf deaktivierte Konten, wegen fehlendem
  Backend-Zugriff abgelehnte Logins und Logouts werden protokolliert (siehe
  [Audit-Log](settings.md#audit-log)). Wird die Sitzung eines Kontos beendet,
  das seinen Backend-Zugriff verloren hat, erscheint das als Logout.
