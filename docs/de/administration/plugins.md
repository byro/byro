# Plugins

byro lässt sich mit Plugins erweitern: Python-Pakete, die sich bei byro
registrieren und Importer, Mitgliedsdaten, Dokumente oder ganze Funktionen
hinzufügen. Wie Plugins geschrieben werden, steht in der
[Plugin-Entwicklung](../development/plugins/overview.md).

Ein Plugin läuft mit denselben Rechten wie byro selbst und hat vollen Zugriff
auf deine Datenbank. Installiere deshalb nur Plugins, denen du vertraust.

## Offizielle Plugins

**Mitgeliefert** (jede byro-Installation, nicht einzeln installierbar oder
entfernbar): `byro.plugins.profile` (zusätzliche persönliche Mitgliedsdaten
wie Spitzname, Geburtsdatum, Telefonnummer) und `byro.plugins.sepa`
(SEPA-Lastschrift-Daten je Mitglied).

**Katalog** (einzeln installierbar über
[Plugin-Verwaltung](plugin-management.md)):

| Plugin | Beschreibung | Repository |
|---|---|---|
| `finance-import-bank-files` | Datei-basierter Bankimport (CAMT.053 und MT940) | [byro/byro-finance-import-bank-files](https://github.com/byro/byro-finance-import-bank-files) |

Das ist der vollständige Katalog zum Zeitpunkt dieser Seite – kein
ausgedachtes Beispiel, sondern `deploy/plugin-catalog.conf` dieses Release.
Zwei weitere von der byro-Organisation gepflegte Plugins existieren, sind
aber mit der aktuellen byro-Version nicht kompatibel und deshalb nicht im
Katalog: [byro-mailman](https://github.com/byro/byro-mailman) und
[byro-gemeinnuetzigkeit](https://github.com/byro/byro-gemeinnuetzigkeit).
Weitere Plugins listet das GitHub-Thema
[byro-plugin](https://github.com/topics/byro-plugin). Das ist ein Ort zum
Nachsehen, keine Empfehlung; byroctl installiert daraus nichts automatisch.

Wie ein Plugin in den Katalog aufgenommen wird, beschreibt
[Plugin-Katalog](../development/releasing.md#plugin-katalog).

## Plugin-Verwaltung

Die Installation, Aktualisierung und Entfernung von Plugins sowie die
Fehlersuche beschreibt die [Plugin-Verwaltung](plugin-management.md).

Für die einzelnen Installationswege siehe [byroctl](../installation/byroctl.md),
[Docker Compose](../installation/docker-compose.md) und
[Bare Metal](../installation/bare-metal.md).

Integrationen, die keine Plugins sind (SMTP-Mailversand, OIDC/SSO), stehen bei
[Konfiguration](../configuration/reference.md) beziehungsweise
[Benutzer und Login](users-and-login.md).
