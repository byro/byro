#!/usr/bin/env bats
# byroctl update and self-update against the docker/curl shims. The installation
# is created from the local deploy/ directory; the update then runs the remote
# path against a fake release tree served by the curl shim.

load helpers/common

# Constants are set in setup(): top-level assignments are not reliably visible
# inside bats test functions.
constants() {
    OLD=v2026.3.0
    NEW=v2026.4.0
    OLD_DIGEST=sha256:1111111111111111111111111111111111111111111111111111111111111111
    NEW_DIGEST=sha256:4444444444444444444444444444444444444444444444444444444444444444
}

# make_release TAG [BREAKING] [DATA_MIGRATION]: a fake deploy/ tree of TAG on the
# "raw" server, based on the repository files, with visible differences.
make_release() {
    local tag="$1" breaking="${2:-0}" datamig="${3:-0}" d
    d="$SHIM_RAW/$tag/deploy"
    rm -rf "$d"
    copy_artifacts "$d"
    cp "$DEPLOY_DIR/byroctl" "$d/byroctl"
    if [[ "$tag" != "$OLD" ]]; then
        printf '\n# byroctl shipped with %s (test marker)\n' "$tag" >>"$d/byroctl"
        printf '\n# compose file of %s (test marker)\n' "$tag" >>"$d/docker-compose.yml"
        printf '\n# New in %s: an option byroctl did not know before.\n# Second comment line.\nBYRO_DEPLOY_NEW_OPTION=42\n' "$tag" >>"$d/byro.conf.example"
    fi
    printf 'BYRO_RELEASE_BREAKING=%s\nBYRO_RELEASE_DATA_MIGRATION=%s\n' "$breaking" "$datamig" >"$d/release.env"
    write_sha256sums "$d" byroctl "${BYROCTL_ARTIFACTS[@]}"
}

# bank_files_release TAG SHA: the shipped catalog entry answered by the curl shim
bank_files_release() {
    mkdir -p "$SHIM_HTTP/api.github.com/repos/byro/byro-finance-import-bank-files/releases" "$SHIM_HTTP/api.github.com/repos/byro/byro-finance-import-bank-files/commits"
    printf '{\n  "tag_name": "%s",\n  "prerelease": false\n}\n' "$1" >"$SHIM_HTTP/api.github.com/repos/byro/byro-finance-import-bank-files/releases/latest"
    printf '%s' "$2" >"$SHIM_HTTP/api.github.com/repos/byro/byro-finance-import-bank-files/commits/$1"
}
BANK_FILES_LINE() { printf 'byro-finance-import-bank-files @ git+https://github.com/byro/byro-finance-import-bank-files.git@%s  # byroctl:catalog=finance-import-bank-files version=%s' "$1" "$2"; }

setup() {
    constants
    load_byroctl
    make_root
    use_shims
    export SHIM_TAGS="ghcr.io/byro/byro:$OLD ghcr.io/byro/byro:$NEW ghcr.io/byro/byro@$OLD_DIGEST ghcr.io/byro/byro@$NEW_DIGEST"
    export SHIM_LOCAL_IMAGES="ghcr.io/byro/byro:$OLD ghcr.io/byro/byro:$NEW"
    export SHIM_DIGESTS="ghcr.io/byro/byro:$OLD ghcr.io/byro/byro@$OLD_DIGEST
ghcr.io/byro/byro:$NEW ghcr.io/byro/byro@$NEW_DIGEST"
    export BYROCTL_ADMIN_PASSWORD="Admin-Passw0rd"
    export BYROCTL_SOURCE_DIR="$DEPLOY_DIR"
    run byroctl --root "$BYRO_ROOT" install --non-interactive --version "$OLD" \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_SITE_URL=https://byro.example.org --set BYROCTL_PROXY=none --set BYRO_DEPLOY_PORT=18996
    [ "$status" -eq 0 ]
    # the installation carries a pinned digest and a secret file
    conf_set BYRO_DEPLOY_IMAGE_DIGEST "$OLD_DIGEST"
    printf 'the-secret-key\n' >"$BYRO_ROOT/data/.secret"
    # switch to the remote path for the update
    unset BYROCTL_SOURCE_DIR
    export BYROCTL_RAW_BASE="https://example.test"
    export SHIM_RAW="$BATS_TEST_TMPDIR/raw"
    mkdir -p "$SHIM_RAW/stable"
    make_release "$OLD"
    make_release "$NEW"
    printf 'BYRO_RELEASE_VERSION=%s\n' "$NEW" >"$SHIM_RAW/stable/stable.env"
    : >"$SHIM_LOG"
}

update() { run byroctl --root "$BYRO_ROOT" update "$@"; }

@test "update --check reports an available release with notes url and flags" {
    update --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"installed:      $OLD"* ]]
    [[ "$output" == *"available:      $NEW"* ]]
    [[ "$output" == *"https://github.com/byro/byro/releases/tag/$NEW"* ]]
    [[ "$output" == *"breaking:       no"* ]]
    grep -q "docker manifest inspect ghcr.io/byro/byro:$NEW" "$SHIM_LOG"
    grep -q "curl .*$NEW/deploy/release.env" "$SHIM_LOG"
    refute grep -qE "compose (pull|stop|up|run|exec)" "$SHIM_LOG"
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$OLD" ]
}

@test "update --check exits 3 when the installation is current" {
    printf 'BYRO_RELEASE_VERSION=%s\n' "$OLD" >"$SHIM_RAW/stable/stable.env"
    update --check
    [ "$status" -eq 3 ]
    [[ "$output" == *"is the current release"* ]]
}

@test "a full update switches script, config, compose files and image in order" {
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    [[ "$output" == *"switching to byroctl of $NEW"* ]]
    [[ "$output" == *"byro updated: $OLD -> $NEW"* ]]
    # configuration
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$NEW" ]
    [ "$(conf_get BYRO_DEPLOY_IMAGE_DIGEST)" = "$NEW_DIGEST" ]
    [ "$(conf_get BYRO_DEPLOY_NEW_OPTION)" = "42" ]
    grep -q "^# New in $NEW" "$BYRO_ROOT/byro.conf"
    grep -q "^# Second comment line." "$BYRO_ROOT/byro.conf"
    [[ "$output" == *"added new configuration keys with defaults: BYRO_DEPLOY_NEW_OPTION"* ]]
    [ "$(stat -c %a "$BYRO_ROOT/byro.conf")" = "600" ]
    # compose files and script of the new release
    grep -q "compose file of $NEW" "$BYRO_ROOT/docker-compose.yml"
    [[ "$output" == *"changes in docker-compose.yml"* ]]
    grep -q "byroctl shipped with $NEW" "$BYRO_ROOT/byroctl"
    [ ! -e "$BYRO_ROOT/.byroctl/byroctl.next" ]
    # docker step order
    seq="$(grep -oE 'docker (manifest inspect ghcr.io/byro/byro:v2026.4.0|compose exec -T db pg_dump|compose pull|image inspect|compose stop periodic web|compose run --rm -T manage migrate|compose up -d --remove-orphans)' "$SHIM_LOG" | tr '\n' '|')"
    # the gate runs twice: once before and once after the stage-2 switch to the new script
    [ "$seq" = "docker manifest inspect ghcr.io/byro/byro:v2026.4.0|docker manifest inspect ghcr.io/byro/byro:v2026.4.0|docker compose exec -T db pg_dump|docker compose pull|docker image inspect|docker compose stop periodic web|docker compose run --rm -T manage migrate|docker compose up -d --remove-orphans|" ]
    # safeguard
    local dir; dir="$(ls -d "$BYRO_ROOT"/backups/pre-update-"$OLD"-*)"
    [ "$(cat "$dir/db.dump")" = "PGDMP-shim" ]
    [ "$(cat "$dir/.secret")" = "the-secret-key" ]
    grep -q "^BYRO_DEPLOY_VERSION=$OLD$" "$dir/byro.conf"
    grep -q "^BYROCTL_PREVIOUS_VERSION=$OLD$" "$dir/META"
    grep -q "^BYROCTL_PREVIOUS_DIGEST=$OLD_DIGEST$" "$dir/META"
    grep -q "^BYROCTL_KIND=pre-update$" "$dir/META"
    [ -f "$dir/plugins.txt" ]
    # state and lock
    [ "$(conf_get BYROCTL_PREVIOUS_VERSION "$BYRO_ROOT/.byroctl/state")" = "$OLD" ]
    [ "$(conf_get BYROCTL_PREVIOUS_DIGEST "$BYRO_ROOT/.byroctl/state")" = "$OLD_DIGEST" ]
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
    # every artefact was verified against the SHA256SUMS of the new tag
    grep -q "curl .*$NEW/deploy/SHA256SUMS" "$SHIM_LOG"
}

@test "a breaking release needs --yes or an interactive confirmation" {
    make_release "$NEW" 1 0
    update --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"flagged as breaking"* ]]
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$OLD" ]
    refute grep -q "compose stop" "$SHIM_LOG"
    update --check
    [[ "$output" == *"breaking:       yes"* ]]
    : >"$SHIM_LOG"
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$NEW" ]
}

@test "a release with file migrations stops before any change unless --data-safeguard-done is given" {
    make_release "$NEW" 0 1
    before="$(cat "$BYRO_ROOT/byro.conf")"
    update --yes --non-interactive
    [ "$status" -eq 1 ]
    [[ "$output" == *"full backup of $BYRO_ROOT/data"* ]]
    [[ "$output" == *"--data-safeguard-done"* ]]
    [ "$(cat "$BYRO_ROOT/byro.conf")" = "$before" ]
    refute grep -qE "compose (pull|stop|up|exec)" "$SHIM_LOG"
    [ ! -e "$BYRO_ROOT/.byroctl/byroctl.next" ]
    update --yes --non-interactive --data-safeguard-done
    [ "$status" -eq 0 ]
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$NEW" ]
}

@test "a non-interactive update without --yes is refused" {
    update --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"use --yes"* ]]
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$OLD" ]
}

@test "downgrades are refused" {
    conf_set BYRO_DEPLOY_VERSION v2026.5.0
    update --to "$NEW" --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"downgrade is not an update"* ]]
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "v2026.5.0" ]
}

@test "--prefetch only pulls the target image" {
    before="$(cat "$BYRO_ROOT/byro.conf")"
    update --prefetch
    [ "$status" -eq 0 ]
    grep -q "^docker pull ghcr.io/byro/byro:$NEW$" "$SHIM_LOG"
    refute grep -qE "compose (pull|stop|up|run|exec)" "$SHIM_LOG"
    [ "$(cat "$BYRO_ROOT/byro.conf")" = "$before" ]
    [ ! -e "$BYRO_ROOT/.byroctl/byroctl.next" ]
}

@test "--skip-safeguard skips the dump" {
    update --yes --non-interactive --skip-safeguard
    [ "$status" -eq 0 ]
    refute grep -q "pg_dump" "$SHIM_LOG"
    [ -z "$(ls -A "$BYRO_ROOT/backups")" ]
    [[ "$output" == *"skipping the pre-update safeguard"* ]]
}

@test "an unreadable data/.secret is read through the image" {
    [ "$(id -u)" -ne 0 ] || skip "root can read everything"
    # owned by the container user and 0600 on a real installation; the host
    # user cannot read it, the byro image (running as root) can
    chmod 000 "$BYRO_ROOT/data/.secret"
    export SHIM_SECRET_IN_IMAGE="from-the-image"
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    local dir; dir="$(ls -d "$BYRO_ROOT"/backups/pre-update-"$OLD"-*)"
    [ "$(cat "$dir/.secret")" = "from-the-image" ]
    [ "$(stat -c %a "$dir/.secret" 2>/dev/null || stat -f %Lp "$dir/.secret")" = "600" ]
    grep -q -- "--entrypoint cat manage /var/byro/data/.secret" "$SHIM_LOG"
}

@test "a missing data/.secret is only a warning" {
    rm -f "$BYRO_ROOT/data/.secret"
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    [[ "$output" == *"data/.secret not found"* ]]
    local dir; dir="$(ls -d "$BYRO_ROOT"/backups/pre-update-"$OLD"-*)"
    [ ! -e "$dir/.secret" ]
}

@test "a tampered byroctl of the target release aborts before anything changes" {
    printf '\n# tampered\n' >>"$SHIM_RAW/$NEW/deploy/byroctl"
    before="$(cat "$BYRO_ROOT/byro.conf")"
    update --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"checksum mismatch for byroctl"* ]]
    [ "$(cat "$BYRO_ROOT/byro.conf")" = "$before" ]
    refute grep -q "compose stop" "$SHIM_LOG"
    refute grep -q "byroctl shipped with" "$BYRO_ROOT/byroctl"
}

@test "a failed migration leaves the stack stopped and prints the way back" {
    export SHIM_FAIL="manage migrate"
    update --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"database migration to $NEW failed"* ]]
    [[ "$output" == *"Manual way back to byro $OLD"* ]]
    [[ "$output" == *"BYRO_DEPLOY_IMAGE_DIGEST $OLD_DIGEST"* ]]
    ls -d "$BYRO_ROOT"/backups/pre-update-"$OLD"-* >/dev/null
    refute grep -q "compose up -d --remove-orphans" "$SHIM_LOG"
    refute conf_has BYROCTL_PREVIOUS_VERSION "$BYRO_ROOT/.byroctl/state"
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
}

@test "an external database is dumped with the postgres image" {
    conf_set COMPOSE_FILE docker-compose.yml
    conf_set BYRO_DB_HOST db.example.org
    conf_set BYRO_DB_PORT 5433
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    grep -q "^docker run --rm -e PGPASSWORD postgres:17-alpine pg_dump -h db.example.org -p 5433 -U byro -Fc byro$" "$SHIM_LOG"
    refute grep -q "compose up -d db" "$SHIM_LOG"
    local dir; dir="$(ls -d "$BYRO_ROOT"/backups/pre-update-"$OLD"-*)"
    [ "$(cat "$dir/db.dump")" = "PGDMP-shim-external" ]
    # the password travelled through the environment only
    refute grep -q "$(conf_get BYRO_DB_PASS)" "$SHIM_LOG"
}

@test "pre- and post-update hooks run in order with the versions in the environment" {
    mkdir -p "$BYRO_ROOT/.byroctl/hooks"
    printf '#!/usr/bin/env bash\necho "pre $BYROCTL_FROM $BYROCTL_TO" >>"$BYRO_ROOT/hooks.log"\n' >"$BYRO_ROOT/.byroctl/hooks/pre-update.sh"
    printf '#!/usr/bin/env bash\necho "post $BYROCTL_FROM $BYROCTL_TO" >>"$BYRO_ROOT/hooks.log"\n' >"$BYRO_ROOT/.byroctl/hooks/post-update.sh"
    chmod +x "$BYRO_ROOT"/.byroctl/hooks/*.sh
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    [ "$(cat "$BYRO_ROOT/hooks.log")" = "$(printf 'pre %s %s\npost %s %s' "$OLD" "$NEW" "$OLD" "$NEW")" ]
}

@test "a failing pre-update hook stops the update" {
    mkdir -p "$BYRO_ROOT/.byroctl/hooks"
    printf '#!/usr/bin/env bash\nexit 7\n' >"$BYRO_ROOT/.byroctl/hooks/pre-update.sh"
    chmod +x "$BYRO_ROOT/.byroctl/hooks/pre-update.sh"
    update --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"hook pre-update failed"* ]]
    refute grep -q "pg_dump" "$SHIM_LOG"
}

@test "self-update restores the script of the installed release and refuses a bad checksum" {
    printf '\n# local modification\n' >>"$BYRO_ROOT/byroctl"
    run byroctl --root "$BYRO_ROOT" self-update
    [ "$status" -eq 0 ]
    [[ "$output" == *"replaced with the version shipped with byro $OLD"* ]]
    refute grep -q "local modification" "$BYRO_ROOT/byroctl"
    run byroctl --root "$BYRO_ROOT" self-update
    [ "$status" -eq 0 ]
    [[ "$output" == *"already the version"* ]]
    printf '\n# tampered on the server\n' >>"$SHIM_RAW/$OLD/deploy/byroctl"
    run byroctl --root "$BYRO_ROOT" self-update
    [ "$status" -ne 0 ]
    [[ "$output" == *"checksum mismatch for byroctl"* ]]
    refute grep -q "tampered on the server" "$BYRO_ROOT/byroctl"
}

# --- plugins during an update

@test "an update rebuilds the plugin image for the new base with the pins unchanged" {
    run byroctl --root "$BYRO_ROOT" plugin add 'byro-x==1.0'
    [ "$status" -eq 0 ]
    : >"$SHIM_LOG"
    update --check
    [ "$status" -eq 0 ]
    [[ "$output" == *"plugins:        1 configured"* ]]
    refute grep -q "compose build" "$SHIM_LOG"
    : >"$SHIM_LOG"
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    grep -qxF 'byro-x==1.0' "$PLUGINS_FILE"
    seq="$(grep -oE 'docker (pull ghcr.io/byro/byro:v2026.4.0|compose pull --ignore-buildable|image inspect|buildx version|compose build web|compose stop periodic web|compose run --rm -T manage migrate|compose up -d --remove-orphans)' "$SHIM_LOG" | tr '\n' '|')"
    [ "$seq" = "docker pull ghcr.io/byro/byro:v2026.4.0|docker compose pull --ignore-buildable|docker image inspect|docker buildx version|docker compose build web|docker compose stop periodic web|docker compose run --rm -T manage migrate|docker compose up -d --remove-orphans|" ]
    local dir; dir="$(ls -d "$BYRO_ROOT"/backups/pre-update-"$OLD"-*)"
    grep -qxF 'byro-x==1.0' "$dir/plugins.txt"
    [[ "$output" == *"plugins:        byro-x==1.0"* ]]
    [[ "$output" == *"docker image rm byro-plugins:$OLD"* ]]
}

@test "--update-plugins moves catalog plugins to their current release during the update" {
    bank_files_release v1.0.0 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    run byroctl --root "$BYRO_ROOT" plugin add finance-import-bank-files
    [ "$status" -eq 0 ]
    bank_files_release v1.1.0 bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    : >"$SHIM_LOG"
    update --yes --non-interactive
    [ "$status" -eq 0 ]
    grep -qxF "$(BANK_FILES_LINE aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa v1.0.0)" "$PLUGINS_FILE"
    conf_set BYRO_DEPLOY_VERSION "$OLD"
    make_release "$NEW"
    : >"$SHIM_LOG"
    update --yes --non-interactive --update-plugins
    [ "$status" -eq 0 ]
    [[ "$output" == *"finance-import-bank-files: v1.0.0 -> v1.1.0"* ]]
    grep -qxF "$(BANK_FILES_LINE bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb v1.1.0)" "$PLUGINS_FILE"
    grep -q "curl .*$NEW/deploy/plugin-catalog.conf" "$SHIM_LOG"
    local dir; dir="$(ls -dt "$BYRO_ROOT"/backups/pre-update-"$OLD"-* | head -n1)"
    grep -qF "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" "$dir/plugins.txt"
}

@test "--update-plugins stops before any change when a release tag moved" {
    bank_files_release v1.0.0 aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
    run byroctl --root "$BYRO_ROOT" plugin add finance-import-bank-files
    [ "$status" -eq 0 ]
    bank_files_release v1.0.0 cccccccccccccccccccccccccccccccccccccccc
    before="$(cat "$PLUGINS_FILE")"; before_conf="$(cat "$CONF_FILE")"
    : >"$SHIM_LOG"
    update --yes --non-interactive --update-plugins
    [ "$status" -eq 1 ]
    [[ "$output" == *"treated as immutable"* ]]
    [[ "$output" == *"the update was not started"* ]]
    [ "$(cat "$PLUGINS_FILE")" = "$before" ]
    [ "$(cat "$CONF_FILE")" = "$before_conf" ]
    [ "$(conf_get BYRO_DEPLOY_VERSION)" = "$OLD" ]
    refute grep -qE "pg_dump|compose build|compose stop|compose up" "$SHIM_LOG"
    [ -z "$(ls -d "$BYRO_ROOT"/backups/pre-update-* 2>/dev/null)" ]
    refute grep -q "byroctl shipped with" "$BYRO_ROOT/byroctl"
    [ ! -d "$BYRO_ROOT/.byroctl/lock" ]
}

@test "a failed plugin image build during the update prints the way back and never stops the stack" {
    run byroctl --root "$BYRO_ROOT" plugin add 'byro-x==1.0'
    [ "$status" -eq 0 ]
    : >"$SHIM_LOG"
    export SHIM_FAIL="compose build"
    update --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"building the image with plugins for $NEW failed"* ]]
    [[ "$output" == *"Manual way back to byro $OLD"* ]]
    [[ "$output" == *"3b. byroctl plugin rebuild"* ]]
    refute grep -qE "compose stop|manage migrate" "$SHIM_LOG"
}

@test "--to with an invalid tag or an unknown image is refused" {
    update --to latest --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"invalid byro release tag"* ]]
    update --to v2027.1.0 --yes --non-interactive
    [ "$status" -ne 0 ]
    [[ "$output" == *"does not exist in the registry"* ]]
}
