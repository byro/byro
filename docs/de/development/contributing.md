# Mitwirken

Wir freuen uns immer über Verbesserungen an byro, und **deine** Hilfe ist
willkommen! Wir prüfen deine Beiträge, geben Rückmeldung zu deinen Änderungen
und helfen dir, wenn du nicht weiterweißt.

Du brauchst ein [GitHub](https://github.com)-Konto, um an byro mitzuwirken, und
solltest wissen, wie man mit git pullt, pusht und committet.

Hast du bereits eine Verbesserung im Kopf, [eröffne ein
Issue](https://github.com/byro/byro/issues/new) dafür. Andernfalls sieh dir
unsere [offenen Issues](https://github.com/byro/byro/issues) an und such dir
eines aus. Zögere nicht, im Issue nachzufragen, wenn etwas unklar ist.

Zuerst [forke byro](https://github.com/byro/byro/fork) und klone dann dein
Repository (GitHub zeigt dir, wie). Hast du dein Repository geklont und
geöffnet, lege einen neuen Feature-Branch mit der Issue-Nummer an:

```console
$ git checkout -b issue/123
```

Erfordert dein Issue Codeänderungen, richte das [Entwicklungs-Setup](setup.md)
ein und mach dann hier weiter. Willst du die Dokumentation ändern, lies
[An der Dokumentation arbeiten](documentation.md).

Wir haben einige Stilprüfungen für Code und Dokumentation, wie im Setup
beschrieben. Unsere Continuous Integration prüft sie bei jedem Commit und Pull
Request, aber du solltest Tests und Prüfungen auch lokal laufen lassen und
deinen Pull Request erst als fertig betrachten, wenn sie bestehen.

Schreibe hilfreiche, gut formatierte Commit-Nachrichten – eine Anleitung
findest du
[hier](https://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html).
Hast du deine Arbeit committet, trage dich in die Datei
`src/byro/office/templates/office/settings/about.html` ein und pushe deinen
Branch:

```console
$ git push -u origin issue/123
```

und eröffne einen Pull Request. Unsere Continuous Integration prüft deine
Änderungen dann auf Probleme (fehlschlagende Tests, Stilfehler im Code oder in
der Dokumentation, …). Gib uns bitte fünf bis sieben Tage für ein Review oder
einen direkten Merge.

## Dokumentation

Ändert dein Pull Request sichtbares Verhalten (eine neue Einstellung, ein
neuer Workflow, ein geänderter Befehl), gehört eine passende Doku-Änderung
zum selben Pull Request, nicht zu einem späteren. Neue oder geänderte
Doku-Inhalte entstehen auf Deutsch (die redaktionell führende Sprache) und
werden im selben Pull Request ins Englische übertragen; `docs/check_parity.py`
schlägt in CI fehl, wenn eine Seite nur in einer Sprache existiert. Den
vollständigen Redaktionsstandard (Terminologie, Ton, Links, Lizenz)
beschreibt [An der Dokumentation arbeiten](documentation.md).

## Neue Plugins

Dieser Ablauf ist für Änderungen **an byro selbst**. Ein neues Plugin wird
nicht als Pull Request gegen dieses Repository eingereicht, sondern als
eigenes Python-Paket mit eigenem Release veröffentlicht (siehe
[Ein Plugin erstellen](plugins/creating-a-plugin.md)). Willst du dein Plugin
im Katalog gelistet haben, den `byroctl plugin add` kennt, beschreibt
[Plugin-Katalog](releasing.md#plugin-katalog), wie das geht.

## Lizenzierung von Beiträgen

byro steht unter der GNU Affero General Public License, Version 3.0 only
(`AGPL-3.0-only`). Die Dokumentation im Verzeichnis `docs/` steht unter der
Creative Commons Attribution-ShareAlike 4.0 International License
(`CC-BY-SA-4.0`). Die Datei
[LICENSE](https://github.com/byro/byro/blob/main/LICENSE) erklärt die
Details, einschließlich der Lizenzhistorie älterer, unter Apache-2.0
veröffentlichter Versionen und der Lizenzen gebündelter Komponenten.

Sofern nicht ausdrücklich anders angegeben, stehen Beiträge zu byro unter der
AGPL-3.0-only und Beiträge zur Dokumentation in `docs/` unter der
CC-BY-SA-4.0. Mit dem Einreichen eines Beitrags, zum Beispiel durch einen Pull
Request, bestätigst du, dass du die nötigen Rechte hast, ihn unter der
jeweiligen Lizenz einzureichen. Enthält dein Beitrag Code, Text, Bilder oder
anderes Material aus anderen Projekten, stelle sicher, dass dessen Lizenz mit
der AGPL-3.0-only bzw. der CC-BY-SA-4.0 vereinbar ist, lass die ursprünglichen
Urheber- und Lizenzhinweise intakt und weise in deinem Pull Request darauf hin.
