# Plugin: Eigene Mitgliedsdaten

Die meisten Gruppen müssen mehr über ihre Mitglieder speichern, als byro von
Haus aus vorsieht.

## Allgemein

Eigene Mitgliedsdaten speicherst du über eine spezielle Modellklasse, die
`byro.members.Member` in einer OneToOne-Beziehung referenzieren **muss**, und
deren related name mit „profile“ beginnen **muss**.

Hast du dieses Plugin erzeugt (und die Migrationen hinzugefügt und ausgeführt),
erkennt byro das Profil von selbst, erzeugt die passenden Formulare für die
Profilseiten der Mitglieder und bietet dir an, es in das Registrierungsformular
aufzunehmen. Profilfelder, die die Datenbank verlangt (`NOT NULL` ohne
Default), sind immer Teil des Registrierungsformulars und lassen sich nicht
daraus entfernen; bevorzuge deshalb nullable Felder oder Felder mit Default.

## Die Profile-Klasse

Willst du zum Beispiel festhalten, ob ein Mitglied deinen Newsletter erhalten
möchte, lege in deinem Plugin eine `models.py` mit folgendem Inhalt an:

```python
from annoying.fields import AutoOneToOneField
from django.db import models

class NewsletterProfile(models.Model):
    member = AutoOneToOneField(
        to='members.Member',
        on_delete=models.CASCADE,
        related_name='profile_shack',
    )
    receives_newsletter = models.BooleanField(default=True)

    def get_member_data(self):
         return [
            "You have opted in to receive our newsletter." if self.receives_newsletter else "",
         ]
```

Mitglieder erhalten gelegentlich Mails mit allen über sie gespeicherten Daten –
du kannst entweder eine Liste von Strings oder eine Liste von Tupeln (Schlüssel
und Wert, etwa `("Has agreed to receive the newsletter", "True"))`)
zurückgeben. Implementierst du diese Methode nicht, zeigt byro alle relevanten
Daten dieses Profils direkt an.

## Eigene Views

Willst du der Mitgliedsansicht einen eigenen Reiter zu deinen Inhalten
hinzufügen, schreibe eine einfache View, trage ihre URL in deine `urls.py` ein
und registriere sie in deiner `signals.py`:

```python
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from byro.office.signals import member_view


@receiver(member_view)
def newsletter_member_view(sender, signal, **kwargs):
    member = sender
    return {
        'label': _('Newsletter'),
        'url': reverse('plugins:byro_newsletter:members.newsletter', kwargs={'pk': member.pk}),
        'url_name': 'plugins:byro_newsletter',
    }
```

Jedes Mitglied hat jetzt einen Reiter „Newsletter“. Du könntest auch eine
allgemeine Newsletter-Ansicht in die Seitenleiste hängen:

```python
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from byro.office.signals import nav_event

@receiver(nav_event)
def newsletter_sidebar(sender, **kwargs):
    request = sender
    return {
        'icon': 'envelope-o',
        'label': _('Newsletter'),
        'url': reverse('plugins:byro_newsletter:dashboard'),
        'active': 'byro_newsletter' in request.resolver_match.namespace and 'member' not in request.resolver_match.url_name,
    }
```

## Dein Plugin konfigurieren

Willst du eigene Konfigurationsoptionen anbieten (zum Beispiel Name oder
aktuelle Ausgabe deines Newsletters), lege ein spezielles Konfigurationsmodell
an. Erbt die Modellklasse von `ByroConfiguration` und endet ihr Name auf
`Configuration`, wird sie automatisch zur Einstellungsseite hinzugefügt:

```python
from django.db import models
from django.utils.translation import gettext_lazy as _

from byro.common.models.configuration import ByroConfiguration


class NewsletterConfiguration(ByroConfiguration):

    url = models.CharField(
        null=True, blank=True,
        max_length=300,
        verbose_name=_('Newsletter information URL'),
        help_text=_('e.g. https://foo.bar.de/news')
    )
```
