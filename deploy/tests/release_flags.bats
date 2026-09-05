#!/usr/bin/env bats
# .github/scripts/check-release-flags.sh against small throwaway repositories.

load helpers/common

# flags BREAKING DATA_MIGRATION: write deploy/release.env
flags() {
    printf '# release flags (test)\n\nBYRO_RELEASE_BREAKING=%s\n# comment between\nBYRO_RELEASE_DATA_MIGRATION=%s\n' "$1" "$2" >deploy/release.env
}

commit() {
    git add -A
    git commit -q --allow-empty -m "$1"
}

# published_release TAG: commit the current release.env as release TAG, then one
# unrelated commit on top, so HEAD is past the release
published_release() {
    commit "prepare release $1"
    git tag "$1"
    commit "unrelated work after $1"
}

setup() {
    SCRIPT="$REPO_ROOT/.github/scripts/check-release-flags.sh"
    use_git
    REPO="$BATS_TEST_TMPDIR/repo"
    git -c init.defaultBranch=main init -q "$REPO"
    cd "$REPO"
    mkdir -p deploy
}

@test "both flags 0 pass" {
    flags 0 0
    commit "init"
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"both 0"* ]]
}

@test "a flag set before any release exists passes" {
    flags 1 0
    commit "prepare the first release"
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"no release tag reachable"* ]]
}

@test "a flag that was published and never reset fails on main" {
    flags 1 0
    published_release v2026.3.0
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"::error::release flag still 1 after v2026.3.0: BYRO_RELEASE_BREAKING"* ]]
}

@test "the same situation is only a warning with --warn-only" {
    flags 0 1
    published_release v2026.3.0
    run "$SCRIPT" --warn-only
    [ "$status" -eq 0 ]
    [[ "$output" == *"::warning::release flag still 1 after v2026.3.0: BYRO_RELEASE_DATA_MIGRATION"* ]]
}

@test "both flags stale are named together" {
    flags 1 1
    published_release v2026.3.0
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"BYRO_RELEASE_BREAKING, BYRO_RELEASE_DATA_MIGRATION"* ]]
}

@test "HEAD being the release commit itself passes" {
    flags 1 0
    commit "prepare release"
    git tag v2026.3.0
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"HEAD is the release commit v2026.3.0"* ]]
}

@test "a flag set after a release that had it at 0 passes" {
    flags 0 0
    commit "release"
    git tag v2026.3.0
    flags 1 0
    commit "prepare the next release"
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"changed since v2026.3.0"* ]]
}

@test "a flag reset and set again after the release passes" {
    flags 1 0
    commit "prepare release"
    git tag v2026.3.0
    flags 0 0
    commit "reset after release"
    flags 1 0
    commit "prepare the next release"
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"changed since v2026.3.0"* ]]
}

@test "a release tag from before release.env existed passes" {
    printf 'byro\n' >README
    commit "old release"
    git tag v2026.2.0
    flags 1 0
    commit "introduce release.env with a flag"
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"v2026.2.0 predates deploy/release.env"* ]]
}

@test "tags that are not release tags are ignored" {
    flags 1 0
    commit "prepare"
    git tag some-marker
    commit "later"
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"no release tag reachable"* ]]
}

@test "pre-release tags do not count as the latest release" {
    flags 1 0
    published_release v2026.3.0-rc1
    run "$SCRIPT"
    [ "$status" -eq 0 ]
    [[ "$output" == *"no release tag reachable"* ]]
}

@test "the script works from a subdirectory" {
    flags 0 0
    commit "init"
    cd deploy
    run "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "a value other than 0 or 1 is an error, also with --warn-only" {
    printf 'BYRO_RELEASE_BREAKING=true\nBYRO_RELEASE_DATA_MIGRATION=0\n' >deploy/release.env
    commit "typo"
    run "$SCRIPT" --warn-only
    [ "$status" -eq 1 ]
    [[ "$output" == *"::error::deploy/release.env must contain exactly one line BYRO_RELEASE_BREAKING=0 or BYRO_RELEASE_BREAKING=1 (found 0)"* ]]
    [[ "$output" == *"unexpected line in deploy/release.env: BYRO_RELEASE_BREAKING=true"* ]]
}

@test "a missing flag is an error" {
    printf 'BYRO_RELEASE_BREAKING=0\n' >deploy/release.env
    commit "missing"
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"BYRO_RELEASE_DATA_MIGRATION=0 or BYRO_RELEASE_DATA_MIGRATION=1 (found 0)"* ]]
}

@test "a duplicated flag is an error" {
    printf 'BYRO_RELEASE_BREAKING=0\nBYRO_RELEASE_BREAKING=1\nBYRO_RELEASE_DATA_MIGRATION=0\n' >deploy/release.env
    commit "duplicate"
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"(found 2)"* ]]
}

@test "an unknown key is an error" {
    printf 'BYRO_RELEASE_BREAKING=0\nBYRO_RELEASE_DATA_MIGRATION=0\nBYRO_RELEASE_FOO=1\n' >deploy/release.env
    commit "unknown"
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"unexpected line in deploy/release.env: BYRO_RELEASE_FOO=1"* ]]
}

@test "a missing file is an error" {
    printf 'x\n' >README
    commit "no release.env"
    run "$SCRIPT"
    [ "$status" -eq 1 ]
    [[ "$output" == *"deploy/release.env is missing"* ]]
}

@test "what the lint accepts is what byroctl reads" {
    flags 1 0
    load_byroctl
    [ "$(read_release_flag deploy/release.env BYRO_RELEASE_BREAKING)" = 1 ]
    [ "$(read_release_flag deploy/release.env BYRO_RELEASE_DATA_MIGRATION)" = 0 ]
}

@test "the real deploy/release.env of this repository passes the lint" {
    cd "$REPO_ROOT"
    run "$SCRIPT" --warn-only
    [ "$status" -eq 0 ]
    load_byroctl
    [ "$(read_release_flag deploy/release.env BYRO_RELEASE_BREAKING)" = 0 ]
    [ "$(read_release_flag deploy/release.env BYRO_RELEASE_DATA_MIGRATION)" = 0 ]
}
