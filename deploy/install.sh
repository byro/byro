#!/usr/bin/env bash
# byro bootstrap: fetch byroctl for the current stable release and start the
# installation.
#
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)" -- [options]
#
# The "stable" alias only serves this script and stable.env; byroctl and every
# other artefact are fetched from the immutable release tag named there and
# verified against the SHA256SUMS of the same tag. Runs as a normal user that
# may use Docker; never calls sudo itself.
#
# Options
#   --root DIR          installation directory (default /opt/byro)
#   --version TAG       install this release tag instead of the current stable one
#   --dry-run           show what would happen, change nothing
#   --no-symlink        do not link byroctl into /usr/local/bin or ~/.local/bin
#   --non-interactive   passed on to byroctl install (also skips the terminal check)
#   anything else is passed on to "byroctl install" (e.g. --set KEY=VALUE, --admin-user)
#
# Environment (all optional)
#   BYROCTL_RAW_BASE     https base for raw files (default https://raw.githubusercontent.com/byro/byro)
#   BYROCTL_STABLE_URL   https URL of stable.env (default $BYROCTL_RAW_BASE/stable/stable.env)
#   BYROCTL_STABLE_FILE  local stable.env instead of the URL (tests/development only)
#   BYROCTL_SOURCE_DIR   local deploy/ directory instead of downloads (tests/development only)

if (( BASH_VERSINFO[0] < 4 )); then
    printf 'install.sh: ERROR: bash >= 4 is required (found %s)\n' "$BASH_VERSION" >&2
    exit 1
fi

MIN_DOCKER="24.0.0"
MIN_COMPOSE="2.20.0"
IMAGE_REPO="${BYRO_DEPLOY_IMAGE_REPO:-ghcr.io/byro/byro}"
RAW_BASE="${BYROCTL_RAW_BASE:-https://raw.githubusercontent.com/byro/byro}"
STABLE_URL="${BYROCTL_STABLE_URL:-$RAW_BASE/stable/stable.env}"
STABLE_FILE="${BYROCTL_STABLE_FILE:-}"
SOURCE_DIR="${BYROCTL_SOURCE_DIR:-}"

ROOT=/opt/byro
VERSION=""
DRY_RUN=0
SYMLINK=1
NONINTERACTIVE=0
PASSTHRU=()

log() { printf 'install.sh: %s\n' "$*" >&2; }
die() { printf 'install.sh: ERROR: %s\n' "$1" >&2; exit "${2:-1}"; }

version_ge() { [[ "$(printf '%s\n%s\n' "$2" "$1" | sort -V | head -n1)" == "$2" ]]; }
require_https() { [[ "$1" == https://* ]] || die "$2 must use https:// (got: $1)"; }

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
    else shasum -a 256 "$1" | awk '{print $1}'; fi
}

fetch() { # fetch URL DEST
    curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 -o "$2" "$1" \
        || die "download failed: $1"
}

usage() {
    cat >&2 <<'USAGE'
Usage: bash -c "$(curl -fsSL https://raw.githubusercontent.com/byro/byro/stable/install.sh)" -- [options]

  --root DIR          installation directory (default /opt/byro)
  --version TAG       install this release tag instead of the current stable one
  --dry-run           show what would happen, change nothing
  --no-symlink        do not link byroctl into /usr/local/bin or ~/.local/bin
  --non-interactive   passed on to byroctl install (also skips the terminal check)
  other options       passed on to "byroctl install" (e.g. --set KEY=VALUE, --admin-user)
USAGE
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --root) [[ $# -ge 2 ]] || die "--root needs a directory" 64; ROOT="$2"; shift 2 ;;
            --root=*) ROOT="${1#--root=}"; shift ;;
            --version) [[ $# -ge 2 ]] || die "--version needs a tag" 64; VERSION="$2"; shift 2 ;;
            --version=*) VERSION="${1#--version=}"; shift ;;
            --dry-run) DRY_RUN=1; shift ;;
            --no-symlink) SYMLINK=0; shift ;;
            --non-interactive) NONINTERACTIVE=1; PASSTHRU+=("$1"); shift ;;
            -h|--help) usage; exit 0 ;;
            --) shift; PASSTHRU+=("$@"); break ;;
            *) PASSTHRU+=("$1"); shift ;;
        esac
    done
    ROOT="${ROOT%/}"
}

check_prerequisites() {
    local dv cv
    command -v curl >/dev/null 2>&1 || die "curl is required"
    command -v docker >/dev/null 2>&1 || die "docker not found. Install Docker Engine >= $MIN_DOCKER with the compose plugin first."
    dv="$(docker version --format '{{.Server.Version}}' 2>/dev/null)" \
        || die "cannot talk to the Docker daemon. Is Docker running and is your user in the docker group?"
    version_ge "${dv%%[-+]*}" "$MIN_DOCKER" || die "Docker $dv is too old, byro needs >= $MIN_DOCKER"
    cv="$(docker compose version --short 2>/dev/null)" || die "the docker compose plugin is missing (need >= $MIN_COMPOSE)"
    version_ge "${cv#v}" "$MIN_COMPOSE" || die "docker compose $cv is too old, byro needs >= $MIN_COMPOSE"
    if [[ -z "$SOURCE_DIR" ]]; then
        require_https "$RAW_BASE" "BYROCTL_RAW_BASE"
    fi
    if [[ -z "$STABLE_FILE" && -z "$VERSION" ]]; then
        require_https "$STABLE_URL" "BYROCTL_STABLE_URL"
    fi
}

# resolve_version: sets VERSION from stable.env unless given. Only a line that
# exactly matches the expected form is accepted; the file is never sourced.
resolve_version() {
    local tmp content
    if [[ -n "$VERSION" ]]; then
        [[ "$VERSION" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]] || die "invalid version tag: $VERSION"
        return 0
    fi
    if [[ -n "$STABLE_FILE" ]]; then
        content="$(cat "$STABLE_FILE")" || die "cannot read $STABLE_FILE"
    else
        tmp="$(mktemp)"
        fetch "$STABLE_URL" "$tmp"
        content="$(cat "$tmp")"; rm -f "$tmp"
    fi
    VERSION="$(grep -E '^BYRO_RELEASE_VERSION=v[0-9]+\.[0-9]+\.[0-9]+$' <<<"$content" | head -n1 | cut -d= -f2 || true)"
    [[ -n "$VERSION" ]] || die "stable.env does not name a valid release (expected BYRO_RELEASE_VERSION=vYYYY.M.P)"
    log "current stable byro release: $VERSION"
}

check_image() {
    if [[ -n "$SOURCE_DIR" ]]; then
        return 0
    fi
    docker manifest inspect "$IMAGE_REPO:$VERSION" >/dev/null 2>&1 \
        || die "the image $IMAGE_REPO:$VERSION is not available (not a published release, or no registry access)"
}

prepare_root() {
    if [[ ! -d "$ROOT" ]] && ! mkdir -p "$ROOT" 2>/dev/null; then
        log "cannot create the installation directory $ROOT."
        log "Create it once with administrator rights, hand it to your user, then run this installer again:"
        log "    sudo mkdir -p '$ROOT' && sudo chown '$(id -u):$(id -g)' '$ROOT'"
        log "    bash -c \"\$(curl -fsSL $RAW_BASE/stable/install.sh)\" -- --root '$ROOT'"
        log "Alternatively choose a directory you own: --root ~/byro"
        exit 1
    fi
    [[ -w "$ROOT" ]] || die "installation directory $ROOT is not writable by $(id -un)"
}

# install_byroctl: download byroctl and SHA256SUMS of the release, verify, then
# publish as $ROOT/byroctl. An unverified file never appears under that name.
install_byroctl() {
    local tmp_script tmp_sums expected actual
    tmp_script="$(mktemp "$ROOT/.byroctl.XXXXXX")"
    tmp_sums="$(mktemp "$ROOT/.SHA256SUMS.XXXXXX")"
    trap 'rm -f "$tmp_script" "$tmp_sums"' EXIT
    if [[ -n "$SOURCE_DIR" ]]; then
        log "using byroctl from local source $SOURCE_DIR (unverified development source)"
        cp "$SOURCE_DIR/byroctl" "$tmp_script"
    else
        fetch "$RAW_BASE/$VERSION/deploy/byroctl" "$tmp_script"
        fetch "$RAW_BASE/$VERSION/deploy/SHA256SUMS" "$tmp_sums"
        expected="$(awk '$2 == "byroctl" {print $1}' "$tmp_sums" | head -n1)"
        [[ -n "$expected" ]] || die "SHA256SUMS of $VERSION has no entry for byroctl"
        actual="$(sha256_of "$tmp_script")"
        [[ "$actual" == "$expected" ]] || die "checksum mismatch for byroctl of $VERSION (expected $expected, got $actual); refusing to install"
    fi
    bash -n "$tmp_script" || die "downloaded byroctl does not parse"
    chmod 0755 "$tmp_script"
    mv "$tmp_script" "$ROOT/byroctl"
    rm -f "$tmp_sums"
    trap - EXIT
    log "installed $ROOT/byroctl"
}

# symlink_dir: the first candidate directory we may write to.
symlink_dir() {
    local dir
    for dir in /usr/local/bin "$HOME/.local/bin"; do
        if [[ -d "$dir" && -w "$dir" ]]; then printf '%s' "$dir"; return 0; fi
    done
    if mkdir -p "$HOME/.local/bin" 2>/dev/null; then printf '%s' "$HOME/.local/bin"; return 0; fi
    return 1
}

create_symlink() {
    local dir
    (( SYMLINK )) || return 0
    if dir="$(symlink_dir)"; then
        ln -sfn "$ROOT/byroctl" "$dir/byroctl"
        log "linked $dir/byroctl -> $ROOT/byroctl"
        case ":$PATH:" in
            *":$dir:"*) ;;
            *) log "note: $dir is not in your PATH; call $ROOT/byroctl directly or add the directory to PATH" ;;
        esac
    else
        log "note: no writable bin directory found; call $ROOT/byroctl directly"
    fi
}

# reattach_terminal: when piped into bash (curl | bash) stdin is the script, so
# questions need the terminal explicitly.
reattach_terminal() {
    (( NONINTERACTIVE )) && return 0
    [[ -t 0 ]] && return 0
    # Test the terminal in a subshell first: a failing redirection on exec would
    # otherwise terminate the script without a helpful message.
    if [[ -r /dev/tty && -w /dev/tty ]] && ( exec </dev/tty ) 2>/dev/null; then
        exec </dev/tty
        return 0
    fi
    die "no terminal available for the installation questions. Run with --non-interactive and --set KEY=VALUE, or use: bash -c \"\$(curl -fsSL $RAW_BASE/stable/install.sh)\""
}

main() {
    set -euo pipefail
    parse_args "$@"
    check_prerequisites
    resolve_version
    check_image
    if (( DRY_RUN )); then
        log "dry run - would install byro $VERSION into $ROOT"
        log "  1. create $ROOT (or ask you to create it with sudo)"
        log "  2. download $RAW_BASE/$VERSION/deploy/byroctl and verify it against SHA256SUMS of $VERSION"
        (( SYMLINK )) && log "  3. link byroctl into /usr/local/bin or ~/.local/bin"
        log "  4. run: byroctl --root $ROOT install --version $VERSION ${PASSTHRU[*]:-}"
        return 0
    fi
    prepare_root
    install_byroctl
    create_symlink
    reattach_terminal
    exec "$ROOT/byroctl" --root "$ROOT" install --version "$VERSION" "${PASSTHRU[@]}"
}

# Run unless sourced (tests). When piped into bash or run via bash -c,
# BASH_SOURCE[0] is empty, and the installer must run.
if [[ -z "${BASH_SOURCE[0]:-}" || "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
