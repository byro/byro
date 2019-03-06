.. highlight:: python
   :linenothreshold: 5

Plugin: Custom member data
==========================

Most groups will need to save more data about their members than byro does by
default.

General
-------

You can save custom member data via a special model class, which **must**
reference ``byro.members.Member`` in a OneToOne relation, and the related name
**must** start with "profile".

Once you have generated this plugin (and have added the migrations, and run
them), byro will discover the profile on its own, generate the fitting forms
for members' profile pages, and offer you to include it when configuring your
registration form.

The Profile class
-----------------

If you want to track, for example, if a member has agreed to receive your newsletter,
you'd add a ``models.py`` file to your plugin, and put this inside::

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

Members will receive occasional emails with all data that is saved about them –
you can either return a list of strings, or a list of tuples (of keys and
values, such as ``("Has agreed to receive the newsletter", "True"))``. If you
do not implement this method, byro will display all relevant data from this
profile directly.


Custom views
------------

If you want to add an custom tab to a member's view related to your new
content, you'll have to write a simple view, add its url in your ``urls.py``,
and register it in your ``signals.py``::

   from django.dispatch import receiver
   from django.urls import reverse
   from django.utils.translation import ugettext_lazy as _

   from byro.office.signals import member_view


   @receiver(member_view)
   def newsletter_member_view(sender, signal, **kwargs):
       member = sender
       return {
           'label': _('Newsletter'),
           'url': reverse('plugins:byro_newsletter:members.newsletter', kwargs={'pk': member.pk}),
           'url_name': 'plugins:byro_newsletter',
       }

Every member will now have a tab with the label "Newsletter". You could also
add a general newsletter view to the sidebar::

   from django.dispatch import receiver
   from django.urls import reverse
   from django.utils.translation import ugettext_lazy as _

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


Configuring your plugin
-----------------------

If you'd like to provide custom configuration options (for example, the
name or latest issue of your newsletter), you can add a special configuration
related model. If the model class inherits from ``ByroConfiguration`` and ends
in ``Configuration``, it will be automatically added to the settings page::

   from django.db import models
   from django.utils.translation import ugettext_lazy as _

   from byro.common.models.configuration import ByroConfiguration


   class NewsletterConfiguration(ByroConfiguration):

       url = models.CharField(
           null=True, blank=True,
           max_length=300,
           verbose_name=_('Newsletter information URL'),
           help_text=_('e.g. https://foo.bar.de/news')
       )
