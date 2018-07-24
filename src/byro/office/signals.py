import django.dispatch

member_view = django.dispatch.Signal()
"""
This signal allows you to add a tab to the member detail view tab list.
Receives the member as sender, and additionally the request
Must return a dict:

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
