# Smoke-Test

!!! warning "Vorläufige Seite"
    Diese Seite prüft nur, ob der Zensical-Build die benötigten Markdown-Funktionen unterstützt. Sie wird vor dem Cutover entfernt.

## Interner Link

Zur [Startseite](index.md) und zum Abschnitt [Tabelle](#tabelle) auf dieser Seite.

## Codeblock

```bash
byroctl update --check
```

Inline-Code: `BYRO_SITE_URL`.

## Admonition

!!! note "Hinweis"
    Eine Notiz mit **Fettdruck** und einem [Link](https://byro.readthedocs.io/).

??? info "Ausklappbare Details"
    Dieser Block ist zugeklappt.

## Tabelle

| Option | Umgebungsvariable | Standard |
|---|---|---|
| `url` | `BYRO_SITE_URL` | `http://localhost` |
| `trust_proxy` | `BYRO_TRUST_PROXY` | `False` |

## Bild

![byro-Logo](img/logo/byro_128.png){ width="64" }

## Tabs

=== "byroctl"

    ```bash
    byroctl start
    ```

=== "Docker Compose"

    ```bash
    docker compose up -d
    ```

## Snippet aus dem Repository

Die folgende Datei wird beim Build aus `deploy/byro.conf.example` eingebunden:

```bash
--8<-- "deploy/byro.conf.example"
```

## Fußnote

Ein Satz mit Fußnote.[^1]

[^1]: Der Fußnotentext.
