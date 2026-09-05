#!/usr/bin/env bash
# Lint deploy/release.env and detect a release flag that stayed at 1 after the
# release that needed it was published.
#
#   .github/scripts/check-release-flags.sh [--warn-only]
#
# release.env carries two flags that byroctl reads before an update
# (BYRO_RELEASE_BREAKING, BYRO_RELEASE_DATA_MIGRATION). Their process: both are
# 0 on main; a flag is set to 1 in the pull request that prepares the release
# needing it, and reset to 0 right after that release was published. This
# script enforces two things:
#
#   1. Lint, always an error: each flag appears exactly once with the value 0 or
#      1, and the file contains nothing else besides comments and blank lines.
#      byroctl reads anything else as 0, so a typo such as "=true" would
#      silently switch a flag off.
#   2. Stale flag: a flag that is still 1 although the latest release tag
#      reachable from HEAD already shipped with it, and deploy/release.env has
#      not changed since. On main this is an error; with --warn-only (pull
#      requests) it is a warning. A flag is not stale when there is no release
#      tag yet, when HEAD is the release commit itself, when the tag predates
#      release.env, or when release.env changed after the tag (it was reset
#      and/or set again for the next release).
#
# Needs the full history and the tags (actions/checkout with fetch-depth: 0),
# and runs against the repository that contains the current directory.

FILE="deploy/release.env"
FLAGS="BYRO_RELEASE_BREAKING BYRO_RELEASE_DATA_MIGRATION"
WARN_ONLY=0

log() { printf '%s\n' "$*" >&2; }
die() { printf '::error::%s\n' "$*"; exit 1; }

lint() {
    local errors=0 flag count line ok
    for flag in $FLAGS; do
        count="$(grep -cE "^$flag=(0|1)$" "$FILE" || true)"
        if [[ "$count" != "1" ]]; then
            printf '::error::%s must contain exactly one line %s=0 or %s=1 (found %s)\n' "$FILE" "$flag" "$flag" "$count"
            grep -nE "^$flag=" "$FILE" >&2 || true
            errors=1
        fi
    done
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ -z "$line" || "$line" == \#* ]]; then
            continue
        fi
        ok=0
        for flag in $FLAGS; do
            if [[ "$line" == "$flag=0" || "$line" == "$flag=1" ]]; then ok=1; fi
        done
        if (( ! ok )); then
            printf '::error::unexpected line in %s: %s\n' "$FILE" "$line"
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
    lint || die "$FILE is malformed (see above)"

    local set_flags="" flag
    for flag in $FLAGS; do
        if grep -qxF "$flag=1" "$FILE"; then
            set_flags="${set_flags:+$set_flags, }$flag"
        fi
    done
    if [[ -z "$set_flags" ]]; then
        log "release flags: both 0"
        exit 0
    fi

    local tag
    tag="$(git describe --tags --abbrev=0 --match 'v[0-9]*' HEAD 2>/dev/null || true)"
    if [[ -z "$tag" ]]; then
        log "release flags: $set_flags set; no release tag reachable from HEAD, nothing to compare"
        exit 0
    fi
    if [[ "$(git rev-parse "$tag^{commit}")" == "$(git rev-parse HEAD)" ]]; then
        log "release flags: $set_flags set; HEAD is the release commit $tag itself"
        exit 0
    fi
    if ! git cat-file -e "$tag:$FILE" 2>/dev/null; then
        log "release flags: $set_flags set; $tag predates $FILE"
        exit 0
    fi
    if [[ -n "$(git log --oneline "$tag..HEAD" -- "$FILE")" ]]; then
        log "release flags: $set_flags set; $FILE changed since $tag"
        exit 0
    fi

    local message
    message="release flag still 1 after $tag: $set_flags. It was published with $tag and $FILE has not changed since; reset it to 0 on main (see docs/developer/releasing.rst)."
    if (( WARN_ONLY )); then
        printf '::warning::%s\n' "$message"
        exit 0
    fi
    printf '::error::%s\n' "$message"
    exit 1
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
