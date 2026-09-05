#!/usr/bin/env bash
# Integration test for byroctl against a locally built byro image and real
# Docker: install, config, start/stop/restart, manage, logs, idempotent re-run.
#
# Usage: byroctl-integration.sh <image repo> <image tag> <root dir> [host port]
#   e.g. byroctl-integration.sh byro-ci smoke "$RUNNER_TEMP/byro-it" 18345
#
# Requires bash >= 4, docker with compose, curl on the machine that runs the
# script; the root directory must be usable as a bind mount source by the
# Docker daemon (same path on host and daemon).
set -euo pipefail

repo="${1:?image repo}"
tag="${2:?image tag}"
root="${3:?root dir}"
port="${4:-18345}"
# host to reach the published port (inside a helper container: host.docker.internal)
http_host="${BYROCTL_IT_HTTP_HOST:-127.0.0.1}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
byroctl="$here/deploy/byroctl"

export BYROCTL_SOURCE_DIR="$here/deploy"
export BYROCTL_ADMIN_PASSWORD="It-Passw0rd-$$"
export BYROCTL_WEB_HEALTH_TIMEOUT=240

failures=0
pass() { printf 'OK    %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; failures=$((failures + 1)); }
# check LABEL COMMAND...: pass/fail by exit status
check() {
    local label="$1"; shift
    if "$@"; then pass "$label"; else fail "$label"; fi
}
compose_id() { (cd "$root" && docker compose ps -q "$1"); }

cleanup() {
    if [[ -f "$root/byro.conf" ]]; then
        (cd "$root" && docker compose down -v --remove-orphans >/dev/null 2>&1) || true
    fi
    rm -rf "$root"
}
trap cleanup EXIT

rm -rf "$root"

echo "--- install"
if "$byroctl" --root "$root" install --non-interactive --no-pull --version "$tag" \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_DEPLOY_IMAGE_REPO="$repo" --set COMPOSE_PROJECT_NAME="byro-it-$$" \
        --set BYRO_SITE_URL=http://localhost --set BYRO_HTTPS=false --set BYROCTL_PROXY=none \
        --set BYRO_DEPLOY_PORT="$port" --set BYROCTL_MAIL=host --set BYRO_MAIL_FROM=byro@example.org; then
    pass "byroctl install"
else
    fail "byroctl install"
    exit 1
fi

check "byro.conf is 0600" [ "$(stat -c %a "$root/byro.conf")" = 600 ]
check "version pinned in byro.conf" grep -q "^BYRO_DEPLOY_VERSION=$tag$" "$root/byro.conf"
check "mail host set" grep -q "^BYRO_MAIL_HOST=host.docker.internal$" "$root/byro.conf"

echo "--- config check / version"
check "config check" "$byroctl" --root "$root" config check
version_out="$("$byroctl" --root "$root" version)"
printf '%s\n' "$version_out"
check "version output" grep -q "byro version:   $tag" <<<"$version_out"

echo "--- http"
code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' "http://$http_host:$port/login/")"
check "GET /login/ -> 200 (got $code)" [ "$code" = 200 ]

echo "--- manage: superuser exists"
check "superuser admin exists" "$byroctl" --root "$root" manage shell -c \
    "import sys; from django.contrib.auth import get_user_model as g; sys.exit(0 if g().objects.filter(is_superuser=True, username='admin').exists() else 1)"

echo "--- config set --apply recreates only the byro services"
db_before="$(compose_id db)"
web_before="$(compose_id web)"
check "config set --apply" "$byroctl" --root "$root" config set BYRO_MAIL_HOST mail.example.org --apply
check "db untouched by config change" [ "$(compose_id db)" = "$db_before" ]
check "web recreated by config change" [ "$(compose_id web)" != "$web_before" ]

echo "--- restart / stop / start / logs"
db_before="$(compose_id db)"
check "restart" "$byroctl" --root "$root" restart
check "db untouched by restart" [ "$(compose_id db)" = "$db_before" ]
check "stop" "$byroctl" --root "$root" stop
check "web stopped" [ -z "$(cd "$root" && docker compose ps -q --status running web)" ]
check "start" "$byroctl" --root "$root" start
logs_out="$("$byroctl" --root "$root" logs web 2>&1)"
check "logs web mention gunicorn" grep -qi "gunicorn" <<<"$logs_out"

echo "--- second install run is idempotent"
before="$(cat "$root/byro.conf")"
check "re-run install" "$byroctl" --root "$root" install --non-interactive --no-pull --admin-user admin --admin-email admin@example.org
check "byro.conf unchanged by re-run" [ "$(cat "$root/byro.conf")" = "$before" ]

echo "--- secrets"
not_in_tree() { ! grep -rq -- "$1" "$2"; }
check "admin password not stored in root" not_in_tree "$BYROCTL_ADMIN_PASSWORD" "$root"

if (( failures > 0 )); then
    printf '\n%d check(s) failed\n' "$failures" >&2
    exit 1
fi
printf '\nall byroctl integration checks passed\n'
