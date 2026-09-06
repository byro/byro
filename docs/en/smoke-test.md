# Smoke test

!!! warning "Preliminary page"
    This page only checks that the Zensical build supports the Markdown features we need. It is removed before the cutover.

## Internal link

To the [start page](index.md) and to the section [Table](#table) on this page.

## Code block

```bash
byroctl update --check
```

Inline code: `BYRO_SITE_URL`.

## Admonition

!!! note
    A note with **bold text** and a [link](https://byro.readthedocs.io/).

??? info "Collapsible details"
    This block is collapsed.

## Table

| Option | Environment variable | Default |
|---|---|---|
| `url` | `BYRO_SITE_URL` | `http://localhost` |
| `trust_proxy` | `BYRO_TRUST_PROXY` | `False` |

## Image

![byro logo](img/logo/byro_128.png){ width="64" }

## Tabs

=== "byroctl"

    ```bash
    byroctl start
    ```

=== "Docker Compose"

    ```bash
    docker compose up -d
    ```

## Snippet from the repository

The following file is included at build time from `deploy/byro.conf.example`:

```bash
--8<-- "deploy/byro.conf.example"
```

## Footnote

A sentence with a footnote.[^1]

[^1]: The footnote text.
