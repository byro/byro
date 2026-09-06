# Bankimporter

byro importiert echte Banktransaktionen aus Dateien, die auf der Seite
„Banktransaktionen importieren“ im Finanzbereich hochgeladen werden. Welche
Dateiformate verfügbar sind, hängt von den installierten Plugins ab: Jedes
Plugin kann einen oder mehrere *Bankimporter* registrieren, und der Benutzer
wählt den Importer, der zur hochgeladenen Datei passt (zum Beispiel „CAMT.053“
oder „Fidor CSV“).

Ein Importer beantwortet nur eine Frage: *Welche Banktransaktionen enthält
diese Datei?* Er parst sein Eingabeformat und liefert neutrale
`ImportedBankTransaction`-Objekte. Der byro-Kern validiert die Transaktionen,
erkennt Dubletten, erzeugt die Buchungen und lässt die Matching-Pipeline
laufen. Ein Importer erzeugt nie `Transaction`- oder `Booking`-Objekte, wählt
nie Buchhaltungskonten und ordnet nie Mitglieder oder Beiträge zu.

!!! note
    Diese API ist für *dateibasierte* Importe. Direkte Bankverbindungen wie
    FinTS brauchen eigene Konfiguration und Oberfläche und werden deshalb nicht
    als Importer registriert. Sie können aber denselben
    `BankTransactionImportService` verwenden, um die geholten Transaktionen zu
    speichern.

## Minimalbeispiel

Ein vollständiger Importer sieht so aus:

```python
from datetime import date
from decimal import Decimal

from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from byro.bookkeeping.bank_import import (
    BankTransactionImporter,
    ImportedBankTransaction,
    InvalidImportFile,
)
from byro.bookkeeping.signals import bank_transaction_importers


class ExampleBankImporter(BankTransactionImporter):
    identifier = "byro_example.bank"
    label = _("Example Bank")

    def parse(self, source):
        with source.source_file.open("rb") as f:
            for row in parse_rows(f):  # dein formatspezifischer Code
                yield ImportedBankTransaction(
                    booking_date=date(2026, 9, 1),
                    amount=Decimal("25.00"),
                    currency="EUR",
                    memo="Membership fee",
                    counterparty_name="Max Mustermann",
                    counterparty_iban="DE12 3456 7890 1234 5678 90",
                    external_id="123456789",
                )


@receiver(bank_transaction_importers)
def register_example_importer(sender, **kwargs):
    return ExampleBankImporter()
```

Das Ableiten von `BankTransactionImporter` ist optional; jedes Objekt mit den
Attributen `identifier` und `label` und einer Methode `parse(source)` wird
akzeptiert. Ein Receiver darf auch eine Liste von Importern zurückgeben.

## Registrierung

Verbinde einen Receiver mit
`byro.bookkeeping.signals.bank_transaction_importers`. Das Signal wird
gesendet, wann immer die Importer-Auswahl aufgebaut oder ein Importer über
seinen Identifier aufgelöst wird; die Registrierung muss also billig und frei
von Nebenwirkungen sein. Ungültige Importer und doppelte Identifier werden
geloggt und ignoriert.

## Stabiler Identifier

`identifier` ist ein stabiler, mit Punkten gegliederter String wie
`byro_finance_import_bank_files.camt053`. Er wird an jeder
`RealTransactionSource` und an jeder daraus erzeugten Buchung
(`Booking.importer`) gespeichert und für Logging und Fehlersuche verwendet. Er
darf nie vom übersetzten `label` abhängen und sollte sich nach der
Veröffentlichung nicht ändern. Stelle den Paketnamen deines Plugins voran, um
Kollisionen mit anderen Plugins zu vermeiden. Die maximale Länge beträgt 255
Zeichen.

## `parse(source)`

`parse` erhält die `RealTransactionSource`, deren `source_file` die
hochgeladene Datei enthält. Es gibt ein Iterable (idealerweise einen Generator)
von `ImportedBankTransaction`-Objekten zurück.

Kann die Datei nicht verstanden werden, wirf `InvalidImportFile`, optional mit
einer für Benutzer geeigneten Meldung. Jede andere Exception wird mit Traceback
geloggt und dem Benutzer als allgemeiner Importer-Fehler gemeldet. Schreibe nie
Bankdaten (IBANs, Namen, Verwendungszwecke, Rohzeilen) in Exception-Meldungen;
sie werden im Browser angezeigt.

## `ImportedBankTransaction`

::: byro.bookkeeping.bank_import.ImportedBankTransaction
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: []

!!! note
    Die Feldbeschreibungen unten sind von Hand gepflegt: Es sind
    Dokumentationskommentare im Quellcode (`#:` über jedem Feld), eine
    Konvention, die Griffe für Dataclass-Felder nicht ausliest; mkdocstrings
    rendert oben deshalb nur die Klasse selbst. Prüfe
    `src/byro/bookkeeping/bank_import/api.py`, wenn sich ein Feld ändert.

`booking_date`
:   Das Datum, an dem die Bank die Transaktion gebucht hat (Pflicht).
    `value_date` fällt auf das Buchungsdatum zurück.

`amount`
:   Ein `decimal.Decimal` mit höchstens zwei Nachkommastellen. **Positive
    Beträge sind Geld, das auf dem Bankkonto eingeht, negative Beträge Geld,
    das abgeht.** Ein Mitglied, das 25 € zahlt, ist `Decimal("25.00")`; der
    Verein, der eine Rechnung über 80 € bezahlt, ist `Decimal("-80.00")`.
    Nullbeträge und Floats werden abgelehnt. Der Kern übersetzt das Vorzeichen
    in die Soll-/Haben-Buchung auf dem Bankkonto; Importer müssen byros
    Buchungsmodell nicht kennen.

`currency`
:   ISO-4217-Code, standardmäßig `"EUR"`. byros Buchhaltung kennt keine
    Währungen, daher wird nur `EUR` akzeptiert. Eine Transaktion in einer
    anderen Währung wirft `UnsupportedCurrency` und lässt den Import
    scheitern; Beträge werden nie stillschweigend als EUR interpretiert.

`memo`
:   Verwendungszweck. Auf 1000 Zeichen gekürzt.

`counterparty_name`, `counterparty_iban`, `counterparty_bic`
:   Angaben zur Gegenseite. Die IBAN wird vor dem Speichern normalisiert
    (Großbuchstaben, keine Leerzeichen). Der Name wird im Office unter dem
    Verwendungszweck in Konten- und Transaktionsansichten angezeigt.

`external_id`
:   Eine stabile Referenz, die die *Bank* dieser Transaktion zugewiesen hat,
    etwa die `AcctSvcrRef` eines CAMT-Eintrags oder eine Transaktions-ID des
    Anbieters. Ist sie vorhanden, ist sie der Primärschlüssel für die
    Dublettenerkennung; sie muss also je Bankkonto über alle Importer eindeutig
    sein und bei jedem Export derselben Transaktion identisch. Verwende
    **keine** Zeilennummern oder andere exportabhängige Werte. Hat dein Format
    keine solche Referenz, lass sie `None` und überlass dem Kern den Rückfall
    auf einen Fingerabdruck.

`end_to_end_id`, `mandate_id`, `creditor_id`, `bank_reference`, `transaction_code`
:   Optionale SEPA- und Bankreferenzen. Sie werden mit der Buchung gespeichert
    und fließen in den Rückfall-Fingerabdruck ein.

`data`
:   Formatspezifische Metadaten dieser einen Transaktion als JSON-serialisierbares
    Dict, z. B. `{"entry_reference": "..."}`. Wird in `Booking.data` neben den
    oben genannten Kernfeldern gespeichert (die Schlüssel `counterparty_name`,
    `counterparty_iban`, `counterparty_bic`, `external_id`, `end_to_end_id`,
    `mandate_id`, `creditor_id`, `bank_reference` und `transaction_code` sind
    dem Kern vorbehalten). Speichere nicht die komplette Quelldatei oder die
    Rohzeile jeder Buchung: Das Original liegt in
    `RealTransactionSource.source_file`, und die Duplizierung bläht die
    Datenbank mit personenbezogenen Daten auf.

## Was der Kern tut

Für jede mit einem Importer verarbeitete Quelle führt der
`BankTransactionImportService` Folgendes aus:

1. validiert und normalisiert jede gelieferte Transaktion,
2. berechnet ihre Identität und überspringt bereits bekannte Transaktionen,
3. erzeugt eine `Transaction` mit einer einzelnen Bank-`Booking` auf dem
   Spezialkonto Bank (`SpecialAccounts.bank`) mit gesetztem `source`,
   `importer` und `data`,
4. speichert die Anzahl importierter und doppelter Transaktionen an der
   Quelle,
5. lässt die Matching-Pipeline `process_transaction` für die neuen
   Transaktionen laufen.

Der gesamte Import ist atomar: `import_transactions()` läuft in einer
Datenbanktransaktion. Ist eine einzelne Transaktion ungültig oder scheitert das
Speichern, wird nichts geschrieben und die Quelle endet im Zustand `FAILED`.
Das gilt auch, wenn der Service direkt verwendet wird, etwa von einem
Bankverbindungs-Plugin. Dubletten sind *keine* Fehler; ein Lauf, der nichts
Neues importiert, weil jede Transaktion schon bekannt war, ist ein
erfolgreicher Import.

## Dublettenerkennung

Wiederholte und überlappende Importe (ein Export für Januar bis März, gefolgt
von einem für Januar bis April) dürfen keine doppelten Buchungen erzeugen, und
dieselbe Transaktion kann im Lauf der Zeit über verschiedene Importer
eintreffen. Der Kern speichert deshalb an jeder importierten Buchung eine
SHA-256-Identität (`Booking.import_identity`, in der Datenbank eindeutig) und
überspringt Transaktionen, deren Identität bereits existiert. Auch zwei
gleichzeitig laufende Importe können dieselbe Transaktion nicht zweimal
speichern: Der Verlierer des Wettlaufs sieht eine Verletzung des
Unique-Constraints, die als Dublette gezählt wird.

* Mit `external_id` wird die Identität nur aus Bankkonto und externer ID
  abgeleitet. Sie enthält nicht den Importer, sodass ein CAMT-Import und ein
  späterer Import eines anderen Formats mit derselben Bankreferenz einander
  erkennen.
* Ohne `external_id` dient ein Fingerabdruck über normalisiertes
  Buchungsdatum, Valutadatum, Betrag, Währung, IBAN und Name der Gegenseite,
  Verwendungszweck und die SEPA-Referenzen. Datum und Betrag allein reichen
  nie: Zwei Mitglieder, die am selben Tag denselben Beitrag zahlen, sind zwei
  Transaktionen. Identische Fingerabdrücke *innerhalb einer Datei* werden alle
  importiert (die n-te Wiederholung erhält eine eigene Identität), und ein
  erneuter Import derselben Datei erkennt sie alle wieder.

Importer implementieren selbst keine Dublettenlogik. Alles andere, auch
legitim ähnlich aussehende Transaktionen, wird bewusst *nicht* zusammengeführt:
Eine Transaktion zu viel ist besser, als eine Zahlung stillschweigend zu
verschlucken.

## Fehler

::: byro.bookkeeping.bank_import.api
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members:
        - BankTransactionImportError
        - UnknownImporter
        - InvalidImportFile
        - ImporterError
        - InvalidBankTransaction
        - UnsupportedCurrency

`UnknownImporter` und `UnsupportedCurrency` haben keinen Klassen-Docstring im
Quellcode; ihre `default_message` ist der nutzersichtbare Text.

`str(error)` ist immer eine für Benutzer geeignete Meldung; technische Details
gehen an den Logger `byro.bookkeeping.bank_import`. Der Kern loggt Beginn,
Abschluss (mit Zählern) und Fehlschlag (mit der Fehlerklasse) jedes Imports,
aber nie IBANs, Namen, Verwendungszwecke oder Rohinhalte. Halte dich in deinem
Importer an dieselbe Regel.

## Import und Matching sind getrennt

Importer wissen nichts über Mitglieder, Beiträge oder Buchhaltungskonten.
Nachdem der Kern die Bankbuchung erzeugt hat, läuft die bestehende Pipeline
`process_transaction` unverändert, und Matcher (etwa einer, der eine
Mitgliedsnummer im Verwendungszweck erkennt) ergänzen die Transaktion. Weil der
Kern die Felder zur Gegenseite und die Referenzen in `Booking.data` speichert,
funktionieren Matcher für jeden Importer gleich.

## Sicherheit

Hochgeladene Bankdateien sind nicht vertrauenswürdige Eingaben.

* Behandle fehlerhafte Eingaben sauber und wirf `InvalidImportFile`, statt
  beliebige Exceptions entkommen zu lassen.
* Führe nie Dateiinhalte aus oder `eval`uiere sie, und importiere nie Module
  auf Basis von Dateiinhalten.
* XML-basierte Formate (CAMT.053, MT94x-Hüllen) müssen externe Entities und
  DTD-Laden deaktivieren, dürfen beim Parsen keinen Netzwerkzugriff machen und
  sollten den Ressourcenverbrauch begrenzen (z. B. mit `defusedxml`). Das ist
  Sache des Plugins; byros Kern enthält keine XML-Verarbeitung.
* Halte Bankdaten aus Exception-Meldungen und Logzeilen heraus.
* byro begrenzt die Upload-Größe (`BANK_TRANSACTION_IMPORT_MAX_FILE_SIZE`,
  standardmäßig 25 MiB) und verarbeitet jede Quelle atomar.

## Legacy-API

Bevor diese API existierte, setzten Plugins den ganzen Import um, indem sie
`process_csv_upload` empfingen und selbst `Transaction`- und
`Booking`-Objekte erzeugten. Dieses Signal wird für Quellen ohne Importer
weiter gesendet (es erscheint als „Legacy bank importer (plugin)“ in der
Auswahl, wenn ein Receiver verbunden ist), sodass bestehende Plugins weiter
funktionieren. Für neue Entwicklungen ist es veraltet, und eine von einem
neuen Importer verarbeitete Quelle löst es nie aus.
