# Bare-Metal-Installation (ohne Docker)

Diese Anleitung hilft dir, byro von PyPI auf einer Linux-Distribution zu
installieren, mit eigenem Datenbankserver, gunicorn, systemd und Reverse Proxy.
Sie ist die richtige Wahl für klassische oder individuelle Installationen. Wenn
Container den Großteil davon übernehmen sollen, siehe
[Installation mit byroctl](byroctl.md) (empfohlen) oder
[Installation mit Docker Compose](docker-compose.md).

## Schritt 0: Voraussetzungen

Richte die folgenden Systeme vorab ein, wir erklären sie hier nicht (siehe aber
die Links zu externen Anleitungen):

* **Python 3.12+** und `pip` für Python 3. Prüfen mit `python -V` und
  `pip3 -V`.
* Ein SMTP-Server zum Mailversand
* Ein HTTP Reverse Proxy, z. B. nginx oder Apache, für HTTPS-Verbindungen
* Ein Datenbankserver: MySQL 5.7+ oder MariaDB 10.2+ oder PostgreSQL 9.6+.
  SQLite geht, aber wir raten dringend davon ab, SQLite produktiv zu
  betreiben. Wenn du die Wahl hast, empfehlen wir PostgreSQL.

<!-- migration note (AP01 GAPS A6): die Datenbank-Mindestversionen stammen aus der Zeit vor Django 5.2 und werden in AP07 neu geschrieben. -->

Wir empfehlen außerdem eine Firewall, auch wenn das keine byro-spezifische
Empfehlung ist. Wenn du neu bei Linux und Firewalls bist, fang mit
[ufw](https://de.wikipedia.org/wiki/Uncomplicated_Firewall) an.

!!! note
    Betreibe byro nicht ohne HTTPS-Verschlüsselung. Du verarbeitest sensible
    Daten, und dank [Let's Encrypt](https://letsencrypt.org/) sind
    SSL-Zertifikate heute kostenlos. Für reine HTTP-Installationen leisten wir
    außer zu Testzwecken *keinen* Support.

## Schritt 1: Unix-Benutzer

Da byro nicht als root laufen soll, legen wir zuerst einen unprivilegierten
Benutzer an:

```console
# adduser byro --disabled-password --home /var/byro
```

In dieser Anleitung sind alle Zeilen mit vorangestelltem `#` Befehle, die du
auf dem Server als `root` ausführst (z. B. mit `sudo`); Zeilen mit `$` führst
du als der unprivilegierte Benutzer aus.

## Schritt 2: Datenbank einrichten

Ist der Datenbankserver installiert, brauchen wir noch eine Datenbank und einen
Datenbankbenutzer. Wir empfehlen PostgreSQL. byro funktioniert auch mit
MariaDB und SQLite (und testet dagegen). Wenn du nicht PostgreSQL verwendest,
schau in die entsprechende Dokumentation. Für PostgreSQL:

```console
postgres $ createuser byro -P
postgres $ createdb -O byro byro
```

Bei MySQL stelle sicher, dass der Zeichensatz der Datenbank `utf8mb4` ist,
zum Beispiel so:

```sql
CREATE DATABASE byro DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci
```

## Schritt 3: Paketabhängigkeiten

Um byro zu bauen und zu betreiben, brauchst du über die oben genannten
Abhängigkeiten hinaus folgende Debian-Pakete:

```console
# apt-get install git build-essential libssl-dev gettext
```

Wenn du ausgehende Mails mit PGP signieren und verschlüsseln willst, brauchst
du vor der Installation von byro außerdem GnuPG:

```console
# apt-get install gnupg gpg-agent
```

Ersetze alle weiteren „pip“-Befehle durch „pip3“, falls Python 3 auf deinem
System nicht die Standardversion ist.

## Schritt 4: Konfiguration

Wir legen ein Konfigurationsverzeichnis und eine Konfigurationsdatei für byro
an:

```console
# mkdir /etc/byro
# touch /etc/byro/byro.cfg
# chown -R byro:byro /etc/byro/
# chmod 0600 /etc/byro/byro.cfg
```

Fülle `/etc/byro/byro.cfg` mit folgendem Inhalt (an deine Umgebung angepasst):

```ini
--8<-- "src/byro.example.cfg"
```

## Schritt 5: Installation

Jetzt installieren wir byro selbst. Führe die folgenden Schritte als Benutzer
`byro` aus. Wir aktualisieren alle relevanten Python-Pakete in der
Python-Umgebung des Benutzers, damit die globale Python-Installation nichts
davon mitbekommt:

```console
$ pip install --user -U pip setuptools wheel gunicorn psycopg2-binary
```

Als Nächstes installieren wir byro – entweder das aktuelle PyPI-Release oder
einen bestimmten Branch oder Commit:

```console
$ pip install --user -U byro  # ODER alternativ
$ pip install --user -U "git+https://github.com/byro/byro.git@main#egg=byro&subdirectory=src"
```

Außerdem brauchen wir ein Datenverzeichnis:

```console
$ mkdir -p /var/byro/data/media
```

Wir legen die Datenbankstruktur an und kompilieren statische Dateien und
Übersetzungen (`rebuild` führt `compilemessages`, `collectstatic` und
`compress` für dich aus):

```console
$ python -m byro migrate
$ python -m byro rebuild
```

Lege nun einen Administrator an:

```console
$ python -m byro createsuperuser
```

Wenn du byro nur ausprobieren willst, kannst du Testdaten laden:

```console
$ python -m byro make_testdata
```

## Schritt 5a: Plugins (optional)

Plugins sind Python-Pakete in derselben Umgebung wie byro (was es gibt, steht
unter [Plugins](../administration/plugins.md)). Pinne eine Version oder einen
Tag, dann migrieren, rebuild und neu starten:

```console
$ pip install --user 'byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@v1.2.0'
$ python -m byro migrate
$ python -m byro rebuild
# systemctl restart byro-web    (sobald der Dienst aus Schritt 6 existiert)
```

`rebuild` kompiliert die Übersetzungen jedes installierten Plugins ebenso wie
die von byro und sammelt die statischen Dateien der Plugins ein.

## Schritt 6: byro als Dienst starten

Wir empfehlen, byro über systemd zu starten, damit es nach einem Neustart
wieder läuft. Lege `/etc/systemd/system/byro-web.service` mit folgendem Inhalt
an (Pfade an dein System anpassen, insbesondere die lokale Python-Version):

```ini
[Unit]
Description=byro web service
After=network.target

[Service]
User=byro
Group=byro
WorkingDirectory=/var/byro/.local/lib/python3.12/site-packages/byro
ExecStart=/var/byro/.local/bin/gunicorn byro.wsgi \
                      --name byro --workers 4 \
                      --max-requests 1200  --max-requests-jitter 50 \
                      --log-level=info --bind=127.0.0.1:8345
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

byro hat außerdem periodische Aufgaben (PGP-Schlüssel auffrischen,
Ablauferinnerungen versenden, unvollendete MFA-Einrichtungen aufräumen). Sie
laufen nur, wenn etwas regelmäßig `python -m byro runperiodic` aufruft. Lege
`/etc/systemd/system/byro-periodic.service` an:

```ini
[Unit]
Description=byro periodic tasks
After=network.target

[Service]
Type=oneshot
User=byro
Group=byro
WorkingDirectory=/var/byro
ExecStart=/var/byro/.local/bin/python -m byro runperiodic
```

und `/etc/systemd/system/byro-periodic.timer`:

```ini
[Unit]
Description=Run byro periodic tasks every 10 minutes

[Timer]
OnBootSec=5min
OnUnitActiveSec=10min

[Install]
WantedBy=timers.target
```

Falls `/var/byro/.local/bin/python` nicht existiert, verwende das `python3`,
in dem byro installiert ist (`which python3` als Benutzer byro).

Jetzt kannst du die Dienste aktivieren und starten:

```console
# systemctl daemon-reload
# systemctl enable --now byro-web
# systemctl enable --now byro-periodic.timer
```

## Schritt 7: SSL

Das folgende Beispiel zeigt eine nginx-Konfiguration als Proxy für byro:

```nginx
server {
    listen 80 default_server;
    listen [::]:80 ipv6only=on default_server;
    server_name byro.mydomain.com;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl ipv6only=on default_server;
    server_name byro.mydomain.com;

    ssl_certificate /path/to/cert.chain.pem;
    ssl_certificate_key /path/to/key.pem;

    add_header Referrer-Policy same-origin;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:8345/;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Host $http_host;
    }
}
```

Weil der Proxy TLS terminiert, muss byro dem Header `X-Forwarded-Proto`
vertrauen. Setze `trust_proxy = True` im Abschnitt `[site]` von
`/etc/byro/byro.cfg` (siehe [Konfiguration](../configuration/index.md)); sonst
erzeugt byro absolute URLs wie den OpenID-Connect-Redirect mit `http` und hält
Anfragen für unsicher.

Liefere `/media/` nicht über den Webserver aus: byro gibt Dokumente selbst
heraus, nachdem es die Anmeldung geprüft hat. Ein `location /media/`-Alias,
wie ihn ältere Fassungen dieser Anleitung vorschlugen, würde jedes hochgeladene
Dokument für jeden offenlegen, der die URL kennt.

Wir empfehlen, dich über
[starke Verschlüsselungseinstellungen](https://mozilla.github.io/server-side-tls/ssl-config-generator/)
für deinen Webserver zu informieren.

Geschafft! byro sollte jetzt unter `https://byro.yourdomain.com/` erreichbar
sein, und du kannst dich als der oben angelegte Administrator anmelden. byro
führt dich durch die restlichen Einrichtungsschritte.

## Schritt 8: Installation prüfen

Ob die Weboberfläche läuft und ob es Probleme gibt, siehst du mit:

```console
# journalctl -u byro-web
```

In der Startausgabe nennt byro auch sein Logverzeichnis, ein guter Ort, um nach
Fehlerursachen zu suchen.

## Nächste Schritte: Updates

!!! warning
    Wir bemühen uns, keine Updates mit Brüchen zu veröffentlichen, aber
    **mache vor jedem Upgrade ein Backup**.

Lies vor einem Upgrade die
[Release Notes](https://github.com/byro/byro/releases) auf relevante
Update-Hinweise. Stelle außerdem sicher, dass du ein aktuelles Backup der
Datenbank, von `/var/byro/data` (enthält die Secret-Key-Datei `.secret`, deren
Verlust alle Sitzungen und MFA-Geräte ungültig macht) und deiner
Konfiguration hast.

Führe dann in derselben Umgebung (vermutlich deiner virtualenv) die folgenden
Befehle aus, um zuerst byro zu aktualisieren, dann bei Bedarf die Datenbank,
dann die statischen Dateien neu zu bauen und schließlich den Dienst neu zu
starten. Vergisst du den Neustart, bekommst du eine unterhaltsame Menge
Fehler.

Willst du auf ein bestimmtes Release aktualisieren, ersetze `byro` in der
ersten Zeile durch `byro==1.2.3`:

```console
$ pip3 install -U byro gunicorn
$ python -m byro migrate
$ python -m byro rebuild
# systemctl restart byro-web
```

Prüfe auch die Release Notes deiner Plugins und aktualisiere sie vor `migrate`
auf demselben Weg (`pip install -U 'byro-finance-import-bank-files @ git+...@<neuer tag>'`).
