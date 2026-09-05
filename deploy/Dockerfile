# syntax=docker/dockerfile:1
# Production image for byro.
#
# Build context is the repository root (deploy/ and src/ are both needed):
#   docker build -f deploy/Dockerfile -t ghcr.io/byro/byro:<tag> .
#
# The development image used by src/docker-compose.yml lives in src/Dockerfile.
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/byro/byro" \
      org.opencontainers.image.authors="byro team"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=byro.settings \
    BYRO_DATA_DIR=/var/byro/data \
    BYRO_FILESYSTEM_STATIC=/byro/static.dist

# Tools the entrypoint relies on are installed explicitly instead of being
# assumed from the base image: bash (entrypoint), util-linux (setpriv),
# passwd (usermod/groupmod). gettext provides msgfmt for compilemessages,
# libmagic1 backs python-magic, gnupg/gpg-agent back the PGP mail features.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        util-linux \
        passwd \
        ca-certificates \
        gettext \
        libmagic1 \
        gnupg \
        gpg-agent \
    && rm -rf /var/lib/apt/lists/* \
    && command -v bash setpriv usermod groupmod >/dev/null

COPY src/ /byro/
WORKDIR /byro
RUN pip install --upgrade pip \
    && pip install -e . gunicorn

# Translations and static assets are built into the image. BYRO_DATA_DIR points
# at a throw-away directory for this step so that importing the settings does
# not bake a generated SECRET_KEY (.secret) into an image layer.
RUN BYRO_DATA_DIR=/tmp/byro-build python -m byro rebuild \
    && rm -rf /tmp/byro-build

# Dedicated unprivileged user. uid/gid 10001 stays clear of the first regular
# host user (1000) and of distribution system accounts (< 1000). /var/byro is
# made traversable (0755) because the data volume below it is also used by
# other uids (legacy account, BYRO_UID remapping); secrets inside are 0600.
#
# "uid1000" (uid/gid 1000) is a compatibility account for the legacy
# production/docker-compose.yml, which selects the user by that name and whose
# data directories on the host are owned by uid 1000. It is not used by the
# entrypoint; when an administrator remaps byro to uid/gid 1000 via
# BYRO_UID/BYRO_GID, the entrypoint removes this account first.
RUN groupadd --gid 10001 byro \
    && useradd --uid 10001 --gid byro --home-dir /var/byro --create-home \
        --shell /usr/sbin/nologin byro \
    && chmod 0755 /var/byro \
    && mkdir -p /var/byro/data \
    && groupadd --gid 1000 uid1000 \
    && useradd --uid 1000 --gid uid1000 --home-dir /home/uid1000 --create-home \
        --shell /usr/sbin/nologin uid1000

COPY deploy/entrypoint.sh /usr/local/bin/byro-entrypoint
COPY deploy/healthcheck.py /byro/healthcheck.py
RUN chmod 0755 /usr/local/bin/byro-entrypoint

EXPOSE 8345
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python3", "/byro/healthcheck.py"]

# Deliberately no USER instruction: the entrypoint starts as root only to fix
# ownership of the data volume and to apply BYRO_UID/BYRO_GID, then drops to
# the byro user with setpriv before running anything else.
ENTRYPOINT ["/usr/local/bin/byro-entrypoint"]
CMD ["web"]
