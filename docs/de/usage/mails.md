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
  [Massenaktionen](members.md#massenaktionen)), Erinnerungen vor dem Ablauf
  des PGP-Schlüssels eines Mitglieds (siehe
  [PGP](../administration/pgp.md#automatisches-auffrischen)) und Dokumente,
  die ein Plugin verschickt (siehe
  [Dokumente](documents.md#als-mailanhang-versenden)).
* **Von Hand verfasst**: „Mails → Verfassen" (siehe unten).

## Vorlagen

„Mails → Vorlagen" verwaltet wiederverwendbare Vorlagen (Betreff, Text,
abweichende Reply-To-Adresse, BCC-Adressen). Text und Betreff werden nur in
der konfigurierten Sprache der Organisation gepflegt (siehe
[Einstellungen](../administration/settings.md#allgemein)), nicht mehrsprachig
je Empfänger.

byro legt für jede Mail, die es selbst erzeugt, eine Vorlage an:
Willkommensmail an Mitglied und Office, Austrittsmail an Mitglied und
Office, Offenlegung von Datensätzen, Saldo-Erinnerung, Dokumentversand und
Erinnerung vor Ablauf des PGP-Schlüssels. Welche Vorlage für welche Mail
verwendet wird, ist fest vorgegeben und lässt sich in der Oberfläche nicht
auswählen. Um den Wortlaut einer solchen Mail zu ändern, bearbeitest du ihre
Vorlage; die Liste zeigt die Vorlagen mit ihrem Betreff.

Die Standardtexte der Mails an Mitglieder enden ohne Gruß; den setzt die
[Fußzeile](../administration/settings.md#fuzeile-fur-mails-an-mitglieder).
Beim Update erhalten Vorlagen, die noch die bisherigen Standardtexte haben,
die neuen. byro vergleicht Betreff und Text je Sprache: Eine Sprache, in der
eins von beiden geändert wurde, behält ihre Texte. Brasilianisches
Portugiesisch verwendet den englischen Standardtext, weil es für die neuen
Texte noch keine Übersetzung gibt.

Text und Betreff können Variablen in geschweiften Klammern enthalten:

| Vorlage | Variablen |
| --- | --- |
| Saldo-Erinnerung | `{name}`, `{start}` und `{end}` (erster und letzter Tag des Zeitraums), `{amount}` (offener Betrag), nur im Text |
| Dokumentversand | `{name}` (das Mitglied, bei einem Dokument ohne Mitglied die Adresse), `{association}` |
| Ablauf des PGP-Schlüssels | `{name}`, `{date}` (Ablaufdatum) |

Eine geschweifte Klammer im Text schreibst du als `{{` oder `}}`.

In der Saldo-Erinnerung sind `{start}` und `{end}` Datumsangaben wie
2026-08-01. Ein anderes Format lässt sich nach einem Doppelpunkt angeben,
zum Beispiel `{start:%d.%m.%Y}` für 01.08.2026. `{amount}` ist der Betrag,
den das Mitglied für den Zeitraum schuldet, mit der Währung aus den
allgemeinen Einstellungen, zum Beispiel 20.00 EUR. Er ist Text, deshalb
werden Zahlenformate wie `{amount:.2f}` abgelehnt.

Die Vorlage der Saldo-Erinnerung füllt nur Betreff und Text des Formulars
unter „Mitglieder → Liste → Salden" vor; beides lässt sich dort für jeden
Lauf ändern. Das Formular prüft den Text vor dem Lauf und zeigt bei einer
unbekannten Variable oder einer ungültigen geschweiften Klammer einen
Fehler an. Lässt sich der Text trotzdem für ein einzelnes Mitglied nicht
füllen, wird der Lauf zurückgerollt und das Formular zeigt denselben
Fehler. Verschickt ein Plugin ein Dokument mit eigenem Betreff oder
Text, ersetzt es damit Betreff oder Text der Vorlage. Verwendet die Vorlage
der Ablauferinnerung eine unbekannte Variable, legt byro für die
betroffenen Schlüssel keine Erinnerung an und versucht es beim nächsten
periodischen Lauf erneut.

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
  Mitglied ermittelt. Eine solche Mail erhält die Fußzeile aus den
  allgemeinen Einstellungen, ausgefüllt für genau dieses Mitglied (siehe
  [Fußzeile für Mails an Mitglieder](../administration/settings.md#fuzeile-fur-mails-an-mitglieder)),
  wird bei aktiver PGP-Verschlüsselung mit dem Schlüssel dieses Mitglieds verschlüsselt und
  erscheint in dessen Mailverlauf. Die Mails, die
  byro für ein Mitglied erzeugt (Willkommen, Austritt, Datenauskunft,
  Erinnerung, Ablauf des PGP-Schlüssels, Dokumente), sind von dieser Art.
* Eine Mail an eine bestimmte Adresse ist genau das. byro sucht nie nach
  einem Mitglied hinter einer Adresse, auch wenn die Adresse bei einem
  Mitglied hinterlegt ist: Eine solche Mail hat keine Fußzeile, wird
  nicht verschlüsselt und erscheint in keinem Mailverlauf eines Mitglieds.
  Wer einem Mitglied schreiben will, wählt „Mitglied".

Mehrere Mitglieder dürfen dieselbe Adresse verwenden, zum Beispiel eine
Familie. Jedes von ihnen erhält trotzdem seine eigene Mail, mit dem Link zur
eigenen Mitgliederseite, wenn die Fußzeile ihn enthält, und eine Mail an alle
Mitglieder wird einmal je Mitglied zugestellt, nicht einmal je Adresse.

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
    werden ohne Fußzeile und **ohne PGP-Verschlüsselung** versendet.
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
