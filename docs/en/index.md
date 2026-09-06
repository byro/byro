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
set up your access; [Usage](usage/index.md) describes day-to-day work with
members, fees and finances (this section is being written). Ask your
administration about login, two-factor sign-in or permissions; technical
background is in [Administration](administration/index.md).

**You are setting up byro for an organization**, as a technically minded
administrator: start at [Installation](installation/index.md), which explains
the three supported paths (byroctl, Docker Compose, bare metal) and how to
choose between them. [Configuration](configuration/index.md) is the reference
of all settings, [Administration](administration/index.md) covers updating,
backup, plugins and day-to-day operation.

**You want to extend byro or contribute to it**: start at
[Development & API](development/index.md).

- [Installation](installation/index.md): run byro on your own server with
  byroctl, Docker Compose or bare metal.
- [Administration](administration/index.md): MFA, PGP, plugins, updating,
  backup and restore, and monitoring and troubleshooting a running instance.
- [Configuration](configuration/index.md): reference of all configuration
  options.
- [Usage](usage/index.md): day-to-day work with byro (being written).
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
