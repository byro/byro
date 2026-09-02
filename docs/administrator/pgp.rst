PGP email encryption
====================

byro can sign outgoing email and encrypt member email using OpenPGP. The
feature is part of byro core, but it uses the GnuPG command line tools as its
crypto backend. This means that a working installation needs the GnuPG system
packages.

Docker installations
--------------------

The official byro Docker image includes the required GnuPG runtime packages.
The default Docker configuration stores the GnuPG home directory in
``/var/byro/data/gnupg`` so keys persist in the normal byro data volume.

After updating the image, run migrations and then configure PGP in the office
settings.

Manual installations
--------------------

Install the system packages required by GnuPG. On Debian or Ubuntu::

    # apt-get install gnupg gpg-agent

Then install byro in the same Python environment that runs byro::

    $ pip install --user -U byro

If you install from git::

    $ pip install --user -U "git+https://github.com/byro/byro.git@main#egg=byro&subdirectory=src"

Configuration file
------------------

The runtime backend is configured in the ``[pgp]`` section of ``byro.cfg``::

    [pgp]
    backend = byro.mails.gnupg_backend.GnuPGBackend
    home = /var/byro/data/gnupg

``backend``
    Python import path of the PGP backend. The default backend wraps the
    ``gpg`` command line tool.

``home``
    GnuPG home directory used by the byro process. This directory should be
    readable and writable only by the user running byro. If the value is empty,
    GnuPG uses its default home directory for that user.

The same values can be provided through environment variables:

* ``BYRO_PGP_BACKEND``
* ``BYRO_PGP_HOME``

Office settings
---------------

The byro office settings contain the operational PGP policy:

* **PGP signing** contains the organization's private signing key and the
  option to sign outgoing email.
* **PGP encryption** contains member-email encryption, the keyserver URLs, and
  the policy for missing, invalid, unverified, or expired member keys.
* **Advanced key management** contains automatic refresh, timeouts, and
  expiry reminders for member keys.

Organization signing key
------------------------

In the PGP settings card, upload the organization's ASCII-armored private
signing key without a passphrase. byro validates that it contains exactly one
signing-capable key, verifies that it can sign without a passphrase, imports it
into the configured GnuPG home directory, and fills in its fingerprint
automatically. The private key material is not stored in the byro database or
audit log; it remains only in the GnuPG keyring.

For an imported key, the settings show its fingerprint, user IDs, creation and
expiry dates, algorithm, and whether it has signing capability. These details
are read from the GnuPG keyring; no private key material is displayed.

Alternatively, import or generate the key in the GnuPG home directory used by
byro through deployment tooling. The office settings display the configured
fingerprint read-only; upload a private key to replace it.

Example as the byro user::

    $ GNUPGHOME=/var/byro/data/gnupg gpg --list-secret-keys --fingerprint

The uploaded signing key must not be password-protected. byro does not store
key passphrases. Protect the GnuPG home directory so that only the byro process
can access the imported private key.

Member keys
-----------

Each member can have one or more PGP public keys. In the member detail view,
the PGP tab allows office users to:

* import a public key from a keyserver by fingerprint
* upload an ASCII-armored public key manually
* deactivate a key
* delete a key

Keys imported from keyservers by fingerprint are marked as valid automatically,
because byro only imports the exact fingerprint provided by the member or
accepted by the office. Manually uploaded public keys are accepted only if the
uploaded key material matches the entered fingerprint; otherwise byro rejects
the upload with a form error.

When PGP encryption is enabled, byro delivers separate messages to recipients
in the ``To``, ``Cc``, and ``Bcc`` fields. Each member recipient is therefore
encrypted using their own key and evaluated against the configured key policy.
The visible ``To`` and ``Cc`` headers are retained, while ``Bcc`` recipients
remain hidden.

Member application fingerprints
-------------------------------

The registration form settings include a ``PGP fingerprint`` field. If this
field is enabled, office users can enter the fingerprint from a membership
application while creating the member. byro stores the fingerprint and
immediately tries to import the matching public key from the configured
keyservers.

If the key cannot be imported at that moment, the member is still created and
the PGP key stays pending or not found. Automatic refresh will try again later
if enabled.

Keyserver imports
-----------------

byro only imports keys by full fingerprint. It does not encrypt to keys found
only by email address. This avoids accidentally using an unrelated key with a
matching user ID.

The PGP office settings accept one keyserver per line. byro tries them in
order until one returns the requested key. You can enter plain hostnames;
byro will use ``hkps://`` for them. If you enter ``https://`` or ``http://``,
byro converts those schemes to GnuPG's ``hkps://`` or ``hkp://`` keyserver
schemes. Explicitly specified schemes are limited to ``hkp://``, ``hkps://``,
``http://``, and ``https://``. The default list is:

* ``keys.openpgp.org``
* ``keyserver.ubuntu.com``
* ``pgp.mit.edu``

Automatic refresh
-----------------

If automatic refresh is enabled, byro refreshes keyserver-managed keys from the
periodic task. The refresh interval and keyserver timeout are configured in the
PGP office settings. Make sure the periodic task is run regularly in your
deployment. Expired keys can trigger reminder emails to members before the
expiry date. These reminders are created as drafts in the byro outbox so office
users can review and send them through the normal mail workflow.

Dashboard warnings
------------------

The office dashboard shows PGP warnings for incomplete signing configuration,
active member keys that are invalid, revoked, or expired, soon-expiring keys,
and keyserver import or refresh errors.
