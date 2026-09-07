# Mehr-Faktor-Authentifizierung (MFA)

byro unterstützt Mehr-Faktor-Authentifizierung für alle Benutzer des Backends
(„Office“) auf Basis zeitbasierter Einmalpasswörter (TOTP,
[RFC 6238](https://www.rfc-editor.org/rfc/rfc6238)). Jede gängige
Authenticator-App funktioniert, zum Beispiel Aegis, Google Authenticator,
Microsoft Authenticator, 1Password oder Bitwarden.

MFA ist **standardmäßig optional**: Jeder Backend-Benutzer kann sie für sein
eigenes Konto aktivieren. Administratoren können zusätzlich **MFA für alle
Administratoren vorschreiben**, also für jeden Benutzer, der sich am Backend
anmelden kann.

MFA betrifft nur die interaktive Anmeldung am Backend. Sie ändert nichts an

- den Mitgliederseiten: Mitglieder verwenden weiter ihre persönlichen Links,
  dort ist weder Anmeldung noch zweiter Faktor nötig,
- der REST-API: API-Tokens funktionieren weiter, unabhängig vom MFA-Zustand
  des Token-Benutzers oder der globalen Richtlinie. API-Anfragen werden nie auf
  eine MFA-Seite umgeleitet.

!!! note
    byro gewährt jedem aktiven Benutzerkonto Zugriff auf das gesamte Backend;
    es gibt keine abgestuften Rollen für das Office (siehe
    [Benutzer und Login](users-and-login.md)). Das Feld `is_staff` existiert,
    steuert aber nur den Zugriff auf die REST-API, nicht auf das Office
    selbst. Die MFA-Richtlinie gilt deshalb für *jeden* Benutzer, der sich am
    Office anmelden kann, unabhängig von `is_staff`.

## Für Backend-Benutzer

### MFA einrichten

1. Öffne das Benutzermenü (dein Benutzername oben rechts) und wähle
   *Mehr-Faktor-Authentifizierung* (auch über die gleichnamige Schaltfläche
   auf deiner Profilseite erreichbar).
2. Klicke auf *MFA einrichten*.
3. Scanne den QR-Code mit deiner Authenticator-App. Wenn du ihn nicht scannen
   kannst, gib den Schlüssel unter dem QR-Code manuell ein (Typ:
   zeitbasiert / TOTP, 6 Stellen, 30 Sekunden, SHA-1).
4. Gib den sechsstelligen Code aus deiner App ein und klicke auf *Prüfen und
   aktivieren*. MFA ist erst aktiv, wenn ein Code erfolgreich geprüft wurde;
   das bloße Öffnen der Einrichtungsseite ändert nichts.
5. byro zeigt nun **zehn Wiederherstellungscodes**. Bewahre sie sicher auf
   (zum Beispiel in einem Passwortmanager). Sie werden nur einmal angezeigt.

Ab jetzt fragt jede Anmeldung nach dem Passwort einen Code aus deiner
Authenticator-App ab. Für ein Konto mit aktivierter MFA lässt sich dieser
Schritt nicht überspringen.

### Anmelden

Gib wie bisher Benutzername und Passwort ein. Auf der nächsten Seite gibst du
den aktuellen sechsstelligen Code aus deiner Authenticator-App ein. Codes sind
nur kurz gültig, und jeder Code kann nur einmal verwendet werden.

### Einen Wiederherstellungscode verwenden

Hast du keinen Zugriff auf deine Authenticator-App, klicke auf der Code-Seite
auf *Wiederherstellungscode verwenden* und gib einen deiner Codes ein
(`XXXX-XXXX-XXXX`, Bindestriche und Groß-/Kleinschreibung spielen keine Rolle).
Jeder Wiederherstellungscode funktioniert genau einmal. Nach der Anmeldung
sagt dir byro, wie viele Codes übrig sind; erzeuge neue, wenn es knapp wird.

### Neue Wiederherstellungscodes erzeugen

*Benutzermenü → Mehr-Faktor-Authentifizierung → Neue Wiederherstellungscodes
erzeugen*. Du musst mit einem aktuellen Code aus deiner Authenticator-App
bestätigen. Alle bisherigen Wiederherstellungscodes werden sofort ungültig.

### MFA deaktivieren

*Benutzermenü → Mehr-Faktor-Authentifizierung → MFA deaktivieren*, bestätigt
mit einem aktuellen Authenticator-Code. Das entfernt den Authenticator und alle
Wiederherstellungscodes; danach schützt nur noch das Passwort das Konto.

Ist MFA für alle Administratoren vorgeschrieben, steht diese Option nicht zur
Verfügung.

### Authenticator verloren und keine Wiederherstellungscodes mehr

Bitte einen Administrator mit Shell-Zugang zum byro-Server, deine MFA mit dem
unten beschriebenen Management Command zurückzusetzen. Über die Weboberfläche
lässt sich die MFA eines anderen Benutzers nicht zurücksetzen.

## Für Administratoren

### MFA für alle Administratoren vorschreiben

Unter *Einstellungen → Allgemein* findest du die Karte
*Mehr-Faktor-Authentifizierung* mit der Option **MFA für alle Administratoren
vorschreiben** (standardmäßig aus). Das Aktivieren hat folgende Auswirkungen:

- Benutzer, die MFA bereits verwenden, sind nicht betroffen; sie können sie
  aber nicht mehr deaktivieren.
- Benutzer ohne MFA werden direkt nach der Passworteingabe zur
  MFA-Einrichtung geschickt. Bis die Einrichtung abgeschlossen ist, können sie
  keine andere Seite des Backends nutzen (nur die Einrichtung und Abmelden).
- Bereits ohne MFA angemeldete Sitzungen werden gleich behandelt: Die nächste
  Anfrage wird zur Einrichtung umgeleitet.
- Die Einstellung gilt auch für Anmeldungen per Single Sign-on (OIDC). byro
  wertet keine MFA-Informationen des Identity Providers aus; OIDC-Benutzer
  müssen den byro-TOTP-Schritt ebenfalls durchlaufen.
- Das Aktivieren setzt nicht voraus, dass alle MFA bereits eingerichtet haben.
  Niemand wird ausgesperrt, aber jeder Benutzer muss sich bei der nächsten
  Anmeldung einrichten.

Das Ändern der Option wird im Audit-Log festgehalten.

### Anzeige in Authenticator-Apps

Einträge aus byros QR-Code zeigen immer **BYRO** als Dienstnamen. Die zweite
Zeile, der Kontoname, ist in derselben Einstellungskarte konfigurierbar
(*Kontoname in Authenticator-Apps*). Standard ist `{association} - {username}`,
also der Vereinsname aus den allgemeinen Einstellungen gefolgt vom
Benutzernamen. Verfügbare Platzhalter: `{username}`, `{email}`, `{name}` (Name
des Benutzers) und `{association}`, zum Beispiel `{name} ({email})`.

Doppelpunkte sind nicht erlaubt: Das von Authenticator-Apps verwendete
`otpauth`-Format trennt Dienstname und Konto mit einem Doppelpunkt.

Die Einstellung wirkt nur auf neu eingerichtete Authenticator; bestehende
Einträge in den Apps behalten den Namen, den sie beim Anlegen hatten.

### MFA-Status eines Benutzers prüfen

Die Benutzerliste markiert Benutzer mit MFA mit einem Schild-Symbol. Auf dem
Server gibt

```console
$ python manage.py mfa_status <benutzername oder e-mail>
```

etwa Folgendes aus:

```text
User: admin (admin@example.org)
Active: yes
MFA enabled: yes
TOTP device: configured (since Sept. 1, 2026, 10:00 a.m., last used Sept. 4, 2026, 9:12 a.m.)
Recovery codes remaining: 6
MFA required by policy: no
```

Geheimnisse und Wiederherstellungscodes werden nie angezeigt.

### MFA eines Benutzers zurücksetzen (Notfallwiederherstellung)

Hat ein Benutzer seinen Authenticator verloren und keine
Wiederherstellungscodes mehr (oder ist aus einem anderen Grund ausgesperrt),
setze seine MFA auf dem Server zurück:

```console
$ python manage.py mfa_reset <benutzername oder e-mail>
```

Der Befehl zeigt eine Warnung und verlangt zur Bestätigung die Eingabe des
Benutzernamens. Danach

1. entfernt er den Authenticator (TOTP-Geheimnis) und alle
   Wiederherstellungscodes,
2. beendet alle bestehenden Sitzungen dieses Benutzers,
3. schreibt einen Audit-Log-Eintrag (`byro.mfa.reset`).

Für skriptgesteuerte Wiederherstellung überspringt `--force` die
Bestätigungsabfrage.

!!! warning
    Ein Reset ist ein Wiederherstellungsmechanismus, kein Weg um die
    Richtlinie herum. **Ist MFA für alle Administratoren vorgeschrieben,
    erlaubt der Reset dem Benutzer nur, sich neu einzurichten**: Nach der
    nächsten Passwortanmeldung wird er zur MFA-Einrichtung geschickt und muss
    einen neuen Authenticator einrichten, bevor er das Backend nutzen kann.
    Die globale Richtlinie ändert der Befehl nicht.

Sitzungen können nur mit dem standardmäßigen datenbankbasierten
Sitzungsspeicher (`SESSION_ENGINE` endet auf `.db`) automatisch beendet werden;
der Befehl sagt dir, wenn das nicht der Fall ist.

### Sicherheitshinweise

- **TOTP-Geheimnisse werden verschlüsselt gespeichert.** Der
  Verschlüsselungsschlüssel wird aus Djangos `SECRET_KEY` abgeleitet (siehe
  [Konfiguration](../configuration/index.md)). Halte den Secret Key stabil und
  sichere ihn zusammen mit der Datenbank (siehe
  [Backup und Restore](backup-restore.md)): Geht er verloren, kann kein
  Benutzer mehr den MFA-Schritt bestehen, und jedes Konto muss mit `mfa_reset`
  zurückgesetzt werden. byro bietet **keine Konfigurationsoption, um einen
  vorherigen Secret Key als Fallback anzugeben**; ein Wechsel des Secret Keys
  ist also gleichbedeutend mit dem Verlust aller bestehenden Sitzungen und
  MFA-Geräte, nicht mit einer nahtlosen Rotation.
- **Wiederherstellungscodes werden als Passwort-Hashes gespeichert** und sind
  nur einmal verwendbar.
- **Brute-Force-Schutz:** Nach jedem falschen Code wird die MFA des Kontos für
  eine exponentiell wachsende Zeit gesperrt (1, 2, 4, 8, … Sekunden), für
  Authenticator-Codes wie für Wiederherstellungscodes. Jeder TOTP-Code wird
  nur einmal akzeptiert. byro selbst begrenzt die Passwortanmeldung nicht; wie
  bisher empfehlen wir Rate Limiting am Reverse Proxy (etwa nginx `limit_req`
  für `/login/`) oder fail2ban auf den Webserver-Logs.
- **Audit-Log:** Aktivieren (`byro.mfa.enabled`), Deaktivieren
  (`byro.mfa.disabled`) und Zurücksetzen (`byro.mfa.reset`) von MFA, Erzeugen
  neuer Wiederherstellungscodes (`byro.mfa.recovery_codes.regenerated`) und
  Anmelden mit einem Wiederherstellungscode (`byro.mfa.recovery_code.used`)
  werden im Audit-Log festgehalten. Geheimnisse, Codes und QR-Codes werden nie
  geloggt; fehlgeschlagene Versuche landen nur im Anwendungslog.
- **Systemzeit:** TOTP hängt von einer korrekten Uhr auf dem Server (und dem
  Telefon des Benutzers) ab. Betreibe einen NTP-Client auf dem Server.

### Hinweise für Plugin-Entwickler

Jede URL, die eine Anmeldung verlangt, ist automatisch von der MFA-Durchsetzung
erfasst, Plugin-Views eingeschlossen. URLs, die ein Plugin über das Signal
`unauthenticated_urls` als öffentlich markiert, sind auch von MFA
ausgenommen. In Views sagt `request.user.is_verified()`, ob die aktuelle
Sitzung den MFA-Schritt bestanden hat (für Benutzer ohne MFA-Pflicht ist es
hinter der Middleware immer `True`).
