.. highlight:: python
   :linenothreshold: 5

Signal list
===========

This page lists the signals and hooks that are available in byro.
The following guides will give examples on how to use these signals.

Member management
-----------------

.. automodule:: byro.members.signals
   :members: new_member, new_member_mail_information, new_member_office_mail_information, leave_member, leave_member_mail_information, leave_member_office_mail_information, update_member


Payment
-------

.. automodule:: byro.bookkeeping.signals
   :members: process_transaction, process_csv_upload


Display
-------

.. automodule:: byro.office.signals
   :members: nav_event, member_view, member_dashboard_tile

.. automodule:: byro.common.signals
   :members: unauthenticated_urls, log_formatters


Import
------

.. automodule:: byro.office.signals
   :members: member_list_importers


General
-------

.. automodule:: byro.common.signals
   :members: periodic_task
