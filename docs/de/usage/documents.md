# Dokumente

Dokumente sind hochgeladene Dateien mit Titel, Datum, Kategorie und Richtung
(eingehend, ausgehend oder sonstig), optional einem Mitglied zugeordnet.

## Wo Dokumente hochgeladen werden

* **An einem Mitglied**: im Reiter „Dokumente" der Mitgliedsansicht (siehe
  [Mitglieder](members.md#dokumente)) – das Dokument ist von Anfang an mit
  diesem Mitglied verknüpft.
* **An einer Transaktion**: auf der Transaktionsseite (siehe
  [Finanzen](finances.md#beleg-anhangen)) – zusätzlich zur Verknüpfung mit
  einem Mitglied lässt sich hier ein Beleg mit der jeweiligen Buchung
  verbinden.
* **Allgemein, ohne Bezug** (`Dokumente → Hinzufügen`): für Dokumente, die zu
  keinem Mitglied und keiner Transaktion gehören.

## Kategorien

Kategorien kommen aus dem Core und aus installierten Apps/Plugins, nicht aus
einer festen Liste. Der Core selbst kennt:

* Sonstiges Dokument, Registrierungsformular (Dokumente-App),
* Beleg, Rechnung, Kontoauszug (Buchhaltung).

Ein installiertes Plugin kann weitere Kategorien beisteuern; welche das im
Einzelfall sind, hängt von den installierten Plugins ab.

## Herunterladen

Jedes Dokument lässt sich über seine Detailseite herunterladen; byro liefert
die Datei erst nach eigener Zugriffsprüfung aus (siehe
[Sicherheits-Baseline](../administration/security-baseline.md#tls-und-reverse-proxy)
zur Begründung, warum `/media/` nie direkt über den Webserver ausgeliefert
werden darf).

## Als Mailanhang versenden

Ein Dokument lässt sich programmatisch als Anhang einer neuen Mail in den
Postausgang legen; das nutzen zum Beispiel Plugins, die ein angefordertes
Dokument automatisch zustellen. **Im Office selbst gibt es dafür keine
eigene Schaltfläche** – weder das Kompose-Formular noch die
Mitgliedsansicht bieten „dieses Dokument per Mail versenden" an. Ein
Dokument landet nur dann als Anhang in einer Mail, wenn eine automatisierte
Funktion (zum Beispiel ein Plugin) es dort hinzufügt.
