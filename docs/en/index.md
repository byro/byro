# byro documentation

![byro](img/logo/byro_128.png){ width="128" }

byro is a membership administration tool. byro is best suited to small and
medium sized clubs/NGOs/associations of all kinds, with a focus on the DACH
region. byro is heavily plugin based to help fit it to different requirements
in different situations and countries.

byro is stable and in active use in several communities. It is currently under
active development.

byro is not (yet) a complete bookkeeping tool and not an event or ticketing
tool; it also does not come with a hosted default instance you could use
without your own server – byro is either self-hosted (see
[Installation](installation/index.md)) or run for you by someone in your
organization or community.

## Where to start

**Your association already has a running byro** and you are meant to use it,
for example as a board member or treasurer: an administrator on your side has
set up your access; the [user guide](usage/index.md) describes day-to-day
work with members, fees, finances and communication. Ask your administration
about login, two-factor sign-in or permissions; technical background is in
[Configuration](administration/index.md).

**You are setting up byro for an organization**, as a technically minded
administrator: start at [Installation](installation/index.md), which covers
the three supported installation paths.
[Administration](administration/operations.md) covers day-to-day operation
afterwards (updating, backup, monitoring),
[Configuration](administration/index.md) what you set up *inside* byro (user
accounts, login, MFA, settings) plus the `byro.cfg`/`BYRO_*` reference, and
[Plugins](administration/plugins.md) shows what byro can be
extended with.

**You want to extend byro or contribute to it**: start at
[Development & API](development/index.md).

- [Installation](installation/index.md): run byro on your own server with
  byroctl, Docker Compose or bare metal.
- [Administration](administration/operations.md): day-to-day operation of an
  installation - updating, backup and restore, monitoring, security
  baseline.
- [Configuration](administration/index.md): user accounts and login, MFA, PGP
  and settings in a running instance, plus the configuration reference.
- [User guide](usage/index.md): day-to-day work with byro - members,
  memberships and fees, finances, documents, communication.
- [Plugins](administration/plugins.md): what byro can be
  extended with.
- [Development & API](development/index.md): develop byro or a plugin.

## Features

As byro is under active development, this feature list can become outdated.
Please [open issues](https://github.com/byro/byro/issues/new) for features you
are missing!

- **Member management:** Add, and edit members and their data.
- **Membership management:** Add and change the membership fees a member should
  pay.
- **Add custom member data:** Track non-standard member data by adding a plugin
  to byro. There are plenty of example plugins and developer documentation to
  help you.
- **Import and match payment data** to members: bank data comes in through a
  plugin (the core itself ships no importer); the official
  [`finance-import-bank-files`](administration/plugins.md) plugin supports
  CAMT.053. Matching to members runs through custom methods contributed by
  plugins.
- **Send mails:** All mails can be reviewed before they are sent out. You can
  also edit the default mail templates and add new ones.
- **See member balances**. You can also check every single transaction at any
  time.
- **Upload member specific documents:** (either for or by them); optionally
  send them per mail automatically.
- **Multi-factor authentication:** Backend users can protect their account with
  an authenticator app (TOTP); administrators can require this for everybody.
- **Let members interact:** Members can choose to make their data (which parts
  is their decision) visible to other members. Having a look at the member
  directory helps them interact directly with other members.

Please note that byro is a tool for tracking member data and payments, and the
administrative acts around it. byro does support bookkeeping and transactions,
but it is not a complete bookkeeping tool (yet).

## License

byro is licensed under the GNU Affero General Public License, version 3.0 only
(`AGPL-3.0-only`). Older versions of byro were released under the Apache
License 2.0.

This documentation is licensed under the
[Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/)
(`CC-BY-SA-4.0`). You may share and adapt it as long as you give appropriate
credit and distribute your adaptations under the same license.

See the [LICENSE](https://github.com/byro/byro/blob/main/LICENSE) file in the
byro repository for details, including the licensing history and the licenses
of bundled third-party components.
