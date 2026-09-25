# PGP-Mailverschlüsselung

byro kann ausgehende Mails signieren und Mails an Mitglieder mit OpenPGP
verschlüsseln. Die Funktion ist Teil des byro-Kerns, verwendet aber die
GnuPG-Kommandozeilenwerkzeuge als Krypto-Backend. Eine funktionierende
Installation braucht daher die GnuPG-Systempakete.

## Docker-Installationen

Das offizielle byro-Docker-Image enthält die nötigen GnuPG-Laufzeitpakete. Die
Standard-Docker-Konfiguration legt das GnuPG-Home-Verzeichnis in
`/var/byro/data/gnupg`, sodass Schlüssel im normalen byro-Datenvolume
erhalten bleiben.

Nach dem Aktualisieren des Images führe die Migrationen aus und konfiguriere
PGP dann in den Office-Einstellungen.

## Manuelle Installationen

Installiere die von GnuPG benötigten Systempakete. Unter Debian oder Ubuntu:

```console
# apt-get install gnupg gpg-agent
```

Installiere dann byro in derselben Python-Umgebung, in der byro läuft:

```console
$ pip install --user -U byro
```

Bei Installation aus git:

```console
$ pip install --user -U "git+https://github.com/byro/byro.git@main#egg=byro&subdirectory=src"
```

## Konfigurationsdatei

Das Laufzeit-Backend wird im Abschnitt `[pgp]` der `byro.cfg` konfiguriert:

```ini
[pgp]
backend = byro.mails.gnupg_backend.GnuPGBackend
home = /var/byro/data/gnupg
```

`backend`
:   Python-Importpfad des PGP-Backends. Das Standard-Backend kapselt das
    Kommandozeilenwerkzeug `gpg`.

`home`
:   GnuPG-Home-Verzeichnis des byro-Prozesses. Es sollte nur für den
    byro-Benutzer lesbar und beschreibbar sein. Ist der Wert leer, verwendet
    GnuPG sein Standard-Home-Verzeichnis für diesen Benutzer.

Dieselben Werte lassen sich über Umgebungsvariablen setzen:

* `BYRO_PGP_BACKEND`
* `BYRO_PGP_HOME`

## Office-Einstellungen

Die Office-Einstellungen von byro enthalten die operative PGP-Richtlinie:

* **PGP-Signatur** enthält den privaten Signaturschlüssel der Organisation und
  die Option, ausgehende Mails zu signieren.
* **PGP-Verschlüsselung** enthält die Verschlüsselung von Mitglieder-Mails,
  die Keyserver-URLs und die Richtlinie für fehlende, ungültige, ungeprüfte
  oder abgelaufene Mitgliedsschlüssel.
* **Erweiterte Schlüsselverwaltung** enthält automatisches Auffrischen,
  Timeouts und Ablauferinnerungen für Mitgliedsschlüssel.

## Signaturschlüssel der Organisation

Lade in der PGP-Einstellungskarte den ASCII-armored privaten Signaturschlüssel
der Organisation ohne Passphrase hoch. byro prüft, dass er genau einen
signaturfähigen Schlüssel enthält, verifiziert, dass er ohne Passphrase
signieren kann, importiert ihn in das konfigurierte GnuPG-Home-Verzeichnis und
trägt seinen Fingerabdruck automatisch ein. Das private Schlüsselmaterial
landet weder in der byro-Datenbank noch im Audit-Log; es liegt nur im
GnuPG-Schlüsselbund.

Für einen importierten Schlüssel zeigen die Einstellungen Fingerabdruck,
User-IDs, Erstellungs- und Ablaufdatum, Algorithmus und ob er signaturfähig
ist. Diese Angaben werden aus dem GnuPG-Schlüsselbund gelesen; privates
Schlüsselmaterial wird nicht angezeigt.

Alternativ importierst oder erzeugst du den Schlüssel über Deployment-Werkzeuge
im GnuPG-Home-Verzeichnis von byro. Die Office-Einstellungen zeigen den
konfigurierten Fingerabdruck dann schreibgeschützt; lade einen privaten
Schlüssel hoch, um ihn zu ersetzen.

Beispiel als Benutzer byro:

```console
$ GNUPGHOME=/var/byro/data/gnupg gpg --list-secret-keys --fingerprint
```

Der hochgeladene Signaturschlüssel darf nicht passwortgeschützt sein. byro
speichert keine Passphrasen. Schütze das GnuPG-Home-Verzeichnis so, dass nur
der byro-Prozess auf den importierten privaten Schlüssel zugreifen kann.

## Mitgliedsschlüssel

Jedes Mitglied kann einen oder mehrere öffentliche PGP-Schlüssel haben. In der
Mitgliedsansicht erlaubt der Reiter PGP den Office-Benutzern:

* einen öffentlichen Schlüssel per Fingerabdruck von einem Keyserver zu
  importieren
* einen ASCII-armored öffentlichen Schlüssel manuell hochzuladen
* einen Schlüssel zu deaktivieren
* einen Schlüssel zu löschen

Per Fingerabdruck von Keyservern importierte Schlüssel werden automatisch als
gültig markiert, weil byro nur den exakt vom Mitglied genannten oder vom Office
akzeptierten Fingerabdruck importiert. Manuell hochgeladene öffentliche
Schlüssel werden nur akzeptiert, wenn das Schlüsselmaterial zum eingegebenen
Fingerabdruck passt; sonst lehnt byro den Upload mit einem Formularfehler ab.

Ist die PGP-Verschlüsselung aktiv, stellt byro getrennte Nachrichten an die
Empfänger in `To`, `Cc` und `Bcc` zu. Jeder Mitgliedsempfänger wird daher mit
seinem eigenen Schlüssel verschlüsselt und gegen die konfigurierte
Schlüsselrichtlinie geprüft. Die sichtbaren Header `To` und `Cc` bleiben
erhalten, `Bcc`-Empfänger bleiben verborgen.

## Fingerabdrücke aus Mitgliedsanträgen

Die Einstellungen des Registrierungsformulars enthalten ein Feld
`PGP-Fingerabdruck`. Ist es aktiviert, können Office-Benutzer beim Anlegen
eines Mitglieds den Fingerabdruck aus dem Mitgliedsantrag eingeben. byro
speichert den Fingerabdruck und versucht sofort, den passenden öffentlichen
Schlüssel von den konfigurierten Keyservern zu importieren.

Kann der Schlüssel in dem Moment nicht importiert werden, wird das Mitglied
trotzdem angelegt und der PGP-Schlüssel bleibt ausstehend oder nicht gefunden.
Das automatische Auffrischen versucht es später erneut, falls aktiviert.

## Keyserver-Importe

byro importiert Schlüssel nur über den vollständigen Fingerabdruck. Es
verschlüsselt nicht an Schlüssel, die nur über die E-Mail-Adresse gefunden
wurden. Das verhindert, versehentlich einen fremden Schlüssel mit passender
User-ID zu verwenden.

Die PGP-Office-Einstellungen nehmen einen Keyserver pro Zeile. byro probiert
sie der Reihe nach, bis einer den angeforderten Schlüssel liefert. Du kannst
reine Hostnamen eingeben; byro verwendet dafür `hkps://`. Gibst du `https://`
oder `http://` ein, wandelt byro diese Schemata in GnuPGs `hkps://` bzw.
`hkp://` um. Explizite Schemata sind auf `hkp://`, `hkps://`, `http://` und
`https://` beschränkt. Die Standardliste ist:

* `keys.openpgp.org`
* `keyserver.ubuntu.com`
* `pgp.mit.edu`

## Automatisches Auffrischen

Ist das automatische Auffrischen aktiv, aktualisiert byro keyserververwaltete
Schlüssel aus der periodischen Aufgabe. Intervall und Keyserver-Timeout werden
in den PGP-Office-Einstellungen konfiguriert. Stelle sicher, dass die
periodische Aufgabe in deiner Installation regelmäßig läuft. Ablaufende
Schlüssel können vor dem Ablaufdatum Erinnerungsmails an Mitglieder auslösen.
Diese Erinnerungen werden als Entwürfe im byro-Postausgang angelegt, damit
Office-Benutzer sie prüfen und über den normalen Mail-Workflow versenden
können.

## Dashboard-Warnungen

Das Office-Dashboard zeigt PGP-Warnungen für eine unvollständige
Signaturkonfiguration, aktive Mitgliedsschlüssel, die ungültig, widerrufen
oder abgelaufen sind, bald ablaufende Schlüssel sowie Fehler beim Import oder
Auffrischen von Keyservern.
