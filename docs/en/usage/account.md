# My account

Your user menu (your username in the top right of the Office) bundles three
actions for your **own** account - unlike "Settings → Users" in
[Configuration](../administration/overview.md), where superusers manage all
accounts (see
[Permission model](../administration/users-and-login.md#permission-model)).

## Editing your own profile

*User menu → My profile* opens the edit form for your own account
(username, name, e-mail address). Every account with access to the Office can
use it. You cannot change your own permissions here: the fields for staff and
superuser status are only shown to superusers, and even a superuser cannot
remove their own superuser status. The same restriction applies as in user
management: **every save requires a new password**, even if you only want to
change your name or e-mail address. Details and background:
[Managing user accounts](../administration/users-and-login.md#managing-user-accounts).

## Multi-factor authentication

*User menu → Multi-factor authentication* sets up or manages TOTP for your
account. Its own page: [MFA](mfa.md).

## API token

*User menu → API token* shows your personal token for the
[REST API](../development/api.md); *Regenerate* deletes the old one and
creates a new one. The token only works while your account is staff or
superuser (see
[Permission model](../administration/users-and-login.md#permission-model));
without either flag the API rejects it.
