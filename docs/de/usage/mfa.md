# Mehr-Faktor-Authentifizierung

byro unterstützt Mehr-Faktor-Authentifizierung (MFA) für dein Office-Konto
auf Basis zeitbasierter Einmalpasswörter (TOTP,
[RFC 6238](https://www.rfc-editor.org/rfc/rfc6238)). Jede gängige
Authenticator-App funktioniert, zum Beispiel Aegis, Google Authenticator,
Microsoft Authenticator, 1Password oder Bitwarden.

MFA ist **standardmäßig optional** – du kannst sie für dein eigenes Konto
aktivieren, unabhängig von anderen Konten. Deine Administration kann sie
zusätzlich für alle Office-Konten vorschreiben; ist das der Fall, lässt sich
MFA nicht mehr deaktivieren (siehe unten).

MFA betrifft nur die interaktive Anmeldung am Office-Backend. Sie ändert
nichts an der öffentlichen [Mitgliederseite](member-page.md) (dort ist weder
Anmeldung noch zweiter Faktor nötig) oder an einem [API-Token](account.md#api-token)
(das funktioniert unabhängig vom MFA-Zustand des Kontos).

## MFA einrichten

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

## Anmelden

Gib wie bisher Benutzername und Passwort ein. Auf der nächsten Seite gibst du
den aktuellen sechsstelligen Code aus deiner Authenticator-App ein. Codes sind
nur kurz gültig, und jeder Code kann nur einmal verwendet werden.

## Einen Wiederherstellungscode verwenden

Hast du keinen Zugriff auf deine Authenticator-App, klicke auf der Code-Seite
auf *Wiederherstellungscode verwenden* und gib einen deiner Codes ein
(`XXXX-XXXX-XXXX`, Bindestriche und Groß-/Kleinschreibung spielen keine Rolle).
Jeder Wiederherstellungscode funktioniert genau einmal. Nach der Anmeldung
sagt dir byro, wie viele Codes übrig sind; erzeuge neue, wenn es knapp wird.

## Neue Wiederherstellungscodes erzeugen

*Benutzermenü → Mehr-Faktor-Authentifizierung → Neue Wiederherstellungscodes
erzeugen*. Du musst mit einem aktuellen Code aus deiner Authenticator-App
bestätigen. Alle bisherigen Wiederherstellungscodes werden sofort ungültig.

## MFA deaktivieren

*Benutzermenü → Mehr-Faktor-Authentifizierung → MFA deaktivieren*, bestätigt
mit einem aktuellen Authenticator-Code. Das entfernt den Authenticator und alle
Wiederherstellungscodes; danach schützt nur noch das Passwort das Konto.

Ist MFA für alle Administratoren vorgeschrieben, steht diese Option nicht zur
Verfügung.

## Authenticator verloren und keine Wiederherstellungscodes mehr

Bitte einen Administrator mit Shell-Zugang zum byro-Server, deine MFA
zurückzusetzen (siehe
[MFA eines Benutzers zurücksetzen](../administration/mfa.md#mfa-eines-benutzers-zurucksetzen-notfallwiederherstellung)).
Über die Weboberfläche lässt sich die MFA eines anderen Benutzers nicht
zurücksetzen.

## Für Administratoren

Die Richtlinie für alle Konten vorschreiben, den MFA-Status eines Benutzers
prüfen, ein verlorenes Gerät zurücksetzen und die sicherheitstechnischen
Hintergründe stehen auf der Administrationsseite:
[Mehr-Faktor-Authentifizierung](../administration/mfa.md).
