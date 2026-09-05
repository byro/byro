#!/usr/bin/env bash
# Lint deploy/release.env and detect a release flag that stayed at 1 after the
# release that needed it was published.
#
#   .github/scripts/check-release-flags.sh [--warn-only]
#
# The two flags (BYRO_RELEASE_BREAKING, BYRO_RELEASE_DATA_MIGRATION) are 0 on
# main, set to 1 in the pull request that prepares a release, and reset to 0
# right after that release. Lint, always an error: each flag exactly once with
# the value 0 or 1, nothing else besides comments and blank lines (byroctl reads
# anything else as 0). Stale flag: a flag at 1 whose line has not changed since
# the latest release, although that release already shipped it at 1; an error,
# or a warning with --warn-only (pull requests). The latest release is the
# highest vYYYY.M.P tag reachable from HEAD. Process and rationale:
# docs/developer/releasing.rst.
#
# Needs the full history and the tags (actions/checkout with fetch-depth: 0),
# refuses shallow checkouts, and runs against the repository that contains the
# current directory.

FILE="deploy/release.env"
FLAGS="BYRO_RELEASE_BREAKING BYRO_RELEASE_DATA_MIGRATION"
RELEASE_TAG='^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
WARN_ONLY=0
SET_FLAGS=""   # the flags at 1, comma separated

# Output: progress on stderr; results as GitHub Actions annotations on stdout
# (harmless prefixes outside Actions).
log() { printf '%s\n' "$*" >&2; }
die() { printf '::error::%s\n' "$*"; exit 1; }
warn() { printf '::warning::%s\n' "$*"; }
error() { printf '::error::%s\n' "$*"; }
ok() { log "release flags: $SET_FLAGS set; $*"; exit 0; }

lint() {
    local errors=0 flag count line
    for flag in $FLAGS; do
        count="$(grep -cE "^$flag=(0|1)$" "$FILE" || true)"
        if [[ "$count" != "1" ]]; then
            error "$FILE must contain exactly one line $flag=0 or $flag=1 (found $count)"
            grep -nE "^$flag=" "$FILE" >&2 || true
            errors=1
        fi
    done
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -n "$line" && "$line" != \#* && ! "$line" =~ ^(${FLAGS// /|})=[01]$ ]]; then
            error "unexpected line in $FILE: $line"
            errors=1
        fi
    done <"$FILE"
    return "$errors"
}

# latest_release_tag: the highest release tag reachable from HEAD, compared
# numerically per field; tags of any other shape are not releases.
latest_release_tag() {
    local version
    version="$(git tag --merged HEAD | grep -E "$RELEASE_TAG" | sed 's/^v//' | sort -t. -k1,1n -k2,2n -k3,3n | tail -n1 || true)"
    [[ -z "$version" ]] || printf 'v%s' "$version"
}

main() {
    set -euo pipefail
    case "${1:-}" in
        "") ;;
        --warn-only) WARN_ONLY=1 ;;
        *) log "usage: $0 [--warn-only]"; exit 64 ;;
    esac
    local top
    top="$(git rev-parse --show-toplevel 2>/dev/null)" || die "run this inside a checkout of the byro repository"
    cd "$top"
    [[ "$(git rev-parse --is-shallow-repository)" != "true" ]] \
        || die "shallow checkout: the stale flag check needs the full history and the tags (actions/checkout with fetch-depth: 0)"
    [[ -f "$FILE" ]] || die "$FILE is missing"
    lint || exit 1

    local flag
    for flag in $FLAGS; do
        if grep -qxF "$flag=1" "$FILE"; then
            SET_FLAGS="${SET_FLAGS:+$SET_FLAGS, }$flag"
        fi
    done
    if [[ -z "$SET_FLAGS" ]]; then
        log "release flags: both 0"
        exit 0
    fi

    local tag
    tag="$(latest_release_tag)"
    [[ -n "$tag" ]] || ok "no release tag reachable from HEAD, nothing to compare"
    [[ "$(git rev-parse "$tag^{commit}")" != "$(git rev-parse HEAD)" ]] || ok "HEAD is the release commit $tag itself"
    git cat-file -e "$tag:$FILE" 2>/dev/null || ok "$tag predates $FILE"

    # a flag is stale when the latest release shipped it at 1 and no commit since
    # then touched that flag's line (neither a reset nor a reset and a new setting)
    local stale="" shipped
    for flag in $FLAGS; do
        grep -qxF "$flag=1" "$FILE" || continue
        shipped="$(git show "$tag:$FILE" | grep -E "^$flag=(0|1)$" | cut -d= -f2 || true)"
        [[ "$shipped" == "1" ]] || continue
        [[ -z "$(git log -n1 --format=%H -G "^$flag=" "$tag..HEAD" -- "$FILE")" ]] || continue
        stale="${stale:+$stale, }$flag"
    done
    [[ -n "$stale" ]] || ok "every flag at 1 was set or changed after $tag"

    local message="release flag still 1 after $tag: $stale. It was published with $tag and not changed since; reset it to 0 on main (see docs/developer/releasing.rst)."
    if (( WARN_ONLY )); then
        warn "$message"
        exit 0
    fi
    die "$message"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
