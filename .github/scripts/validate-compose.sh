#!/usr/bin/env bash
# Validate the Compose files in deploy/ the way an installation uses them.
#
# Creates a temporary project directory that mirrors a real installation
# (compose files, Caddyfile, byro.conf.example copied as byro.conf, .env
# symlink) and runs `docker compose config` for every file combination, with
# and without an image digest. byro.conf.example deliberately leaves
# BYRO_DEPLOY_VERSION and BYRO_DB_PASS empty, so syntactically valid test
# values are provided through the environment (which takes precedence over
# the env file for interpolation).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
deploy="$repo_root/deploy"

workdir="$(mktemp -d)"
trap 'rm -rf "$workdir"' EXIT

cp "$deploy/docker-compose.yml" "$deploy/Caddyfile" "$workdir/"
cp -R "$deploy/compose" "$workdir/compose"
cp "$deploy/byro.conf.example" "$workdir/byro.conf"
ln -s byro.conf "$workdir/.env"
cd "$workdir"

export BYRO_DEPLOY_VERSION="${BYRO_DEPLOY_VERSION:-v0.0.0-ci}"
export BYRO_DB_PASS="${BYRO_DB_PASS:-ci-only}"
test_digest="sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

combos=(
    "docker-compose.yml"
    "docker-compose.yml:compose/postgres.yml"
    "docker-compose.yml:compose/postgres.yml:compose/caddy.yml"
    "docker-compose.yml:compose/caddy.yml"
)

failures=0
check() {
    local label="$1"
    shift
    if "$@" >/dev/null 2>"$workdir/error.log"; then
        printf 'OK    %s\n' "$label"
    else
        printf 'FAIL  %s\n' "$label"
        sed 's/^/      /' "$workdir/error.log"
        failures=$((failures + 1))
    fi
}

for combo in "${combos[@]}"; do
    check "$combo" env COMPOSE_FILE="$combo" docker compose --profile tools config -q
    check "$combo (with digest)" env COMPOSE_FILE="$combo" \
        BYRO_DEPLOY_IMAGE_DIGEST="$test_digest" docker compose --profile tools config -q
done

# The default COMPOSE_FILE from byro.conf must work on its own.
check "COMPOSE_FILE from byro.conf" docker compose config -q

# Required values must be enforced.
if env -u BYRO_DB_PASS COMPOSE_FILE="docker-compose.yml:compose/postgres.yml" \
        docker compose config -q >/dev/null 2>&1; then
    printf 'FAIL  empty BYRO_DB_PASS was accepted\n'
    failures=$((failures + 1))
else
    printf 'OK    empty BYRO_DB_PASS is rejected\n'
fi
if env -u BYRO_DEPLOY_VERSION docker compose config -q >/dev/null 2>&1; then
    printf 'FAIL  empty BYRO_DEPLOY_VERSION was accepted\n'
    failures=$((failures + 1))
else
    printf 'OK    empty BYRO_DEPLOY_VERSION is rejected\n'
fi

# Spot-check the rendered model.
rendered="$(env COMPOSE_FILE="docker-compose.yml:compose/postgres.yml:compose/caddy.yml" \
    BYRO_DEPLOY_IMAGE_DIGEST="$test_digest" docker compose --profile tools config)"
expect() {
    local label="$1" pattern="$2"
    if grep -qE -- "$pattern" <<<"$rendered"; then
        printf 'OK    rendered: %s\n' "$label"
    else
        printf 'FAIL  rendered: %s (pattern %s)\n' "$label" "$pattern"
        failures=$((failures + 1))
    fi
}
expect "image pinned by digest" "image: ghcr.io/byro/byro:${BYRO_DEPLOY_VERSION}@${test_digest}"
expect "web depends on db" "condition: service_healthy"
expect "caddy sets BYRO_TRUST_PROXY" 'BYRO_TRUST_PROXY: "true"'
expect "periodic disables auto-migrate" 'BYRO_AUTO_MIGRATE: "false"'
expect "manage entrypoint" "byro-entrypoint"

if [[ "$failures" -gt 0 ]]; then
    printf '\n%d check(s) failed\n' "$failures" >&2
    exit 1
fi
printf '\nall compose checks passed\n'
