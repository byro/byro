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

Then install byro with the PGP extra in the same Python environment that runs
byro::

    $ pip install --user -U "byro[pgp]"

If you install from git, keep the ``[pgp]`` extra on the package specifier::

    $ pip install --user -U "git+https://github.com/byro/byro.git@main#egg=byro[pgp]&subdirectory=src"

Configuration file
------------------

The runtime backend is configured in the ``[pgp]`` section of ``byro.cfg``::

    [pgp]
    backend = byro.mails.gpgme_backend.GnuPGPGPBackend
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

* enable or disable encryption for member email
* enable or disable signing of outgoing email
* configure the organization's signing key fingerprint
* configure keyserver URLs
* configure the keyserver timeout and automatic refresh interval
* decide whether missing, invalid, unverified, or expired keys block member
  email or fall back to plain mail
* enable or disable automatic key refresh
* enable or disable reminders before member keys expire

Organization signing key
------------------------

Import or generate the organization's private signing key in the GnuPG home
directory used by byro. The private key material is not stored in the byro
database. byro stores only the configured signing key fingerprint.

Example as the byro user::

    $ GNUPGHOME=/var/byro/data/gnupg gpg --list-secret-keys --fingerprint

Copy the full fingerprint into the PGP settings in the office area.

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
schemes. The default list is:

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
