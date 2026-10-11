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
* ein bestimmtes Mitglied (nur Mitglieder und externe Kontakte mit
  hinterlegter E-Mail-Adresse stehen zur Auswahl; niemand ist vorausgewählt,
  ein Mitglied muss immer ausdrücklich gewählt werden),
* **alle Mitglieder mit aktiver Mitgliedschaft und E-Mail-Adresse**.

Es gibt keine Möglichkeit, eine frei gewählte Gruppe von Mitgliedern
auszuwählen – dafür sind die Massenaktionen auf der Mitgliederliste gedacht
(siehe [Mitglieder](members.md#massenaktionen)).

### Mitglieder und Adressen

byro unterscheidet eine Mail **an ein Mitglied** von einer Mail **an eine
Adresse**:

* Eine Mail an ein Mitglied oder an alle Mitglieder weiß, für welches
  Mitglied sie bestimmt ist. Die Adresse wird erst beim Versand aus dem
  Mitglied ermittelt. Eine solche Mail erhält die Signatur mit dem Link zur
  Mitgliederseite genau dieses Mitglieds, wird bei aktiver
  PGP-Verschlüsselung mit dem Schlüssel dieses Mitglieds verschlüsselt und
  erscheint in dessen Mailverlauf. Die Mails, die
  byro für ein Mitglied erzeugt (Willkommen, Austritt, Datenauskunft,
  Erinnerung, Ablauf des PGP-Schlüssels, Dokumente), sind von dieser Art.
* Eine Mail an eine bestimmte Adresse ist genau das. byro sucht nie nach
  einem Mitglied hinter einer Adresse, auch wenn die Adresse bei einem
  Mitglied hinterlegt ist: Eine solche Mail hat keine Mitgliedssignatur, wird
  nicht verschlüsselt und erscheint in keinem Mailverlauf eines Mitglieds.
  Wer einem Mitglied schreiben will, wählt „Mitglied".

Mehrere Mitglieder dürfen dieselbe Adresse verwenden, zum Beispiel eine
Familie. Jedes von ihnen erhält trotzdem seine eigene Mail mit dem Link zur
eigenen Mitgliederseite, und eine Mail an alle Mitglieder wird einmal je
Mitglied zugestellt, nicht einmal je Adresse.

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
  Mitglieder merkt sich byro dabei als Mitglieder, nicht über ihre Adresse:
  Teilen sich zwei Mitglieder eine Adresse und war nur eine Zustellung
  erfolgreich, erreicht der neue Versuch das andere Mitglied.
* Sobald eine Mail an mindestens einen Empfänger zugestellt wurde, lassen
  sich ihre Empfänger nicht mehr ändern: Die Mail ist der Nachweis, wer sie
  erhalten hat. Ein neuer Versuch erreicht die noch offenen Empfänger; wer
  jemand anderem schreiben will, nutzt „Zu neuer Mail kopieren" – das erzeugt
  einen Entwurf ohne Zustellungen.
* **Löschen** verwirft den Entwurf ungesendet, ohne Rückfrage nach einer
  Bestätigung außer der einmaligen Aktion selbst.

!!! warning "Entwürfe aus älteren Versionen"
    Ältere byro-Versionen haben in den Mails, die sie für ein Mitglied
    erzeugt haben, nur die Adresse gespeichert. Liegen solche Entwürfe nach
    einem Update noch im Postausgang, sind sie Mails an eine Adresse: Sie
    werden ohne Mitgliedssignatur und **ohne PGP-Verschlüsselung** versendet.
    Versende den Postausgang vor dem Update oder öffne den Entwurf danach und
    wähle das Mitglied als Empfänger. Erinnerungsmails aus dem
    Beitragsabgleich und über „Verfassen" an ein Mitglied oder an alle
    Mitglieder geschriebene Entwürfe werden automatisch umgestellt, solange
    noch nichts davon zugestellt wurde.

    Ältere Versionen haben nicht festgehalten, welchem Mitglied eine Mail
    zugestellt wurde. Ein Entwurf an ein Mitglied oder an alle Mitglieder,
    der bereits teilweise zugestellt wurde oder mit anderen Mitgliedern
    verknüpft ist, wird deshalb nicht umgestellt: Der Postausgang zeigt ihn
    als „Prüfung erforderlich" und verweigert den Versand, statt zu raten,
    wer ihn erhalten hat. Öffne ihn und wähle den Empfänger neu; wurde er
    teilweise zugestellt, kopiere ihn in eine neue Mail (dann erhalten ihn
    alle erneut) oder lösche ihn.

## Gesendet

„Mails → Gesendet" ist eine reine Leseansicht bereits versendeter Mails,
sortiert nach Versanddatum. Eine Mail an ein Mitglied zeigt die Adresse, an
die sie tatsächlich zugestellt wurde, auch wenn das Mitglied seine Adresse
inzwischen geändert hat.

## Anhänge

Ein Dokument landet nur dann als Anhang in einer Mail, wenn eine
automatisierte Funktion es dort hinzufügt (siehe
[Dokumente](documents.md#als-mailanhang-versenden)); das Kompose-Formular
selbst bietet keine Anhangsauswahl.

## PGP

Ist die Mitglieder-Verschlüsselung aktiv, verschlüsselt byro jede Mail an
ein Mitglied mit dem für dieses Mitglied hinterlegten Schlüssel, unabhängig
davon, ob sie über die Vorlagen, „Verfassen" oder automatisch erzeugt wurde.
Mails an eine bestimmte Adresse und Kopien an CC- oder BCC-Adressen werden
nicht verschlüsselt. Details:
[PGP-Mailverschlüsselung](../administration/pgp.md).
