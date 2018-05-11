.. highlight:: python
   :linenothreshold: 5

Signal list
===========

This page lists the signals and hooks that are available in byro.
The following guides will give examples on how to use these signals.

Member management
-----------------

.. automodule:: byro.members.signals
   :members: new_member, new_member_mail_information, new_member_office_mail_information, leave_member, leave_member_mail_information, leave_member_office_mail_information


Payment
-------

.. automodule:: byro.bookkeeping.signals
   :members: derive_virtual_transactions, process_csv_upload


Display
-------

.. automodule:: byro.office.signals
   :members: nav_event, member_view

General
-------

.. automodule:: byro.common.signals
   :members: periodic_task
