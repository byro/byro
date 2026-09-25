# Multi-factor authentication

byro supports multi-factor authentication (MFA) for your Office account
based on time-based one-time passwords (TOTP,
[RFC 6238](https://www.rfc-editor.org/rfc/rfc6238)). Any common authenticator
app works, for example Aegis, Google Authenticator, Microsoft Authenticator,
1Password or Bitwarden.

MFA is **optional by default** - you can enable it for your own account,
independent of other accounts. Your administration can additionally require
it for every Office account; if that is the case, MFA can no longer be
disabled (see below).

MFA only concerns the interactive login to the Office backend. It does not
change anything about the public [member page](member-page.md) (no login or
second factor needed there) or an [API token](account.md#api-token) (which
works regardless of the account's MFA state).

## Setting up MFA

1. Open the user menu (your username in the top right corner) and choose
   *Multi-factor authentication* (also reachable from the *Multi-factor
   authentication* button on your own profile page).
2. Click *Set up MFA*.
3. Scan the QR code with your authenticator app. If you cannot scan it, enter
   the key shown below the QR code manually (type: time-based / TOTP, 6
   digits, 30 seconds, SHA-1).
4. Enter the six-digit code your app shows and click *Verify and enable*. MFA
   is only activated once a code has been verified successfully – simply
   opening the setup page does not change anything.
5. byro now shows **ten recovery codes**. Store them in a safe place (for
   example a password manager). They are shown only once.

From now on, every login asks for a code from your authenticator app after
the password. There is no way to skip this step for an account with MFA
enabled.

## Signing in

Enter username and password as before. On the next page, enter the current
six-digit code from your authenticator app. Codes are valid for a short time
only and every code can be used only once.

## Using a recovery code

If you do not have access to your authenticator app, click *Use a recovery
code* on the code page and enter one of your recovery codes
(`XXXX-XXXX-XXXX`, dashes and case do not matter). Every recovery code works
exactly once. After signing in, byro tells you how many codes are left;
generate new codes if you are running low.

## Generating new recovery codes

*User menu → Multi-factor authentication → Generate new recovery codes*. You
have to confirm with a current code from your authenticator app. All previous
recovery codes stop working immediately.

## Disabling MFA

*User menu → Multi-factor authentication → Disable MFA*, confirmed with a
current authenticator code. This removes the authenticator and all recovery
codes; afterwards the account is protected by the password only.

If MFA is required for all administrators, this option is not available.

## Lost authenticator and no recovery codes left

Ask an administrator with shell access to the byro server to reset your MFA
(see
[Resetting the MFA of a user](../administration/mfa.md#resetting-the-mfa-of-a-user-break-glass-recovery)).
It is not possible to reset another user's MFA from the web interface.

## For administrators

Requiring the policy for all accounts, checking a user's MFA status,
resetting a lost device, and the security background are on the
administration page:
[Multi-factor authentication](../administration/mfa.md).
