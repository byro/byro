# Plugins

byro can be extended with plugins: Python packages that register themselves
with byro and add importers, member data, documents or whole features. How
plugins are written is covered in [Plugin development](../development/plugins/overview.md).

A plugin runs with the same privileges as byro itself and has full access to
your database. Install only plugins you trust.

## Official plugins

**Bundled** (every byro installation, not individually installable or
removable): `byro.plugins.profile` (additional personal member data such as
nickname, birth date, phone number) and `byro.plugins.sepa` (SEPA direct debit
data per member).

**Catalog** (individually installable through
[plugin management](plugin-management.md)):

| Plugin | Description | Repository |
|---|---|---|
| `finance-import-bank-files` | File-based bank import (CAMT.053 and MT940) | [byro/byro-finance-import-bank-files](https://github.com/byro/byro-finance-import-bank-files) |

This is the complete catalog as of this page - not a made-up example, but
`deploy/plugin-catalog.conf` of this release. Further plugins are listed under
the GitHub topic [byro-plugin](https://github.com/topics/byro-plugin). Two more
plugins maintained by the byro organization exist, but are not compatible with
the current byro version and therefore not in the catalog:
[byro-mailman](https://github.com/byro/byro-mailman) and
[byro-gemeinnuetzigkeit](https://github.com/byro/byro-gemeinnuetzigkeit).
The topic is a place to look, not a recommendation; byroctl never installs
anything from there automatically.

How a plugin gets added to the catalog is described in
[Plugin catalog](../development/releasing.md#plugin-catalog).

## Plugin management

Installing, updating and removing plugins, as well as troubleshooting, is
covered in [plugin management](plugin-management.md).

For the individual installation methods, see [byroctl](../installation/byroctl.md),
[Docker Compose](../installation/docker-compose.md) and
[bare metal](../installation/bare-metal.md).

Integrations that are not plugins (SMTP mail delivery, OIDC/SSO) live under
[Configuration](../configuration/reference.md) and
[Users and login](users-and-login.md) respectively.
