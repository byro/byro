# byro Dokumentation

![byro](img/logo/byro_128.png){ width="128" }

byro ist eine Mitgliederverwaltung. byro eignet sich am besten für kleine und
mittelgroße Vereine, NGOs und Verbände aller Art, mit Schwerpunkt auf dem
deutschsprachigen Raum. byro setzt stark auf Plugins, damit es sich an
unterschiedliche Anforderungen in verschiedenen Situationen und Ländern
anpassen lässt.

byro ist stabil und in mehreren Communities im Einsatz. Es wird aktiv
weiterentwickelt.

byro ist (noch) keine vollständige Buchhaltungssoftware und kein
Veranstaltungs- oder Ticketing-Tool; es bringt auch keine gehostete
Standardinstanz mit, die du ohne eigenen Server nutzen könntest – byro wird
selbst betrieben (siehe [Installation](installation/index.md)) oder von
jemandem in deiner Organisation oder deinem Umfeld für dich betrieben.

## Wie du hier anfängst

**Dein Verein hat bereits ein laufendes byro** und du sollst es benutzen, zum
Beispiel als Vorstand oder Kassenwart: Ein Administrator oder eine
Administratorin bei dir hat den Zugang eingerichtet; die [Benutzung](usage/index.md)
beschreibt die tägliche Arbeit mit Mitgliedern, Beiträgen und Finanzen (dieser
Bereich entsteht gerade). Fragen zu Login, Zwei-Faktor-Anmeldung oder Rechten
beantwortet zunächst deine Administration, technische Hintergründe stehen unter
[Administration](administration/index.md).

**Du richtest byro für eine Organisation neu ein**, als technisch versierter
Administrator oder Administratorin: Beginne bei
[Installation](installation/index.md), das die drei unterstützten Wege
(byroctl, Docker Compose, Bare Metal) und die Entscheidung dazwischen erklärt.
[Konfiguration](configuration/index.md) ist die Referenz aller
Einstellungen, [Administration](administration/index.md) beschreibt Update,
Backup, Plugins und laufenden Betrieb.

**Du willst byro erweitern oder daran mitarbeiten**: Start ist
[Entwicklung & API](development/index.md).

- [Installation](installation/index.md): byro auf dem eigenen Server betreiben,
  mit byroctl, Docker Compose oder Bare Metal.
- [Administration](administration/index.md): MFA, PGP, Plugins, Update, Backup
  und Restore, sowie Monitoring und Fehlersuche in einer laufenden
  Installation.
- [Konfiguration](configuration/index.md): Referenz aller
  Konfigurationsoptionen.
- [Benutzung](usage/index.md): die tägliche Arbeit mit byro (entsteht).
- [Entwicklung & API](development/index.md): byro oder ein Plugin
  weiterentwickeln.

## Funktionen

Da byro aktiv weiterentwickelt wird, kann diese Liste veralten. Bitte
[eröffne ein Issue](https://github.com/byro/byro/issues/new) für Funktionen,
die dir fehlen!

- **Mitgliederverwaltung:** Mitglieder und ihre Daten anlegen und bearbeiten.
- **Mitgliedschaftsverwaltung:** Beiträge, die ein Mitglied zahlen soll,
  anlegen und ändern.
- **Eigene Mitgliedsdaten:** Zusätzliche Daten über ein Plugin erfassen. Es gibt
  viele Beispiel-Plugins und eine Entwicklerdokumentation.
- **Zahlungen importieren und zuordnen:** Bankdaten kommen über ein Plugin
  hinein (der Core selbst bringt keinen Importer mit); das offizielle Plugin
  [`finance-import-bank-files`](administration/plugins.md) unterstützt
  CAMT.053. Die Zuordnung zu Mitgliedern läuft über eigene Verfahren, die
  Plugins beisteuern.
- **Mails versenden:** Alle Mails können vor dem Versand geprüft werden. Die
  Standardvorlagen lassen sich bearbeiten und erweitern.
- **Mitgliedssalden einsehen:** Jede einzelne Transaktion ist jederzeit
  nachvollziehbar.
- **Mitgliedsbezogene Dokumente hochladen:** für oder von Mitgliedern, optional
  automatisch per Mail versandt.
- **Mehr-Faktor-Authentifizierung:** Backend-Nutzer schützen ihr Konto mit
  einer Authenticator-App (TOTP); Administratoren können das für alle
  vorschreiben.
- **Mitglieder vernetzen:** Mitglieder entscheiden selbst, welche ihrer Daten
  für andere Mitglieder sichtbar sind. Das Mitgliederverzeichnis hilft ihnen,
  direkt miteinander in Kontakt zu treten.

Bitte beachte: byro ist ein Werkzeug zur Verwaltung von Mitgliedsdaten,
Zahlungen und den zugehörigen Verwaltungsvorgängen. byro unterstützt Buchungen
und Transaktionen, ist aber (noch) keine vollständige Buchhaltungssoftware.

## Lizenz

byro steht unter der GNU Affero General Public License, Version 3.0 only
(`AGPL-3.0-only`). Ältere Versionen von byro wurden unter der Apache License
2.0 veröffentlicht.

Diese Dokumentation steht unter der
[Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/deed.de)
(`CC-BY-SA-4.0`). Du darfst sie teilen und bearbeiten, solange du die
Urheber nennst und deine Bearbeitungen unter derselben Lizenz weitergibst.

Details, die Lizenzhistorie und die Lizenzen gebündelter Komponenten stehen in
der Datei [LICENSE](https://github.com/byro/byro/blob/main/LICENSE) im
byro-Repository.
