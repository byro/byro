# My account

Your user menu (your username in the top right of the Office) bundles three
actions for your **own** account - unlike "Settings → Users" in
[Configuration](../administration/overview.md), where superusers manage all
accounts (see
[Permission model](../administration/users-and-login.md#permission-model)).

## Editing your own profile

*User menu → My profile* opens the edit form for your own account
(username, name, e-mail address). Every account with access to the Office can
use it. The fields for staff and superuser status are only shown to
superusers, so a staff account cannot change its own permissions here. A
superuser can change their own staff status, but not remove their own
superuser status. The password field is optional: **leave it empty to keep
your current password**, for example if you only want to change your name or
e-mail address. If you enter a new password, it replaces the current one and
you have to sign in again. Details and background:
[Managing user accounts](../administration/users-and-login.md#managing-user-accounts).

## Multi-factor authentication

*User menu → Multi-factor authentication* sets up or manages TOTP for your
account. Its own page: [MFA](mfa.md).

## API token

*User menu → API token* shows your personal token for the
[REST API](../development/api.md). If your account has no token yet, opening
the page creates one. *Regenerate* deletes the old one and creates a new
one; the old token stops working immediately. The token only works while
your account is staff or superuser (see
[Permission model](../administration/users-and-login.md#permission-model));
without either flag the API rejects it.

Only you see and manage your token. A superuser can revoke it in the user
management, for example because it may have leaked (see
[Managing user accounts](../administration/users-and-login.md#managing-user-accounts)),
but can neither read it nor create one for you. A revoked token stops
working immediately. Your account, your password and your sign-in are not
affected, and you get a new token by opening this page again.

Creating, regenerating and revoking a token is recorded in the audit log,
never with the token itself.
