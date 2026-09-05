#!/usr/bin/env bats
# deploy/install.sh (bootstrap) against the docker/curl shims.

load helpers/common

setup() {
    make_root
    use_shims
    export HOME="$BATS_TEST_TMPDIR/home"; mkdir -p "$HOME"
    export SHIM_TAGS="ghcr.io/byro/byro:v2026.3.0"
    export SHIM_LOCAL_IMAGES="ghcr.io/byro/byro:v2026.3.0"
    export SHIM_DIGESTS="ghcr.io/byro/byro:v2026.3.0 ghcr.io/byro/byro@sha256:1111111111111111111111111111111111111111111111111111111111111111"
    export BYROCTL_RAW_BASE="https://example.test"
    export SHIM_RAW="$BATS_TEST_TMPDIR/raw"
    # a fake release tag on the "raw" server: deploy/ of the repository + correct checksums
    mkdir -p "$SHIM_RAW/v2026.3.0/deploy/compose" "$SHIM_RAW/stable"
    for f in byroctl docker-compose.yml compose/postgres.yml compose/caddy.yml Caddyfile byro.conf.example release.env; do
        cp "$DEPLOY_DIR/$f" "$SHIM_RAW/v2026.3.0/deploy/$f"
    done
    ( cd "$SHIM_RAW/v2026.3.0/deploy" && sha256sum byroctl docker-compose.yml compose/postgres.yml compose/caddy.yml Caddyfile byro.conf.example release.env >SHA256SUMS )
    printf 'BYRO_RELEASE_VERSION=v2026.3.0\n' >"$SHIM_RAW/stable/stable.env"
    export BYROCTL_ADMIN_PASSWORD="Admin-Passw0rd"
    unset BYROCTL_SOURCE_DIR BYROCTL_STABLE_FILE
    INSTALL_ROOT="$BYRO_ROOT/byro"
}

install_sh() { "$DEPLOY_DIR/install.sh" "$@"; }

@test "help prints usage and exits 0" {
    run install_sh --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--dry-run"* ]]
}

@test "missing docker is reported" {
    PATH="$(dirname "$(command -v bash)"):/usr/bin:/bin" run install_sh --dry-run
    [ "$status" -ne 0 ]
    [[ "$output" == *"docker not found"* ]] || [[ "$output" == *"curl is required"* ]]
}

@test "dry run resolves the stable version, checks the image and writes nothing" {
    run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"current stable byro release: v2026.3.0"* ]]
    [[ "$output" == *"would install byro v2026.3.0 into $INSTALL_ROOT"* ]]
    grep -q "curl .*--proto =https .*/stable/stable.env" "$SHIM_LOG"
    grep -q "docker manifest inspect ghcr.io/byro/byro:v2026.3.0" "$SHIM_LOG"
    [ ! -e "$INSTALL_ROOT" ]
}

@test "stable.env is parsed strictly and never executed" {
    printf '%s\n' 'echo pwned > /tmp/install-sh-pwned' '$(touch /tmp/install-sh-pwned2)' 'BYRO_RELEASE_VERSION=v2026.3.0' 'BYRO_RELEASE_VERSION=v9.9.9' >"$SHIM_RAW/stable/stable.env"
    run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"current stable byro release: v2026.3.0"* ]]
    [ ! -e /tmp/install-sh-pwned ] && [ ! -e /tmp/install-sh-pwned2 ]
    printf 'BYRO_RELEASE_VERSION=latest\n' >"$SHIM_RAW/stable/stable.env"
    run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -ne 0 ]
    [[ "$output" == *"does not name a valid release"* ]]
    : >"$SHIM_RAW/stable/stable.env"
    run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -ne 0 ]
}

@test "BYROCTL_STABLE_FILE replaces the download in tests" {
    printf 'BYRO_RELEASE_VERSION=v2026.3.0\n' >"$BATS_TEST_TMPDIR/stable.env"
    BYROCTL_STABLE_FILE="$BATS_TEST_TMPDIR/stable.env" run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -eq 0 ]
    ! grep -q "stable.env" "$SHIM_LOG"
}

@test "a missing image stops the installer before anything is written" {
    export SHIM_TAGS=""
    run install_sh --root "$INSTALL_ROOT" --non-interactive --no-symlink
    [ "$status" -ne 0 ]
    [[ "$output" == *"is not available"* ]]
    [ ! -e "$INSTALL_ROOT" ]
}

@test "insecure base URLs are refused" {
    BYROCTL_RAW_BASE="http://example.test" run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -ne 0 ]
    [[ "$output" == *"must use https://"* ]]
    BYROCTL_STABLE_URL="http://example.test/stable.env" run install_sh --root "$INSTALL_ROOT" --dry-run
    [ "$status" -ne 0 ]
}

@test "a checksum mismatch aborts and leaves no byroctl behind" {
    echo "# tampered" >>"$SHIM_RAW/v2026.3.0/deploy/byroctl"
    run install_sh --root "$INSTALL_ROOT" --non-interactive --no-symlink
    [ "$status" -ne 0 ]
    [[ "$output" == *"checksum mismatch for byroctl"* ]]
    [ ! -e "$INSTALL_ROOT/byroctl" ]
    [ -z "$(ls -A "$INSTALL_ROOT" 2>/dev/null)" ]
}

@test "the full bootstrap installs byroctl, links it and runs the installation" {
    run install_sh --root "$INSTALL_ROOT" --non-interactive --no-symlink \
        --admin-user admin --admin-email admin@example.org \
        --set BYRO_SITE_URL=https://byro.example.org --set BYROCTL_PROXY=none --set BYRO_DEPLOY_PORT=18997
    [ "$status" -eq 0 ]
    [ -x "$INSTALL_ROOT/byroctl" ]
    [ "$(sha256sum <"$INSTALL_ROOT/byroctl")" = "$(sha256sum <"$DEPLOY_DIR/byroctl")" ]
    [ -f "$INSTALL_ROOT/byro.conf" ]
    grep -q '^BYRO_DEPLOY_VERSION=v2026.3.0$' "$INSTALL_ROOT/byro.conf"
    [[ "$output" == *"is installed and running"* ]]
    # byroctl fetched its artefacts from the same tag and verified them
    grep -q "curl .*v2026.3.0/deploy/SHA256SUMS" "$SHIM_LOG"
    grep -q "curl .*v2026.3.0/deploy/compose/postgres.yml" "$SHIM_LOG"
    [ ! -e "$INSTALL_ROOT/.byroctl/lock" ]
}

@test "--no-symlink is honoured; otherwise a bin directory is chosen" {
    # shellcheck disable=SC1091
    source "$DEPLOY_DIR/install.sh"
    if [[ -w /usr/local/bin ]]; then
        [ "$(symlink_dir)" = "/usr/local/bin" ]
    else
        [ "$(symlink_dir)" = "$HOME/.local/bin" ]
        [ -d "$HOME/.local/bin" ]
    fi
}

@test "without a terminal and without --non-interactive the bootstrap stops with a hint" {
    run install_sh --root "$INSTALL_ROOT" --no-symlink </dev/null
    [ "$status" -ne 0 ]
    [[ "$output" == *"no terminal"* ]] || [[ "$output" == *"--non-interactive"* ]]
}

@test "an unwritable root prints the sudo hint including the re-run command" {
    if [ "$(id -u)" -eq 0 ]; then skip "root can always write"; fi
    mkdir -p "$BATS_TEST_TMPDIR/ro"; chmod 555 "$BATS_TEST_TMPDIR/ro"
    run install_sh --root "$BATS_TEST_TMPDIR/ro/byro" --non-interactive --no-symlink
    chmod 755 "$BATS_TEST_TMPDIR/ro"
    [ "$status" -ne 0 ]
    [[ "$output" == *"sudo mkdir -p"* ]]
    [[ "$output" == *"install.sh"* ]]
}

@test "the installer also runs when piped into bash or passed to bash -c" {
    run bash -c "$(cat "$DEPLOY_DIR/install.sh")" -- --root "$INSTALL_ROOT" --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"would install byro v2026.3.0"* ]]
    run bash -s -- --root "$INSTALL_ROOT" --dry-run <"$DEPLOY_DIR/install.sh"
    [ "$status" -eq 0 ]
    [[ "$output" == *"would install byro v2026.3.0"* ]]
    run bash -c "$(cat "$DEPLOY_DIR/install.sh")" -- --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--dry-run"* ]]
}
