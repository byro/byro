# Einstellungen

Diese Seite beschreibt die anwendungsinternen Einstellungen unter
„Einstellungen“ im Office. Benutzerkonten und Login stehen auf einer eigenen
Seite: [Benutzer und Login](users-and-login.md). Dein persönlicher API-Token
und deine eigene MFA-Einrichtung sind kein Teil von „Einstellungen“, sondern
über dein Benutzermenü erreichbar – siehe
[Mein Konto](../usage/account.md) im Benutzerhandbuch.

Das Menü „Einstellungen“ steht in der Seitenleiste unter „Mails“ und wird
**nur Superusern angezeigt**. Staff-Konten sehen es nicht und können seine
Seiten auch nicht direkt aufrufen (siehe
[Berechtigungsmodell](users-and-login.md#berechtigungsmodell)). Abschnitte,
für die das gilt, sind unten mit **nur Superuser** gekennzeichnet. „Über“ ist
ein eigener Eintrag der Seitenleiste direkt darunter und steht jedem Konto
offen.

## Ersteinrichtung

**Nur Superuser.** Direkt nach der Installation, solange die Pflichtfelder
fehlen (siehe [Erstlogin](users-and-login.md#erstlogin)), fragt byro einen
Superuser nach drei Angaben:

- **Vereinsname**,
- **Absenderadresse** für Mails, die byro im Namen des Vereins verschickt,
- **Benachrichtigungsadresse**, an die byro administrative Hinweise schickt.

Erst danach schaltet byro zur Registrierungsformular-Einrichtung weiter (siehe
unten) und der Rest des Office wird nutzbar.

## Allgemein

**Nur Superuser.** Die allgemeinen Einstellungen (`settings/`) fassen mehrere
Formulare auf einer Seite zusammen: die eigentliche Vereinskonfiguration sowie, sofern
installiert, PGP (siehe [PGP-Mailverschlüsselung](pgp.md)) und
Konfigurationsmodelle, die Plugins über `ByroConfiguration` beisteuern (siehe
[Eigene Mitgliedsdaten](../development/plugins/member-data.md)) – jedes Plugin
kann so einen eigenen Abschnitt auf dieser Seite ergänzen.

Die Vereinskonfiguration selbst umfasst:

- **Vereinsname, -adresse, -URL**,
- **Verjährungsfrist** (`liability_interval`, in Monaten): bis zu welchem
  Alter offene Beitragsforderungen eines Mitglieds noch eingefordert werden
  können,
- **Buchhaltung ab** (`accounting_start`): optionales Datum, ab dem
  Beiträge rückwirkend berechnet werden – nützlich bei einer Migration in
  byro, wenn ältere, unbezahlte Beiträge nicht nachträglich fällig werden
  sollen,
- **Sprache** und **Währung** (Code, Symbol, Symbol vor/nach dem Betrag,
  Cent-Anzeige),
- **Externe Basis-URL** (`public_base_url`): nur nötig, wenn öffentliche
  Mitgliederseiten unter einer anderen Basis-URL erreichbar sein sollen als
  der Rest von byro; sonst leer lassen.
- **Absender- und Benachrichtigungsadresse** (dieselben Felder wie in der
  Ersteinrichtung, hier änderbar),
- **Standard-Sortierreihenfolge** und **Standard-Anredeform** für Mitglieder
  (Vor- oder Nachname zuerst), mit einer Aktion, um sie nachträglich auf alle
  bestehenden Mitglieder anzuwenden,
- **Standard-Mailvorlagen** für Willkommens- und Austrittsmails (an Mitglied
  und Office) sowie für die Offenlegung von Datensätzen.

Jede gespeicherte Änderung wird mit den geänderten Feldern (vorher/nachher)
im Audit-Log festgehalten (siehe unten); Formulare können einzelne Felder
(zum Beispiel Geheimnisse) von dieser Protokollierung ausnehmen.

## Registrierungsformular

**Nur Superuser.** Unter „Einstellungen → Registrierungsformular“ legst du
fest, welche Felder beim Anlegen eines neuen Mitglieds abgefragt werden: Mitglieds- und
Mitgliedschaftsfelder sowie alle Felder, die installierte Profil-Plugins
beisteuern (zum Beispiel `byro.plugins.profile`), dazu die PGP-Fingerabdruck-
Angabe. Für jedes Feld lässt sich einstellen:

- **Position** im Formular (leer = nicht anzeigen, sofern nicht Pflichtfeld),
- ein **Vorbelegungswert** (bei Datumsfeldern eine relative Vorgabe wie
  „Anfang des laufenden Monats“, bei Wahrheitswerten Wahr/Falsch/keine
  Vorgabe),
- ob es **Pflichtfeld** ist. Felder, die die Datenbank ohnehin nicht leer
  lässt (`NOT NULL` ohne Vorgabewert), erscheinen automatisch als
  Pflichtfeld und lassen sich nicht aus dem Formular entfernen.

Ohne gespeicherte Konfiguration zeigt byro eine sinnvolle Vorbelegung
(Mitgliedsnummer, Name, Adresse, E-Mail, Beitragsbeginn, -intervall, -betrag).

## Über byro

Der Eintrag „Über“ in der Seitenleiste, direkt unter „Einstellungen“, zeigt
die installierte byro-Version und die geladenen Plugins mit ihren Metadaten
(Name, Version, Beschreibung). Er steht jedem Konto mit Zugriff auf das Office
offen, nicht nur Superusern.

## Audit-Log

**Nur Superuser.** „Einstellungen → Log“ zeigt die letzten Einträge des
Audit-Logs: wer was wann geändert hat (Mitgliederänderungen, Einstellungen, Logins, Plugin-
Ereignisse, …). Jeder Eintrag ist Teil einer **kryptografisch verketteten
Hash-Kette** (jeder Eintrag verweist über einen Hash auf den vorherigen);
Einträge lassen sich über die Anwendung weder löschen noch nachträglich
ändern. Der Reiter „Log“ am einzelnen Mitglied bleibt für Staff erreichbar.
`/log/info` zeigt unauthentifiziert den aktuellen Kettenkopf – eine
externe Partei kann so ohne Login prüfen, ob eine ihr vorliegende Kopie der
Kette noch mit dem aktuellen Stand übereinstimmt.

Für einen vollständigen, maschinenlesbaren Export siehe den Management-Befehl
`export_logchain` unter [Management-Befehle](management-commands.md#prufung-und-export).

!!! note
    Fehlgeschlagene Passwort-Logins erscheinen **nicht** im Audit-Log (siehe
    [Anmeldeverhalten](users-and-login.md#anmeldeverhalten)); es ist kein
    Werkzeug zur Erkennung von Anmeldeversuchen, sondern ein Nachweis
    tatsächlich durchgeführter Änderungen und erfolgreicher Logins.
