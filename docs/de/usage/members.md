# Mitglieder

Diese Seite beschreibt die tägliche Arbeit mit Mitgliedsdatensätzen: suchen,
anlegen, bearbeiten, Ein- und Austritt, Dokumente sowie Export/Import und
Massenaktionen für viele Mitglieder gleichzeitig. Beiträge und
Zahlungsintervalle stehen auf einer eigenen Seite:
[Mitgliedschaften und Beiträge](memberships-and-fees.md).

!!! note
    Einige Felder, die auf den ersten Blick zum Kern gehören, stammen aus den
    mitgelieferten Plugins `byro.plugins.profile` (Spitzname, Geburtsdatum,
    Telefonnummer) und `byro.plugins.sepa` (Bankverbindung für
    SEPA-Lastschrift). Sie erscheinen wie Kernfelder in Formularen und Export,
    sind aber Plugins – wird eines deaktiviert, verschwinden die Felder.

## Mitgliederliste

„Mitglieder → Liste“ zeigt alle Mitglieder mit Suche und Filter:

* **Suche** durchsucht Name, Spitzname (aus dem Profil-Plugin) und die
  Mitgliedsnummer.
* **Filter**: Aktiv (Standard), Inaktiv, Negativer Saldo, Ausstehende
  Änderungsvorschläge, Alle. „Aktiv“ bedeutet: mindestens eine Mitgliedschaft
  mit Beginn in der Vergangenheit und ohne Ende oder einem Ende in der
  Zukunft – das ist eine berechnete Eigenschaft, kein eigenes Feld, das du
  manuell setzt.

Dieselbe Suche steht als Autovervollständigung an anderen Stellen im Office
zur Verfügung, zum Beispiel um beim Bankimport eine Zahlung einem Mitglied
zuzuordnen (siehe die Finanzen-Seite, sobald sie entsteht).

## Mitglied anlegen

„Mitglieder → Hinzufügen“ zeigt genau die Felder, die unter
[Einstellungen → Registrierungsformular](../administration/settings.md#registrierungsformular)
konfiguriert sind – Kernfelder, Mitgliedschaftsfelder, Profil-Plugin-Felder
und optional der PGP-Fingerabdruck, in der dort festgelegten Reihenfolge.
Pflichtfelder aus dieser Konfiguration lassen sich nicht überspringen; die
Mitgliedsnummer wird mit dem nächsten freien numerischen Wert vorbelegt, du
kannst sie aber durch einen beliebigen Text ersetzen.

Beim Speichern:

1. Das Mitglied und seine erste Mitgliedschaft (Beginn, Intervall, Beitrag)
   werden angelegt.
2. Ist eine Willkommensvorlage konfiguriert (siehe
   [Einstellungen → Allgemein](../administration/settings.md#allgemein)) und
   hat das Mitglied eine E-Mail-Adresse, landet eine Willkommensmail im
   Postausgang – inklusive automatisch eingefügtem Link zur persönlichen
   [Mitgliederseite](member-page.md#zugang).
3. Ist eine interne Willkommensvorlage konfiguriert, geht eine entsprechende
   Mail an die Benachrichtigungsadresse.
4. Wurde beim Anlegen ein PGP-Fingerabdruck angegeben, versucht byro sofort,
   den passenden Schlüssel von den konfigurierten Keyservern zu importieren
   (siehe [PGP-Mailverschlüsselung](../administration/pgp.md#fingerabdrucke-aus-mitgliedsantragen)).

Mails landen immer im Postausgang zur Prüfung, nie werden sie direkt
verschickt.

## Die Mitgliedsansicht

Ein Mitglied öffnen zeigt mehrere Reiter:

| Reiter | Inhalt |
|---|---|
| Dashboard | Mitgliedsdauer, aktuelle Mitgliedschaft, Verjährungsstand, Kacheln von Plugins (z. B. PGP-Warnungen) |
| Daten | Kernfelder, alle Mitgliedschaften, neue Mitgliedschaft anlegen, Profil-Plugin-Felder, Änderungsvorschläge |
| Zeitleiste | zusammengeführter Verlauf aus Finanzen, Mails, Vorgängen und Dokumenten |
| Finanzen | Buchungen dieses Mitglieds (siehe die Finanzen-Seite, sobald sie entsteht) |
| Vorgänge | Austritt, Saldenkorrektur (siehe unten) |
| Mails | an dieses Mitglied gesendete Mails (siehe die Kommunikations-Seite, sobald sie entsteht) |
| PGP | Mitgliedsschlüssel verwalten (siehe [PGP-Mailverschlüsselung](../administration/pgp.md#mitgliedsschlussel)) |
| Dokumente | Dokumente dieses Mitglieds hoch- und herunterladen (siehe unten) |
| Log | Audit-Log-Einträge zu diesem Mitglied |
| Offenlegung | einzelne Datenoffenlegung (siehe unten) |

### Mitgliedsdaten ändern

Im Reiter „Daten“ ist jeder Abschnitt (Kerndaten, jede einzelne
Mitgliedschaft, neue Mitgliedschaft, jedes Profil-Plugin) ein eigenes
Formular; nur geänderte Formulare werden beim Speichern übernommen.

**Änderungsvorschläge prüfen:** Hat das Mitglied über die
[Mitgliederseite](member-page.md) Änderungen an seinen eigenen Daten
vorgeschlagen, erscheinen sie hier zur Annahme oder Ablehnung. Nichts wird
automatisch übernommen. Ein angenommener PGP-Fingerabdruck-Vorschlag löst
sofort einen Keyserver-Import aus; eine ungültige Fingerabdruck-Eingabe wird
mit einer Fehlermeldung abgelehnt, statt übernommen zu werden.

### Ein-/Austritt

Im Reiter „Vorgänge“ hat jede aktuell laufende Mitgliedschaft ein Formular
„Mitgliedschaft beenden“ (nur das Enddatum ist editierbar). Nach dem Speichern:

* die Mitgliedschaft bekommt das angegebene Enddatum,
* offene Forderungen werden neu berechnet,
* ist eine Austrittsvorlage (Mitglied bzw. intern) konfiguriert, landet eine
  entsprechende Mail im Postausgang.

Es gibt keine Funktion, eine Mitgliedschaft rückgängig zu beenden, außer das
Enddatum wieder zu leeren.

### Saldenkorrektur

Ebenfalls im Reiter „Vorgänge“: die Kontokorrektur für dieses Mitglied, mit
zwei Gründen:

* **Anfangssaldo**: für eine Migration in byro, wenn ein Mitglied bereits
  einen Saldo aus der Zeit vor byro mitbringt.
* **Beitrag erlassen**: senkt eine bestehende Schuld; der Betrag muss die
  Schuld verringern (im relativen Modus negativ, im absoluten Modus kleiner
  als der aktuelle Saldo), sonst weist byro die Eingabe zurück.

Beträge lassen sich relativ (addieren/subtrahieren) oder absolut (Zielsaldo)
eingeben. Details zum Kontenmodell dahinter stehen auf der Finanzen-Seite,
sobald sie entsteht.

### Dokumente

Der Reiter „Dokumente“ lädt Dateien direkt für dieses Mitglied hoch (Titel,
Datum, Kategorie – die Kategorien kommen aus dem Core und installierten Apps
und Plugins –, Richtung eingehend/ausgehend/sonstig) und listet die bereits
vorhandenen. Mehr zum allgemeinen Dokumentensystem (Versand als Mailanhang,
Kategorien im Detail) auf der Dokumente-Seite, sobald sie entsteht.

### Datenoffenlegung

„Offenlegung“ erzeugt eine einzelne Auskunftsmail für dieses Mitglied (Inhalt:
alle gespeicherten Daten) und legt sie in den Postausgang. Für viele
Mitglieder gleichzeitig siehe „Massenaktionen“ unten.

## Export

„Mitglieder → Liste → Export“ exportiert die aktuell gefilterten Mitglieder
(gleiche Filter wie die Liste, plus „Alle“) als CSV, wahlweise mit Komma
(Standard) oder Semikolon (für deutsche Windows-Excel-Versionen: Dezimalkomma
statt -punkt). Du wählst dabei einzeln, welche Felder exportiert werden –
vorbelegt sind die Felder, die auch im Registrierungsformular erscheinen.
Kein XLSX-Export.

## Import

„Mitglieder → Liste → Import“ liest eine CSV-Datei (dieselben zwei Formate wie
der Export) und ordnet Spalten anhand ihrer **Kopfzeile** (exakter Text der
Feldbezeichnung) automatisch Feldern zu; passt eine Spalte zu keinem Feld,
bricht der Import mit einer Fehlermeldung ab, bevor irgendetwas geschrieben
wird.

* Eine Spalte für die interne Datenbank-ID aktualisiert ein **bestehendes**
  Mitglied statt ein neues anzulegen.
* Spalten für Saldo und letzten Beitragszeitpunkt legen bei **neuen**
  Mitgliedern einen Anfangssaldo an (beide Spalten müssen zusammen vorhanden
  sein).
* Neue Mitglieder ohne Mitgliedschaftsspalten werden ohne Mitgliedschaft
  angelegt.

## Massenaktionen

* **Salden generieren** (`Mitglieder → Liste → Salden`): erzeugt für alle
  Mitglieder mit aktiver Mitgliedschaft einen Saldo über einen gewählten
  Zeitraum und legt optional Erinnerungsmails für Mitglieder mit einem Saldo
  unter einem einstellbaren Schwellwert in den Postausgang. Läuft
  synchron beim Absenden des Formulars.
* **Datenoffenlegung für alle** (`Mitglieder → Liste → Offenlegung`): erzeugt
  für **alle aktuell gefilterten** Mitglieder eine Auskunftsmail im
  Postausgang – prüfe vorher den gesetzten Filter.
* **Saldenauffrischung** (Button auf der Mitgliederliste): berechnet die
  Salden aller Mitglieder im Hintergrund neu; läuft nur einmal gleichzeitig,
  ein zweiter Klick während des Laufs meldet das nur.

## Referenz: Kontakttyp

Jedes Mitglied hat einen Kontakttyp (Person, Organisation, Rolle) ohne
weitere Auswirkung auf Formulare oder Berechtigungen – rein informativ, außer
er ist über das Registrierungsformular sichtbar geschaltet.
