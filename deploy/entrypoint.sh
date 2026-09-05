#!/usr/bin/env bash
# byro container entrypoint.
#
# The container starts as root, but root is used for exactly three things:
#   1. validate and apply BYRO_UID / BYRO_GID (remap the "byro" user, fail-closed),
#   2. make sure the data volume is owned by that user (fixed only when it differs),
#   3. drop privileges with setpriv and re-execute this script as "byro".
# Everything else – configuration check, migrations, gunicorn, periodic tasks
# and management commands – runs unprivileged.
#
# Usage: byro-entrypoint web | periodic | manage <django command> [args...]
set -euo pipefail

BYRO_USER=byro
BYRO_HOME=/var/byro
BYRO_DATA="${BYRO_DATA_DIR:-/var/byro/data}"
# Compatibility account (uid/gid 1000) for the legacy production/docker-compose.yml;
# see deploy/Dockerfile. Never used when this entrypoint runs.
LEGACY_USER=uid1000

log() { printf 'byro-entrypoint: %s\n' "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

usage() {
    cat >&2 <<USAGE
Usage: byro-entrypoint <command>

  web                  wait for the database, run migrations (unless
                       BYRO_AUTO_MIGRATE=false) and start gunicorn on :8345
  periodic             run "runperiodic" every BYRO_DEPLOY_PERIODIC_INTERVAL
                       seconds (default 600)
  manage <cmd> [...]   run a byro/Django management command, e.g. "manage migrate"
USAGE
    exit 64
}

# --- root phase ---------------------------------------------------------------

validate_id() {
    local name="$1" value="$2"
    [[ "$value" =~ ^[0-9]+$ ]] || die "$name must be a positive integer, got '$value'"
    [[ "$value" -ne 0 ]] || die "$name must not be 0 (root)"
}

# The legacy account only exists for the old compose files, which never run this
# entrypoint. Free its ids when an administrator wants them for byro.
release_legacy_account() {
    if getent passwd "$LEGACY_USER" >/dev/null; then
        userdel "$LEGACY_USER" 2>/dev/null || die "could not remove legacy account $LEGACY_USER"
    fi
    if getent group "$LEGACY_USER" >/dev/null; then
        groupdel "$LEGACY_USER" || die "could not remove legacy group $LEGACY_USER"
    fi
    log "removed compatibility account $LEGACY_USER to free its ids"
}

# Fail closed: only numeric, non-zero ids that are not yet taken by another
# user/group are applied, and never with usermod/groupmod -o (no duplicate ids).
# The only exception is the legacy compatibility account, which is removed.
remap_ids() {
    local current_uid current_gid owner
    current_uid="$(id -u "$BYRO_USER")"
    current_gid="$(id -g "$BYRO_USER")"

    if [[ -n "${BYRO_GID:-}" ]]; then
        validate_id BYRO_GID "$BYRO_GID"
        if [[ "$BYRO_GID" != "$current_gid" ]]; then
            owner="$(getent group "$BYRO_GID" | cut -d: -f1 || true)"
            if [[ "$owner" == "$LEGACY_USER" ]]; then
                release_legacy_account
                owner=""
            fi
            [[ -z "$owner" ]] || die "BYRO_GID=$BYRO_GID is already used by group '$owner'"
            groupmod --gid "$BYRO_GID" "$BYRO_USER"
            log "group $BYRO_USER remapped to gid $BYRO_GID"
        fi
    fi
    if [[ -n "${BYRO_UID:-}" ]]; then
        validate_id BYRO_UID "$BYRO_UID"
        if [[ "$BYRO_UID" != "$current_uid" ]]; then
            owner="$(getent passwd "$BYRO_UID" | cut -d: -f1 || true)"
            if [[ "$owner" == "$LEGACY_USER" ]]; then
                release_legacy_account
                owner=""
            fi
            [[ -z "$owner" ]] || die "BYRO_UID=$BYRO_UID is already used by user '$owner'"
            usermod --uid "$BYRO_UID" "$BYRO_USER"
            log "user $BYRO_USER remapped to uid $BYRO_UID"
        fi
    fi
}

# Ownership (uid and gid) of the home and the data directory must match the
# byro user. Only fixed when it differs, so a normal start never chowns
# recursively.
fix_ownership() {
    local uid gid
    uid="$(id -u "$BYRO_USER")"
    gid="$(id -g "$BYRO_USER")"
    mkdir -p "$BYRO_DATA"
    if [[ "$(stat -c '%u:%g' "$BYRO_HOME")" != "$uid:$gid" ]]; then
        chown "$uid:$gid" "$BYRO_HOME"
    fi
    if [[ "$(stat -c '%u:%g' "$BYRO_DATA")" != "$uid:$gid" ]]; then
        log "fixing ownership of $BYRO_DATA (uid:gid $uid:$gid)"
        chown -R "$uid:$gid" "$BYRO_DATA"
    fi
}

if [[ "$(id -u)" -eq 0 ]]; then
    remap_ids
    fix_ownership
    # Re-execute as byro with a proper user environment (not root's HOME).
    # No --reset-env: the BYRO_* configuration must survive the switch.
    exec setpriv --reuid="$BYRO_USER" --regid="$BYRO_USER" --init-groups --no-new-privs \
        -- env HOME="$BYRO_HOME" USER="$BYRO_USER" LOGNAME="$BYRO_USER" "$0" "$@"
fi

# --- unprivileged phase -------------------------------------------------------

[[ "$(id -u)" -ne 0 ]] || die "still running as root after the privilege drop"

cmd="${1:-}"
[[ -n "$cmd" ]] || usage

wait_for_db() {
    log "waiting for the database..."
    python - <<'PY'
import os
import sys
import time

import django

django.setup()
from django.db import connection  # noqa: E402

deadline = time.monotonic() + float(os.environ.get("BYRO_DB_WAIT_SECONDS", "120"))
while True:
    try:
        connection.ensure_connection()
        break
    except Exception as exc:
        if time.monotonic() > deadline:
            print(f"database not reachable: {exc}", file=sys.stderr)
            sys.exit(1)
        time.sleep(2)
PY
}

# Validates the configuration and creates the SECRET_KEY file exactly once, in a
# single process, before gunicorn forks its workers. Output goes to stderr so
# that stdout of management commands (e.g. dumpdata) stays clean.
python -m byro check >&2

case "$cmd" in
    web)
        wait_for_db
        if [[ "${BYRO_AUTO_MIGRATE:-true}" != "false" ]]; then
            python -m byro migrate --noinput
        fi
        exec gunicorn byro.wsgi --name byro \
            --workers "${BYRO_DEPLOY_WEB_WORKERS:-4}" \
            --max-requests 1200 --max-requests-jitter 50 \
            --log-level=info --bind=0.0.0.0:8345
        ;;
    periodic)
        wait_for_db
        interval="${BYRO_DEPLOY_PERIODIC_INTERVAL:-600}"
        [[ "$interval" =~ ^[0-9]+$ ]] || die "BYRO_DEPLOY_PERIODIC_INTERVAL must be a number of seconds"
        trap 'log "periodic: stopping"; exit 0' TERM INT
        log "periodic: running runperiodic every ${interval}s"
        while true; do
            python -m byro runperiodic || log "periodic: runperiodic failed (exit $?)"
            sleep "$interval" &
            wait $!
        done
        ;;
    manage)
        shift
        exec python -m byro "$@"
        ;;
    *)
        usage
        ;;
esac
