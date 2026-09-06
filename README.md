# byro stable pointer

This branch is written by CI and points at the current stable byro release.
It is not a source branch. It only carries

* `install.sh`, the bootstrap script: a byte-identical copy of `deploy/install.sh`
  from the release tag named in `stable.env`, and
* `stable.env`, one line `BYRO_RELEASE_VERSION=vYYYY.M.P`.

Everything else (byroctl, the Compose files, the container image) comes from the
immutable release tag. Install byro with

    bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)"

Documentation: https://byro.readthedocs.io/en/latest/administrator/installation-byroctl.html

Do not edit this branch or push to it by hand. The pointer moves automatically
after every release; to move it deliberately, run the "Stable pointer" workflow
(see docs/developer/releasing.rst in the main branch).
