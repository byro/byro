# Mitgliederseite

Jedes Mitglied hat eine eigene, öffentlich erreichbare Seite – ohne Login,
ohne Passwort, ohne Zwei-Faktor-Anmeldung. Das ist kein Office-Zugang und
sollte nicht mit einem Benutzerkonto verwechselt werden (siehe
[Benutzer und Login](../administration/users-and-login.md) für den
tatsächlichen Office-Zugang mit Passwort oder OIDC).

## Zugang

Die Adresse enthält ein 32 Zeichen langes, zufälliges Token
(`/member/<token>/`) und ist der einzige Zugriffsschutz – wer die Adresse
kennt, kann die Seite öffnen. Ein Mitglied bekommt seine Adresse:

* automatisch als Link in der Willkommensmail, sofern eine Willkommensvorlage
  konfiguriert ist (siehe [Mitglied anlegen](members.md#mitglied-anlegen)),
* als Verknüpfung „Öffentliches Profil“ auf dem Dashboard des Mitglieds im
  Office.

!!! warning
    Wer die Adresse kennt, kann die Seite öffnen und im Rahmen der
    Datenschutzeinstellungen unten Änderungen vorschlagen. Gib den Link nur
    an das jeweilige Mitglied weiter, wie ein Passwort.

## Was die Seite zeigt

* Mitgliedsdauer (Tage/Jahre seit Beginn der ersten Mitgliedschaft),
  aktuelle Mitgliedschaft (Beitrag, Intervall),
* die eigenen Buchungen (Beiträge, Spenden),
* Dashboard-Kacheln, die Plugins ausdrücklich für die öffentliche Ansicht
  freigeben (nicht dieselben Kacheln wie im Office-Dashboard),
* nur für **aktive** Mitglieder zusätzlich einen Link zum
  [Mitgliederverzeichnis](#mitgliederverzeichnis).

## Änderungsvorschläge

Ein Mitglied kann auf seiner Seite Änderungen an einem Teil seiner eigenen
Daten vorschlagen: Name, Adresse, E-Mail (Core), dazu Spitzname, Geburtsdatum
und Telefonnummer, falls das `profile`-Plugin installiert ist, sowie
Bankverbindungsdaten, falls das `sepa`-Plugin installiert ist, und der
PGP-Fingerabdruck.

**Kein Vorschlag wird automatisch übernommen.** Jede Änderung landet als
Vorschlag, den ein Office-Benutzer im Reiter „Daten“ der Mitgliedsansicht
prüft und annimmt oder ablehnt (siehe
[Änderungsvorschläge prüfen](members.md#mitgliedsdaten-andern)). Ein
Mitglied sieht auf seiner Seite, welche Vorschläge noch offen sind, inklusive
des aktuell gespeicherten Werts zum Vergleich.

## Datenschutzeinstellungen

Auf derselben Seite legt das Mitglied fest, ob und was von ihm für andere
Mitglieder sichtbar ist:

* eine Checkbox „Ja, meine Daten dürfen in der Mitgliederliste erscheinen“ –
  ohne sie erscheint das Mitglied dort nicht, unabhängig von den folgenden
  Einstellungen,
* je Feld eine eigene Freigabe-Checkbox, welche Daten dann sichtbar sind.

**Nie freigebbar**, unabhängig von diesen Einstellungen: Bankverbindungsdaten,
das Zugriffstoken selbst, der Kontostand, der Aktiv-Status und die interne
Datenbank-ID – diese Felder bietet die Datenschutzseite gar nicht erst zur
Freigabe an.

## Mitgliederverzeichnis

`/member/<token>/list` zeigt alle **aktiven** Mitglieder, die der Sichtbarkeit
zugestimmt haben, mit den Feldern, die sie einzeln freigegeben haben. Ein
Mitglied, dessen Mitgliedschaft endet, verschwindet aus der Liste, auch wenn
es früher zugestimmt hatte. Die Seite nennt zusätzlich die Anzahl aktiver
Mitglieder, die (noch) nicht zugestimmt haben, ohne sie zu nennen.

Ein Mitglied ohne aktive Mitgliedschaft sieht diesen Verzeichnis-Link auf
seiner eigenen Seite nicht.
