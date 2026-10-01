# Signalliste

Diese Seite listet die Signale und Hooks, die byro anbietet. Die
[Plugin-Anleitungen](plugins/overview.md) zeigen Beispiele für ihre Verwendung.

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

### Einträge unter Einstellungen sind nur für Superuser

Das Untermenü „Einstellungen“ der Seitenleiste wird nur Superusern angezeigt
(siehe
[Berechtigungsmodell](../administration/users-and-login.md#berechtigungsmodell)).
Ein `nav_event`-Eintrag mit `section` gleich `settings` kennzeichnet deshalb
eine **administrative Funktion, die nur für Superuser vorgesehen ist**.

Das Ausblenden des Navigationseintrags ist kein Zugriffsschutz. byro kann
nicht erkennen, welche Views zu einem Navigationseintrag gehören, und versucht
nicht, Plugin-URLs von sich aus zu sperren. Ein Plugin muss jede View hinter
einem solchen Eintrag selbst serverseitig schützen:

```python
from django.views.generic import FormView

from byro.common.permissions import SuperuserRequiredMixin, superuser_required


class NewsletterSettingsView(SuperuserRequiredMixin, FormView):
    ...


@superuser_required
def newsletter_settings_export(request):
    ...
```

Beide Prüfungen sind eigenständig: Sie verlangen einen angemeldeten, aktiven
Superuser und hängen nicht von byros Middleware ab. Nicht angemeldete Besucher
werden zur Login-Seite umgeleitet, jedes andere Konto erhält byros Seite
„Zugriff verweigert“ (HTTP 403). In Templates entscheidest du mit
`request.user.is_superuser`, ob ein Link auf eine solche Seite angezeigt wird.
`byro.common.permissions.has_backend_access(user)` ist die zentrale Definition
dafür, wer das Office überhaupt nutzen darf (Staff oder Superuser).

Konfigurationsmodelle, die von `ByroConfiguration` erben, brauchen keine
zusätzliche Arbeit: Sie sind Teil der allgemeinen Einstellungsseite, die
bereits Superusern vorbehalten ist. Einträge mit `section` gleich `finance`
oder ohne Sektion bleiben für jedes Konto mit Zugriff auf das Office sichtbar.

!!! warning "Migrationshinweis für bestehende Plugins"
    Vor Einführung des Berechtigungsmodells konnte jedes Konto jede Seite
    öffnen, bestehende Plugins enthalten deshalb in der Regel keine solche
    Prüfung. Ihre Einträge unter „Einstellungen“ sind für Staff jetzt
    ausgeblendet, die Seiten dahinter **bleiben für Staff aber über ihre
    direkte Adresse erreichbar**, bis das Plugin sie wie oben gezeigt schützt.
    Das ist eine Kompatibilitätsgrenze bestehender Drittanbieter-Plugins,
    nicht das gewünschte Berechtigungsverhalten.

    Wenn du ein Plugin mit Einträgen in der Sektion „Einstellungen“ pflegst:
    Ergänze das Mixin oder den Decorator an jeder View hinter diesen
    Einträgen, auch an Views, die nur Formulare entgegennehmen oder Exporte
    liefern. `byro.common.permissions` gibt es ab dem byro-Release, das das
    Berechtigungsmodell einführt; ein Plugin, das auch auf älteren Releases
    laufen muss, kann `request.user.is_superuser` selbst prüfen und
    `django.core.exceptions.PermissionDenied` auslösen.

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
