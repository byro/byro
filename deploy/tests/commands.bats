#!/usr/bin/env bats
# byroctl config / start / stop / restart / logs / manage / version against the
# docker shim, on top of an installation created with the shims.

load helpers/common

setup() {
    load_byroctl
    make_root
    use_shims
    export BYROCTL_SOURCE_DIR="$DEPLOY_DIR"
    export SHIM_TAGS="ghcr.io/byro/byro:v2026.3.0 ghcr.io/byro/byro@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    export SHIM_LOCAL_IMAGES="ghcr.io/byro/byro:v2026.3.0"
    export SHIM_DIGESTS="ghcr.io/byro/byro:v2026.3.0 ghcr.io/byro/byro@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    export BYROCTL_ADMIN_PASSWORD="Admin-Passw0rd"
    run byroctl --root "$BYRO_ROOT" install --non-interactive --version v2026.3.0 \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_SITE_URL=https://byro.example.org --set BYROCTL_PROXY=none --set BYRO_DEPLOY_PORT=18998
    [ "$status" -eq 0 ]
    : >"$SHIM_LOG"
}

@test "config get prints values and masks secrets" {
    run byroctl --root "$BYRO_ROOT" config get BYRO_SITE_URL
    [ "$status" -eq 0 ]
    [ "$output" = "https://byro.example.org" ]
    run byroctl --root "$BYRO_ROOT" config get BYRO_DB_PASS
    [ "$status" -eq 0 ]
    [ "$output" = "********" ]
    run byroctl --root "$BYRO_ROOT" config get BYRO_NOT_THERE
    [ "$status" -ne 0 ]
}

@test "config set writes a value, --apply checks and runs compose up" {
    run byroctl --root "$BYRO_ROOT" config set BYRO_MAIL_HOST mail.example.org
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_MAIL_HOST)" = "mail.example.org" ]
    refute grep -q "compose up" "$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" config set BYRO_MAIL_PORT 465 --apply
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_MAIL_PORT)" = "465" ]
    grep -q "docker compose config -q" "$SHIM_LOG"
    grep -q "docker compose up -d$" "$SHIM_LOG"
}

@test "config set refuses secrets on the command line and takes them from BYROCTL_VALUE" {
    run byroctl --root "$BYRO_ROOT" config set BYRO_MAIL_PASSWORD leak
    [ "$status" -eq 64 ]
    [[ "$output" == *"BYROCTL_VALUE"* ]]
    BYROCTL_VALUE='se$cret #x' run byroctl --root "$BYRO_ROOT" config set BYRO_MAIL_PASSWORD
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_MAIL_PASSWORD)" = 'se$cret #x' ]
    [[ "$output" == *"********"* ]]
    refute grep -q 'se$cret' "$SHIM_LOG"
}

@test "config check passes for a fresh installation" {
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" == *"config check: OK"* ]]
    grep -q "docker compose config -q" "$SHIM_LOG"
}

@test "config check reports an empty database password, a bad digest and unquoted \$" {
    conf_set BYRO_DB_PASS ""
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -ne 0 ]
    [[ "$output" == *"BYRO_DB_PASS is empty"* ]]
    conf_set BYRO_DB_PASS again
    conf_set BYRO_DEPLOY_IMAGE_DIGEST sha256:short
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -ne 0 ]
    [[ "$output" == *"unexpected format"* ]]
    conf_set BYRO_DEPLOY_IMAGE_DIGEST sha256:1111111111111111111111111111111111111111111111111111111111111111
    printf 'BYRO_MAIL_PASSWORD=un$quoted\n' >>"$BYRO_ROOT/byro.conf"
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -ne 0 ]
    [[ "$output" == *"would be interpolated"* ]]
}

@test "config check reports missing compose files, wrong mode and a debug flag" {
    rm "$BYRO_ROOT/compose/postgres.yml"
    chmod 644 "$BYRO_ROOT/byro.conf"
    conf_set BYRO_DEBUG true
    chmod 644 "$BYRO_ROOT/byro.conf"
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -ne 0 ]
    [[ "$output" == *"compose/postgres.yml, but the file does not exist"* ]]
    [[ "$output" == *"must be 600"* ]]
    [[ "$output" == *"BYRO_DEBUG is set"* ]]
}

@test "config check accepts the deprecated OIDC admin group with a warning" {
    conf_set BYRO_OIDC_ADMIN_GROUP byro-admins
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" == *"BYRO_OIDC_ADMIN_GROUP is deprecated"* ]]
    [[ "$output" == *"config check: OK"* ]]
    # the same group under both names is not a conflict
    conf_set BYRO_OIDC_STAFF_GROUP byro-admins
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" == *"BYRO_OIDC_ADMIN_GROUP is deprecated"* ]]
}

@test "config check rejects different OIDC admin and staff groups" {
    conf_set BYRO_OIDC_ADMIN_GROUP byro-admins
    conf_set BYRO_OIDC_STAFF_GROUP byro-staff
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -ne 0 ]
    [[ "$output" == *"ERROR: BYRO_OIDC_ADMIN_GROUP and BYRO_OIDC_STAFF_GROUP are set to different values"* ]]
    # and config set refuses to apply it
    conf_set BYRO_OIDC_STAFF_GROUP ""
    : >"$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" config set BYRO_OIDC_STAFF_GROUP byro-staff --apply
    [ "$status" -ne 0 ]
    [[ "$output" == *"not applying a configuration with errors"* ]]
    refute grep -q "compose up" "$SHIM_LOG"
}

@test "config check compares the OIDC groups without surrounding whitespace" {
    # byro strips the values, so these two name the same group
    conf_set BYRO_OIDC_ADMIN_GROUP " admins "
    conf_set BYRO_OIDC_STAFF_GROUP admins
    [ "$(conf_get BYRO_OIDC_ADMIN_GROUP)" = " admins " ]
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" != *"different values"* ]]
    [[ "$output" == *"BYRO_OIDC_ADMIN_GROUP is deprecated"* ]]
    conf_set BYRO_OIDC_ADMIN_GROUP admins
    conf_set BYRO_OIDC_STAFF_GROUP "	admins  "
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" != *"different values"* ]]
    # still a conflict if the names really differ
    conf_set BYRO_OIDC_ADMIN_GROUP " admins "
    conf_set BYRO_OIDC_STAFF_GROUP " other "
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -ne 0 ]
    [[ "$output" == *"set to different values"* ]]
}

@test "config check treats a whitespace-only OIDC group as not set" {
    # nothing but whitespace under the old name: neither deprecated nor a conflict
    conf_set BYRO_OIDC_ADMIN_GROUP "   "
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" != *"OIDC"* ]]
    conf_set BYRO_OIDC_STAFF_GROUP byro-staff
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" != *"OIDC"* ]]
    # and the other way round: the old name alone stays a plain deprecation
    conf_set BYRO_OIDC_ADMIN_GROUP admins
    conf_set BYRO_OIDC_STAFF_GROUP "   "
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" != *"different values"* ]]
    [[ "$output" == *"BYRO_OIDC_ADMIN_GROUP is deprecated"* ]]
}

@test "conf_get_trimmed strips surrounding whitespace only" {
    conf_set A "  two words  "
    conf_set B "   "
    [ "$(conf_get_trimmed A)" = "two words" ]
    [ "$(conf_get_trimmed B)" = "" ]
    [ "$(conf_get_trimmed NOT_THERE)" = "" ]
}

@test "config check says nothing about the current OIDC group options" {
    conf_set BYRO_OIDC_STAFF_GROUP byro-staff
    conf_set BYRO_OIDC_SUPERUSER_GROUP byro-superusers
    conf_set BYRO_OIDC_SYNC_GROUPS true
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" != *"OIDC"* ]]
}

@test "config check warns when the pinned digest cannot be confirmed" {
    export SHIM_TAGS="ghcr.io/byro/byro:v2026.3.0"
    run byroctl --root "$BYRO_ROOT" config check
    [ "$status" -eq 0 ]
    [[ "$output" == *"could not confirm"* ]]
}

@test "config edit runs the editor, checks and does not apply without a terminal" {
    EDITOR=true run byroctl --root "$BYRO_ROOT" config edit
    [ "$status" -eq 0 ]
    [[ "$output" == *"config check: OK"* ]]
    refute grep -q "compose up" "$SHIM_LOG"
    EDITOR=/nonexistent/editor run byroctl --root "$BYRO_ROOT" config edit
    [ "$status" -ne 0 ]
}

@test "start and stop map to compose up -d and compose stop" {
    run byroctl --root "$BYRO_ROOT" start
    [ "$status" -eq 0 ]
    grep -q "docker compose up -d$" "$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" stop
    [ "$status" -eq 0 ]
    grep -q "docker compose stop$" "$SHIM_LOG"
}

@test "restart recreates the byro services but never db or manage" {
    export SHIM_SERVICES="db web periodic caddy manage"
    run byroctl --root "$BYRO_ROOT" restart
    [ "$status" -eq 0 ]
    grep -q "docker compose up -d --force-recreate --no-deps web periodic caddy$" "$SHIM_LOG"
    export SHIM_SERVICES="db web periodic"
    : >"$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" restart
    grep -q "docker compose up -d --force-recreate --no-deps web periodic$" "$SHIM_LOG"
}

@test "logs does not follow unless -f is given" {
    run byroctl --root "$BYRO_ROOT" logs
    [ "$status" -eq 0 ]
    grep -q "docker compose logs --tail=200$" "$SHIM_LOG"
    : >"$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" logs -f web
    grep -q "docker compose logs --tail=200 --follow web$" "$SHIM_LOG"
}

@test "manage forwards the management command to a one-off container" {
    run byroctl --root "$BYRO_ROOT" manage migrate --plan
    [ "$status" -eq 0 ]
    grep -q "docker compose run --rm -T manage migrate --plan$" "$SHIM_LOG"
    run byroctl --root "$BYRO_ROOT" manage
    [ "$status" -eq 64 ]
}

@test "version shows the pinned version, digest and the running byro" {
    run byroctl --root "$BYRO_ROOT" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"byro version:   v2026.3.0"* ]]
    [[ "$output" == *"sha256:1111111111111111111111111111111111111111111111111111111111111111"* ]]
    [[ "$output" == *"running byro:   v9.9.9-shim"* ]]
}

@test "commands other than install refuse to run without an installation" {
    make_root
    run byroctl --root "$BYRO_ROOT" start
    [ "$status" -ne 0 ]
    [[ "$output" == *"not installed yet"* ]]
    run byroctl --root "$BYRO_ROOT/does-not-exist" version
    [ "$status" -ne 0 ]
}

@test "a second byroctl process is refused while the lock is held" {
    mkdir -p "$BYRO_ROOT/.byroctl/lock"; echo $$ >"$BYRO_ROOT/.byroctl/lock/pid"
    run byroctl --root "$BYRO_ROOT" start
    [ "$status" -ne 0 ]
    [[ "$output" == *"another byroctl process"* ]]
    rm -rf "$BYRO_ROOT/.byroctl/lock"
}
