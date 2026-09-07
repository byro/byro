# My account

Your user menu (your username in the top right of the Office) bundles three
actions for your **own** account - unlike "Settings → Users" in
[Configuration](../administration/index.md), where accounts are managed
(including other people's, as long as you are signed in, see the security
notes there).

## Editing your own profile

*User menu → My profile* opens the same edit form used to manage other
accounts (username, name, e-mail address, `is_staff`/`is_superuser`). The
same restriction applies as there: **every save requires a new password**,
even if you only want to change your name or e-mail address. Details and
background:
[Managing user accounts](../administration/users-and-login.md#managing-user-accounts).

## Multi-factor authentication

*User menu → Multi-factor authentication* sets up or manages TOTP for your
account. Its own page: [MFA](mfa.md).

## API token

*User menu → API token* shows your personal token for the
[REST API](../development/api.md); *Regenerate* deletes the old one and
creates a new one. The token only works while your account is `is_staff`
(see
[Managing user accounts](../administration/users-and-login.md#managing-user-accounts));
without `is_staff` it can still be displayed, but the API rejects it.
