# Installation

byro ist freie Software. Du kannst es also selbst auf deinem eigenen Server
(oder deinem Raspberry Pi, …) betreiben. Diese Freiheit bringt aber auch
Verantwortung mit sich:

!!! warning
    Wer byro hostet, übernimmt die Verantwortung für die persönlichen und
    finanziellen Daten der Mitglieder. Stelle sicher, dass Installation und
    Server sicher sind und auch künftig gepflegt werden. Wenn du dich damit
    nicht wohlfühlst, sprich uns an oder wähle eine Offline-Installation.

Es gibt drei Wege, byro zu installieren:

1. **byroctl** (empfohlen): ein kleines Kommandozeilenwerkzeug, das byro mit
   Docker Compose einrichtet, die Konfiguration in einer Datei hält und Updates
   für dich einspielt. Fang hier an, wenn nichts dagegen spricht:
   [Installation mit byroctl](byroctl.md).
2. **Docker Compose von Hand**: dasselbe Container-Image und dieselben
   Compose-Dateien wie bei byroctl, verwaltet mit gewöhnlichen
   `docker compose`-Befehlen. Für Administratoren mit eigener Docker-Umgebung:
   [Installation mit Docker Compose](docker-compose.md).
3. **Bare Metal**: byro von PyPI in einer Python-Umgebung mit PostgreSQL,
   gunicorn, systemd und eigenem Reverse Proxy. Für klassische oder
   individuelle Installationen: [Bare-Metal-Installation](bare-metal.md).

Alle drei Wege teilen dieselben Konfigurationsoptionen
([Konfiguration](../configuration/index.md)), denselben Weg zu Plugins
([Plugins](../administration/plugins.md)), dieselben Wartungsaufgaben und
denselben Rat: byro nur hinter HTTPS betreiben und Daten sichern.

Die folgenden Seiten beschreiben eine geradlinige Einrichtung, ohne auf
Grundlagen wie Serverhärtung oder Backups im Allgemeinen einzugehen.

Das veraltete `production/`-Setup hat eine eigene Seite:
[Legacy-Setup mit den production/-Dateien](legacy-production.md).
