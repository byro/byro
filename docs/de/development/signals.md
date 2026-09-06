# Signalliste

Diese Seite listet die Signale und Hooks, die byro anbietet. Die
[Plugin-Anleitungen](plugins/index.md) zeigen Beispiele für ihre Verwendung.

!!! info "Docstrings auf Englisch"
    Die generierten Beschreibungen unten kommen unverändert aus den
    englischsprachigen Docstrings im Quellcode; Python-Bezeichner werden nicht
    automatisch übersetzt (siehe [Entwicklungs-Setup](setup.md)).

## Mitgliederverwaltung

::: byro.members.signals
    options:
      members:
        - new_member
        - new_member_mail_information
        - new_member_office_mail_information
        - leave_member
        - leave_member_mail_information
        - leave_member_office_mail_information
        - update_member

## Zahlungen

::: byro.bookkeeping.signals
    options:
      members:
        - process_transaction
        - bank_transaction_importers
        - process_csv_upload

`process_csv_upload` ist das Legacy-Signal, siehe
[Bankimporter](plugins/bank-transaction-importers.md#legacy-api).
Bankimporter werden über `bank_transaction_importers` registriert (siehe
[Bankimporter](plugins/bank-transaction-importers.md)).

## Anzeige und Import

::: byro.office.signals
    options:
      members:
        - nav_event
        - member_view
        - member_dashboard_tile
        - member_list_importers

## Allgemein

!!! info "Nicht generiert"
    `byro.common` hat, anders als jede andere byro-App, keine `__init__.py`
    (siehe `src/byro/common/`). mkdocstrings/Griffe kann
    `byro.common.signals` deshalb nicht statisch erfassen; die Beschreibungen
    unten sind von Hand aus dem Quellcode übernommen. Das ist als
    Produktbefund gemeldet, nicht hier behoben (die Dokumentation ändert
    keinen Produktcode).

Modul `byro.common.signals`:

`unauthenticated_urls`
:   Wird gesendet, um zu ermitteln, ob eine URL ohne Anmeldung erreichbar sein
    soll. Plugins verbinden einen Receiver, um eigene Views öffentlich zu
    markieren; die MFA- und die Permission-Middleware nehmen passende URLs aus.

`log_formatters`
:   Wird gesendet, um Formatter für Audit-Log-Einträge zu sammeln, damit
    Plugins ihre eigenen Log-Aktionen im Office darstellen können.

`periodic_task`
:   Wird von `byroctl manage runperiodic` bzw. `python -m byro runperiodic`
    gesendet. Verbinde einen Receiver für wiederkehrende Aufgaben, zum
    Beispiel das eingebaute Auffrischen der PGP-Schlüssel und die
    Ablauferinnerungen.
