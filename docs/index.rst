byro
----

byro is a membership administration tool. byro is best suited to small and
medium sized clubs/NGOs/associations of all kinds, with a focus on the DACH
region.  byro is heavily plugin based to help fit it to different requirements
in different situations and countries.

We are planning to have a large amount of documentation, but at the moment we are still working on
it (and on byro itself), so it's incomplete and work-in-progress.

We're organizing our documentation in the following categories:

- **Developer documentation** for those helping develop byro features and plugins.
- **Administrator documentation** for those who deploy, update, and maintain byro instances.
- **[TODO] User documentation** which explains how to use a byro instance with your organization, what to
  expect, and which plugins to use.

.. toctree::
   :maxdepth: 2
   
   developer/index
   administrator/index


Features
========

As byro is under active development, this feature list can become outdated.
Please `open issues`_ for features you are missing!

- Member management: Add, and edit members and their data.
- Membership management: Add and change the membership fees a member should pay.
- Add custom member data: Track non-standard member data by adding a plugin to byro.
- Import payment data: Inbuilt support for CSV imports.
- Import and match payment data to members via custom methods, added by plugins.
- Send mails, and review mails before you send them out.
- Edit the default mail templates and add new ones.
- See member balances and transactions.
- Upload member specific documents (either for or by them); optionally send them per mail automatically.

Please note that byro is a tool for tracking member data and payments, and
the administrative acts around it. byro is not a bookkeeping tool (yet?).

.. _open issues: https://github.com/byro/byro/issues/new
