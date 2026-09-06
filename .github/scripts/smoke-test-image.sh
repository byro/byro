#!/usr/bin/env bash
# Smoke test for the production image (deploy/Dockerfile).
#
# Usage: smoke-test-image.sh <image>
#
# Everything is verified from the host (docker top / docker exec with the
# image's own python3); the image does not need ps, curl or other tooling.
set -euo pipefail

image="${1:?usage: smoke-test-image.sh <image>}"
name="byro-smoke-$$"
volume="byro-smoke-data-$$"
sqlite_env=(-e BYRO_DB_ENGINE=sqlite3 -e BYRO_DB_NAME=/var/byro/data/db.sqlite3)

cleanup() {
    docker rm -f "$name" "$name-periodic" "$name-legacy" >/dev/null 2>&1 || true
    docker volume rm "$volume" "$volume-legacy" "$volume-legacy-cfg" >/dev/null 2>&1 || true
}
trap cleanup EXIT

failures=0
pass() { printf 'OK    %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*"; failures=$((failures + 1)); }
expect_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        pass "$label"
    else
        fail "$label: expected '$expected', got '$actual'"
    fi
}

# byro prints a startup banner to stdout, so callers compare the last line only.
shell_probe='import os; print(os.getuid(), os.getgid(), os.environ["HOME"], os.environ["USER"], os.environ["LOGNAME"])'

# --- manage dispatch and privilege drop --------------------------------------

if docker run --rm "${sqlite_env[@]}" "$image" manage check --deploy >/dev/null 2>&1; then
    pass "manage check --deploy"
else
    fail "manage check --deploy"
fi

expect_eq "environment after privilege drop" "10001 10001 /var/byro byro byro" \
    "$(docker run --rm "${sqlite_env[@]}" "$image" manage shell -c "$shell_probe" 2>/dev/null | tail -n1)"

expect_eq "environment with BYRO_UID/BYRO_GID remapping" "1234 1234 /var/byro byro byro" \
    "$(docker run --rm "${sqlite_env[@]}" -e BYRO_UID=1234 -e BYRO_GID=1234 "$image" manage shell -c "$shell_probe" 2>/dev/null | tail -n1)"

# uid/gid 1000 belong to the legacy compatibility account; remapping must release it.
expect_eq "remapping to uid/gid 1000 releases the legacy account" "1000 1000 /var/byro byro byro" \
    "$(docker run --rm "${sqlite_env[@]}" -e BYRO_UID=1000 -e BYRO_GID=1000 "$image" manage shell -c "$shell_probe" 2>/dev/null | tail -n1)"

# Fail-closed remapping: root, non-numeric and ids already taken (1 = daemon).
for bad in BYRO_UID=0 BYRO_UID=abc BYRO_UID=1 BYRO_GID=0 BYRO_GID=-5 BYRO_GID=1; do
    if docker run --rm -e "$bad" "$image" manage --version >/dev/null 2>&1; then
        fail "$bad was accepted"
    else
        pass "$bad is rejected"
    fi
done

if docker run --rm "$image" bogus >/dev/null 2>&1; then
    fail "unknown subcommand was accepted"
else
    pass "unknown subcommand is rejected"
fi

# --- web service ----------------------------------------------------------------

docker volume create "$volume" >/dev/null
docker run -d --name "$name" -v "$volume:/var/byro/data" \
    -e BYRO_SITE_URL=http://byro.test "${sqlite_env[@]}" -e BYRO_DEPLOY_WEB_WORKERS=2 \
    "$image" >/dev/null

status=starting
for _ in $(seq 1 90); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$name")"
    [[ "$status" == starting ]] || break
    sleep 2
done
if [[ "$status" == healthy ]]; then
    pass "web container becomes healthy"
else
    fail "web container health is '$status'"
    docker logs "$name" 2>&1 | tail -40
fi

processes="$(docker top "$name" -eo pid,uid,comm)"
if grep -Eq '^ *[0-9]+ +10001 +gunicorn' <<<"$processes"; then
    pass "gunicorn runs as uid 10001"
else
    fail "gunicorn not running as uid 10001:"$'\n'"$processes"
fi
if grep -Eq '^ *[0-9]+ +0 +(python|gunicorn)' <<<"$processes"; then
    fail "python/gunicorn process running as root:"$'\n'"$processes"
else
    pass "no python/gunicorn process runs as root"
fi
if grep -q runserver <<<"$processes"; then
    fail "development server is running"
else
    pass "no development server is running"
fi

http_status() {
    docker exec "$name" python3 -c "
import sys, urllib.request, urllib.error
req = urllib.request.Request('http://127.0.0.1:8345/healthz', headers={'Host': sys.argv[1]})
try:
    with urllib.request.urlopen(req, timeout=5) as r:
        print(r.status)
except urllib.error.HTTPError as e:
    print(e.code)
" "$1"
}
expect_eq "/healthz with configured host" "200" "$(http_status byro.test)"
expect_eq "/healthz with foreign host is rejected by ALLOWED_HOSTS" "400" "$(http_status wrong.example)"

if docker exec "$name" python3 /byro/healthcheck.py; then
    pass "healthcheck.py"
else
    fail "healthcheck.py"
fi

expect_eq ".secret is private and owned by byro" "0o600 10001 10001 50" \
    "$(docker exec "$name" python3 -c "import os, stat; st = os.stat('/var/byro/data/.secret'); print(oct(stat.S_IMODE(st.st_mode)), st.st_uid, st.st_gid, st.st_size)")"

expect_eq "static files are served from the image" "200" \
    "$(docker exec "$name" python3 -c "
import sys, urllib.request, urllib.error
req = urllib.request.Request('http://127.0.0.1:8345/login/', headers={'Host': 'byro.test'})
with urllib.request.urlopen(req, timeout=5) as r:
    print(r.status)
")"

# --- periodic service (shares the migrated database of the web container) -----

docker run -d --name "$name-periodic" -v "$volume:/var/byro/data" \
    -e BYRO_SITE_URL=http://byro.test "${sqlite_env[@]}" \
    -e BYRO_AUTO_MIGRATE=false -e BYRO_DEPLOY_PERIODIC_INTERVAL=1 \
    "$image" periodic >/dev/null
sleep 8
periodic_logs="$(docker logs "$name-periodic" 2>&1)"
if grep -q "periodic: running runperiodic every 1s" <<<"$periodic_logs" \
    && ! grep -q "runperiodic failed" <<<"$periodic_logs"; then
    pass "periodic loop runs runperiodic"
else
    fail "periodic loop:"$'\n'"$periodic_logs"
fi
docker stop -t 10 "$name-periodic" >/dev/null
expect_eq "periodic stops cleanly on SIGTERM" "0" "$(docker inspect -f '{{.State.ExitCode}}' "$name-periodic")"

# --- legacy production/docker-compose.yml compatibility ----------------------
# That file selects the user by name ("uid1000"), overrides the entrypoint with
# "python -m byro" / "gunicorn" and configures byro through a mounted byro.cfg
# (no BYRO_* variables). It must keep working with this image.

expect_eq "legacy account uid1000 is uid/gid 1000" "1000 1000" \
    "$(docker run --rm --user uid1000 --entrypoint python3 "$image" -c 'import os; print(os.getuid(), os.getgid())')"

docker volume create "$volume-legacy" >/dev/null
docker volume create "$volume-legacy-cfg" >/dev/null
# Data volume owned by uid 1000, like the host directories of a legacy install.
# The volume must not stay empty: Docker re-initialises an empty named volume
# (including the owner of its root) from the image on every mount.
docker run --rm -v "$volume-legacy:/var/byro/data" --entrypoint sh "$image" \
    -c 'mkdir -p /var/byro/data/logs && chown -R 1000:1000 /var/byro/data'
docker run --rm -v "$volume-legacy-cfg:/cfg" --entrypoint sh "$image" -c \
    'printf "[site]\nurl = http://legacy.test\n[database]\nengine = sqlite3\nname = /var/byro/data/legacy.sqlite3\n" > /cfg/byro.cfg'

# Compose mounts a file; emulate that with a directory volume + BYRO_CONFIG_FILE.
legacy_run=(--user uid1000 -e DEVELOPMENT=0 -e PYTHONUNBUFFERED=1 -v "$volume-legacy:/var/byro/data")
cfg_mount=(--mount "type=volume,src=$volume-legacy-cfg,dst=/cfgdir,readonly")

if docker run --rm "${legacy_run[@]}" "${cfg_mount[@]}" -w /byro --entrypoint sh "$image" \
        -c 'cp /cfgdir/byro.cfg /tmp/byro.cfg && BYRO_CONFIG_FILE=/tmp/byro.cfg python -m byro check' >/dev/null 2>&1; then
    pass "legacy: python -m byro check as uid1000 with byro.cfg"
else
    fail "legacy: python -m byro check as uid1000 with byro.cfg"
fi

docker run -d --name "$name-legacy" "${legacy_run[@]}" "${cfg_mount[@]}" -w /byro \
    -e BYRO_CONFIG_FILE=/cfgdir/byro.cfg --entrypoint gunicorn "$image" \
    byro.wsgi --workers 1 --bind 0.0.0.0:8345 >/dev/null
status=starting
for _ in $(seq 1 90); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$name-legacy")"
    [[ "$status" == starting ]] || break
    sleep 2
done
if [[ "$status" == healthy ]]; then
    pass "legacy: gunicorn container is healthy (health check reads site url from byro.cfg)"
else
    fail "legacy: gunicorn container health is '$status'"
    docker logs "$name-legacy" 2>&1 | tail -20
    docker inspect -f '{{range .State.Health.Log}}{{.Output}}{{end}}' "$name-legacy" | tail -5
fi
if docker top "$name-legacy" -eo pid,uid,comm | grep -Eq '^ *[0-9]+ +1000 +gunicorn'; then
    pass "legacy: gunicorn runs as uid 1000"
else
    fail "legacy: gunicorn does not run as uid 1000"
fi

if [[ "$failures" -gt 0 ]]; then
    printf '\n%d check(s) failed\n' "$failures" >&2
    exit 1
fi
printf '\nall smoke checks passed\n'
