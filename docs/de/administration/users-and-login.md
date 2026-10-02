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
während es angemeldet ist, wird mit dem nächsten Aufruf einer geschützten
Seite abgemeldet. Seiten, die keinen Login verlangen (Login-Seite,
Mitgliederseiten, `/log/info`), beenden die Sitzung nicht; ein API-Token des
Kontos funktioniert sofort nicht mehr.

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
auf dem Server ändern (Shell, Datenbank), und mit der
OIDC-Gruppensynchronisation kann der Identity-Provider jedem Konto, das sich
per OIDC anmeldet, den Superuser-Status entziehen (siehe
[Rechte bei jedem Login synchronisieren](#rechte-bei-jedem-login-synchronisieren)).

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
zuerst ein Superuser die Einrichtung abschließen muss. Abmelden und die
Anmeldung mit einem anderen Konto (Passwort oder OIDC) bleiben möglich,
solange die Einrichtung unvollständig ist.

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
3. Ist `staff_group` oder `superuser_group` gesetzt, liest byro die Gruppen
   des Benutzers: aus dem Claim `groups` des ID-Tokens, wenn das Token einen
   hat, sonst vom Userinfo-Endpunkt. Ein vorhandener, aber leerer Claim ist
   eine gültige Antwort (Mitglied keiner Gruppe), Userinfo wird dann nicht
   gefragt. Nur wenn der Claim an beiden Stellen fehlt, gilt der Benutzer als
   Mitglied keiner Gruppe.
4. byro sucht ein bestehendes Konto mit dem Benutzernamen aus `username_field`
   (Standard `preferred_username`). Findet es keins, besteht der Benutzer die
   Gruppenprüfung aus Schritt 6 und ist `auto_create_account` aktiviert, legt
   es ein neues, **passwortloses** Konto mit den unter
   [OIDC-Gruppen und Rechte](#oidc-gruppen-und-rechte) beschriebenen Rechten
   an. Ist `auto_create_account` deaktiviert, schlägt der Login für unbekannte
   Benutzernamen fehl.
5. Ist `sync_groups` aktiviert, werden die Rechte eines bestehenden, aktiven
   Kontos anhand der Gruppen aktualisiert und gespeichert.
6. Gruppenprüfung: Ist `staff_group` gesetzt, muss der Benutzer Mitglied von
   `staff_group` oder der konfigurierten `superuser_group` sein, sonst
   schlägt der Login fehl. Das passiert nach Schritt 5; gerade entzogene
   Rechte bleiben also entzogen, obwohl der Login abgewiesen wird.
7. Ist das Konto `is_active=False`, wird die Anmeldung mit einer Fehlermeldung
   abgelehnt. Ein deaktiviertes Konto wird von Schritt 5 nie verändert.
8. Ist das Konto weder Staff noch Superuser, wird die Anmeldung mit einer
   Fehlermeldung abgelehnt und im Audit-Log festgehalten.

### OIDC-Gruppen und Rechte

Zwei Optionen bilden Gruppen des Identity-Providers auf die beiden Flags des
[Berechtigungsmodells](#berechtigungsmodell) ab:

- `staff_group`: Mitglieder erhalten `is_staff`. Die Gruppe begrenzt außerdem,
  wer sich überhaupt per OIDC anmelden darf (Schritt 6). Ist sie leer, darf
  sich jeder Benutzer des Identity-Providers anmelden.
- `superuser_group`: Mitglieder erhalten `is_superuser`. Ist sie leer, vergibt
  und entzieht OIDC den Superuser-Status nie.

Die beiden Flags bleiben unabhängig: Die Mitgliedschaft in `superuser_group`
setzt `is_staff` nie von sich aus. Ob ein Mitglied von `superuser_group`
auch Staff ist, entscheidet allein die Staff-Seite:

- Ist `staff_group` konfiguriert, folgt `is_staff` dieser Gruppe. Ein
  Benutzer, der nur in `superuser_group` ist, erhält dann `is_superuser`
  ohne `is_staff`, als neues Konto oder über `sync_groups`, und kann sich
  trotzdem anmelden, weil ein Superuser immer Zugriff hat.
- Ist keine `staff_group` konfiguriert, wird ein neues Konto standardmäßig
  Staff (siehe Tabelle unten), auch wenn es in `superuser_group` ist. Bei
  einem bestehenden Konto bleibt `is_staff`, wie es ist.

Ein Konto mit `is_superuser`, aber ohne `is_staff`, entsteht also nur, wenn
die Staff-Seite das so vorgibt: über eine konfigurierte `staff_group` oder
weil das Flag lokal bereits so gesetzt ist.

Ein **neues Konto** (`auto_create_account`) erhält seine Rechte einmalig:

| `staff_group` gesetzt | `superuser_group` gesetzt | `is_staff` | `is_superuser` |
|---|---|---|---|
| nein | nein | ja | nein |
| ja | nein | ja (die Mitgliedschaft ist Voraussetzung für den Login) | nein |
| nein | ja | ja | wenn Mitglied von `superuser_group` |
| ja | ja | wenn Mitglied von `staff_group` | wenn Mitglied von `superuser_group` |

Die einfachste Einrichtung, `auto_create_account` ohne jede Gruppe, macht
also weiterhin jeden neuen OIDC-Benutzer zu einem normalen Staff-Konto und
nie zu einem Superuser.

Bei einem **bestehenden Konto** kommt es auf `sync_groups` an:

- `sync_groups = false` (Standard): Ein OIDC-Login ändert die Flags nie. Die
  Gruppenprüfung entscheidet, ob sich der Benutzer per OIDC anmelden darf,
  die lokalen Flags entscheiden, was das Konto darf. Eine spätere Aufnahme in
  eine Gruppe vergibt nichts: Ein Superuser setzt die Flags unter
  „Einstellungen → Benutzer“.
- `sync_groups = true`: siehe nächster Abschnitt.

Gruppennamen mit Leerzeichen funktionieren nur, wenn der Anbieter den Claim
`groups` als Liste sendet; ein als einzelne Zeichenkette gesendeter Claim
wird an Leerzeichen getrennt. Ein Claim in jeder anderen Form, zum Beispiel
eine Liste, die etwas anderes als Gruppennamen enthält, lässt die Anmeldung
scheitern. byro legt dann kein Konto an und ändert keine Rechte.

### Rechte bei jedem Login synchronisieren

Mit `sync_groups = true` ist der Identity-Provider für die konfigurierten
Gruppen die **maßgebliche Quelle**. Bei jedem erfolgreichen OIDC-Login eines
bestehenden Kontos gilt:

- Ist `staff_group` gesetzt, wird `is_staff` auf „Mitglied von `staff_group`“
  gesetzt.
- Ist `superuser_group` gesetzt, wird `is_superuser` auf „Mitglied von
  `superuser_group`“ gesetzt.
- Ein Flag, dessen Gruppe nicht konfiguriert ist, bleibt genau so, wie es ist.

byro liest das Konto unmittelbar vor dem Vergleich und dem Schreiben unter
einer Sperre neu und schreibt nur ein Flag, das zugeordnet ist und sich
tatsächlich unterscheidet. Ein Flag, dessen Gruppe nicht konfiguriert ist,
wird also nie geschrieben, auch wenn es im selben Moment jemand im Office
ändert.

Eine Änderung wird gespeichert, bevor Gruppenprüfung und Berechtigungsmodell
ausgewertet werden, und mit den alten und neuen Flags im Audit-Log
festgehalten. Ein Benutzer, der aus `staff_group` entfernt wurde, verliert
`is_staff` mit dem nächsten OIDC-Login; ist das Konto danach weder Staff noch
Superuser, wird dieser Login abgewiesen.

!!! warning
    - Wer Benutzer beim Identity-Provider aus einer synchronisierten Gruppe
      entfernt, entzieht ihnen das Recht in byro, ohne jede Absicherung. Das
      kann **jeden** Superuser entfernen, der sich per OIDC anmeldet. Behalte
      einen
      [lokalen Notfall-Superuser](#lokalen-notfall-superuser-behalten) mit
      Passwort.
    - Synchronisiert wird nur **während eines OIDC-Logins des jeweiligen
      Kontos**. Bis dahin ändert sich nichts: Sitzungen, Passwort-Anmeldung
      und API-Token des Kontos funktionieren weiter. Konten, die sich nicht
      per OIDC anmelden, verändert byro nie.
    - `staff_group` allein verwaltet keine Superuser. Nach dem Update auf
      das Berechtigungsmodell ist jedes vorhandene Konto Superuser (siehe
      [Bestehende Installationen](#bestehende-installationen)). Ein solches
      Konto verliert `is_staff` und seine OIDC-Anmeldung, wenn es
      `staff_group` verlässt, behält aber `is_superuser` und damit
      Passwort-Anmeldung und API-Token, bis du zusätzlich `superuser_group`
      setzt oder das Flag von Hand entziehst.
    - Sendet der Anbieter den Claim `groups` nicht mehr, zum Beispiel nach
      einer Änderung an Scope oder Mapper, gilt jeder Benutzer als Mitglied
      keiner Gruppe und verliert mit dem nächsten Login die synchronisierten
      Rechte.

### Die veraltete Option `admin_group`

`admin_group` ist der alte Name von `staff_group` und wird weiterhin gelesen.
Für sich allein verhält sich die Option wie bisher: Nur Mitglieder dürfen
sich per OIDC anmelden, und neue Konten werden Staff. Zwei Dinge sind neu:
Zusammen mit `superuser_group` genügt die Mitgliedschaft in **einer** der
beiden Gruppen für die Anmeldung, und mit `sync_groups` steuert sie wie
`staff_group` auch `is_staff`.

Benenne sie bei Gelegenheit in `staff_group` um. Sind beide Optionen mit
unterschiedlichen Werten gesetzt, rät byro nicht, welche gemeint ist: Der
SSO-Button verschwindet und OIDC-Logins werden abgewiesen, bis die
Konfiguration korrigiert ist. Die Passwort-Anmeldung funktioniert weiter.
`manage.py check` meldet das Problem, und `byroctl config check` verweigert
das Anwenden einer solchen Konfiguration.

**Fehlerfälle** (abgelaufener Code, ungültiger `state`, Ablehnung durch den
Anbieter, Netzwerkfehler beim Anbieter) landen alle als Fehlermeldung auf der
Login-Seite; es gibt keine gesonderte Fehlerseite und keinen Rückfall auf
Passwort-Login im selben Versuch.

!!! warning
    „Passwort deaktivieren“ (siehe unten) sperrt nur die
    Passwort-Anmeldung dieses Kontos. Ist OIDC konfiguriert und der
    Benutzername identisch, kann sich das Konto weiterhin per OIDC anmelden.
    Um ein Konto vollständig zu sperren, muss es beim OIDC-Anbieter selbst
    entfernt oder deaktiviert werden (für die OIDC-Anmeldung genügt es, die
    konfigurierten Gruppen zu verlassen), oder `is_active` muss falsch sein.

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

**Keine Selbst-Herabstufung:** Im eigenen Profil ist nur das Superuser-Feld
gesperrt. Du kannst dir den Superuser-Status nicht selbst entziehen; das muss
ein anderer Superuser tun. Dein eigenes `is_staff` bleibt änderbar: Du kannst
es selbst ein- oder abschalten, was nichts ändert, solange du Superuser bist.

**Passwort beim Bearbeiten:** Das Passwortfeld des Bearbeitungsformulars ist
optional. Lass es leer, damit das Passwort des Kontos genau so bleibt, wie es
ist – das gilt auch für ein deaktiviertes Passwort, das deaktiviert bleibt.
Gibst du ein Passwort ein, ersetzt es beim Speichern das bisherige; informiere
die betroffene Person danach über das neue Passwort. Beim Anlegen eines Kontos
ist ein Passwort weiterhin erforderlich. Um ein Passwort zu setzen, ohne das
Bearbeitungsformular zu öffnen, nutze `changepassword` (siehe
[Management-Befehle](management-commands.md#kontoverwaltung)).

**Passwort deaktivieren** (`settings/users/<pk>/disable-password`) setzt ein
unbrauchbares Passwort; das Konto kann sich danach nicht mehr per Passwort
anmelden (siehe die OIDC-Warnung oben zur Wechselwirkung). Es lässt sich nicht
selbst auf das eigene Konto anwenden. Um das Passwort wieder zu aktivieren,
speichere das Bearbeitungsformular mit einem neuen Passwort.

**API-Token widerrufen** (`settings/users/<pk>/revoke-api-token`): Die Seite
eines anderen Kontos zeigt, ob dieses Konto einen
[API-Token](../usage/account.md#api-token) hat, nie den Token selbst.
„API-Token widerrufen“ löscht ihn. Der Token funktioniert sofort nicht mehr
(die API antwortet mit `401`), und es wird kein Ersatz ausgestellt. Sonst
ändert sich am Konto nichts: Passwort, OIDC-Anmeldung, MFA, Sitzungen und
Rechte bleiben, wie sie sind. Es lässt sich nicht auf das eigene Konto
anwenden; nutze dafür deine eigene API-Token-Seite.

Widerrufen ist **keine API-Sperre**. Es macht den bisher ausgegebenen Token
ungültig, zum Beispiel weil er in falsche Hände geraten sein könnte. Die
Person, der das Konto gehört, bekommt einen neuen Token, sobald sie ihre
API-Token-Seite das nächste Mal öffnet. Um ein Konto von der API
fernzuhalten, entferne `is_staff` und `is_superuser` (siehe
[Berechtigungsmodell](#berechtigungsmodell)).

Jeder Widerruf wird im Audit-Log festgehalten, ohne den Token. Lässt sich
nur dieser Eintrag nicht schreiben, bleibt der Token trotzdem widerrufen: Du
siehst statt der Bestätigung eine Warnung, und das Anwendungslog bekommt
eine Zeile mit den IDs der beiden Konten, nie mit dem Token oder einer
Fehlermeldung.

Schlägt der Widerruf selbst fehl, zum Beispiel weil die Datenbank ihn nicht
speichern kann, bekommst du eine Fehlerseite. Das Ergebnis ist dann nicht
bestätigt: Meist wurde nichts geändert, aber wenn die Verbindung zur
Datenbank beim Speichern abgebrochen ist, kann der Token trotzdem entfernt
sein. Öffne die Seite des Kontos erneut, um zu sehen, ob es noch einen Token
hat, und widerrufe ihn dann noch einmal. Auch das Log eines solchen Fehlers
enthält keinen Token.

**Es gibt keine Möglichkeit, ein Konto zu löschen oder zu deaktivieren**
(`is_active=False` zu setzen) über die Office-Oberfläche. „Passwort
deaktivieren“ blockiert nur die Passwort-Anmeldung, und „API-Token
widerrufen“ macht nur den bisher ausgegebenen Token ungültig. Um einem Konto
den Zugriff zu nehmen, entferne `is_staff` und `is_superuser`.

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
  das seinen Backend-Zugriff verloren hat, erscheint das als Logout. Durch
  die OIDC-Gruppensynchronisation geänderte Rechte werden mit den alten und
  neuen Flags protokolliert; der Eintrag enthält keine Claims und keine
  Gruppennamen.
- **API-Tokens:** Das Erzeugen, Erneuern und Widerrufen eines API-Tokens wird
  mit dem betroffenen Konto und dem Konto protokolliert, das es ausgelöst
  hat. Die Einträge enthalten nie einen Token.
