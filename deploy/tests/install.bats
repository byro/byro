#!/usr/bin/env bats
# byroctl install, exercised as a program against docker/curl shims.
# BYROCTL_SOURCE_DIR points at the real deploy/ directory, so the compose
# files that get installed are the ones from the repository.

load helpers/common

setup() {
    load_byroctl
    make_root
    use_shims
    export BYROCTL_SOURCE_DIR="$DEPLOY_DIR"
    export SHIM_TAGS="ghcr.io/byro/byro:v2026.3.0"
    export SHIM_LOCAL_IMAGES="ghcr.io/byro/byro:v2026.3.0 byro-local:dev"
    export SHIM_DIGESTS="ghcr.io/byro/byro:v2026.3.0 ghcr.io/byro/byro@sha256:1111111111111111111111111111111111111111111111111111111111111111
ghcr.io/byro/byro:v2026.3.0 docker.io/other/mirror@sha256:2222222222222222222222222222222222222222222222222222222222222222"
    export BYROCTL_ADMIN_PASSWORD="Admin-Passw0rd"
    unset BYROCTL_DB_PASSWORD BYROCTL_MAIL_PASSWORD BYROCTL_OIDC_CLIENT_SECRET
}

# run_install [EXTRA ARGS...]: a complete non-interactive installation into the
# current BYRO_ROOT; later --set/--version arguments override the defaults.
run_install() {
    run byroctl --root "$BYRO_ROOT" install --non-interactive --version v2026.3.0 \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_SITE_URL=https://byro.example.org --set BYROCTL_PROXY=none \
        --set BYRO_DEPLOY_PORT=18999 "$@"
}

@test "install writes byro.conf, .env, artefacts and directories" {
    run_install
    [ "$status" -eq 0 ]
    [ -f "$BYRO_ROOT/byro.conf" ]
    [ "$(stat -c %a "$BYRO_ROOT/byro.conf")" = "600" ]
    [ "$(readlink "$BYRO_ROOT/.env")" = "byro.conf" ]
    for f in docker-compose.yml compose/postgres.yml compose/caddy.yml Caddyfile byro.conf.example release.env; do
        [ -f "$BYRO_ROOT/$f" ]
        [ "$(sha256sum <"$BYRO_ROOT/$f")" = "$(sha256sum <"$DEPLOY_DIR/$f")" ]
    done
    for d in data db caddy backups .byroctl; do [ -d "$BYRO_ROOT/$d" ]; done
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "v2026.3.0" ]
    [ "$(conf_get BYRO_SITE_URL)" = "https://byro.example.org" ]
    [ "$(conf_get BYRO_HTTPS)" = "true" ]
    [ "$(conf_get BYRO_TRUST_PROXY)" = "false" ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml" ]
    [ "$(conf_get BYRO_DEPLOY_PORT)" = "18999" ]
    [ "$(conf_get BYRO_DB_HOST)" = "db" ]
    pw="$(conf_get BYRO_DB_PASS)"; [ "${#pw}" -eq 32 ]
    [ -f "$BYRO_ROOT/.byroctl/state" ]
    conf_has BYROCTL_INSTALLED_AT "$BYRO_ROOT/.byroctl/state"
    [[ "$output" == *"is installed and running"* ]]
}

@test "install runs the docker steps in order and pins the digest of the configured repository" {
    run_install
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_DEPLOY_IMAGE_DIGEST)" = "sha256:1111111111111111111111111111111111111111111111111111111111111111" ]
    # order: gate -> pull -> inspect -> db up -> migrate -> superuser probe -> createsuperuser -> up
    seq="$(grep -oE 'docker (manifest inspect|compose pull|image inspect|compose up -d db|compose run --rm -T manage migrate|compose run --rm -T manage shell|compose run --rm -T -e DJANGO_SUPERUSER_PASSWORD manage createsuperuser|compose up -d$)' "$SHIM_LOG" | tr '\n' '|')"
    [ "$seq" = "docker manifest inspect|docker compose pull|docker image inspect|docker compose up -d db|docker compose run --rm -T manage migrate|docker compose run --rm -T manage shell|docker compose run --rm -T -e DJANGO_SUPERUSER_PASSWORD manage createsuperuser|docker compose up -d|" ]
    # the password never appears on a docker command line
    ! grep -q "Admin-Passw0rd" "$SHIM_LOG"
    grep -q "createsuperuser --noinput --username admin --email admin@example.org" "$SHIM_LOG"
}

@test "install fails closed when the pulled image has no digest for the repository" {
    export SHIM_DIGESTS="ghcr.io/byro/byro:v2026.3.0 docker.io/other/mirror@sha256:2222222222222222222222222222222222222222222222222222222222222222"
    run_install
    [ "$status" -ne 0 ]
    [[ "$output" == *"carries no digest"* ]]
    ! grep -q "compose up -d db" "$SHIM_LOG"
}

@test "install refuses a version whose image is missing in the registry" {
    export SHIM_TAGS=""
    run_install
    [ "$status" -ne 0 ]
    [[ "$output" == *"does not exist in the registry"* ]]
}

@test "--no-pull uses a local image and never pulls; a missing local image is an error" {
    run_install --no-pull --set BYRO_DEPLOY_IMAGE_REPO=byro-local --version dev
    [ "$status" -eq 0 ]
    ! grep -q "compose pull" "$SHIM_LOG"
    ! grep -q "manifest inspect" "$SHIM_LOG"
    [ "$(conf_get BYRO_DEPLOY_IMAGE_DIGEST)" = "" ]
    make_root
    : >"$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" install --non-interactive --version missing --no-pull \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_SITE_URL=https://byro.example.org --set BYROCTL_PROXY=none --set BYRO_DEPLOY_IMAGE_REPO=byro-local
    [ "$status" -ne 0 ]
    [[ "$output" == *"not present locally"* ]]
    ! grep -q "compose up" "$SHIM_LOG"
}

@test "an existing superuser skips account creation, --skip-superuser too" {
    export SHIM_SUPERUSER_EXISTS=1
    run_install
    [ "$status" -eq 0 ]
    ! grep -q createsuperuser "$SHIM_LOG"
    [[ "$output" == *"superuser exists already"* ]]
    make_root; : >"$SHIM_LOG"; export SHIM_SUPERUSER_EXISTS=0
    run_install --skip-superuser
    [ "$status" -eq 0 ]
    ! grep -q "manage shell" "$SHIM_LOG"
    ! grep -q createsuperuser "$SHIM_LOG"
}

@test "a second run resumes without questions, copies nothing twice and re-asks only the admin data" {
    run_install
    [ "$status" -eq 0 ]
    before="$(cat "$BYRO_ROOT/byro.conf")"
    : >"$SHIM_LOG"
    # no --set at all: general questions must not be asked again; the superuser
    # is missing again (shim), so the admin data has to be provided.
    run byroctl --root "$BYRO_ROOT" install --non-interactive --admin-user admin2 --admin-email admin2@example.org
    [ "$status" -eq 0 ]
    [ "$(cat "$BYRO_ROOT/byro.conf")" = "$before" ]
    [[ "$output" == *"resuming the installation"* ]]
    grep -q "createsuperuser --noinput --username admin2" "$SHIM_LOG"
    # and without the admin data it says exactly what is missing
    : >"$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" install --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"ADMIN_EMAIL"* ]]
}

@test "a failed createsuperuser is reported and leaves the installation resumable" {
    export SHIM_FAIL="createsuperuser"
    run_install
    [ "$status" -ne 0 ]
    [[ "$output" == *"run 'byroctl install' again"* ]]
    [ -f "$BYRO_ROOT/byro.conf" ]
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
}

@test "secrets are refused on the command line" {
    run_install --set BYRO_DB_PASS=leak
    [ "$status" -eq 64 ]
    [[ "$output" == *"must not be passed on the command line"* ]]
    [ ! -f "$BYRO_ROOT/byro.conf" ]
    run_install --set BYRO_OIDC_CLIENT_SECRET=leak
    [ "$status" -eq 64 ]
}

@test "non-interactive install lists the missing required values" {
    run byroctl --root "$BYRO_ROOT" install --non-interactive --version v2026.3.0
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing values"* ]]
    [[ "$output" == *"BYRO_SITE_URL"* ]]
    [ ! -f "$BYRO_ROOT/byro.conf" ]
}

@test "without a terminal and without --non-interactive the installer stops with a hint" {
    run byroctl --root "$BYRO_ROOT" install --version v2026.3.0 </dev/null
    [ "$status" -ne 0 ]
    [[ "$output" == *"no terminal"* ]]
}

@test "caddy mode adds the caddy add-on, keeps BYRO_TRUST_PROXY false and checks ports 80/443" {
    run_install --set BYROCTL_PROXY=caddy
    [ "$status" -eq 0 ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml:compose/caddy.yml" ]
    [ "$(conf_get BYRO_TRUST_PROXY)" = "false" ]
    # occupy a port and expect a clear message
    make_root; : >"$SHIM_LOG"
    python3 -c 'import socket,time; s=socket.socket(); s.bind(("127.0.0.1",18999)); s.listen(1); time.sleep(20)' &
    listener=$!
    sleep 1
    run_install --set BYROCTL_PROXY=caddy
    kill "$listener" 2>/dev/null || true
    [ "$status" -ne 0 ]
    [[ "$output" == *"already in use"* ]]
    [[ "$output" == *"18999"* ]]
    [ ! -f "$BYRO_ROOT/byro.conf" ]
}

@test "own proxy mode sets BYRO_TRUST_PROXY=true" {
    run_install --set BYROCTL_PROXY=own
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_TRUST_PROXY)" = "true" ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml:compose/postgres.yml" ]
}

@test "external database: no generated password, no db service, password from the environment" {
    export BYROCTL_DB_PASSWORD='ext$pass #1'
    run_install --set BYROCTL_DB=external --set BYRO_DB_HOST=db.example.org --set BYRO_DB_NAME=byrodb --set BYRO_DB_USER=byrouser
    [ "$status" -eq 0 ]
    [ "$(conf_get COMPOSE_FILE)" = "docker-compose.yml" ]
    [ "$(conf_get BYRO_DB_HOST)" = "db.example.org" ]
    [ "$(conf_get BYRO_DB_PASS)" = 'ext$pass #1' ]
    ! grep -q "compose up -d db" "$SHIM_LOG"
    grep -q "^BYRO_DB_PASS='ext\$pass #1'$" "$BYRO_ROOT/byro.conf"
}

@test "mail on the docker host uses host.docker.internal" {
    run_install --set BYROCTL_MAIL=host --set BYRO_MAIL_FROM=byro@example.org
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_MAIL_HOST)" = "host.docker.internal" ]
    [ "$(conf_get BYRO_MAIL_PORT)" = "25" ]
    [ "$(conf_get BYRO_MAIL_FROM)" = "byro@example.org" ]
}

@test "an unwritable root prints the sudo hint and changes nothing" {
    local root="$BATS_TEST_TMPDIR/ro/byro"
    mkdir -p "$BATS_TEST_TMPDIR/ro"; chmod 555 "$BATS_TEST_TMPDIR/ro"
    run byroctl --root "$root" install --non-interactive --version v2026.3.0
    chmod 755 "$BATS_TEST_TMPDIR/ro"
    if [ "$(id -u)" -eq 0 ]; then skip "root can always write"; fi
    [ "$status" -ne 0 ]
    [[ "$output" == *"sudo mkdir -p"* ]]
    [ ! -d "$root" ]
}

@test "a remote base URL without https is refused" {
    export BYROCTL_SOURCE_DIR=""
    export BYROCTL_RAW_BASE="http://example.org/raw"
    run_install
    [ "$status" -ne 0 ]
    [[ "$output" == *"must use https://"* ]]
}

@test "the lock is released after a failure and a stale lock is taken over" {
    export SHIM_FAIL="compose pull"
    run_install
    [ "$status" -ne 0 ]
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
    unset SHIM_FAIL
    mkdir -p "$BYRO_ROOT/.byroctl/lock"; echo 999999 >"$BYRO_ROOT/.byroctl/lock/pid"
    run_install
    [ "$status" -eq 0 ]
    [[ "$output" == *"stale lock"* ]]
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
}

@test "remote installation verifies every artefact against SHA256SUMS of the tag" {
    export BYROCTL_SOURCE_DIR=""
    export BYROCTL_RAW_BASE="https://example.test"
    export SHIM_RAW="$BATS_TEST_TMPDIR/raw"
    mkdir -p "$SHIM_RAW/v2026.3.0/deploy/compose"
    for f in docker-compose.yml compose/postgres.yml compose/caddy.yml Caddyfile byro.conf.example release.env; do
        cp "$DEPLOY_DIR/$f" "$SHIM_RAW/v2026.3.0/deploy/$f"
    done
    ( cd "$SHIM_RAW/v2026.3.0/deploy" && sha256sum docker-compose.yml compose/postgres.yml compose/caddy.yml Caddyfile byro.conf.example release.env >SHA256SUMS )
    run_install
    [ "$status" -eq 0 ]
    grep -q "curl .*--proto =https .*v2026.3.0/deploy/SHA256SUMS" "$SHIM_LOG"
    # tamper with one file -> abort, nothing half-installed
    make_root; : >"$SHIM_LOG"
    echo "# tampered" >>"$SHIM_RAW/v2026.3.0/deploy/Caddyfile"
    run_install
    [ "$status" -ne 0 ]
    [[ "$output" == *"checksum mismatch for Caddyfile"* ]]
    [ ! -f "$BYRO_ROOT/Caddyfile" ]
    [ ! -f "$BYRO_ROOT/byro.conf" ]
}
