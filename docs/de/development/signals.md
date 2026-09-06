# Signalliste

Diese Seite listet die Signale und Hooks, die byro anbietet. Die
[Plugin-Anleitungen](plugins/index.md) zeigen Beispiele für ihre Verwendung.

!!! info "Generierte Referenz"
    In der Sphinx-Dokumentation wurden die Beschreibungen auf dieser Seite aus
    den Docstrings im Quellcode erzeugt. Die generierte Referenz wird mit
    mkdocstrings neu aufgesetzt (Doku-Arbeitspaket AP05). Bis dahin sind die
    Docstrings in den unten genannten Modulen maßgeblich.

## Mitgliederverwaltung

Modul `byro.members.signals`:

- `new_member`
- `new_member_mail_information`
- `new_member_office_mail_information`
- `leave_member`
- `leave_member_mail_information`
- `leave_member_office_mail_information`
- `update_member`

## Zahlungen

Modul `byro.bookkeeping.signals`:

- `process_transaction`
- `bank_transaction_importers`
- `process_csv_upload` (Legacy, siehe
  [Bankimporter](plugins/bank-transaction-importers.md#legacy-api))

## Anzeige

Modul `byro.office.signals`:

- `nav_event`
- `member_view`
- `member_dashboard_tile`

Modul `byro.common.signals`:

- `unauthenticated_urls`
- `log_formatters`

## Import

Modul `byro.office.signals`:

- `member_list_importers`

Bankimporter werden über `byro.bookkeeping.signals.bank_transaction_importers`
registriert (siehe Zahlungen oben und
[Bankimporter](plugins/bank-transaction-importers.md)).

## Allgemein

Modul `byro.common.signals`:

- `periodic_task`
