# syntax=docker/dockerfile:1
# Derived byro image with the plugins from plugins.txt.
# Managed by byroctl - do not edit; byroctl replaces it on update.
#
# Build context: the plugins/ directory of the installation (this file,
# plugins.txt, optional local plugin checkouts referenced by relative path).
#   docker compose build web      (what byroctl plugin add|remove|update|rebuild run)
#   docker build --build-arg BYRO_BASE_IMAGE=ghcr.io/byro/byro:vYYYY.M.P@sha256:... plugins/
#
# Stage 1 builds one wheel per line of plugins.txt (git is needed for git+https
# specs); stage 2 installs the wheels into an untouched copy of the base image,
# so git and build tooling never reach the final image. No default for
# BYRO_BASE_IMAGE on purpose: an unset build argument fails the build instead
# of silently deriving from an unpinned image.
ARG BYRO_BASE_IMAGE
FROM ${BYRO_BASE_IMAGE} AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY . /build
# Only the plugins themselves; their dependencies are resolved in stage 2
# against the base image. Isolated builds: setuptools is fetched per build (the
# base image ships none) and Django is not importable while building, so plugin
# .po files ship uncompiled; the rebuild in stage 2 compiles them.
RUN pip wheel --no-deps --requirement plugins.txt --wheel-dir /wheels

FROM ${BYRO_BASE_IMAGE}
ARG BYRO_BASE_IMAGE
LABEL org.byro.base-image="${BYRO_BASE_IMAGE}"

COPY --from=builder /wheels /wheels
# The list this image was built from; byroctl reads it as the applied state.
COPY plugins.txt /byro/plugins.txt
# The package set of the base image is the constraint: a plugin may add
# packages, but it can never upgrade, downgrade or replace Django, byro or
# their dependencies; pip fails instead. pip list (not pip freeze) includes the
# editable byro as byro==X, so a plugin's "byro>=..." requirement is checked
# against the installed release. An empty plugins.txt leaves /wheels empty and
# the build still succeeds.
RUN pip list --format=freeze --disable-pip-version-check >/tmp/base-constraints.txt \
    && set -- /wheels/*.whl \
    && if [ -e "$1" ]; then pip install --constraint /tmp/base-constraints.txt "$@"; fi \
    && rm -rf /wheels /tmp/base-constraints.txt

# Plugin translations (byro's plugin-aware rebuild), static files and the
# offline compressor cache. A throw-away BYRO_DATA_DIR keeps the generated
# SECRET_KEY out of the image, exactly as in the base image.
RUN BYRO_DATA_DIR=/tmp/byro-build python -m byro rebuild \
    && rm -rf /tmp/byro-build
