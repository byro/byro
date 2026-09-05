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
# anything else as 0). Stale flag: 1 at HEAD although the latest release tag
# reachable from HEAD already shipped with it and the file has not changed
# since; an error, or a warning with --warn-only (pull requests). Process and
# rationale: docs/developer/releasing.rst.
#
# Needs the full history and the tags (actions/checkout with fetch-depth: 0),
# and runs against the repository that contains the current directory.

FILE="deploy/release.env"
FLAGS="BYRO_RELEASE_BREAKING BYRO_RELEASE_DATA_MIGRATION"
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

main() {
    set -euo pipefail
    case "${1:-}" in
        "") ;;
        --warn-only) WARN_ONLY=1 ;;
        *) log "usage: $0 [--warn-only]"; exit 64 ;;
    esac
    cd "$(git rev-parse --show-toplevel)" || die "run this inside a checkout of the byro repository"
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

    # the latest release tag reachable from HEAD; pre-release tags (v…-rc1) do not count
    local tag
    tag="$(git describe --tags --abbrev=0 --match 'v[0-9]*' --exclude '*-*' HEAD 2>/dev/null || true)"
    [[ -n "$tag" ]] || ok "no release tag reachable from HEAD, nothing to compare"
    [[ "$(git rev-parse "$tag^{commit}")" != "$(git rev-parse HEAD)" ]] || ok "HEAD is the release commit $tag itself"
    git cat-file -e "$tag:$FILE" 2>/dev/null || ok "$tag predates $FILE"
    [[ -z "$(git rev-list -n1 "$tag..HEAD" -- "$FILE")" ]] || ok "$FILE changed since $tag"

    local message="release flag still 1 after $tag: $SET_FLAGS. It was published with $tag and $FILE has not changed since; reset it to 0 on main (see docs/developer/releasing.rst)."
    if (( WARN_ONLY )); then
        warn "$message"
        exit 0
    fi
    die "$message"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
