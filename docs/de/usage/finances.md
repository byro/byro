# Finanzen

byro führt eine doppelte Buchhaltung für Beiträge und Zahlungen, ist aber
**keine vollständige Buchhaltungssoftware** – es gibt keine Bilanz- oder
GuV-Berichte, keine Steuer- oder Jahresabschlussfunktionen und keinen
eigenständigen Export- oder Report-Bereich über das hinaus, was auf dieser
Seite beschrieben ist.

## Konten

„Finanzen → Konten" zeigt alle Konten mit ihrer Kategorie (Aktiva, Passiva,
Ertrag, Aufwand, Eigenkapital) und ihrem Saldo. byro legt bei Bedarf
automatisch sechs Konten an:

| Konto | Kategorie | Zweck |
|---|---|---|
| Bank | Aktiva | Gegenkonto jeder importierten Bankbuchung |
| Mitgliedsbeiträge (Forderung) | Aktiva | offene Beitragsforderungen |
| Anfangssaldo | Aktiva | Gegenkonto für Anfangssalden bei der Migration |
| Mitgliedsbeiträge (Ertrag) | Ertrag | vereinnahmte Beiträge |
| Spenden | Ertrag | Spendenbuchungen |
| Entgangene Einnahmen | Aufwand | erlassene Beiträge |

Du kannst zusätzliche eigene Konten anlegen („Finanzen → Konten →
Hinzufügen"), zum Beispiel für eine Kasse oder weitere Ertragsarten. Ein
Konto öffnen zeigt seine Buchungen, mit einem Filter auf **unausgeglichene**
Transaktionen (siehe unten).

Es gibt keine Funktion, ein Konto zu löschen; ein entsprechender Link
existiert nicht in der Oberfläche.

## Transaktionen und Buchungen

Eine **Transaktion** besteht aus einer oder mehreren **Buchungen**, jede davon
Soll oder Haben auf genau einem Konto, wahlweise einem Mitglied zugeordnet.
Eine Transaktion gilt als **ausgeglichen**, wenn Soll- und Habensumme
übereinstimmen; nur ausgeglichene Transaktionen gelten als abgeschlossen.

**Buchungen lassen sich nicht direkt löschen oder ändern.** Um eine
Transaktion rückgängig zu machen, storniere sie („Stornieren" auf der
Transaktionsseite): byro legt eine neue Transaktion mit exakt umgekehrten
Buchungen an und verknüpft sie mit dem Original. Beide bleiben sichtbar.

### Eine unausgeglichene Transaktion manuell ausgleichen

Nach einem Bankimport (siehe unten) kann eine Transaktion unausgeglichen
bleiben, wenn keine automatische Zuordnung möglich war. Auf der
Transaktionsseite trägst du dann manuell ein Gegenkonto ein (optional mit
Mitglied) und einen Soll- oder Habenbetrag – vorbelegt mit exakt der
Differenz, die zum Ausgleich fehlt. Kommst du über die Liste unausgeglichener
Buchungen eines Kontos hierher, führt dich byro nach dem Speichern direkt zur
nächsten unausgeglichenen Transaktion.

### Beleg anhängen

Auf derselben Transaktionsseite lässt sich ein Dokument hochladen und mit der
Transaktion verknüpfen (vorbelegte Kategorie „Beleg"). Mehr zu Dokumenten und
Kategorien: [Dokumente](documents.md).

## Bankimport

„Finanzen → Bankimport → Hinzufügen" lädt eine Datei hoch (Standardlimit 25
MiB) und verarbeitet sie sofort mit dem gewählten Importformat.

* Steht kein Importformat zur Auswahl, ist kein passendes Plugin installiert
  – byro selbst bringt keinen Bankimporter mit (siehe
  [Plugins](../administration/plugins.md) für die Installation, zum Beispiel
  des offiziellen Plugins für CAMT.053- und MT940-Dateien).
* Nach der Verarbeitung meldet byro, wie viele Buchungen gelesen, neu
  importiert und als bereits bekannt übersprungen wurden. Ein wiederholter
  Import derselben oder überlappender Dateien erzeugt **keine** doppelten
  Buchungen.
* Direkt nach dem Import versucht byro automatisch, jede neue Buchung einem
  Mitglied zuzuordnen (abhängig von installierten Matching-Plugins).
  Buchungen, die dabei nicht zugeordnet werden konnten, bleiben unausgeglichen
  (siehe oben) und lassen sich später manuell ausgleichen oder über „Match"
  in der Uploadliste erneut automatisch zuordnen lassen – zum Beispiel,
  nachdem ein passendes Matching-Plugin installiert oder aktualisiert wurde.
* Schlägt die Verarbeitung fehl (nicht lesbare Datei, nicht unterstützte
  Währung, ungültiger Betrag oder ungültiges Datum in der Datei), meldet
  byro das mit einer verständlichen Fehlermeldung; **nichts wird
  geschrieben**, der Import ist alles-oder-nichts. Der Upload selbst bleibt
  erhalten und lässt sich über „Verarbeiten" in der Uploadliste erneut
  versuchen, zum Beispiel nach einer korrigierten Datei.
* byro akzeptiert nur Beträge in Euro.

Technische Details zur Dublettenerkennung, den genauen Fehlerklassen und wie
ein Bankimporter-Plugin funktioniert: die Entwicklerdokumentation
[Bankimporter](../development/plugins/bank-transaction-importers.md).

## Referenz: Zahlungsstatus

Der Saldo eines Mitglieds (siehe
[Mitgliedschaften und Beiträge](memberships-and-fees.md)) ist die Summe
seiner Buchungen auf den Beitragskonten; ein negativer Saldo bedeutet offene
Forderungen. Es gibt keinen separaten „Zahlungsstatus" über den berechneten
Saldo hinaus.
