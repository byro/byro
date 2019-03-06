import django.dispatch

member_view = django.dispatch.Signal()
"""
This signal allows you to add a tab to the member detail view tab list.
Receives the member as sender, and additionally the request
Must return a dict::

    {
        "label": _("Fancy Member View"),
        "url": "/member/123/foo/",
        "url_name": "plugins:myplugin:foo_view",
    }

Please use byro.office.views.members.MemberView as base class for these views.
"""

nav_event = django.dispatch.Signal()
"""
This signal allows you to add additional views to the sidebar.
Receives the request as sender. Must return a dictionary containing at least
the keys ``label`` and ``url``. You can also return a ForkAwesome icon name
iwth the key ``icon``. You should also return an ``active`` key with a boolean
set to ``True`` if this item should be marked as active.

If you want your Plugin to appear in the "Finance" or "Settings" submenu in the
side bar, please set ``section`` in your return dict to either ``finance`` or
``settings``, and don't set an ``icon``.

May return an iterable of multiple dictionaries as described above.
"""

member_list_importers = django.dispatch.Signal()
"""
This signal allows you to add additional member list importers.
Receives None as argument, must return a dict::

    {
        "id": "dot.scoped.importer.id",
        "label": _("My super importer"),
        "form_valid": form_valid_callback,
    }

where `form_valid_callback` should accept two arguments: view (the View object
handling the request), and form (the form object that was submitted, the file
to import is in the `upload_file` form field) and should return a Response
object.
"""
member_dashboard_tile = django.dispatch.Signal()
"""
This signal allows you to add tiles to the member's dashboard.
Receives None as argument, must return either None or a dict::

    {
        "title": _("Dash!"),
        "lines": [_('Line 1'), _('Line 2')]
        "url": "/member/123/foo/",
        "public": False,  # False is the default
    }

All of the parts of this dict are optional. You cannot include HTML in the
response, all strings will be escaped at render time. If "public" is set to
True, the dasboard tile will also be shown on the member's personal page.
"""
