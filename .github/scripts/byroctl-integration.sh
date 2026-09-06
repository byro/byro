#!/usr/bin/env bash
# Integration test for byroctl against a locally built byro image and real
# Docker: install with a plugin, config, start/stop/restart, manage, logs,
# idempotent re-run, update, plugin remove/add.
#
# Usage: byroctl-integration.sh <image repo> <image tag> <root dir> [host port]
#   e.g. byroctl-integration.sh byro-ci smoke "$RUNNER_TEMP/byro-it" 18345
#
# Requires bash >= 4, docker with compose and buildx, curl on the machine that
# runs the script; the root directory must be usable as a bind mount source by
# the Docker daemon (same path on host and daemon). The plugin image is built
# FROM the daemon-local test image, which only the docker-driver builder can
# see, hence BUILDX_BUILDER=default (a docker-container builder, as set up by
# docker/setup-buildx-action, would try to pull it).
set -euo pipefail

repo="${1:?image repo}"
tag="${2:?image tag}"
root="${3:?root dir}"
port="${4:-18345}"
# host to reach the published port (inside a helper container: host.docker.internal)
http_host="${BYROCTL_IT_HTTP_HOST:-127.0.0.1}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
byroctl="$here/deploy/byroctl"
fixture="$here/deploy/tests/fixtures/byro-testplugin"
plugin_image="byro-it-$$-plugins"

export BYROCTL_SOURCE_DIR="$here/deploy"
export BYROCTL_ADMIN_PASSWORD="It-Passw0rd-$$"
export BYROCTL_WEB_HEALTH_TIMEOUT=240
export BUILDX_BUILDER="${BUILDX_BUILDER:-default}"

failures=0
pass() { printf 'OK    %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; failures=$((failures + 1)); }
# check LABEL COMMAND...: pass/fail by exit status
check() {
    local label="$1"; shift
    if "$@"; then pass "$label"; else fail "$label"; fi
}
compose_id() { (cd "$root" && docker compose ps -q "$1"); }

# Run COMMAND... as root inside the test image with the root directory bind
# mounted at /mnt. The containers write data/ (byro user) and db/ (postgres
# user) with their own ids, so the host user can neither read nor remove those
# files directly. The image's entrypoint is bypassed; it would drop privileges.
in_root_container() {
    docker run --rm --entrypoint "$1" -v "$root:/mnt" "$repo:$tag" "${@:2}"
}

cleanup() {
    if [[ -f "$root/byro.conf" ]]; then
        (cd "$root" && docker compose down -v --remove-orphans >/dev/null 2>&1) || true
    fi
    if [[ -d "$root" ]]; then
        # hand the tree back to us before removing it; best effort, a leftover
        # directory must not turn a passed run into a failed one
        in_root_container chown -R "$(id -u):$(id -g)" /mnt >/dev/null 2>&1 || true
        rm -rf "$root" || true
    fi
    docker rmi "$repo:${tag}2" "$plugin_image:$tag" "$plugin_image:${tag}2" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if [[ -d "$root" ]]; then
    in_root_container chown -R "$(id -u):$(id -g)" /mnt >/dev/null 2>&1 || true
    rm -rf "$root"
fi
# a local plugin checkout inside the build context, referenced as ./testplugin
mkdir -p "$root/plugins"
cp -R "$fixture" "$root/plugins/testplugin"

echo "--- install (with a plugin)"
if "$byroctl" --root "$root" install --non-interactive --no-pull --version "$tag" \
        --admin-user admin --admin-email admin@example.org --plugin ./testplugin \
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

echo "--- plugin image"
web_image() { docker inspect --format '{{.Config.Image}}' "$(compose_id web)"; }
in_plugin_image() { docker run --rm --entrypoint sh "$plugin_image:$1" -c "$2"; }
check "plugins.txt lists the local plugin" grep -qx './testplugin' "$root/plugins/plugins.txt"
check "compose/plugins.yml active" grep -q 'compose/plugins.yml' "$root/byro.conf"
check "plugin image exists" docker image inspect "$plugin_image:$tag"
check "web runs the plugin image (got $(web_image))" [ "$(web_image)" = "$plugin_image:$tag" ]
check "plugin importable in the container" "$byroctl" --root "$root" manage shell -c "import byro_testplugin"
check "plugin migration applied" "$byroctl" --root "$root" manage shell -c \
    "import sys; from django.db import connection; sys.exit(0 if 'byro_testplugin_testpluginmarker' in connection.introspection.table_names() else 1)"
# shellcheck disable=SC2016  # expanded by the shell inside the container
check "plugin translation compiled in the image" in_plugin_image "$tag" \
    'test -f "$(python -c "import byro_testplugin, os; print(os.path.dirname(byro_testplugin.__file__))")/locale/de/LC_MESSAGES/django.mo"'
check "plugin static file collected" in_plugin_image "$tag" 'test -f /byro/static.dist/byro_testplugin/testplugin.css'
check "no git in the final image" in_plugin_image "$tag" '! command -v git'
check "/byro/plugins.txt matches the list" diff <(docker run --rm --entrypoint cat "$plugin_image:$tag" /byro/plugins.txt) "$root/plugins/plugins.txt"
list_out="$("$byroctl" --root "$root" plugin list)"
check "plugin list names the local plugin" grep -q './testplugin' <<<"$list_out"
check "plugin list names the image" grep -q "plugin image: $plugin_image:$tag" <<<"$list_out"

echo "--- config check / version"
check "config check" "$byroctl" --root "$root" config check
version_out="$("$byroctl" --root "$root" version)"
printf '%s\n' "$version_out"
check "version output" grep -q "byro version:   $tag" <<<"$version_out"
check "version lists the loaded plugin" grep -q "loaded plugins: byro_testplugin" <<<"$version_out"

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

echo "--- update to a second tag of the same image (stage 2, safeguard, migration)"
docker tag "$repo:$tag" "$repo:${tag}2"
check "update --check reports the new tag" "$byroctl" --root "$root" update --check --to "${tag}2" --no-pull
check "update --to ${tag}2" "$byroctl" --root "$root" update --to "${tag}2" --no-pull --yes --non-interactive
check "version pinned to ${tag}2" grep -q "^BYRO_DEPLOY_VERSION=${tag}2$" "$root/byro.conf"
safeguard="$(find "$root/backups" -mindepth 1 -maxdepth 1 -type d -name "pre-update-$tag-*" | head -n1 || true)"
has_safeguard_files() { [ -f "$1/byro.conf" ] && [ -f "$1/.secret" ]; }
check "safeguard directory exists" [ -n "$safeguard" ]
check "safeguard has a non-empty database dump" [ -s "$safeguard/db.dump" ]
check "safeguard has byro.conf and .secret" has_safeguard_files "$safeguard"
check "state records the previous version" grep -q "^BYROCTL_PREVIOUS_VERSION=$tag$" "$root/.byroctl/state"
code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' "http://$http_host:$port/login/")"
check "GET /login/ -> 200 after update (got $code)" [ "$code" = 200 ]
set +e
"$byroctl" --root "$root" update --check --to "${tag}2" --no-pull >/dev/null 2>&1
rc=$?
set -e
check "update --check exits 3 when current (got $rc)" [ "$rc" = 3 ]
check "self-update keeps an identical script" "$byroctl" --root "$root" self-update
check "plugin image rebuilt for ${tag}2" docker image inspect "$plugin_image:${tag}2"
check "web runs the rebuilt plugin image (got $(web_image))" [ "$(web_image)" = "$plugin_image:${tag}2" ]
check "update safeguard carries plugins.txt" [ -f "$safeguard/plugins.txt" ]

echo "--- plugin remove / add on a running stack"
check "plugin remove" "$byroctl" --root "$root" plugin remove ./testplugin
check "web back on the base image (got $(web_image))" [ "$(web_image)" = "$repo:${tag}2" ]
check "add-on disabled" bash -c "! grep -q compose/plugins.yml '$root/byro.conf'"
plugin_safeguard="$(find "$root/backups" -mindepth 1 -maxdepth 1 -type d -name "pre-plugin-*" | head -n1 || true)"
check "pre-plugin safeguard exists" [ -n "$plugin_safeguard" ]
check "pre-plugin safeguard has a non-empty database dump" [ -s "$plugin_safeguard/db.dump" ]
check "pre-plugin safeguard has the previous plugins.txt" grep -qx './testplugin' "$plugin_safeguard/plugins.txt"
check "pre-plugin safeguard has the previous byro.conf" grep -q 'compose/plugins.yml' "$plugin_safeguard/byro.conf"
web_before="$(compose_id web)"
check "plugin add" "$byroctl" --root "$root" plugin add ./testplugin
check "web recreated by plugin add" [ "$(compose_id web)" != "$web_before" ]
check "web runs the plugin image again (got $(web_image))" [ "$(web_image)" = "$plugin_image:${tag}2" ]
code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' "http://$http_host:$port/login/")"
check "GET /login/ -> 200 after plugin add (got $code)" [ "$code" = 200 ]
plugins_before="$(cat "$root/plugins/plugins.txt")"
set +e
"$byroctl" --root "$root" plugin add 'byro-does-not-exist-xyz==99'
rc=$?
set -e
check "unresolvable requirement fails in phase 1 (exit $rc)" [ "$rc" = 1 ]
check "plugins.txt unchanged after the failed add" [ "$(cat "$root/plugins/plugins.txt")" = "$plugins_before" ]
check "web still runs the plugin image (got $(web_image))" [ "$(web_image)" = "$plugin_image:${tag}2" ]
code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: localhost' "http://$http_host:$port/login/")"
check "GET /login/ -> 200 after the failed add (got $code)" [ "$code" = 200 ]

echo "--- secrets"
# grep as root in a container so .secret and db/ are actually read; only a
# clean "no match" (exit 1) passes, an unreadable file (exit 2) fails the check
not_in_tree() {
    local rc=0
    in_root_container grep -rq -- "$1" /mnt || rc=$?
    [[ "$rc" -eq 1 ]]
}
check "admin password not stored in root" not_in_tree "$BYROCTL_ADMIN_PASSWORD"

if (( failures > 0 )); then
    printf '\n%d check(s) failed\n' "$failures" >&2
    exit 1
fi
printf '\nall byroctl integration checks passed\n'
