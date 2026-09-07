# Kommunikation

Jede Mail, die byro verschickt – ob automatisch ausgelöst oder von Hand
verfasst – landet zunächst als **Entwurf im Postausgang** und wird nie ohne
Zutun verschickt.

## Woher Mails kommen

* **Automatisch erzeugt**: Willkommens- und Austrittsmails (siehe
  [Mitglied anlegen](members.md#mitglied-anlegen) und
  [Ein-/Austritt](members.md#ein-austritt)), Datenoffenlegungen (einzeln oder
  als Massenaktion, siehe [Mitglieder](members.md#datenoffenlegung)),
  Erinnerungsmails beim Beitragsabgleich (siehe
  [Massenaktionen](members.md#massenaktionen)).
* **Von Hand verfasst**: „Mails → Verfassen" (siehe unten).

## Vorlagen

„Mails → Vorlagen" verwaltet wiederverwendbare Vorlagen (Betreff, Text,
abweichende Reply-To-Adresse, BCC-Adressen). Text und Betreff werden nur in
der konfigurierten Sprache der Organisation gepflegt (siehe
[Einstellungen](../administration/settings.md#allgemein)), nicht mehrsprachig
je Empfänger. Welche Vorlagen an welcher Stelle automatisch verwendet werden
(Willkommen, Austritt, Offenlegung), legst du unter
[Einstellungen → Allgemein](../administration/settings.md#allgemein) fest.

!!! note
    Es gibt keine Funktion, eine Vorlage zu löschen; ein entsprechender Link
    existiert nicht in der Oberfläche.

## Mail verfassen

„Mails → Verfassen" erstellt eine neue Mail mit genau einem Empfängertyp:

* eine bestimmte Adresse,
* ein bestimmtes Mitglied (nur Mitglieder mit hinterlegter E-Mail-Adresse
  stehen zur Auswahl),
* **alle Mitglieder mit aktiver Mitgliedschaft und E-Mail-Adresse**.

Es gibt keine Möglichkeit, eine frei gewählte Gruppe von Mitgliedern
auszuwählen – dafür sind die Massenaktionen auf der Mitgliederliste gedacht
(siehe [Mitglieder](members.md#massenaktionen)).

„Speichern" legt die Mail als Entwurf ab, „Speichern und senden" verschickt
sie sofort. Eine bereits versendete Mail lässt sich nicht mehr bearbeiten;
„Kopieren" erstellt daraus einen neuen, bearbeitbaren Entwurf.

## Postausgang

„Mails → Postausgang" listet alle noch nicht versendeten Mails. Einzeln oder
für die gesamte Liste stehen **Senden** und **Löschen** zur Verfügung.

* **Senden** an „alle Mitglieder" löst die Empfängerliste erst beim
  tatsächlichen Versand auf (aktueller Mitgliederbestand zu diesem
  Zeitpunkt, nicht zum Zeitpunkt des Verfassens).
* Schlägt der Versand an einzelne Empfänger fehl, bricht das den restlichen
  Versand nicht ab: byro meldet, an wen erfolgreich zugestellt wurde und bei
  wem es Fehler gab. Bereits zugestellte Empfänger werden bei einem erneuten
  Sendeversuch **nicht** doppelt angeschrieben – nur die noch offenen.
* **Löschen** verwirft den Entwurf ungesendet, ohne Rückfrage nach einer
  Bestätigung außer der einmaligen Aktion selbst.

## Gesendet

„Mails → Gesendet" ist eine reine Leseansicht bereits versendeter Mails,
sortiert nach Versanddatum.

## Anhänge

Ein Dokument landet nur dann als Anhang in einer Mail, wenn eine
automatisierte Funktion es dort hinzufügt (siehe
[Dokumente](documents.md#als-mailanhang-versenden)); das Kompose-Formular
selbst bietet keine Anhangsauswahl.

## PGP

Ist die Mitglieder-Verschlüsselung aktiv, verschlüsselt byro jede Mail
einzeln je Empfänger mit dessen hinterlegtem Schlüssel, unabhängig davon, ob
sie über die Vorlagen, „Verfassen" oder automatisch erzeugt wurde. Details:
[PGP-Mailverschlüsselung](../administration/pgp.md).
