# Mitgliedschaften und Beiträge

Ein Mitglied kann über die Zeit mehrere **Mitgliedschaften** haben, zum
Beispiel weil sich der Beitrag ändert oder ein früherer Austritt und
Wiedereintritt dokumentiert werden soll. Jede Mitgliedschaft trägt ihren
eigenen Beitrag – es gibt **keine wiederverwendbare „Beitragsart“**, die du an
mehrere Mitgliedschaften anhängst: Betrag und Intervall werden direkt an
jeder einzelnen Mitgliedschaft gesetzt (siehe
[Mitgliedsdaten ändern](members.md#mitgliedsdaten-andern)).

## Felder einer Mitgliedschaft

* **Beginn** und **Ende** (Ende leer = läuft weiter),
* **Beitrag**: der Betrag, der je Intervall fällig wird,
* **Intervall**: monatlich, vierteljährlich, halbjährlich oder jährlich.

Nur eine Mitgliedschaft ohne Ende oder mit einem Ende in der Zukunft zählt als
aktiv; hat ein Mitglied keine oder nur vergangene Mitgliedschaften, gilt es
als inaktiv (siehe [Mitgliederliste](members.md#mitgliederliste)).

## Wie Beiträge fällig werden

byro berechnet die Fälligkeiten einer Mitgliedschaft aus Beginn, Intervall
und Beitrag: ab dem Beginn wird der Beitrag alle `Intervall` Monate erneut
fällig, bis zum Ende der Mitgliedschaft oder, ohne Ende, bis heute. Es gibt
keine Vorschau- oder Änderungsfunktion für einzelne Fälligkeiten – Korrekturen
laufen über die [Saldenkorrektur](members.md#saldenkorrektur) am Mitglied.

## Verjährung

Wie lange offene Beiträge eines Mitglieds noch eingefordert werden können,
legt die **Verjährungsfrist** fest (Einstellungen → Allgemein, siehe
[Einstellungen](../administration/settings.md#allgemein)), organisationsweit
in Monaten, nicht je Mitgliedschaft. Das Mitglieds-Dashboard zeigt den
aktuell verjährten Betrag sowie eine Vorschau, was in einem Jahr zusätzlich
verjährt sein wird.

## Beitragsabgleich für viele Mitglieder

Um für alle aktiven Mitglieder auf einmal Salden über einen Zeitraum zu
erzeugen und optional Erinnerungsmails für Mitglieder mit einem Saldo unter
einem Schwellwert vorzubereiten, siehe
[Massenaktionen](members.md#massenaktionen).
